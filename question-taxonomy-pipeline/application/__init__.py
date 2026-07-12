"""
Application layer: Use cases and workflow orchestration.

This layer coordinates between domain logic and infrastructure,
implementing the main workflows for inference and evaluation.

Structure:
- use_cases/: High-level operations (run_experiment, capture_run_snapshot)
- dto/: Data transfer objects (QuestionLabel, BatchLabels)
- ports/: Abstract interfaces for infrastructure dependencies
- Internal modules: batching, prompting, serialize, inference, evaluation
"""

__all__: list[str] = []
