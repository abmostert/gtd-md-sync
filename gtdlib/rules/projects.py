
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
