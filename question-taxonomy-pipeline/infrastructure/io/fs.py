"""Filesystem utility functions."""

import json
import os
from pathlib import Path
from typing import Any


def ensure_exists(path: Path, what: str) -> None:
    """
    Check that a path exists, raise FileNotFoundError if not.

    Args:
        path: Path to check
        what: Description of what this path represents (for error message)

    Raises:
        FileNotFoundError: If path does not exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing {what} at: {path}")


def read_text(path: Path) -> str:
    """
    Read text file with UTF-8 encoding and strip whitespace.

    Args:
        path: Path to text file

    Returns:
        File contents with leading/trailing whitespace removed
    """
    return path.read_text(encoding="utf-8").strip()


def write_text_atomic(path: Path, text: str) -> None:
    """
    Write text to file atomically using write-then-rename pattern.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")

    with tmp_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())

    tmp_path.replace(path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """
    Write JSON data to file atomically using write-then-rename pattern.

    This prevents corrupted files if the program crashes mid-write.
    The atomic replace operation ensures the file is either fully written
    or not modified at all.

    Args:
        path: Destination file path (will create parent directories if needed)
        data: Dictionary to serialize as JSON

    Raises:
        OSError: If directory creation or file write fails
        TypeError: If data contains non-serializable objects
    """
    # Ensure parent directory exists (idempotent operation)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first (atomic write pattern)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()  # Force write to OS buffer
        os.fsync(f.fileno())

    # Atomically replace target file (POSIX guarantees atomicity)
    tmp_path.replace(path)
