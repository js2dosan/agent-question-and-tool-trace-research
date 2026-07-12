"""
Artifact storage implementations.

Provides concrete implementations for persisting experiment outputs,
including predictions, metrics, and run snapshots.
"""

from .filesystem_store import FilesystemArtifactStore

__all__ = [
    "FilesystemArtifactStore",
]
