import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from application.ports.artifact_store import ArtifactStore, RunId, RunSnapshotRequest
from infrastructure.io.fs import write_json, write_text_atomic
from infrastructure.utils import file_fingerprint, git_commit

from .layout import (
    BATCH_OUTPUTS_DIRNAME,
    CONFIG_SNAPSHOT_FILENAME,
    DATA_FINGERPRINT_FILENAME,
    METRICS_FILENAME,
    PREDICTIONS_FILENAME,
    PROMPT_METADATA_FILENAME,
    PROMPT_OUTPUTS_DIRNAME,
    RUN_MANIFEST_FILENAME,
    SUBCATEGORY_ALIGNMENT_FILENAME,
    TRACE_ID_FILENAME_PATTERN,
)


class FilesystemArtifactStore(ArtifactStore):
    def __init__(self, outputs_root: Path) -> None:
        """
        Initialize filesystem artifact store.

        Args:
            outputs_root: Root directory for storing experiment outputs
        """
        self._outputs_root = outputs_root

    def _run_dir(self, run_id: RunId) -> Path:
        return self._outputs_root / run_id

    def save_batch_raw_response(self, run_id: RunId, batch_id: int, payload: Any) -> Path:
        batch_dir = self._run_dir(run_id) / BATCH_OUTPUTS_DIRNAME
        batch_dir.mkdir(parents=True, exist_ok=True)

        path = batch_dir / f"batch_{batch_id:03d}_raw.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def save_predictions_json(self, run_id: RunId, records: Sequence[Mapping[str, Any]]) -> Path:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        path = run_dir / PREDICTIONS_FILENAME
        with path.open("w", encoding="utf-8") as f:
            json.dump(list(records), f, ensure_ascii=False, indent=2)
        return path

    def save_metrics_json(self, run_id: RunId, metrics: Mapping[str, Any]) -> Path:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        path = run_dir / METRICS_FILENAME
        write_json(path, dict(metrics))
        return path

    def save_subcategory_alignment_csv(self, run_id: RunId, csv_text: str) -> Path:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        path = run_dir / SUBCATEGORY_ALIGNMENT_FILENAME
        write_text_atomic(path, csv_text)
        return path

    def save_trace_id(self, run_id: RunId, trace_id: str, source: str = "opik") -> Path:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        path = run_dir / TRACE_ID_FILENAME_PATTERN.format(source=source)
        path.write_text(trace_id, encoding="utf-8")
        return path

    def save_run_snapshot(self, request: RunSnapshotRequest) -> None:
        """Save config, prompts, and data fingerprints for the run."""
        run_dir = self._run_dir(request.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        # create prompts output directory
        prompts_dir = run_dir / PROMPT_OUTPUTS_DIRNAME
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # save config snapshot
        write_json(run_dir / CONFIG_SNAPSHOT_FILENAME, dict(request.cfg_json))

        # save prompt texts
        (prompts_dir / "system.txt").write_text(request.system_prompt_text, encoding="utf-8")
        (prompts_dir / "user.txt").write_text(request.user_prompt_text, encoding="utf-8")
        if request.icl_examples_text:
            (prompts_dir / "icl_examples.txt").write_text(request.icl_examples_text, encoding="utf-8")

        # save prompt metadata
        if request.prompt_metadata is not None:
            write_json(prompts_dir / PROMPT_METADATA_FILENAME, dict(request.prompt_metadata))

        # save data fingerprints
        write_json(
            run_dir / DATA_FINGERPRINT_FILENAME,
            {
                "test_file": str(request.test_file),
                "icl_demo_file": str(request.icl_demo_file) if request.icl_demo_file else None,
                # fingerprints
                "test_file_fingerprint": file_fingerprint(request.test_file),
                "icl_demo_file_fingerprint": file_fingerprint(request.icl_demo_file) if request.icl_demo_file else None,
                "test_rows": int(request.test_rows),
                "icl_rows": int(request.icl_rows) if request.icl_rows is not None else None,
                # columns used
                "test_columns_used": list(request.test_columns_used),
                "icl_columns_used": list(request.icl_columns_used) if request.icl_columns_used is not None else None,
                "experiment_config": {
                    "path": str(request.experiment_yaml) if request.experiment_yaml else None,
                    "fingerprint": file_fingerprint(request.experiment_yaml) if request.experiment_yaml else None,
                },
            },
        )

        write_json(
            run_dir / RUN_MANIFEST_FILENAME,
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "git_commit": git_commit(),
                "execution": dict(request.execution_context) if request.execution_context else {},
            },
        )
