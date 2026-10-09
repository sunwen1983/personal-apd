# Architecture

```
            ┌──────────┐
            │  Planner │  task -> ordered steps (JSON)
            └────┬─────┘
                 ▼
            ┌──────────┐
            │ Builder  │  implements steps via file tools
            └────┬─────┘
                 ▼
   ┌─────────────────────────────┐
   │  Reviewers (read-only tools) │
   │  1. correctness & logic      │
   │  2. security & code style    │
   │  3. tests & edge cases       │
   └──────────────┬──────────────┘
                  │ findings (major/minor)
                  ▼
            ┌──────────┐    no actionable findings
            │ Builder  │ ────────────────────────► done
            │ (fix-up) │ ◄────────────────────────
            └──────────┘    up to max_rounds (default 3)
```

## Components

| File | Responsibility |
|---|---|
| `apd/cli.py` | argparse entry point (`python -m apd "task" --workdir …`) |
| `apd/orchestrator.py` | `run()`: plan → build → review/fix loop → metrics + JSON report |
| `apd/agents.py` | `LLMClient` (Anthropic wrapper + token accounting), `Agent` tool-use loop, `Planner`, `Builder`, three `Reviewer` subclasses |
| `apd/tools.py` | `ToolRegistry`: `read_file` / `write_file` / `list_dir`, sandboxed to the workdir |
| `apd/metrics.py` | `RunMetrics` dataclass and `write_report()` (JSON schema shared with manual runs) |

## Tool layer

Tools follow the MCP tool shape (`name`, `description`, `inputSchema`) and are
executed in-process against a sandboxed workdir — no separate server process.
`ToolRegistry.mcp_tools()` returns MCP-shaped definitions and
`ToolRegistry.anthropic_tools()` returns the Anthropic Messages API shape, so
the same definitions can be served over a real MCP server later without
changing the agents. Path traversal outside the workdir is rejected.
Reviewers receive a read-only registry (`read_file`, `list_dir` only).

## Review loop

Each reviewer returns findings as a JSON array:
`[{"severity": "major"|"minor"|"info", "file, "message", "suggestion"}]`.
`major`/`minor` findings go back to the Builder; `info` is FYI. The loop ends
early when a round produces no actionable findings, otherwise after
`max_rounds`.

## Metrics

Every run writes a JSON report (default `./runs/<slug>-<timestamp>.json`) with:
task, model, plan steps, per-round reviewer findings, iteration count, token
usage (`input`/`output`/`total`/`calls`), files changed, and status.

## Limits (honest)

- Single-machine, single-model; no parallel agents, no persistent memory.
- The Builder cannot run shell commands or tests — verification is by re-reading
  files. (The demo app in `demo/` was type-checked and built with Vite/TS,
  which is stronger verification than the framework itself provides today.)
- Needs `ANTHROPIC_API_KEY`; the live LLM loop has not been exercised in this
  repo's CI-less environment — the demo app was built by the author following
  this exact loop manually (see `runs/demo-notes-app-report.json`).
