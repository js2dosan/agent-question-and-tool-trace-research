"""Google Gemini provider adapter."""

import json
import logging
import os
import time
from collections.abc import Sequence
from typing import Any

from google import genai
from google.genai import errors
from google.genai import types
from opik import opik_context

from application.dto.question_labeling import BatchLabels
from infrastructure.config.models import Provider, RunConfig

from .base import ProviderAdapter
from .registry import register_adapter

logger = logging.getLogger(__name__)

_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiAdapter(ProviderAdapter):
    """Adapter for Google Gemini API using structured JSON output."""

    @classmethod
    def from_cfg(cls, cfg: RunConfig) -> "GeminiAdapter":
        if cfg.gemini is None:
            raise ValueError("Provider=gemini but cfg.gemini is missing")

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env.")

        client = genai.Client(api_key=api_key)
        return cls(cfg=cfg, client=client, pricing=cfg.provider_model.pricing or None)

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
        provider_cfg = self.cfg.gemini
        if provider_cfg is None:
            raise ValueError("GeminiAdapter requires cfg.gemini")

        config = types.GenerateContentConfig(
            system_instruction=system_text,
            temperature=provider_cfg.temperature,
            top_p=provider_cfg.top_p,
            top_k=provider_cfg.top_k,
            max_output_tokens=provider_cfg.max_output_tokens,
            seed=provider_cfg.seed,
            response_mime_type="application/json",
            response_schema=response_model,
        )

        response = self._generate_content_with_retry(
            user_text=user_text,
            config=config,
            batch_id=batch_id,
        )

        parsed_obj = getattr(response, "parsed", None)
        if isinstance(parsed_obj, response_model):
            parsed = parsed_obj
        elif parsed_obj is not None:
            parsed = response_model.model_validate(parsed_obj)
        else:
            raw_text = getattr(response, "text", "") or ""
            try:
                parsed = response_model.model_validate_json(raw_text)
            except Exception as e:
                try:
                    parsed = response_model.model_validate(json.loads(raw_text))
                except Exception:
                    raise ValueError(
                        f"Failed to parse Gemini response as {response_model.__name__}. Raw text:\n{raw_text}"
                    ) from e

        self._validate_indices(parsed=parsed, questions=questions, batch_id=batch_id)

        usage = getattr(response, "usage_metadata", None)
        input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_tokens = int(getattr(usage, "total_token_count", input_tokens + output_tokens) or 0)

        input_cost = 0.0
        output_cost = 0.0
        total_cost = 0.0
        if self.pricing:
            input_per_1m = float(self.pricing.get("input_per_1m", 0.0) or 0.0)
            output_per_1m = float(self.pricing.get("output_per_1m", 0.0) or 0.0)
            input_cost = input_tokens * input_per_1m / 1_000_000
            output_cost = output_tokens * output_per_1m / 1_000_000
            total_cost = input_cost + output_cost

        result = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cache_meta": {},
            "batch_input_cost": input_cost,
            "batch_output_cost": output_cost,
            "batch_total_cost": total_cost,
            "batch_output_payload": parsed.model_dump(),
        }

        meta = {
            "batch_id": batch_id,
            "temperature": provider_cfg.temperature,
            "top_p": provider_cfg.top_p,
            "top_k": provider_cfg.top_k,
            "max_output_tokens": provider_cfg.max_output_tokens,
            "batch_input_cost_usd": round(input_cost, 6),
            "batch_output_cost_usd": round(output_cost, 6),
            "batch_total_cost_usd": round(total_cost, 6),
        }
        if extra_trace_meta:
            meta.update(extra_trace_meta)

        opik_context.update_current_span(
            provider=self.provider.value,
            model=self.model,
            usage=self._opik_usage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens),
            total_cost=float(total_cost),
            metadata=meta,
        )

        logger.info(
            "Batch %d: Gemini - total_tokens=%d, cost=$%.6f",
            batch_id,
            total_tokens,
            total_cost,
        )

        return parsed, result

    def _generate_content_with_retry(
        self,
        *,
        user_text: str,
        config: types.GenerateContentConfig,
        batch_id: int,
    ) -> Any:
        max_attempts = 6
        delay_s = 30.0

        for attempt in range(1, max_attempts + 1):
            try:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=user_text,
                    config=config,
                )
            except errors.APIError as e:
                status_code = int(getattr(e, "code", 0) or getattr(e, "status_code", 0) or 0)
                if status_code not in _TRANSIENT_STATUS_CODES or attempt >= max_attempts:
                    raise

                logger.warning(
                    "Batch %d: Gemini transient API error %s on attempt %d/%d. Retrying in %.0fs.",
                    batch_id,
                    status_code,
                    attempt,
                    max_attempts,
                    delay_s,
                )
                time.sleep(delay_s)
                delay_s = min(delay_s * 2, 300.0)


register_adapter(Provider.GEMINI, GeminiAdapter)
