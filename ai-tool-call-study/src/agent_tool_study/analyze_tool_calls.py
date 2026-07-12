from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


CATEGORY_ORDER = ["orientation", "implementation", "verification", "finalization"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify and report tool-call traces.")
    parser.add_argument("--runs-dir", default=Path("runs"), type=Path)
    parser.add_argument("--out-dir", default=Path("analysis"), type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    events = load_formal_tool_events(args.runs_dir)
    rows = [classify_event(event) for event in events]

    write_csv(args.out_dir / "tool_call_events_categorized.csv", rows)
    prompt_rows = summarize_by_prompt(rows, args.runs_dir)
    write_csv(args.out_dir / "prompt_level_tool_summary.csv", prompt_rows)
    write_report(args.out_dir / "pilot_report.md", prompt_rows, rows)

    print(f"Wrote {args.out_dir / 'tool_call_events_categorized.csv'}")
    print(f"Wrote {args.out_dir / 'prompt_level_tool_summary.csv'}")
    print(f"Wrote {args.out_dir / 'pilot_report.md'}")


def load_formal_tool_events(runs_dir: Path) -> List[Dict[str, Any]]:
    events = []
    for event_path in sorted(runs_dir.glob("trial_*/events.jsonl")):
        for event in read_jsonl(event_path):
            if event.get("event_type") == "tool_call_completed":
                events.append(event)
    return events


def classify_event(event: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = str(event.get("tool_name", ""))
    args = event.get("tool_args", {}) or {}
    result = event.get("tool_result", {}) or {}
    command = str(args.get("command", ""))
    file_diff = event.get("file_diff", {}) or {}

    category = "implementation"
    evidence = ""
    if tool_name in {"list_files", "read_file"}:
        category = "orientation"
        evidence = "workspace/file inspection"
    elif tool_name == "run_command":
        if is_verification_command(command):
            category = "verification"
            evidence = command
        else:
            category = "orientation"
            evidence = command
    elif tool_name == "write_file":
        category = "implementation"
        evidence = str(args.get("path", ""))
    elif tool_name == "finish":
        category = "finalization"
        evidence = str(args.get("summary", ""))[:180]

    return {
        "trial_id": event.get("trial_id"),
        "turn_index": event.get("turn_index"),
        "call_index": event.get("call_index"),
        "tool_name": tool_name,
        "category": category,
        "tool_target": args.get("path") or command or "",
        "returncode": result.get("returncode", ""),
        "created_files": ";".join(file_diff.get("created", [])),
        "modified_files": ";".join(file_diff.get("modified", [])),
        "deleted_files": ";".join(file_diff.get("deleted", [])),
        "evidence": evidence,
    }


def is_verification_command(command: str) -> bool:
    command_lower = command.lower()
    verification_markers = [
        "test",
        "node test",
        "npm test",
        "pytest",
        "playwright",
        "vitest",
        "ls -l",
        "cat ",
        "grep ",
    ]
    return any(marker in command_lower for marker in verification_markers)


def summarize_by_prompt(rows: List[Dict[str, Any]], runs_dir: Path) -> List[Dict[str, Any]]:
    summary_by_trial = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in runs_dir.glob("trial_*/summary.json")
    }
    rows_by_trial: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_trial[str(row["trial_id"])].append(row)

    output = []
    for trial_id in sorted(rows_by_trial):
        tool_rows = rows_by_trial[trial_id]
        counts = Counter(row["category"] for row in tool_rows)
        summary = summary_by_trial.get(trial_id, {})
        created_files = sorted(
            {
                file_name
                for row in tool_rows
                for file_name in str(row.get("created_files", "")).split(";")
                if file_name
            }
        )
        output.append(
            {
                "trial_id": trial_id,
                "prompt": summary.get("prompt", ""),
                "model": summary.get("model", ""),
                "model_calls": summary.get("model_calls", 0),
                "tool_calls": summary.get("tool_calls", 0),
                "orientation_calls": counts.get("orientation", 0),
                "implementation_calls": counts.get("implementation", 0),
                "verification_calls": counts.get("verification", 0),
                "finalization_calls": counts.get("finalization", 0),
                "created_files": ";".join(created_files),
                "tool_sequence": " -> ".join(row["category"] for row in tool_rows),
                "final_summary": summary.get("final", {}).get("summary", ""),
                "final_verification": summary.get("final", {}).get("verification", ""),
            }
        )
    return output


def write_report(path: Path, prompt_rows: List[Dict[str, Any]], event_rows: List[Dict[str, Any]]) -> None:
    lines = [
        "# Pilot Report: Prompt Effects on Gemini Tool Use",
        "",
        "## Research Framing",
        "",
        "This pilot treats tool calls as observable action traces in a Thought-Action-Observation style loop. The model's hidden reasoning is not directly visible, but the sequence of tool calls, tool arguments, tool outputs, generated files, and final summaries provides a behavioral trace of how the agent approached the task.",
        "",
        "Task held constant: build a three-player tic-tac-toe web game.",
        "",
        "Model held constant: `gemini-3.1-flash-lite`.",
        "",
        "## Prompt Conditions",
        "",
    ]

    for row in prompt_rows:
        lines.append(f"- `{row['trial_id']}`: {row['prompt']}")

    lines.extend(
        [
            "",
            "## Tool-Call Category Summary",
            "",
            "| Trial | Model Calls | Tool Calls | Orientation | Implementation | Verification | Finalization | Created Files |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in prompt_rows:
        lines.append(
            "| {trial_id} | {model_calls} | {tool_calls} | {orientation_calls} | {implementation_calls} | {verification_calls} | {finalization_calls} | {created_files} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Early Findings",
            "",
            "1. All five prompts produced completed artifacts, but prompt framing changed the trace shape.",
            "2. The verification-heavy prompt produced the strongest verification behavior: it created `test.js` and ran `node test.js` before finalizing.",
            "3. The trace-aware prompt produced a more modular implementation by splitting the game into `index.html` and `game.js`.",
            "4. The design-heavy prompt produced the largest single HTML artifact among the non-test runs, suggesting more styling/UI code.",
            "5. The minimal and rules-heavy prompts completed with fewer structural side effects and mostly single-file implementations.",
            "",
            "## Interpretation",
            "",
            "The pilot suggests that prompt wording can shift agent behavior from simple implementation toward verification or modularization. The most visible distinction is not only in the final app, but in the intermediate tool trace: whether the model creates test artifacts, runs commands, or separates implementation files.",
            "",
            "## Limitations",
            "",
            "- This is a small pilot with one model and one task.",
            "- The harness captures observable behavior, not hidden chain-of-thought.",
            "- UI verification is still shallow; the current agent can run commands but does not yet perform browser screenshots or interaction checks.",
            "- The category labels are rule-based and should be manually audited before being used as final research data.",
            "",
            "## Suggested Next Step",
            "",
            "Run a second batch with browser/screenshot tools enabled, then compare whether design-heavy prompts trigger more visual inspection and iterative styling changes.",
            "",
            "## Event-Level Data",
            "",
            "See `tool_call_events_categorized.csv` for every categorized tool call.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
