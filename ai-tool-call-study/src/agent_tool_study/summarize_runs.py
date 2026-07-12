from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize local trial runs.")
    parser.add_argument("--runs-dir", default=Path("runs"), type=Path)
    args = parser.parse_args()

    rows: List[Dict[str, Any]] = []
    for summary_path in sorted(args.runs_dir.glob("*/summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        events = list(read_jsonl(summary_path.parent / "events.jsonl"))
        rows.append(
            {
                "trial_id": summary.get("trial_id"),
                "model": summary.get("model"),
                "finished": summary.get("finished"),
                "dry_run": summary.get("dry_run"),
                "model_calls": summary.get("model_calls", 0),
                "tool_calls": summary.get("tool_calls", 0),
                "total_prompt_tokens": sum_usage(events, "prompt_token_count"),
                "total_candidate_tokens": sum_usage(events, "candidates_token_count"),
                "total_tokens": sum_usage(events, "total_token_count"),
                "list_files": count_tool(events, "list_files"),
                "read_file": count_tool(events, "read_file"),
                "write_file": count_tool(events, "write_file"),
                "run_command": count_tool(events, "run_command"),
                "finish": count_tool(events, "finish"),
                "files_written_count": len(summary.get("files_written", [])),
                "chars_written": sum_chars_written(events),
                "tool_sequence": " -> ".join(tool_sequence(events)),
                "commands": " | ".join(commands_run(events)),
                "tools": ", ".join(summary.get("tools", [])),
            }
        )

    out_path = args.runs_dir / "summary.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "trial_id",
        "model",
        "finished",
        "dry_run",
        "model_calls",
        "tool_calls",
        "total_prompt_tokens",
        "total_candidate_tokens",
        "total_tokens",
        "list_files",
        "read_file",
        "write_file",
        "run_command",
        "finish",
        "files_written_count",
        "chars_written",
        "tool_sequence",
        "commands",
        "tools",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {out_path}")


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def count_tool(events: Iterable[Dict[str, Any]], tool_name: str) -> int:
    return sum(
        1
        for event in events
        if event.get("event_type") == "tool_call_completed" and event.get("tool_name") == tool_name
    )


def tool_sequence(events: Iterable[Dict[str, Any]]) -> List[str]:
    return [
        str(event.get("tool_name"))
        for event in events
        if event.get("event_type") == "tool_call_completed" and event.get("tool_name")
    ]


def commands_run(events: Iterable[Dict[str, Any]]) -> List[str]:
    return [
        str(event.get("tool_args", {}).get("command"))
        for event in events
        if event.get("event_type") == "tool_call_completed"
        and event.get("tool_name") == "run_command"
        and event.get("tool_args", {}).get("command")
    ]


def sum_chars_written(events: Iterable[Dict[str, Any]]) -> int:
    return sum(
        int(event.get("tool_result", {}).get("chars_written", 0))
        for event in events
        if event.get("event_type") == "tool_call_completed" and event.get("tool_name") == "write_file"
    )


def sum_usage(events: Iterable[Dict[str, Any]], key: str) -> int:
    return sum(
        int(event.get("usage_metadata", {}).get(key) or 0)
        for event in events
        if event.get("event_type") == "model_call_completed"
    )


if __name__ == "__main__":
    main()
