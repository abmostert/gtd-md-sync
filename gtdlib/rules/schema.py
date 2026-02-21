# gtdlib/rules/schema.py
from __future__ import annotations

from typing import Any, Dict

PROJECT_STATES = {"active", "someday", "completed"}
PROJECT_LIFECYCLES = {"live", "review", "trash"}
ACTION_STATES = {"active", "waiting", "someday"}  
# “Open” for stalled-project logic
ACTION_OPEN_STATES = {"active", "waiting"}
RESERVED_CONTEXTS = {"waiting_for", "waiting"}


def validate_project_state(state: str) -> str:
    s = (state or "").strip().lower()
    if s not in PROJECT_STATES:
        raise ValueError("Invalid project state. Use active/someday/completed/dropped.")
    return s

def validate_action_state(state: str) -> str:
    s = (state or "").strip().lower()
    if s not in ACTION_STATES:
        raise ValueError("Invalid action state. Use active/waiting/someday.")
    return s

def normalize_master_in_memory(master: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply non-destructive defaults for missing fields so older data keeps working.
    This does NOT write anything; caller may save.
    """
    master.setdefault("projects", {})
    master.setdefault("actions", {})

    projects = master.get("projects", {})
    if isinstance(projects, dict):
        for pid, p in projects.items():
            if not isinstance(p, dict):
                continue
            # default lifecycle
            if "lifecycle" not in p:
                p["lifecycle"] = "live"
            # allow only expected lifecycles; if corrupted, force safe default
            lc = (p.get("lifecycle") or "").strip().lower()
            if lc not in PROJECT_LIFECYCLES:
                p["lifecycle"] = "live"
    return master


