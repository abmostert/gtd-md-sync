from __future__ import annotations

from pathlib import Path
import re

from gtdlib.store import (
    load_master,
    save_master,
    utc_now_iso,
    VIEWS_DIRNAME,
    new_id,
)
from gtdlib.config import get_contexts
from gtdlib.prompts.action_prompts import (
    prompt_action_draft,
    render_action_preview,
)
from gtdlib.rules.projects import is_project_stalled
from gtdlib.parsing.markdown import (
    extract_completions_from_markdown,
    prune_checked_top_level_tasks,
)




def _create_next_action_for_project(
    *,
    master: dict,
    base_dir: Path,
    project_id: str,
    actions: dict,
    contexts: list[str],
) -> str | None:
    """
    Prompt the user to add a next action for a stalled project.
    This is intentionally minimal: yes/no + shared action draft prompt.
    """
    projects = master.get("projects", {})
    proj = projects.get(project_id)
    if not proj:
        return None

    title = (proj.get("title") or project_id).strip()
    print(f"\nProject stalled: {title}")

    ans = input("Add a next action now? [Y/n]: ").strip().lower()
    if ans in ("n", "no"):
        return None

    now = utc_now_iso()

    try:
        draft = prompt_action_draft(
            base_dir=base_dir,
            contexts=contexts,
            now_iso=now,
            project_id=project_id,
            default_state="active",
            ask_context_when_waiting=False,
        )
    except ValueError as e:
        print(str(e))
        return None

    render_action_preview(draft)

    confirm = input("Save this next action? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        print("Cancelled. Not saved.")
        return None

    aid = new_id("a")
    actions[aid] = draft
    print(f"Added next action {aid}: {draft.get('title','')}")
    return aid


def cmd_sync(base_dir: Path, *, prompt_next: bool = True) -> int:
    """
    Read checkbox completions from Markdown views and update master.json.
    """
    views_dir = base_dir / VIEWS_DIRNAME
    if not views_dir.exists():
        raise FileNotFoundError(f"{VIEWS_DIRNAME}/ not found in {base_dir}. Run `init` first.")

    master = load_master(base_dir)
    actions: dict = master.get("actions", {})
    projects: dict = master.get("projects", {})

    # Read relevant view files
    view_files = [
        views_dir / "next_actions.md",
        views_dir / "projects.md",
        views_dir / "someday.md",
        views_dir / "waiting_for.md",
        views_dir / "agenda.md",
    ]

    completion_map: dict[str, bool] = {}
    for fp in view_files:
        if fp.exists():
            completion_map.update(extract_completions_from_markdown(fp.read_text(encoding="utf-8"))
        )

    now = utc_now_iso()
    completed_actions = 0
    completed_projects = 0

    # Apply completions
    for item_id, done in completion_map.items():
        if not done:
            continue

        if item_id.startswith("a_") and item_id in actions:
            a = actions[item_id]
            if a.get("state") != "completed":
                a["state"] = "completed"
                a["completed"] = now
                a["last_touched"] = now
                a["waiting_since"] = None
                a["waiting_for"] = None
                completed_actions += 1

        elif item_id.startswith("p_") and item_id in projects:
            p = projects[item_id]
            if p.get("state") != "completed":
                p["state"] = "completed"
                p["completed"] = now
                completed_projects += 1

    # Prompt for next actions on stalled active projects
    if prompt_next:
        contexts = get_contexts(base_dir)

        for pid in projects.keys():
            if is_project_stalled(projects, actions, pid):
                _create_next_action_for_project(
                    master=master,
                    base_dir=base_dir,
                    project_id=pid,
                    actions=actions,
                    contexts=contexts,
                )

    inbox_md = base_dir / "inbox" / "inbox.md"
    if inbox_md.exists():
        new_text, removed = prune_checked_top_level_tasks(inbox_md.read_text(encoding="utf-8"))
        if removed:
            inbox_md.write_text(new_text, encoding="utf-8")
            print(f"Pruned {removed} checked capture item(s) from inbox/inbox.md")


    master["actions"] = actions
    master["projects"] = projects
    save_master(base_dir, master)

    print(f"Sync complete. Marked completed: {completed_actions} actions, {completed_projects} projects.")
    return 0
