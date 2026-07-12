"""Mock provider adapter for testing."""

import logging
from collections.abc import Sequence
from random import random
from typing import Any, Literal

from opik import opik_context

from application.dto.question_labeling import BatchLabels, QuestionLabel
from infrastructure.config.models import RunConfig
from infrastructure.providers.base import ProviderAdapter

logger = logging.getLogger(__name__)


class MockAdapter(ProviderAdapter):
    """Mock adapter for testing without real API calls."""

    supports_structured_outputs: bool = True
    supports_prompt_caching: bool = False
    supports_token_usage: bool = True

    def __init__(
        self,
        *,
        cfg: RunConfig,
        fixtures: dict[int, dict[str, Any]] | None = None,
        default_label: Literal["LLQ", "DRQ", "GDQ"] = "LLQ",
        default_subcategory: str = "Verification",
    ) -> None:
        """
        Initialize mock adapter for testing.

        Args:
            cfg: RunConfig instance
            fixtures: Optional dict mapping question indices to {label, subcategory} overrides
            default_label: Default label to use when not in fixtures (default: "LLQ")
            default_subcategory: Default subcategory to use when not in fixtures (default: "Verification")
        """
        super().__init__(cfg=cfg, client=None, pricing=None)
        self.fixtures = fixtures or {}
        self.default_label = default_label
        self.default_subcategory = default_subcategory
        logger.info("Initialized Mock adapter (no real API calls will be made)")

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
        Return mock responses for testing.

        Args:
            system_text: System prompt text (unused in mock)
            user_text: User prompt text (unused in mock)
            response_model: Pydantic model for structured output
            batch_id: Batch identifier for logging
            questions: List of questions to generate labels for
            extra_trace_meta: Optional extra metadata for tracing/logging

        Returns:
            Tuple of (mock BatchLabels model, mock metadata dict with tokens/costs)
        """

        if questions is None:
            questions = []
        # Generate mock labels
        items = []
        for i, question in enumerate(questions, start=1):
            fx = self.fixtures.get(i)
            label = (fx or {}).get("label", self.default_label)
            subcat = (fx or {}).get("subcategory", self.default_subcategory if self.cfg.label_subcategories else None)

            # q_len = len(question)
            # if q_len < 50:
            #     label = "LLQ"
            #     subcat = "Verification" if self.cfg.label_subcategories else None
            # elif q_len < 100:
            #     label = "DRQ"
            #     subcat = "Causal Antecedent" if self.cfg.label_subcategories else None
            # else:
            #     label = "GDQ"
            #     subcat = "Ideation" if self.cfg.label_subcategories else None

            items.append(
                QuestionLabel(
                    index=i,
                    question=str(question).strip(),
                    label=label,
                    subcategory=subcat,
                )
            )

        parsed = response_model(items=items)

        # Mock usage statistics
        input_tokens = len(system_text) // 4 + len(user_text) // 4  # Rough approximation
        output_tokens = sum(len(item.question) // 4 for item in items) + len(items) * 5
        total_tokens = input_tokens + output_tokens

        # mock cost calculations (simple per-token pricing with small random variance)
        per_input_token_cost = 0.000005
        per_output_token_cost = 0.00001

        batch_input_cost = round(input_tokens * per_input_token_cost * (0.9 + random() * 0.2), 6)
        batch_output_cost = round(output_tokens * per_output_token_cost * (0.9 + random() * 0.2), 6)
        batch_total_cost = round(batch_input_cost + batch_output_cost, 6)

        result = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cache_meta": {},
            "batch_input_cost": batch_input_cost,
            "batch_output_cost": batch_output_cost,
            "batch_total_cost": batch_total_cost,
            "batch_output_payload": parsed.model_dump(),
        }
        logger.debug("Mock adapter returned %d labels for batch %d", len(items), batch_id)

        meta = {
            "batch_id": batch_id,
            "mock": True,
            "cost": {
                "batch_input_cost": batch_input_cost,
                "batch_output_cost": batch_output_cost,
                "batch_total_cost": batch_total_cost,
            },
        }
        if extra_trace_meta:
            meta.update(extra_trace_meta)

        opik_context.update_current_span(
            provider="mock",
            model=self.model,
            usage=self._opik_usage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens),
            total_cost=batch_total_cost,
            metadata=meta,
        )
        return parsed, result
