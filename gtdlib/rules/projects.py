
from __future__ import annotations

from typing import Dict, Iterable, Tuple
from gtdlib.rules.schema import ACTION_OPEN_STATES
from gtdlib.rules.visibility import is_active_project, is_visible_next_action



def iter_actions_for_project(actions: dict, project_id: str) -> Iterable[dict]:
    for a in actions.values():
        if a.get("project") == project_id:
            yield a

def is_project_stalled(projects: dict, actions: dict, project_id: str) -> bool:
    """
    A project is "stalled" if:
      - the project exists
      - the project is a live, active project
      - it has NO visible next actions

    Waiting-for items do not count as next actions.
    Agenda items do not count as next actions.
    """
    project = projects.get(project_id)
    if not project:
        return False

    if not is_active_project(project):
        return False

    for action in actions.values():
        if action.get("project") != project_id:
            continue

        if is_visible_next_action(action, projects):
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

