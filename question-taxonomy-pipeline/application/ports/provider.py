"""
Provider adapter "port" for the application layer.

Concrete adapters live in infrastructure (`infrastructure.providers.*`).
The application depends only on the `call_batch` interface.
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from application.dto.question_labeling import BatchLabels


@runtime_checkable
class ProviderAdapter(Protocol):
    """Minimal provider adapter interface used by application inference."""

    def call_batch(
        self,
        *,
        system_text: str,
        user_text: str,
        response_model: type[BatchLabels],
        batch_id: int,
        questions: Sequence[str] | None = None,
        extra_trace_meta: dict[str, Any] | None = None,
    ) -> tuple[BatchLabels, dict[str, Any]]: ...
