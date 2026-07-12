"""
Prompt loading and management.
Handles loading prompts from disk and optionally registering them in the Opik prompt library.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import opik
from opik import Prompt, PromptType

from application.ports.prompts import PromptObj as PromptObjPort
from infrastructure.config.models import Provider, RunConfig
from infrastructure.io import ensure_exists, read_text

logger = logging.getLogger(__name__)


class PromptRole(Enum):
    """Role of the prompt in the LLM interaction."""

    SYSTEM = "system"
    USER = "user"

    def default_relative_path(self, cfg: RunConfig) -> Path:
        """Return the provider-relative prompt path, matching the on-disk directory structure."""
        label_dir = "sub-category" if cfg.label_subcategories else "category"

        if self is PromptRole.SYSTEM:
            # prompts/<provider>/system/<category|sub-category>/chat-system.txt
            return Path(self.value) / label_dir / "chat-system.txt"

        if self is PromptRole.USER:
            # prompts/<provider>/user/label/<category|sub-category>/
            # icl-demo/<none|category|sub-category>/classify-questions.txt
            if not cfg.include_icl_demo:
                icl_dir = "none"
            else:
                icl_dir = "sub-category" if cfg.include_subcategory_in_icl_demo else "category"

            return Path(self.value) / "label" / label_dir / "icl-demo" / icl_dir / "classify-questions.txt"

        raise ValueError(f"Unsupported role: {self}")


@dataclass(frozen=True)
class LocalPrompt(PromptObjPort):
    """Lightweight prompt wrapper for disk-only prompting (no Opik prompt library writes)."""

    name: str
    prompt: str
    metadata: dict[str, object] | None = None
    commit: str | None = None

    def format(self, **kwargs: Any) -> str:
        """Format the prompt template with variables using Mustache syntax."""
        rendered = self.prompt

        # Replace longer keys first to reduce accidental partial replacements
        for k in sorted(kwargs, key=lambda x: len(str(x)), reverse=True):
            v = str(kwargs[k])
            placeholder = f"{{{{{k}}}}}"

            if placeholder in rendered:
                rendered = rendered.replace(placeholder, v)
            else:
                # Whitespace-tolerant {{ key }} support
                pattern = re.compile(r"\{\{\s*" + re.escape(str(k)) + r"\s*\}\}")
                rendered = pattern.sub(v, rendered)

        return rendered


@dataclass(frozen=True)
class OpikPromptAdapter(PromptObjPort):
    """
    Adapter exposing an `opik.Prompt` via the application's PromptObj port.

    Wraps the third-party prompt object to provide a stable, well-typed
    interface for the rest of the application, avoiding reliance on possibly
    incomplete external type stubs.
    """

    name: str
    prompt: str
    metadata: dict[str, object] | None
    commit: str | None
    _raw: Prompt

    @classmethod
    def from_raw(cls, raw: Prompt, *, metadata: dict[str, object] | None) -> "OpikPromptAdapter":
        # Bind fields explicitly to keep the adapter well-typed even if opik stubs are loose.
        return cls(
            name=str(getattr(raw, "name", "")),
            prompt=str(getattr(raw, "prompt", "")),
            metadata=metadata if metadata is not None else getattr(raw, "metadata", None),
            commit=getattr(raw, "commit", None),
            _raw=raw,
        )

    def format(self, **kwargs: Any) -> str:
        # opik.Prompt.format returns rendered prompt text
        return str(self._raw.format(**kwargs))


class PromptManager:
    """
    Manages prompt loading from disk and (optionally) registers them in the Opik prompt library

    Prompts are organized as:
        prompts/
        ├─ <vendor1>/
        │  ├─ system/<condition>/chat-system.txt
        │  └─ user/<label>/<condition>/icl-demo/<condition>/classify-questions.txt
        └─ <vendor2>/
           ├─ system/<condition>/chat-system.txt
           └─ user/<label>/<condition>/icl-demo/<condition>/classify-questions.txt
    """

    def __init__(self, prompts_root: Path):
        """
        Initialize prompt manager.

        Args:
            prompts_root: Root directory containing prompt templates organized by provider
        """
        self.prompts_root = prompts_root
        self.client = opik.Opik()
        # Cache stores the PORT type (not opik.Prompt), so the rest of the app never sees vendor types.
        self._cache: dict[tuple[str, str, str, int, bool], PromptObjPort] = {}

    def _get_prompt_path(
        self,
        provider: Provider,
        role: PromptRole,
        cfg: RunConfig,
        override_path: Path | None = None,
    ) -> Path:
        if override_path is not None:
            return override_path
        return self.prompts_root / provider.value / role.default_relative_path(cfg)

    def _make_opik_prompt_name(self, provider: Provider, role: PromptRole, path: Path) -> str:
        """
        Build a stable Opik prompt name derived from provider, role, and relative path.

        Format:
          {provider}.{role}.{relative_path_with_dots}

        - If `path` is under prompts_root/provider, use that relative path to avoid
          duplicating provider segments (e.g., avoid `openai.system.openai.system...`).
        - Otherwise, fall back to a normalized path string.
        """
        provider_root = (self.prompts_root / provider.value).resolve()
        p = path.resolve()

        try:
            rel = p.relative_to(provider_root)
            rel_str = rel.as_posix()
        except ValueError:
            # Path is outside provider_root (e.g., override_path elsewhere). Use a normalized path string.
            rel_str = p.as_posix()

        if rel_str.endswith(".txt"):
            rel_str = rel_str.removesuffix(".txt")

        prefix = f"{role.value}/"
        if rel_str.startswith(prefix):
            rel_str = rel_str[len(prefix) :]

        rel_str = rel_str.replace("/", ".")
        return f"{provider.value}.{role.value}.{rel_str}"

    def get_prompt(
        self,
        provider: Provider,
        role: PromptRole,
        cfg: RunConfig,
        override_path: Path | None = None,
    ) -> PromptObjPort:
        """
        Load a prompt from disk and optionally register it in the Opik prompt library.

        Args:
            provider: Provider enum (OpenAI, Anthropic, etc.)
            role: Prompt role (SYSTEM or USER) to resolve the relative path
            cfg: Runtime configuration
            override_path: If provided, use this file instead of the provider/default path

        Returns:
            PromptObjPort object implementing the minimal prompt interface

        Raises:
            FileNotFoundError: If the resolved prompt file does not exist
            ValueError: For invalid prompt content or failures during optional Opik registration
        """
        prompt_path = self._get_prompt_path(provider, role, cfg, override_path)
        ensure_exists(prompt_path, f"{provider.value}:{role.value}-prompt")
        mtime_ns = prompt_path.stat().st_mtime_ns

        cache_key = (
            provider.value,
            role.value,
            str(prompt_path),
            mtime_ns,
            cfg.prompts_register_in_opik,
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_text = read_text(prompt_path)
        prompt_name = self._make_opik_prompt_name(provider, role, prompt_path)

        metadata: dict[str, object] = {
            "provider": provider.value,
            "role": role.value,
            "source_path": str(prompt_path),
            "label_subcategories": cfg.label_subcategories,
            "include_icl_demo": cfg.include_icl_demo,
            "include_subcategory_in_icl_demo": cfg.include_subcategory_in_icl_demo,
        }

        if cfg.prompts_register_in_opik:
            # Creates/versions the prompt in the Opik prompt library.
            try:
                raw = Prompt(
                    name=prompt_name,
                    prompt=prompt_text,
                    type=PromptType.MUSTACHE,
                    metadata=metadata,  # opik accepts dict-like metadata
                )
                prompt_obj: PromptObjPort = OpikPromptAdapter.from_raw(raw, metadata=metadata)
            except Exception as e:
                raise ValueError(f"Failed to create/register prompt '{prompt_name}' in Opik prompt library.") from e
        else:
            prompt_obj = LocalPrompt(name=prompt_name, prompt=prompt_text, metadata=metadata)

        self._cache[cache_key] = prompt_obj
        logger.info("Loaded %s prompt from %s as %s", role.value, prompt_path, prompt_name)
        return prompt_obj

    def load_prompt(self, name: str, commit: str | None = None) -> Prompt | None:
        return self.client.get_prompt(name=name, commit=commit)
