"""
CLI entry point for the question-labelling pipeline.

This script performs the following steps:
- Loads .env and configs/experiment.yaml.
- Creates a per-run output folder under `outputs/`.
- Loads prompts (provider-aware) and optional ICL examples.
- Runs batched inference via the selected provider adapter.
- Serializes predictions and runs evaluation if human labels are available.
- Computes a subcategory alignment table (if applicable).
- Saves metrics to JSON.
- Logs a human-readable summary of results.
- Saves a snapshot of the run configuration, prompts, and data references.
"""

import argparse
import logging

from opik import track

from application.use_cases.run_experiment import run_experiment
from infrastructure.bootstrap import bootstrap_experiment
from infrastructure.constants import EXPERIMENT_FILE

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run LLM question labelling pipeline")
    p.add_argument(
        "--experiment",
        type=str,
        default=str(EXPERIMENT_FILE),
        help="Path to experiment.yaml (default: configs/experiment.yaml)",
    )
    p.add_argument(
        "--env",
        type=str,
        default=".env",
        help="Path to .env file (default: .env)",
    )
    p.add_argument(
        "--mock",
        action="store_true",
        help="Use Mock adapter instead of calling a real provider.",
    )
    p.add_argument(
        "--console-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Console log level",
    )
    p.add_argument(
        "--file-level",
        type=str,
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="File log level",
    )
    return p.parse_args()


@track(
    name="Question.labelling",
    type="general",
    metadata={"task": "question_labelling"},
    capture_input=False,
    capture_output=False,
    flush=True,
)
def main() -> None:
    args = _parse_args()
    req = bootstrap_experiment(args)
    run_experiment(req)
    logger.info("Detailed log: %s", req.log_path)


if __name__ == "__main__":
    main()
