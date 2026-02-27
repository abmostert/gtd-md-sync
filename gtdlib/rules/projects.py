
from __future__ import annotations

from typing import Dict, Iterable, Tuple
from gtdlib.rules.schema import ACTION_OPEN_STATES



def iter_actions_for_project(actions: dict, project_id: str) -> Iterable[dict]:
    for a in actions.values():
        if a.get("project") == project_id:
            yield a

def is_project_stalled(projects: dict, actions: dict, project_id: str) -> bool:
    """
    A project is "stalled" if:
      - the project exists and is state == "active"
      - it has NO open actions (open = active or waiting)
    """
    p = projects.get(project_id)
    if not p:
        return False

    lifecycle = (p.get("lifecycle") or "live").strip().lower()
    if lifecycle != "live":
        return False
    
    if (p.get("state") or "").strip().lower() != "active":
        return False

    has_active = False
    has_waiting = False

    for a in actions.values():
        if a.get("project") != project_id:
            continue

        state = (a.get("state") or "").strip().lower()
        if state == "active":
            has_active = True
        elif state == "waiting":
            has_waiting = True

        if has_active or has_waiting:
            return False

    return True


def count_open_actions(actions: dict, project_id: str) -> int:
    n = 0
    for a in actions.values():
        if a.get("project") != project_id:
            continue
        if (a.get("state") or "").strip().lower() in ACTION_OPEN_STATES:
            n += 1
    return n


def count_actions_by_state(actions: dict, project_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for a in actions.values():
        if a.get("project") != project_id:
            continue
        st = (a.get("state") or "unknown").strip().lower()
        counts[st] = counts.get(st, 0) + 1
    return counts

