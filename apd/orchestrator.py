"""Orchestrator: Planner -> Builder -> 3 Reviewers -> iterate (max N rounds)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .agents import (
    REVIEWERS,
    Builder,
    LLMClient,
    Planner,
    parse_plan,
)
from .metrics import RunMetrics, snapshot_files, write_report
from .tools import ToolRegistry as FileTools


def _slug(task: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", task.lower()).strip("-")[:40]
    return slug or "task"


def run(
    task: str,
    workdir: str | Path = "./apd-out",
    *,
    model: str | None = None,
    max_rounds: int = 3,
    report_dir: str | Path = "runs",
    run_id: str | None = None,
) -> RunMetrics:
    """Execute the full agent loop for one task. Returns the run metrics."""
    workdir = Path(workdir)
    llm = LLMClient(model=model)
    metrics = RunMetrics(
        run_id=run_id or f"{_slug(task)}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}",
        task=task,
        model=llm.model,
    )
    try:
        tools = FileTools(workdir)
        read_tools = FileTools(workdir, read_only=True)

        # 1. Plan ---------------------------------------------------------
        planner = Planner(llm, tools)
        plan_text = planner.run(task)
        steps = parse_plan(plan_text)
        metrics.plan_steps = steps
        plan_summary = "\n".join(
            f"{s['id']}. {s['title']} - {s['detail']}" for s in steps
        )

        # 2. Build --------------------------------------------------------
        builder = Builder(llm, tools)
        build_summary = builder.run(
            f"Task: {task}\n\nImplementation plan:\n{plan_summary}\n\n"
            f"Implement the plan now in the workdir ({workdir.resolve()})."
        )

        # 3. Review -> fix loop -------------------------------------------
        for round_no in range(1, max_rounds + 1):
            round_findings: list[dict] = []
            for reviewer_cls in REVIEWERS:
                reviewer = reviewer_cls(llm, read_tools)
                findings = reviewer.review(
                    f"Task: {task}\nPlan:\n{plan_summary}\n"
                    f"Builder summary:\n{build_summary}"
                )
                round_findings.append(
                    {
                        "round": round_no,
                        "reviewer": reviewer.role_name,
                        "findings": [f.as_dict() for f in findings],
                        "findings_count": len(findings),
                    }
                )
            metrics.rounds.extend(round_findings)

            to_fix = [
                f
                for entry in round_findings
                for f in entry["findings"]
                if f["severity"] in ("major", "minor")
            ]
            if not to_fix:
                break  # reviewers are satisfied

            metrics.iterations += 1
            fix_list = "\n".join(
                f"- [{f['severity']}] {f['file']}: {f['message']}"
                + (f" Suggestion: {f['suggestion']}" if f["suggestion"] else "")
                for f in to_fix
            )
            build_summary = builder.run(
                "Address ALL of the following reviewer findings in the workdir. "
                "Edit the files with the file tools, then re-read the changed "
                "files to verify.\n\nFindings:\n" + fix_list
            )

        metrics.files_changed = snapshot_files(workdir)
        metrics.tokens = llm.usage.as_dict()
        metrics.finish()
    except Exception as exc:  # noqa: BLE001 - surfaced in the report
        metrics.finish(status="failed", notes=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        metrics.tokens = llm.usage.as_dict()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        write_report(
            Path(report_dir) / f"{_slug(task)}-{stamp}.json", metrics
        )
    return metrics
