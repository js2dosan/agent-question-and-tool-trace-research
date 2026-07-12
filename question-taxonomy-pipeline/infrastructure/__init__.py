"""
Infrastructure layer: External dependencies and I/O boundaries.

This is the only layer that performs I/O operations and interacts
with external systems (APIs, filesystem, databases, configuration).

Structure:
- bootstrap/: Dependency injection and application setup
- config/: Configuration loading and management
- providers/: LLM provider adapters (OpenAI, Anthropic, Ollama, Mock)
- prompting/: Prompt management (disk, Opik integration)
- io/: File system operations, dataset loading, artifact storage
- observability/: Logging and tracing setup
- utils/: Utility functions (seeding, fingerprinting, VCS)
"""

from infrastructure.config import (
    Provider,
    RunConfig,
    StatsConfig,
    load_run_config,
)
from infrastructure.providers import ProviderAdapter, make_adapter

__all__ = [
    # Provider adapters
    "make_adapter",
    "ProviderAdapter",
    # Configuration
    "load_run_config",
    "RunConfig",
    "Provider",
    "StatsConfig",
]
