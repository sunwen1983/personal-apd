"""personal-apd: a small multi-agent software-development framework.

Pipeline: Planner -> Builder -> 3 Reviewers (correctness, security/style,
tests & edge cases) -> iterate on findings (max N rounds).
"""

__version__ = "0.1.0"

from .orchestrator import run

__all__ = ["run", "__version__"]
