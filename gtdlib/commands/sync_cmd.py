from __future__ import annotations

from pathlib import Path

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
from gtdlib.prompts.stalled_project_prompts import prompt_next_action_for_stalled_project




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
            completion_map.update(extract_completions_from_markdown(fp.read_text(encoding="utf-8")))

    now = utc_now_iso()
    completed_actions = 0
    completed_projects = 0

    # Scanning of project notes
    projects_dir = base_dir / "projects"
    if projects_dir.exists():
        for folder in projects_dir.iterdir():
            if not folder.is_dir():
                continue
            pn = folder / "project_notes.md"
            if pn.exists():
                completion_map.update(extract_completions_from_markdown(pn.read_text(encoding="utf-8")))
  

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
                proj = projects.get(pid, {})
                title = (proj.get("title") or pid).strip()

                prompt_next_action_for_stalled_project(
                    base_dir=base_dir,
                    project_id=pid,
                    project_title=title,
                    contexts=contexts,
                    actions=actions,
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
