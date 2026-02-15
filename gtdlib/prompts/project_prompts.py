
from __future__ import annotations

from pathlib import Path

from gtdlib.store import prompt, prompt_optional_date


def prompt_project_draft(
    base_dir: Path,
    *,
    now_iso: str,
    default_state: str = "active",
) -> dict:
    """
    Prompt for project fields and return a project draft dict.

    Returned keys match your master.json project schema:
      title, state, created, reviewed, due, notes
    """
    # Title (required)
    title = prompt("Project title (outcome): ")
    if not title:
        raise ValueError("Project title is required.")

    state = prompt(
        "Project state (active/someday/completed/dropped): ",
        default=default_state,
    ).strip().lower()

    if state not in {"active", "someday", "completed", "dropped"}:
        raise ValueError("Invalid project state. Use active/someday/completed/dropped.")

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
    """
    Print a human-readable preview of a project draft (or existing project).
    """
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
