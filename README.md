# personal-apd

A small, working multi-agent software-development framework in Python — my personal reimplementation of the APD-style (Autonomous Product Developer) loop I built at GM. No proprietary code; written from scratch.

> **Scope note:** this is a deliberately small version — the planner/builder/reviewer core with file tools. The production system this is modeled on is considerably broader: it drives the full lifecycle from Jira story to merged PR to closed story (planning, implementation, code review, PR creation, CI), with a deeper review and evaluation system on top.

The loop:

```
Planner → Builder → 3 Reviewers → fix → repeat (max 3 rounds)
```

- **Planner** breaks a natural-language task into concrete steps.
- **Builder** implements them with file tools (`read_file` / `write_file` / `list_dir`), sandboxed to a workdir.
- **Three reviewers** inspect the result with read-only tools, each through a different lens:
  1. correctness & logic, 2. security & code style, 3. tests & edge cases.
- Actionable findings go back to the Builder; the loop ends early when a round is clean.
- Every run writes a JSON report (`runs/`) with the plan, per-round findings, token usage, and files changed.

The file tools follow the MCP tool shape (`name` / `description` / `inputSchema`) and run in-process — the same definitions can be served by a real MCP server later without changing the agents. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it

```bash
git clone https://github.com/sunwen1983/personal-apd.git
cd personal-apd
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
python -m apd "build a tiny JSON log viewer CLI" --workdir ./demo-out
# model override: --model claude-sonnet-4-5  (or set APD_MODEL)
```

## Dogfooding: the demo app

`demo/notes-app/` is a real markdown notes app (React + TypeScript + Vite): create/edit/delete notes, markdown preview, search, tags, localStorage persistence. It was built by following this repo's loop manually — plan, build, then the three reviewer passes, one fix iteration, re-verify. The honest record is [runs/demo-notes-app-report.json](runs/demo-notes-app-report.json), including what the reviewers actually caught (4 minor findings, all fixed) and what wasn't verified.

```bash
cd demo/notes-app
npm install
npm run build   # tsc --strict + vite build
npm run dev     # local dev server
```

## Honest limitations

- Single-machine, single-model; no parallel agents, no persistent memory.
- The Builder can't run shell commands — verification is by re-reading files (the demo got the stronger check of `tsc` + `vite build`).
- The live LLM loop needs `ANTHROPIC_API_KEY` and hasn't been exercised end-to-end in this environment; the framework's non-LLM paths (tool sandboxing, parsing, metrics, CLI) are tested.
- No automated test suite yet (the markdown renderer was smoke-tested by hand; a vitest suite is the obvious next step).
