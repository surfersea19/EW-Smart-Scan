"""
repo_paths.py

Single source of truth for locating Person 1's and Person 2's sibling
packages on disk, and registering them on sys.path exactly once. Every
integration module imports from here instead of recomputing paths --
avoids subtle bugs from three different files guessing the layout
slightly differently.

Assumes the standard repo layout:

    EW-Smart-Scan/
    ├── ew_scheduler/            <- Person 2
    ├── smart-scan-person1/      <- Person 1
    └── smart-ew-scan-scheduler/ <- Person 3 (this package lives inside here)
"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# .../smart-ew-scan-scheduler/backend/integration -> up 3 -> EW-Smart-Scan/
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))

P1_ROOT = os.path.join(REPO_ROOT, "smart-scan-person1")
P2_ROOT = os.path.join(REPO_ROOT, "ew_scheduler")

_registered = False


def register_p1_p2_on_path() -> None:
    """
    Idempotent. Adds P1's project root (so `import backend...` resolves
    to Person 1's package) and P2's prediction/scheduler/evaluation
    folders (matching the exact sys.path pattern P2's own run_pipeline.py
    and internal modules already use -- their files do
    `from history_manager import ...`, not
    `from backend.prediction.history_manager import ...`, so we must
    add those subfolders directly, not just ew_scheduler/).
    """
    global _registered
    if _registered:
        return

    if not os.path.isdir(P1_ROOT):
        raise RuntimeError(
            f"Expected Person 1's package at {P1_ROOT} -- check repo layout."
        )
    if not os.path.isdir(P2_ROOT):
        raise RuntimeError(
            f"Expected Person 2's package at {P2_ROOT} -- check repo layout."
        )

    sys.path.insert(0, P1_ROOT)
    for sub in ("prediction", "scheduler", "evaluation"):
        p = os.path.join(P2_ROOT, "backend", sub)
        if p not in sys.path:
            sys.path.insert(0, p)

    _registered = True
