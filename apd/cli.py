"""CLI: python -m apd "build a ..." --workdir ./demo-out"""

from __future__ import annotations

import argparse
import json
import sys

from .agents import DEFAULT_MODEL
from .orchestrator import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apd",
        description=(
            "personal-apd: run a Planner -> Builder -> 3-Reviewer agent loop "
            "to implement a natural-language software task."
        ),
    )
    p.add_argument("task", help="Natural-language description of what to build.")
    p.add_argument(
        "--workdir",
        default="./apd-out",
        help="Directory the agents read/write (created if missing).",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model id (default: {DEFAULT_MODEL}; or set APD_MODEL).",
    )
    p.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Max review->fix rounds (default: 3).",
    )
    p.add_argument(
        "--report-dir",
        default="runs",
        help="Where to write the JSON run report (default: ./runs).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        metrics = run(
            args.task,
            args.workdir,
            model=args.model,
            max_rounds=args.max_rounds,
            report_dir=args.report_dir,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"run_id:  {metrics.run_id}")
    print(f"status:  {metrics.status}")
    print(f"rounds:  {len({r['round'] for r in metrics.rounds})}")
    print(f"tokens:  {json.dumps(metrics.tokens)}")
    print(f"files:   {len(metrics.files_changed)} changed")
    if metrics.notes:
        print(f"notes:   {metrics.notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
