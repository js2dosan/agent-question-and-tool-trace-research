"""NVIDIA chat-completions provider adapter."""

import json
import logging
import os
import re
import time
from collections.abc import Sequence
from typing import Any

import requests
from opik import opik_context

from application.dto.question_labeling import BatchLabels
from infrastructure.config.models import Provider, RunConfig

from .base import ProviderAdapter
from .registry import register_adapter

logger = logging.getLogger(__name__)

_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class NvidiaAdapter(ProviderAdapter):
    """Adapter for NVIDIA hosted OpenAI-compatible chat completions."""

    @classmethod
    def from_cfg(cls, cfg: RunConfig) -> "NvidiaAdapter":
        if cfg.nvidia is None:
            raise ValueError("Provider=nvidia but cfg.nvidia is missing")

        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("Missing NVIDIA API key. Set NVIDIA_API_KEY in .env.")

        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        return cls(cfg=cfg, client=session, pricing=cfg.provider_model.pricing or None)

    def call_batch(
        self,
        *,
        system_text: str,
        user_text: str,
        response_model: type[BatchLabels],
        batch_id: int,
        questions: Sequence[str] | None = None,
        extra_trace_meta: dict[str, Any] | None = None,
    ) -> tuple[BatchLabels, dict[str, Any]]:
        provider_cfg = self.cfg.nvidia
        if provider_cfg is None:
            raise ValueError("NvidiaAdapter requires cfg.nvidia")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        system_text
                        + "\n\nReturn only one valid JSON object matching the requested schema. "
                        + "Do not include markdown fences, commentary, or extra text."
                    ),
                },
                {"role": "user", "content": user_text},
            ],
            "max_tokens": provider_cfg.max_tokens,
            "temperature": provider_cfg.temperature,
            "top_p": provider_cfg.top_p,
            "frequency_penalty": provider_cfg.frequency_penalty,
            "presence_penalty": provider_cfg.presence_penalty,
            "stream": False,
        }

        data = self._post_with_retry(payload=payload, batch_id=batch_id)
        raw_text = self._extract_response_text(data=data, batch_id=batch_id)
        parsed = self._parse_response(raw_text=raw_text, response_model=response_model, batch_id=batch_id)
        self._validate_indices(parsed=parsed, questions=questions, batch_id=batch_id)

        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or 0)

        result = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cache_meta": {},
            "batch_input_cost": 0.0,
            "batch_output_cost": 0.0,
            "batch_total_cost": 0.0,
            "batch_output_payload": parsed.model_dump(),
        }

        meta = {
            "batch_id": batch_id,
            "invoke_url": provider_cfg.invoke_url,
            "temperature": provider_cfg.temperature,
            "top_p": provider_cfg.top_p,
            "max_tokens": provider_cfg.max_tokens,
            "usage_raw": usage,
        }
        if extra_trace_meta:
            meta.update(extra_trace_meta)

        opik_context.update_current_span(
            provider=self.provider.value,
            model=self.model,
            usage=self._opik_usage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens),
            total_cost=0.0,
            metadata=meta,
        )

        logger.info(
            "Batch %d: NVIDIA - total_tokens=%d",
            batch_id,
            total_tokens,
        )

        return parsed, result

    def _post_with_retry(self, *, payload: dict[str, Any], batch_id: int) -> dict[str, Any]:
        provider_cfg = self.cfg.nvidia
        if provider_cfg is None:
            raise ValueError("NvidiaAdapter requires cfg.nvidia")

        delay_s = provider_cfg.retry_initial_delay_s
        for attempt in range(1, provider_cfg.retry_attempts + 1):
            try:
                response = self.client.post(
                    provider_cfg.invoke_url,
                    json=payload,
                    timeout=provider_cfg.timeout_s,
                )
            except requests.RequestException as e:
                if attempt >= provider_cfg.retry_attempts:
                    raise RuntimeError(f"NVIDIA API request failed after timeout/network retries: {e}") from e

                logger.warning(
                    "Batch %d: NVIDIA network error on attempt %d/%d: %s. Retrying in %.0fs.",
                    batch_id,
                    attempt,
                    provider_cfg.retry_attempts,
                    e,
                    delay_s,
                )
                time.sleep(delay_s)
                delay_s = min(delay_s * 2, 300.0)
                continue
            if response.status_code < 400:
                return response.json()

            if response.status_code not in _TRANSIENT_STATUS_CODES or attempt >= provider_cfg.retry_attempts:
                raise RuntimeError(
                    f"NVIDIA API request failed with status {response.status_code}: {response.text[:2000]}"
                )

            logger.warning(
                "Batch %d: NVIDIA transient API error %s on attempt %d/%d. Retrying in %.0fs.",
                batch_id,
                response.status_code,
                attempt,
                provider_cfg.retry_attempts,
                delay_s,
            )
            time.sleep(delay_s)
            delay_s = min(delay_s * 2, 300.0)

        raise RuntimeError("NVIDIA API retry loop ended unexpectedly.")

    def _extract_response_text(self, *, data: dict[str, Any], batch_id: int) -> str:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Batch {batch_id}: NVIDIA response did not contain choices[0].message: {data}") from e

        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

        reasoning = message.get("reasoning")
        reasoning_len = len(reasoning) if isinstance(reasoning, str) else 0
        finish_reason = data.get("choices", [{}])[0].get("finish_reason")
        usage = data.get("usage") or {}
        keys = sorted(message.keys())
        raise ValueError(
            "Batch "
            f"{batch_id}: NVIDIA response message.content was empty. "
            f"message_keys={keys}, finish_reason={finish_reason!r}, "
            f"reasoning_present={reasoning_len > 0}, reasoning_chars={reasoning_len}, usage={usage}. "
            "This usually means the model spent its output budget on hidden/visible reasoning instead of final JSON. "
            "Use a smaller batch size, a shorter prompt, or a different model."
        )

    def _parse_response(
        self,
        *,
        raw_text: str,
        response_model: type[BatchLabels],
        batch_id: int,
    ) -> BatchLabels:
        try:
            return response_model.model_validate_json(raw_text)
        except Exception:
            pass

        cleaned = raw_text.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]

        try:
            return response_model.model_validate(json.loads(cleaned))
        except Exception as e:
            raise ValueError(
                f"Batch {batch_id}: Failed to parse NVIDIA response as {response_model.__name__}. Raw text:\n{raw_text}"
            ) from e


register_adapter(Provider.NVIDIA, NvidiaAdapter)
