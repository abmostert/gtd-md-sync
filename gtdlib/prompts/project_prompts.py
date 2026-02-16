from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from gtdlib.prompts.common import prompt, prompt_optional_date_keep
from gtdlib.rules.schema import validate_project_state


def prompt_project_edit(existing_project: dict) -> dict:
    p = deepcopy(existing_project or {})

    current_title = (p.get("title") or "").strip()
    current_state = (p.get("state") or "active").strip().lower()
    current_notes = p.get("notes") or ""

    title = prompt("Title", default=current_title).strip()
    if not title:
        raise ValueError("Project title cannot be blank.")

    state = validate_project_state(
        prompt("State (active/someday/completed/dropped)", default=current_state)
    )

    due = prompt_optional_date_keep("Due date", p.get("due"))
    notes = prompt("Notes", default=str(current_notes)).strip()

    p["title"] = title
    p["state"] = state
    p["due"] = due
    p["notes"] = notes
    return p


def prompt_project_draft(
    base_dir: Path,
    *,
    now_iso: str,
    default_state: str = "active",
) -> dict:
    title = prompt("Project title (outcome): ").strip()
    if not title:
        raise ValueError("Project title is required.")

    state = validate_project_state(
        prompt("Project state (active/someday/completed/dropped): ", default=default_state)
    )

    due = prompt_optional_date("Project due date")
    notes = prompt("Project notes (optional): ", default="")

    return {
        "title": title,
        "state": state,
        "created": now_iso,
        "reviewed": None,
        "due": due,
        "notes": notes,
    }


def render_project_preview(project_id: str | None, project: dict) -> None:
    pid = project_id or "(new project)"
    title = (project.get("title") or "").strip()
    state = (project.get("state") or "").strip()
    due = project.get("due")
    notes = project.get("notes", "")

    print("\n--- Project preview ---")
    print(f"Project ID: {pid}")
    print(f"Title:      {title}")
    print(f"State:      {state}")
    print(f"Due:        {due}")
    print(f"Notes:      {notes}")
    print("-----------------------\n")

