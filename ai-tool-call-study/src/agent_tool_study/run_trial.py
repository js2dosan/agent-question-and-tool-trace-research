from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from google import genai
from google.genai import types

from agent_tool_study.event_log import EventLogger
from agent_tool_study.tools import LocalToolbox


SYSTEM_INSTRUCTION = """You are a coding agent inside a controlled research trial.

Your task is to build the requested web app inside the provided workspace using only the available tools.
Use simple static web files unless the user prompt clearly requires a framework.
Inspect the workspace when useful, write files, run targeted checks, and call finish when done.

Research constraint: tool use is being studied. Use tools naturally and only when they help complete or verify the task.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Gemini tool-call study trial.")
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--runs-dir", default=Path("runs"), type=Path)
    parser.add_argument(
        "--seed-dir",
        type=Path,
        help="Copy files from this directory into the otherwise empty trial workspace before the run.",
    )
    parser.add_argument(
        "--disable-run-command",
        action="store_true",
        help="Remove run_command from the agent tool set for a tool-availability control condition.",
    )
    parser.add_argument("--model", default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--temperature", default=0.7, type=float)
    parser.add_argument("--max-turns", default=40, type=int)
    parser.add_argument("--min-call-interval-seconds", default=5.0, type=float)
    parser.add_argument(
        "--thinking-level",
        choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
        help="Optional Gemini thinking level when supported by the selected model.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Delete an existing run folder for this trial id.")
    args = parser.parse_args()

    prompt = args.prompt.read_text(encoding="utf-8").strip()
    run_dir = (args.runs_dir / args.trial_id).resolve()
    workspace = run_dir / "workspace"
    if run_dir.exists() and (run_dir / "events.jsonl").exists():
        if not args.overwrite:
            raise SystemExit(f"Run already exists: {run_dir}. Use --overwrite or choose a new --trial-id.")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    seed_dir = args.seed_dir.resolve() if args.seed_dir else None
    if seed_dir:
        if not seed_dir.is_dir():
            raise SystemExit(f"Seed directory does not exist: {seed_dir}")
        shutil.copytree(seed_dir, workspace, dirs_exist_ok=True)

    logger = EventLogger(run_dir / "events.jsonl", args.trial_id)
    logger.write(
        "trial_started",
        prompt=prompt,
        prompt_file=str(args.prompt),
        model=args.model,
        temperature=args.temperature,
        workspace=str(workspace),
        seed_dir=str(seed_dir) if seed_dir else None,
        run_command_available=not args.disable_run_command,
        dry_run=args.dry_run,
        thinking_level=args.thinking_level,
    )

    if args.dry_run:
        logger.write("trial_finished", dry_run=True)
        write_summary(run_dir, args.trial_id, args.model, prompt, finished=False, dry_run=True)
        return

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY before running a real trial.")

    toolbox = LocalToolbox(workspace, allow_run_command=not args.disable_run_command)
    client = genai.Client(api_key=api_key)
    tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=spec["name"],
                description=spec["description"],
                parameters_json_schema=spec["parameters"],
            )
            for spec in toolbox.tool_specs()
        ]
    )

    contents: List[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]
    final_payload: Dict[str, Any] = {}

    last_model_call_at = 0.0
    for turn_index in range(args.max_turns):
        elapsed_since_call = time.monotonic() - last_model_call_at
        if turn_index > 0 and elapsed_since_call < args.min_call_interval_seconds:
            time.sleep(args.min_call_interval_seconds - elapsed_since_call)

        logger.write("model_call_started", turn_index=turn_index)
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=args.temperature,
            tools=[tool],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        if args.thinking_level:
            config.thinking_config = types.ThinkingConfig(
                thinking_level=types.ThinkingLevel(args.thinking_level)
            )

        response = generate_with_retries(
            client=client,
            model=args.model,
            contents=contents,
            config=config,
            logger=logger,
            turn_index=turn_index,
        )
        last_model_call_at = time.monotonic()
        logger.write(
            "model_call_completed",
            turn_index=turn_index,
            text=response.text,
            function_call_count=len(response.function_calls or []),
            usage_metadata=_to_plain(getattr(response, "usage_metadata", None)),
        )

        if response.candidates:
            contents.append(response.candidates[0].content)

        if response.function_calls:
            tool_response_parts = []
            for call_index, function_call in enumerate(response.function_calls):
                tool_name = function_call.name
                tool_args = dict(function_call.args or {})
                logger.write(
                    "tool_call_requested",
                    turn_index=turn_index,
                    call_index=call_index,
                    tool_name=tool_name,
                    tool_args=tool_args,
                )
                files_before = workspace_snapshot(workspace)
                try:
                    tool_result = toolbox.execute(tool_name, tool_args)
                except Exception as exc:
                    tool_result = {"error": str(exc)}
                files_after = workspace_snapshot(workspace)

                logger.write(
                    "tool_call_completed",
                    turn_index=turn_index,
                    call_index=call_index,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_result=tool_result,
                    file_diff=workspace_diff(files_before, files_after),
                )
                if tool_name == "finish" and tool_result.get("finished"):
                    final_payload = tool_result

                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": tool_result},
                    )
                )

            contents.append(types.Content(role="tool", parts=tool_response_parts))

            if final_payload:
                logger.write("trial_finished", final=final_payload)
                write_summary(run_dir, args.trial_id, args.model, prompt, finished=True, dry_run=False, final=final_payload)
                return

            continue

        if response.text:
            final_payload = {
                "finished": True,
                "summary": response.text,
                "verification": "Model returned a final text response without calling finish.",
                "files": _workspace_files(workspace),
            }
            logger.write("trial_finished", final=final_payload)
            write_summary(run_dir, args.trial_id, args.model, prompt, finished=True, dry_run=False, final=final_payload)
            return

    logger.write("trial_stopped", reason="max_turns_exceeded", max_turns=args.max_turns)
    write_summary(run_dir, args.trial_id, args.model, prompt, finished=False, dry_run=False, final=final_payload)


def write_summary(
    run_dir: Path,
    trial_id: str,
    model: str,
    prompt: str,
    finished: bool,
    dry_run: bool,
    final: Dict[str, Any] | None = None,
) -> None:
    events = list(read_jsonl(run_dir / "events.jsonl"))
    summary = {
        "trial_id": trial_id,
        "model": model,
        "prompt": prompt,
        "finished": finished,
        "dry_run": dry_run,
        "event_count": len(events),
        "model_calls": sum(1 for e in events if e.get("event_type") == "model_call_completed"),
        "tool_calls": sum(1 for e in events if e.get("event_type") == "tool_call_completed"),
        "tools": sorted(
            {
                e.get("tool_name")
                for e in events
                if e.get("event_type") == "tool_call_completed" and e.get("tool_name")
            }
        ),
        "files_written": [
            e["tool_args"]["path"]
            for e in events
            if e.get("event_type") == "tool_call_completed"
            and e.get("tool_name") == "write_file"
            and "tool_args" in e
            and "path" in e["tool_args"]
        ],
        "final": final or {},
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _workspace_files(workspace: Path) -> List[str]:
    return sorted(str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file())


def workspace_snapshot(workspace: Path) -> Dict[str, Dict[str, Any]]:
    snapshot = {}
    for path in workspace.rglob("*"):
        if path.is_file():
            stat = path.stat()
            snapshot[str(path.relative_to(workspace))] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
    return snapshot


def workspace_diff(
    before: Dict[str, Dict[str, Any]],
    after: Dict[str, Dict[str, Any]],
) -> Dict[str, List[str]]:
    before_keys = set(before)
    after_keys = set(after)
    common = before_keys & after_keys
    return {
        "created": sorted(after_keys - before_keys),
        "deleted": sorted(before_keys - after_keys),
        "modified": sorted(key for key in common if before[key] != after[key]),
    }


def _to_plain(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    return str(value)


def generate_with_retries(
    client: genai.Client,
    model: str,
    contents: List[types.Content],
    config: types.GenerateContentConfig,
    logger: EventLogger,
    turn_index: int,
) -> Any:
    for attempt in range(4):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as exc:
            if attempt == 3:
                logger.write("model_call_failed", turn_index=turn_index, attempt=attempt, error=str(exc))
                raise
            delay = 10 * (attempt + 1)
            logger.write(
                "model_call_retry",
                turn_index=turn_index,
                attempt=attempt,
                delay_seconds=delay,
                error=str(exc),
            )
            time.sleep(delay)


if __name__ == "__main__":
    main()
