"""
Provider configuration registry.

Maps provider types to their configuration model classes.
"""

from typing import Any

from .models import AnthropicConfig, GeminiConfig, NvidiaConfig, OllamaConfig, OpenAIConfig, Provider

# Provider -> params config model
# Add future providers here
PARAM_MODEL_BY_PROVIDER: dict[Provider, type[Any]] = {
    Provider.OPENAI: OpenAIConfig,
    Provider.ANTHROPIC: AnthropicConfig,
    Provider.OLLAMA: OllamaConfig,
    Provider.GEMINI: GeminiConfig,
    Provider.NVIDIA: NvidiaConfig,
}
