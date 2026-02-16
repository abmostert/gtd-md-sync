# gtdlib/rules/schema.py
from __future__ import annotations

PROJECT_STATES = {"active", "someday", "completed", "dropped"}
ACTION_STATES = {"active", "waiting", "someday"}  
# “Open” for stalled-project logic
ACTION_OPEN_STATES = {"active", "waiting"}

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
