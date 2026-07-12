"""
Application layer ports (interfaces/protocols).

Defines abstract interfaces that the application depends on,
with concrete implementations provided by the infrastructure layer.
"""

from application.ports.artifact_store import ArtifactStore, RunSnapshotRequest
from application.ports.config import RunConfig
from application.ports.prompts import PromptObj
from application.ports.provider import ProviderAdapter

__all__ = [
    "ArtifactStore",
    "RunSnapshotRequest",
    "RunConfig",
    "PromptObj",
    "ProviderAdapter",
]
