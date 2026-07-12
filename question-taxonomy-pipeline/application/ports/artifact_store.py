from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

RunId = str


@dataclass(frozen=True)
class RunSnapshotRequest:
    run_id: RunId
    cfg_json: Mapping[str, Any]
    system_prompt_text: str
    user_prompt_text: str
    icl_examples_text: str
    prompt_metadata: Mapping[str, Any] | None
    test_file: Path
    test_rows: int
    test_columns_used: Sequence[str]
    icl_demo_file: Path | None
    icl_rows: int | None
    icl_columns_used: Sequence[str] | None
    experiment_yaml: Path | None = None
    execution_context: Mapping[str, Any] | None = None


class ArtifactStore(Protocol):
    def save_run_snapshot(self, request: RunSnapshotRequest) -> None: ...

    def save_batch_raw_response(self, run_id: RunId, batch_id: int, payload: Any) -> Path: ...

    def save_predictions_json(self, run_id: RunId, records: Sequence[Mapping[str, Any]]) -> Path: ...

    def save_metrics_json(self, run_id: RunId, metrics: Mapping[str, Any]) -> Path: ...

    def save_trace_id(self, run_id: RunId, trace_id: str, source: str = "opik") -> Path: ...

    def save_subcategory_alignment_csv(self, run_id: RunId, csv_text: str) -> Path: ...
