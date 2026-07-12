from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List


MAX_READ_CHARS = 20000
MAX_COMMAND_OUTPUT_CHARS = 20000


class ToolError(ValueError):
    pass


class LocalToolbox:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tool_specs(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_files",
                "description": "List files under the trial workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path inside the workspace."}
                    },
                    "required": [],
                },
            },
            {
                "name": "read_file",
                "description": "Read a UTF-8 text file from the trial workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path inside the workspace."}
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write a UTF-8 text file inside the trial workspace, creating parent directories as needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path inside the workspace."},
                        "content": {"type": "string", "description": "Full file contents to write."},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "run_command",
                "description": "Run a shell command inside the trial workspace. Use this for tests, builds, and simple inspection commands.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to run."},
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Timeout in seconds. Defaults to 30.",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "finish",
                "description": "Finish the trial with a concise summary of the implementation and verification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "verification": {"type": "string"},
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Important files created or edited.",
                        },
                    },
                    "required": ["summary", "verification", "files"],
                },
            },
        ]

    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "list_files":
            return self.list_files(args.get("path", "."))
        if name == "read_file":
            return self.read_file(args["path"])
        if name == "write_file":
            return self.write_file(args["path"], args["content"])
        if name == "run_command":
            return self.run_command(args["command"], int(args.get("timeout_seconds", 30)))
        if name == "finish":
            return {"finished": True, **args}
        raise ToolError(f"Unknown tool: {name}")

    def list_files(self, path: str = ".") -> Dict[str, Any]:
        root = self._resolve(path)
        if not root.exists():
            return {"path": path, "files": []}
        if root.is_file():
            return {"path": path, "files": [path]}
        files = []
        for item in sorted(root.rglob("*")):
            if item.is_file():
                files.append(str(item.relative_to(self.workspace)))
        return {"path": path, "files": files}

    def read_file(self, path: str) -> Dict[str, Any]:
        target = self._resolve(path)
        if not target.exists():
            raise ToolError(f"File does not exist: {path}")
        if not target.is_file():
            raise ToolError(f"Not a file: {path}")
        content = target.read_text(encoding="utf-8")
        truncated = len(content) > MAX_READ_CHARS
        return {
            "path": path,
            "content": content[:MAX_READ_CHARS],
            "truncated": truncated,
            "chars": len(content),
        }

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": path, "chars_written": len(content)}

    def run_command(self, command: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        timeout_seconds = max(1, min(timeout_seconds, 120))
        completed = subprocess.run(
            command,
            shell=True,
            cwd=self.workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            env={**os.environ, "NO_COLOR": "1"},
        )
        stdout = completed.stdout[-MAX_COMMAND_OUTPUT_CHARS:]
        stderr = completed.stderr[-MAX_COMMAND_OUTPUT_CHARS:]
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": len(completed.stdout) > MAX_COMMAND_OUTPUT_CHARS,
            "stderr_truncated": len(completed.stderr) > MAX_COMMAND_OUTPUT_CHARS,
        }

    def _resolve(self, path: str) -> Path:
        target = (self.workspace / path).resolve()
        if target != self.workspace and self.workspace not in target.parents:
            raise ToolError(f"Path escapes trial workspace: {path}")
        return target
