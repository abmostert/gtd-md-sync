from __future__ import annotations

from gtdlib.rules.projects import count_actions_by_state

def choose_project_edit_operation(*, pid: str, project: dict, actions: dict) -> str:
    """
    Show project summary + menu.
    Returns: "edit_fields" | "add_action" | "cancel"
    """
    title = (project.get("title") or pid).strip()
    state = (project.get("state") or "unknown").strip().lower()
    due = project.get("due")
    notes = project.get("notes") or ""
    counts = count_actions_by_state(actions, pid)

    print("\n--- Project ---")
    print(f"ID:    {pid}")
    print(f"Title: {title}")
    print(f"State: {state}")
    print(f"Due:   {due}")
    print(f"Notes: {notes}")
    print("Actions:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("--------------\n")

    print("What do you want to do?")
    print("  1) Edit project fields (title/state/due/notes)")
    print("  2) Add another action to this project")
    print("  3) Cancel")

    choice = input("Choose [1-3]: ").strip()
    if choice in ("", "3"):
        return "cancel"
    if choice == "1":
        return "edit_fields"
    if choice == "2":
        return "add_action"
    return "cancel"
