"""Compare two model prediction files.

The baseline file is usually the Gemini CSV. The candidate file can be either
the pipeline JSON output or a CSV with the same prediction column names.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


QUESTION_COL = "question"
LABEL_COL = "LLM_Label"
SUBCATEGORY_COL = "LLM_Subcategory"


def _load_predictions(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        with path.open(encoding="utf-8") as f:
            data: list[dict[str, Any]] = json.load(f)
        df = pd.DataFrame(data)
    else:
        df = pd.read_csv(path)

    missing = [col for col in (QUESTION_COL, LABEL_COL, SUBCATEGORY_COL) if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")

    return df[[QUESTION_COL, LABEL_COL, SUBCATEGORY_COL]].copy()


def compare_predictions(baseline_path: Path, candidate_path: Path, output_dir: Path) -> dict[str, Any]:
    baseline = _load_predictions(baseline_path).rename(
        columns={
            LABEL_COL: "gemini_label",
            SUBCATEGORY_COL: "gemini_subcategory",
        }
    )
    candidate = _load_predictions(candidate_path).rename(
        columns={
            LABEL_COL: "step_label",
            SUBCATEGORY_COL: "step_subcategory",
        }
    )

    if len(baseline) != len(candidate):
        raise ValueError(f"Row count mismatch: baseline={len(baseline)}, candidate={len(candidate)}")

    comparison = pd.DataFrame(
        {
            "question": baseline[QUESTION_COL],
            "gemini_label": baseline["gemini_label"],
            "step_label": candidate["step_label"],
            "label_match": baseline["gemini_label"].eq(candidate["step_label"]),
            "gemini_subcategory": baseline["gemini_subcategory"],
            "step_subcategory": candidate["step_subcategory"],
            "subcategory_match": baseline["gemini_subcategory"].eq(candidate["step_subcategory"]),
        }
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = output_dir / "gemini_vs_step_comparison.csv"
    summary_path = output_dir / "gemini_vs_step_summary.json"
    mismatches_path = output_dir / "gemini_vs_step_mismatches.csv"

    total = len(comparison)
    label_matches = int(comparison["label_match"].sum())
    subcategory_matches = int(comparison["subcategory_match"].sum())
    summary = {
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "total_rows": total,
        "label_matches": label_matches,
        "label_agreement_rate": label_matches / total if total else None,
        "subcategory_matches": subcategory_matches,
        "subcategory_agreement_rate": subcategory_matches / total if total else None,
    }

    comparison.to_csv(comparison_path, index=False)
    comparison.loc[~comparison["label_match"] | ~comparison["subcategory_match"]].to_csv(
        mismatches_path,
        index=False,
    )
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"comparison_csv={comparison_path}")
    print(f"mismatches_csv={mismatches_path}")
    print(f"summary_json={summary_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Gemini and Step prediction outputs.")
    parser.add_argument("--baseline", required=True, type=Path, help="Gemini baseline CSV or JSON path.")
    parser.add_argument("--candidate", required=True, type=Path, help="Step candidate CSV or JSON path.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for comparison outputs.")
    args = parser.parse_args()

    compare_predictions(
        baseline_path=args.baseline,
        candidate_path=args.candidate,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
