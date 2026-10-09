"""Agent roles for the personal-apd loop.

Roles:
  Planner             - breaks the task into concrete implementation steps.
  Builder             - implements the steps using the file tools.
  CorrectnessReviewer - logic errors, broken imports, wrong APIs, crashes.
  SecurityStyleReviewer - injection / traversal / secrets, plus style consistency.
  TestsEdgeReviewer   - edge cases, empty inputs, error paths; suggests tests.

Reviewers are read-only: they can inspect the tree but cannot change it.
All LLM traffic goes through :class:`LLMClient`, which wraps the Anthropic
Messages API and accounts token usage per run.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

try:
    import anthropic
except ImportError:  # pragma: no cover - surfaced as a clear error at runtime
    anthropic = None

DEFAULT_MODEL = os.environ.get("APD_MODEL", "claude-sonnet-4-5")
MAX_TOOL_TURNS = 25
MAX_TOKENS = 4096


class UsageTracker:
    """Accumulates input/output tokens across every LLM call in a run."""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def add(self, usage) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.calls += 1

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def as_dict(self) -> dict:
        return {
            "input": self.input_tokens,
            "output": self.output_tokens,
            "total": self.total_tokens,
            "calls": self.calls,
        }


class LLMClient:
    """Thin wrapper over the Anthropic SDK with usage accounting.

    The API key is read from ``ANTHROPIC_API_KEY`` (or passed explicitly).
    The client is created lazily on first use so ``import apd`` never needs
    a key; a clear error is raised only when a call is actually attempted.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or DEFAULT_MODEL
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None
        self.usage = UsageTracker()

    def _ensure_client(self):
        if anthropic is None:
            raise RuntimeError(
                "The 'anthropic' package is not installed. Run: pip install anthropic"
            )
        if not self._api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it before running the "
                "agent loop, e.g.: export ANTHROPIC_API_KEY=sk-ant-..."
            )
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def chat(self, *, system: str, messages: list, tools: list | None = None):
        client = self._ensure_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            tools=tools or [],
        )
        self.usage.add(response.usage)
        return response


def _text_of(response) -> str:
    return "".join(
        block.text for block in response.content if block.type == "text"
    )


class Agent:
    """Base agent: system prompt + agentic tool-use loop."""

    role_name = "agent"
    system_prompt = "You are a helpful software engineering assistant."

    def __init__(self, llm: LLMClient, tools):
        self.llm = llm
        self.tools = tools

    def run(self, task_prompt: str) -> str:
        messages = [{"role": "user", "content": task_prompt}]
        tool_defs = self.tools.anthropic_tools()
        for _ in range(MAX_TOOL_TURNS):
            response = self.llm.chat(
                system=self.system_prompt, messages=messages, tools=tool_defs
            )
            messages.append({"role": "assistant", "content": response.content})
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                return _text_of(response)
            for tu in tool_uses:
                result = self.tools.dispatch(tu.name, tu.input or {})
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tu.id,
                                "content": result,
                            }
                        ],
                    }
                )
        raise RuntimeError(f"{self.role_name}: exceeded {MAX_TOOL_TURNS} tool turns")


class Planner(Agent):
    role_name = "planner"
    system_prompt = (
        "You are a senior software engineer planning an implementation task. "
        "Break the task into small, concrete, ordered steps that a builder agent "
        "can execute with file read/write tools. Keep it to at most 8 steps. "
        "Respond with ONLY a JSON object of this shape, no other text:\n"
        '{"steps": [{"id": 1, "title": "...", "detail": "..."}, ...]}'
    )


def parse_plan(text: str) -> list[dict]:
    """Extract the planner's step list; falls back to one free-form step."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            steps = data.get("steps", [])
            if isinstance(steps, list) and steps:
                return [
                    {
                        "id": s.get("id", i + 1),
                        "title": str(s.get("title", "")),
                        "detail": str(s.get("detail", "")),
                    }
                    for i, s in enumerate(steps)
                    if isinstance(s, dict)
                ]
        except (json.JSONDecodeError, AttributeError):
            pass
    return [{"id": 1, "title": "Implement the task", "detail": text.strip()}]


class Builder(Agent):
    role_name = "builder"
    system_prompt = (
        "You are a senior software engineer implementing a task. Follow the plan "
        "step by step using the file tools. Write complete, working code - no "
        "placeholders, no TODOs, no truncated files. Keep the change surface "
        "small and consistent with the existing code style. After writing files, "
        "re-read the important ones to double-check them. When you are done, "
        "summarize what you built and which files you changed."
    )


@dataclass
class Finding:
    severity: str  # "major" | "minor" | "info"
    file: str
    message: str
    suggestion: str = ""

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "file": self.file,
            "message": self.message,
            "suggestion": self.suggestion,
        }


def parse_findings(text: str) -> list[Finding]:
    """Parse a reviewer's JSON findings; never fails, degrades to one finding."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            findings = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                sev = str(item.get("severity", "minor")).lower()
                if sev not in ("major", "minor", "info"):
                    sev = "minor"
                findings.append(
                    Finding(
                        severity=sev,
                        file=str(item.get("file", "")),
                        message=str(item.get("message", ""))[:2000],
                        suggestion=str(item.get("suggestion", ""))[:2000],
                    )
                )
            return findings
        except json.JSONDecodeError:
            pass
    return [
        Finding(
            severity="info",
            file="",
            message="Reviewer returned unstructured feedback.",
            suggestion=text.strip()[:2000],
        )
    ]


class Reviewer(Agent):
    """Read-only reviewer. Subclasses only change the review lens."""

    role_name = "reviewer"
    lens = "general code quality"
    system_prompt = "You are a careful code reviewer."

    def __init__(self, llm: LLMClient, tools):
        super().__init__(llm, tools)

    @property
    def prompt(self) -> str:
        return (
            f"You are an expert code reviewer focused on {self.lens}. "
            "Inspect the files in the workdir with the read-only file tools. "
            "Respond with ONLY a JSON array of findings, no other text. Each "
            'finding: {"severity": "major"|"minor"|"info", "file": "path", '
            '"message": "what is wrong", "suggestion": "how to fix"}. '
            "If you find nothing worth flagging, return an empty array []. "
            "Be concrete and file-specific; do not invent problems."
        )

    def review(self, task_summary: str) -> list[Finding]:
        raw = self.run(
            f"{self.prompt}\n\nTask context:\n{task_summary}\n\n"
            "Review the current state of the workdir."
        )
        return parse_findings(raw)


class CorrectnessReviewer(Reviewer):
    role_name = "correctness-reviewer"
    lens = (
        "correctness and logic: wrong algorithms, broken imports, incorrect API "
        "usage, off-by-one errors, unhandled exceptions, dead code paths, and "
        "anything that would crash or misbehave at runtime"
    )


class SecurityStyleReviewer(Reviewer):
    role_name = "security-style-reviewer"
    lens = (
        "security and code style: injection flaws, path traversal, hardcoded "
        "secrets, unsafe deserialization, XSS, plus inconsistent naming, "
        "formatting, and dead or duplicated code"
    )


class TestsEdgeReviewer(Reviewer):
    role_name = "tests-edge-reviewer"
    lens = (
        "tests and edge cases: empty inputs, boundary values, error paths, "
        "concurrency or timing assumptions, missing validation, and untested "
        "branches. Suggest concrete test cases for the riskiest behavior"
    )


REVIEWERS: tuple[type[Reviewer], ...] = (
    CorrectnessReviewer,
    SecurityStyleReviewer,
    TestsEdgeReviewer,
)


def actionable(findings: list[Finding]) -> list[Finding]:
    """Findings the builder should address (major/minor; info is FYI)."""
    return [f for f in findings if f.severity in ("major", "minor")]
