"""
Logging contextvars utilities (application-layer, framework-agnostic).

- Adds run_tag and batch_id into every log line (via contextvars).
- Provides helpers to set/get/clear per-run and per-batch context.
- Intended to be imported by application layer code (use-cases/services).
"""

import contextvars
import hashlib
import logging

# Context variables for dynamic log metadata
cv_run_tag = contextvars.ContextVar("run_tag", default="-")
cv_batch_id = contextvars.ContextVar("batch_id", default="-")

# Optional: keep full IDs in context for metadata (not printed every line)
cv_provider = contextvars.ContextVar("provider", default="-")
cv_model = contextvars.ContextVar("model", default="-")
cv_run_id_full = contextvars.ContextVar("run_id_full", default="-")


def make_run_tag(run_id_full: str, length: int = 8) -> str:
    """
    Stable short tag derived from the full run_id.
    8 hex chars is usually enough; bump to 10–12 if running many jobs/day.
    Uses BLAKE2s for collision resistance.
    """
    h = hashlib.blake2s(run_id_full.encode("utf-8"), digest_size=8).hexdigest()
    return h[:length]


class ContextInjectFilter(logging.Filter):
    """Inject context variables into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run = cv_run_tag.get() or "-"
        record.batch = cv_batch_id.get() or "-"
        return True


def set_log_context(
    *,
    run_id_full: str | None = None,
    batch_id: int | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    """
    Update logging context (thread-safe via contextvars).

    Args:
        run_id_full: Full run identifier (optional)
        batch_id: Batch identifier (optional)
        provider: Provider name (optional)
        model: Model name (optional)
    """
    if run_id_full is not None:
        cv_run_id_full.set(str(run_id_full))
        cv_run_tag.set(make_run_tag(str(run_id_full)))

    # Batch: set as zero-padded string
    if batch_id is not None:
        cv_batch_id.set(f"{int(batch_id):03d}")

    # Optional (not printed each line in this Option A formatter)
    if provider is not None:
        cv_provider.set(str(provider))
    if model is not None:
        cv_model.set(str(model))


def get_log_context() -> dict[str, str]:
    """
    Return the current context in a convenient dict form.

    Useful for:
      - attaching `extra_trace_meta` to LLM calls,
      - adding consistent metadata to JSON artifacts,
      - debugging/log correlation.
    """
    return {
        "run_tag": str(cv_run_tag.get() or "-"),
        "run_id_full": str(cv_run_id_full.get() or "-"),
        "batch_id": str(cv_batch_id.get() or "-"),
        "provider": str(cv_provider.get() or "-"),
        "model": str(cv_model.get() or "-"),
    }


def clear_batch_context() -> None:
    """Reset batch context to default (keep run info)."""
    cv_batch_id.set("-")
