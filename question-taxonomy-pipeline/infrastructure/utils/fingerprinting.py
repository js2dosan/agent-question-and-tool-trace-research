"""File integrity and fingerprinting utilities."""

import hashlib
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        path: Path to file

    Returns:
        Hexadecimal hash digest
    """
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        # Read in 1MB chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def file_fingerprint(path: Path | None) -> dict[str, Any] | None:
    """
    Generate file fingerprint with metadata.

    Args:
        path: Path to file (None returns None)

    Returns:
        Dictionary containing path, size, and SHA-256 hash, or None if path is None
    """
    if path is None:
        return None
    stat = path.stat()
    return {
        "path": str(path),
        "bytes": int(stat.st_size),
        "sha256": sha256_file(path),
    }
