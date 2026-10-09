"""Per-run metrics and JSON run reports.

The report schema is shared: the orchestrator writes it automatically, and the
same shape is used for manually-executed runs (see runs/demo-notes-app-report.json).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class RunMetrics:
    run_id: str
    task: str
    model: str
    started_at: str = field(default_factory=utcnow)
    ended_at: str = ""
    plan_steps: list[dict] = field(default_factory=list)
    rounds: list[dict] = field(default_factory=list)  # reviewer findings per round
    iterations: int = 0  # builder fix-up passes after round 1
    tokens: dict = field(default_factory=dict)  # {"input","output","total","calls"}
    files_changed: list[str] = field(default_factory=list)
    status: str = "completed"  # completed | failed
    notes: str = ""

    def finish(self, status: str = "completed", notes: str = "") -> None:
        self.ended_at = utcnow()
        self.status = status
        if notes:
            self.notes = notes

    def as_dict(self) -> dict:
        return asdict(self)


def write_report(report_path: str | Path, metrics: RunMetrics) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics.as_dict(), indent=2), encoding="utf-8")
    return path


def snapshot_files(workdir: Path) -> list[str]:
    """Relative paths of all files under workdir (excluding .git and runs)."""
    out = []
    for p in sorted(workdir.rglob("*")):
        if p.is_file() and ".git" not in p.parts and "runs" not in p.parts:
            out.append(str(p.relative_to(workdir)))
    return out
