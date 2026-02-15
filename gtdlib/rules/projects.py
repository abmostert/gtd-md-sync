
from __future__ import annotations

from typing import Dict, Iterable, Tuple


OPEN_STATES = {"active", "waiting"}


def iter_actions_for_project(actions: dict, project_id: str) -> Iterable[dict]:
    for a in actions.values():
        if a.get("project") == project_id:
            yield a


def count_actions_by_state(actions: dict, project_id: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for a in iter_actions_for_project(actions, project_id):
        st = (a.get("state") or "unknown").strip().lower()
        counts[st] = counts.get(st, 0) + 1
    return counts


def count_open_actions(actions: dict, project_id: str) -> int:
    n = 0
    for a in iter_actions_for_project(actions, project_id):
        if (a.get("state") or "").strip().lower() in OPEN_STATES:
            n += 1
    return n


def is_project_stalled(projects: dict, actions: dict, project_id: str) -> bool:
    p = projects.get(project_id)
    if not p:
        return False
    if (p.get("state") or "").strip().lower() != "active":
        return False
    return count_open_actions(actions, project_id) == 0



def is_project_stalled(actions: dict, project_id: str) -> bool:

    has_active = False
    has_waiting = False

    for a in actions.values():

        if a.get("project") != project_id:
            continue

        state = a.get("state")

        if state == "active":
            has_active = True

        elif state == "waiting":
            has_waiting = True

    return not (has_active or has_waiting)
