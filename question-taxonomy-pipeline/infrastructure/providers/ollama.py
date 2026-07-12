"""
Ollama provider adapter for local LLM inference.

Supports structured outputs via JSON schema constraints and provides
token usage tracking. Cost tracking defaults to $0.00 for local inference.
"""

import logging
from collections.abc import Sequence
from typing import Any

import httpx
from opik import opik_context

from application.dto.question_labeling import BatchLabels
from infrastructure import Provider, ProviderAdapter, RunConfig
from infrastructure.providers.registry import register_adapter

logger = logging.getLogger(__name__)


class OllamaAdapter(ProviderAdapter):
    """
    Ollama backend using Ollama's native Chat API: POST /api/chat

    - Uses JSON schema constrained output via `format` (json schema object)
    - Token usage comes from `prompt_eval_count` and `eval_count`
    - Cost is treated as $0.00 by default (local inference)
    """

    supports_structured_outputs: bool = True
    supports_prompt_caching: bool = False
    supports_token_usage: bool = True

    @classmethod
    def from_cfg(cls, cfg: RunConfig) -> "OllamaAdapter":
        """
        Create OllamaAdapter from configuration.

        Args:
            cfg: RunConfig instance with Ollama settings

        Returns:
            Configured OllamaAdapter instance

        Raises:
            ValueError: If Ollama configuration is missing
        """
        if cfg.ollama is None:
            raise ValueError(
                "Ollama provider selected but ollama configuration is missing. Add 'ollama:' section to experiment.yaml"
            )
        base_url = cfg.ollama.base_url.rstrip("/")
        client = httpx.Client(
            base_url=base_url,
            timeout=cfg.ollama.timeout_s,
            headers={"Content-Type": "application/json"},
        )
        # No per-token pricing for local by default
        return cls(cfg=cfg, client=client, pricing=None)

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
        """
        Call Ollama API with structured output via JSON schema.

        Args:
            system_text: System prompt text
            user_text: User prompt text (formatted with questions)
            response_model: Pydantic model for structured output
            batch_id: Batch identifier for logging
            questions: List of questions in this batch (optional, for validation)
            extra_trace_meta: Optional extra metadata for tracing/logging

        Returns:
            Tuple of (parsed BatchLabels model, metadata dict with tokens/costs)

        Raises:
            ValueError: If configuration is missing or response parsing fails
        """
        provider_cfg = self.cfg.ollama
        if provider_cfg is None:
            raise ValueError("OllamaAdapter requires cfg.ollama")

        # Ollama supports format as either "json" or a JSON schema object
        schema_obj = response_model.model_json_schema()

        # Ollama "options" are optional; only send non-None values
        options: dict[str, Any] = {}
        for k in ("temperature", "seed", "num_ctx", "top_p", "top_k", "num_predict"):
            v = getattr(provider_cfg, k, None)
            if v is not None:
                options[k] = v

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "stream": False,
            "format": schema_obj,
        }

        if options:
            payload["options"] = options
        if provider_cfg.keep_alive is not None:
            payload["keep_alive"] = provider_cfg.keep_alive
        if provider_cfg.think is not None:
            payload["think"] = provider_cfg.think

        resp = self.client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        raw_text = ((data.get("message") or {}).get("content")) or ""
        try:
            parsed = response_model.model_validate_json(raw_text)
        except Exception as e:
            raise ValueError(
                f"Failed to parse Ollama response as {response_model.__name__}. Raw text:\n{raw_text}"
            ) from e

        self._validate_indices(parsed=parsed, questions=questions, batch_id=batch_id)

        input_tokens = int(data.get("prompt_eval_count", 0) or 0)
        output_tokens = int(data.get("eval_count", 0) or 0)
        total_tokens = int(input_tokens + output_tokens)

        # Keep the same meta keys the pipeline expects
        result: dict[str, Any] = {
            "provider": self.provider.value,
            "model": self.model,
            "batch_id": batch_id,
            "raw_text": raw_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            # Local inference: default $0.00
            "batch_input_cost": 0.0,
            "batch_output_cost": 0.0,
            "batch_total_cost": 0.0,
            "batch_output_payload": None,
        }

        meta = {
            "batch_id": batch_id,
            "base_url": provider_cfg.base_url,
            "keep_alive": provider_cfg.keep_alive,
            "think": provider_cfg.think,
            "ollama_options": options,
            "batch_total_cost_usd": 0.0,
        }
        if extra_trace_meta:
            meta.update(extra_trace_meta)

        # Match the existing Opik conventions (OpenAI-style usage keys)
        opik_context.update_current_span(
            provider=self.provider.value,
            model=self.model,
            usage=self._opik_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            total_cost=0.0,
            metadata=meta,
        )

        logger.info(
            "Batch %d: Ollama - total_tokens=%d (in=%d, out=%d), cost=$%.6f",
            batch_id,
            total_tokens,
            input_tokens,
            output_tokens,
            0.0,
        )

        return parsed, result


register_adapter(Provider.OLLAMA, OllamaAdapter)
