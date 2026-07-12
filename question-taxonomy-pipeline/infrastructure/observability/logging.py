"""
Logging setup with contextvars-based metadata injection.

- Adds run_tag and batch_id into every log line (via contextvars).
- Supports console-only logging OR console + rotating file logs.
- Tunes noisy third-party library loggers (httpx, openai, anthropic, etc.).
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Application-layer log context (ports/cross-cutting concerns)
from application.observability.log_context import ContextInjectFilter


def configure_logging(
    *,
    log_file: Path | None = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10_000_000,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configure application logging with contextvars support.

    Args:
        log_file: Path to log file
        console_level: Minimum level for console output (default: INFO)
        file_level: Minimum level for file output (default: DEBUG)
        max_bytes: Max log file size before rotation
        backup_count: Number of backup files to keep
    """
    # Clear existing handlers to avoid duplicate logs if called multiple times
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)  # keep root permissive; handlers enforce levels

    # Formatter includes context fields injected by ContextInjectFilter
    console_fmt = "%(asctime)s [%(levelname)s] r=%(run)s b=%(batch)s | %(message)s"
    file_fmt = "%(asctime)s [%(levelname)s] %(name)s | r=%(run)s b=%(batch)s | %(message)s"

    console_formatter = logging.Formatter(console_fmt, datefmt="%H:%M:%S")
    file_formatter = logging.Formatter(file_fmt, datefmt="%Y-%m-%d %H:%M:%S")

    ctx_filter = ContextInjectFilter()

    # Console handler (human-readable, INFO+)
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(console_formatter)
    ch.addFilter(ctx_filter)
    root.addHandler(ch)

    # File handler (detailed, DEBUG+, with rotation)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setLevel(file_level)
        fh.setFormatter(file_formatter)
        fh.addFilter(ctx_filter)
        root.addHandler(fh)

    # Third-party library log levels
    # Reduce noise from HTTP libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # LLM provider SDKs
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    # Keep opik at INFO (useful for debugging traces)
    logging.getLogger("opik").setLevel(logging.INFO)

    logging.getLogger(__name__).info(
        "Logging configured (console_level=%s, file=%s)",
        logging.getLevelName(console_level),
        str(log_file) if log_file is not None else "None",
    )
