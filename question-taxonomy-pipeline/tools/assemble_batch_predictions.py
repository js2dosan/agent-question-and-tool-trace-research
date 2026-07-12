"""Assemble saved raw batch outputs into one prediction JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _records_from_run(run_dir: Path, source_df: pd.DataFrame) -> dict[int, dict[str, Any]]:
    config = _load_json(run_dir / "config_snapshot.json")
    batch_size = int(config["batch_size"])
    row_start = config.get("row_start")
    row_start = int(row_start) if row_start is not None else 0

    records: dict[int, dict[str, Any]] = {}
    batches_dir = run_dir / "batches"
    for batch_path in sorted(batches_dir.glob("batch_*_raw.json")):
        batch_id = int(batch_path.stem.split("_")[1])
        batch = _load_json(batch_path)
        for item in batch.get("items", []):
            source_row = row_start + ((batch_id - 1) * batch_size) + int(item["index"]) - 1
            source_question = source_df.iloc[source_row]["question"]
            records[source_row] = {
                "source_row_number": source_row,
                "question": source_question,
                "human_label": None,
                "human_subcategory": None,
                "human_subcategory_normalized": None,
                "LLM_Label": item["label"],
                "LLM_Subcategory": item.get("subcategory"),
                "LLM_Subcategory_normalized": item.get("subcategory"),
            }
    return records


def assemble(source: Path, run_dirs: list[Path], output: Path) -> None:
    source_df = pd.read_csv(source)
    records: dict[int, dict[str, Any]] = {}
    for run_dir in run_dirs:
        records.update(_records_from_run(run_dir=run_dir, source_df=source_df))

    missing = [idx for idx in range(len(source_df)) if idx not in records]
    if missing:
        raise ValueError(f"Missing predictions for {len(missing)} rows. First missing rows: {missing[:20]}")

    ordered = [records[idx] for idx in range(len(source_df))]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
    print(f"assembled_rows={len(ordered)}")
    print(f"output={output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble raw batch predictions from one or more run directories.")
    parser.add_argument("--source", required=True, type=Path, help="Source CSV used for the runs.")
    parser.add_argument("--run-dir", required=True, type=Path, action="append", help="Run directory with batches/*.json.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path.")
    args = parser.parse_args()

    assemble(source=args.source, run_dirs=args.run_dir, output=args.output)


if __name__ == "__main__":
    main()
