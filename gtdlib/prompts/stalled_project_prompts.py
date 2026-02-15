from __future__ import annotations

from pathlib import Path

from gtdlib.store import utc_now_iso, new_id
from gtdlib.prompts.action_prompts import prompt_action_draft, render_action_preview


def prompt_next_action_for_stalled_project(
    *,
    base_dir: Path,
    project_id: str,
    project_title: str,
    contexts: list[str],
    actions: dict,
) -> str | None:
    print(f"\nProject stalled: {project_title}")

    ans = input("Add a next action now? [Y/n]: ").strip().lower()
    if ans in ("n", "no"):
        return None

    now = utc_now_iso()

    draft = prompt_action_draft(
        base_dir=base_dir,
        contexts=contexts,
        now_iso=now,
        project_id=project_id,
        default_state="active",
        ask_context_when_waiting=False,
    )

    render_action_preview(draft)

    confirm = input("Save this next action? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        print("Cancelled. Not saved.")
        return None

    aid = new_id("a")
    actions[aid] = draft
    print(f"Added next action {aid}: {draft.get('title','')}")
    return aid
