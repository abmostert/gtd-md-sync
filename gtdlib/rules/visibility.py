from __future__ import annotations


def is_live_project(project: dict) -> bool:
    return (project.get("lifecycle") or "live").strip().lower() == "live"


def is_active_project(project: dict) -> bool:
    return is_live_project(project) and (project.get("state") or "").strip().lower() == "active"


def is_someday_project(project: dict) -> bool:
    return is_live_project(project) and (project.get("state") or "").strip().lower() == "someday"


def is_agenda_action(action: dict) -> bool:
    if (action.get("state") or "").strip().lower() != "active":
        return False

    context = (action.get("context") or "").strip().lower()
    return context.startswith("agenda_")


def _linked_project(action: dict, projects: dict) -> dict | None:
    pid = action.get("project")
    if not pid:
        return None
    return projects.get(pid)


def is_visible_next_action(action: dict, projects: dict) -> bool:
    if (action.get("state") or "").strip().lower() != "active":
        return False

    if is_agenda_action(action):
        return False

    project = _linked_project(action, projects)
    if project is None:
        return True

    return is_active_project(project)


def is_visible_waiting_action(action: dict, projects: dict) -> bool:
    if (action.get("state") or "").strip().lower() != "waiting":
        return False

    project = _linked_project(action, projects)
    if project is None:
        return True

    return is_active_project(project)


def is_visible_agenda_action(action: dict, projects: dict) -> bool:
    if not is_agenda_action(action):
        return False

    project = _linked_project(action, projects)
    if project is None:
        return True

    return is_active_project(project)


def is_visible_someday_action(action: dict, projects: dict) -> bool:
    if (action.get("state") or "").strip().lower() != "someday":
        return False

    project = _linked_project(action, projects)
    if project is None:
        return True

    return is_live_project(project)
