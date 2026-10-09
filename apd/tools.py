"""MCP-style file tools, executed in-process against a sandboxed workdir.

Each tool follows the MCP tool shape: ``{"name", "description", "inputSchema"}``.
``ToolRegistry`` exposes them both in MCP shape (``to_mcp()``) and in the
Anthropic Messages API shape (``to_anthropic()``), so the same definitions can
later be served by a real MCP server without changing the agents.

All paths are resolved relative to the workdir, and path traversal outside the
workdir is rejected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], str]
    read_only: bool = False

    def to_mcp(self) -> dict:
        """MCP tool definition shape: name / description / inputSchema."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def to_anthropic(self) -> dict:
        """Anthropic Messages API tool definition shape."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    """Owns the file tools for one run. Reviewers get a read-only view."""

    def __init__(self, workdir: str | Path, *, read_only: bool = False):
        self.workdir = Path(workdir).resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._read_only = read_only
        self._tools: dict[str, Tool] = {}
        self._register_defaults()

    # -- sandboxing ------------------------------------------------------
    def _resolve(self, rel: str) -> Path:
        candidate = (self.workdir / rel).resolve()
        if candidate != self.workdir and self.workdir not in candidate.parents:
            raise ValueError(f"path escapes workdir: {rel!r}")
        return candidate

    # -- handlers --------------------------------------------------------
    def _read_file(self, args: dict) -> str:
        path = self._resolve(args["path"])
        if not path.is_file():
            return f"ERROR: not a file: {args['path']!r}"
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"ERROR: not a UTF-8 text file: {args['path']!r}"

    def _write_file(self, args: dict) -> str:
        path = self._resolve(args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        content = args["content"]
        path.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content.encode('utf-8'))} bytes to {args['path']!r}"

    def _list_dir(self, args: dict) -> str:
        path = self._resolve(args.get("path", "."))
        if not path.is_dir():
            return f"ERROR: not a directory: {args.get('path', '.')!r}"
        entries = sorted(
            ("[dir] " if p.is_dir() else "") + p.name
            for p in path.iterdir()
            if p.name != ".git"
        )
        return json.dumps(entries, indent=2)

    # -- registration ----------------------------------------------------
    def _register_defaults(self) -> None:
        self.register(
            Tool(
                name="read_file",
                description=(
                    "Read a UTF-8 text file. Path is relative to the workdir, "
                    "e.g. 'src/app.py'."
                ),
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                handler=self._read_file,
                read_only=True,
            )
        )
        self.register(
            Tool(
                name="list_dir",
                description="List files in a directory relative to the workdir.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory relative to workdir; default '.'",
                        }
                    },
                },
                handler=self._list_dir,
                read_only=True,
            )
        )
        if not self._read_only:
            self.register(
                Tool(
                    name="write_file",
                    description=(
                        "Create or overwrite a UTF-8 text file. Path is relative "
                        "to the workdir; parent directories are created as needed. "
                        "Writes the COMPLETE file content."
                    ),
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                    handler=self._write_file,
                    read_only=False,
                )
            )

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    # -- execution -------------------------------------------------------
    def dispatch(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"ERROR: unknown tool: {name!r}"
        if self._read_only and not tool.read_only:
            return f"ERROR: tool {name!r} is not available in read-only mode"
        try:
            return tool.handler(arguments or {})
        except (ValueError, KeyError, OSError) as exc:
            return f"ERROR: {exc}"

    def anthropic_tools(self) -> list[dict]:
        return [t.to_anthropic() for t in self._tools.values()]

    def mcp_tools(self) -> list[dict]:
        return [t.to_mcp() for t in self._tools.values()]

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())
