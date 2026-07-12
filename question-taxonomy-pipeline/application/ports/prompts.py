"""
Prompt "port" for the application layer.
"""

from abc import ABC, abstractmethod
from typing import Any


class PromptObj(ABC):
    """Minimal prompt interface required by application prompting utilities."""

    # Plain attributes (not @property) = fewer false-negative type errors.
    name: str
    prompt: str
    commit: str | None
    metadata: dict[str, object] | None

    @abstractmethod
    def format(self, **kwargs: Any) -> str:
        """Render the prompt template with keyword arguments."""
        raise NotImplementedError
