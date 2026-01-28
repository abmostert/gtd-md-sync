from __future__ import annotations

from pathlib import Path
import re
from datetime import date

from gtdlib.store import (
    load_master,
    save_master,
    utc_now_iso,
    VIEWS_DIRNAME,
    ensure_config,
    normalize_context,
    new_id,
)

ID_COMMENT_RE = re.compile(r"<!--\s*id:(?P<id>[^>]+?)\s*-->")
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.*)$")

def _create_next_action_for_project(master: dict, base_dir, project_id: str) -> str | None:
    projects = master.get("projects", {})
    actions = master.get("actions", {})

    proj = projects.get(project_id)
    if not proj:
        return None

    title = (proj.get("title") or project_id).strip()

    print(f"\nProject stalled: {title}")
    ans = input("Add a next action now? [Y/n]: ").strip().lower()
    if ans in ("n", "no"):
        return None

    a_title = input("Next action title: ").strip()
    if not a_title:
        print("No title entered. Skipping.")
        return None

    context = _choose_context_from_config(base_dir)
    due = _prompt_due_date()

    # Reuse existing ID creation
    import secrets
    new_id = new_id("a")

    
    now = utc_now_iso() if "utc_now_iso" in dir(__import__("gtdlib.store")) else None

    action = {
        "title": a_title,
        "context": context,
        "state": "active",
        "project": project_id,
    }
    if now:
        action["created"] = now
        action["updated"] = now
    if due:
        action["due"] = due

    actions[new_id] = action
    master["actions"] = actions
    return new_id


def _count_active_actions_for_project(actions: dict, project_id: str) -> int:
    n = 0
    for a in actions.values():
        if a.get("project") != project_id:
            continue
        if a.get("state") == "active":
            n += 1
    return n


def _choose_context_from_config(base_dir) -> str:
    cfg = ensure_config(base_dir)
    contexts = [normalize_context(c) for c in cfg.get("contexts", [])]
    contexts = sorted(set(contexts))
    if not contexts:
        # Fallback (shouldn't happen if config exists)
        return "inbox"

    print("\nChoose context:")
    for i, c in enumerate(contexts, start=1):
        print(f"  {i}. {c}")

    while True:
        raw = input("Context (number or name): ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(contexts):
                return contexts[idx - 1]
        cand = normalize_context(raw)
        if cand in contexts:
            return cand
        print("Invalid context. Choose a number from the list or type an exact context name.")


def _prompt_due_date() -> str | None:
    raw = input("Due date (YYYY-MM-DD, blank for none): ").strip()
    if not raw:
        return None
    # Keep it simple: accept ISO date only
    try:
        date.fromisoformat(raw)
        return raw
    except ValueError:
        print("Invalid date format. Skipping due date.")
        return None

def _extract_completions_from_markdown(text: str) -> dict[str, bool]:
    """
    Returns a mapping: { item_id: True/False }
    Only items that include an <!-- id:... --> marker are considered.
    Completion is True if:
      - checkbox is [x] or [X], OR
      - line contains 'XXX' (user marker) anywhere after the text
    """
    results: dict[str, bool] = {}

    for line in text.splitlines():
        m_id = ID_COMMENT_RE.search(line)
        if not m_id:
            continue
        item_id = m_id.group("id").strip().replace("\\_", "_")

        # Determine completion
        done = False
        
        norm_line = line.lstrip("\ufeff")  # remove BOM if present
        m_cb = CHECKBOX_RE.match(norm_line)
        if m_cb:
            done = (m_cb.group("mark").lower() == "x")

        if "XXX" in line:
            done = True

        results[item_id] = done

    return results


def cmd_sync(base_dir: Path, *, prompt_next: bool = True) -> int:
    """
    Read checkbox completions from Markdown views and update master.json.
    This is intentionally non-interactive in v1.
    """
    views_dir = base_dir / VIEWS_DIRNAME
    if not views_dir.exists():
        raise FileNotFoundError(f"{VIEWS_DIRNAME}/ not found in {base_dir}. Run `init` first.")

    master = load_master(base_dir)
    actions: dict = master.get("actions", {})
    projects: dict = master.get("projects", {})

    # Read relevant view files (we care most about next_actions.md)
    view_files = [
        views_dir / "next_actions.md",
        views_dir / "projects.md",
        views_dir / "someday.md",
    ]

    completion_map: dict[str, bool] = {}
    for fp in view_files:
        if fp.exists():
            completion_map.update(_extract_completions_from_markdown(fp.read_text(encoding="utf-8")))

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
                completed_actions += 1

        elif item_id.startswith("p_") and item_id in projects:
            p = projects[item_id]
            if p.get("state") != "completed":
                p["state"] = "completed"
                p["completed"] = now
                completed_projects += 1

    # Prompt for next actions on stalled active projects
    if prompt_next:
        for pid, p in projects.items():
            if p.get("state") != "active":
                continue

            # Count active actions for this project
            active_count = 0
            for a in actions.values():
                if a.get("project") == pid and a.get("state") == "active":
                    active_count += 1

            if active_count == 0:
                _create_next_action_for_project(master, base_dir, pid)


    # Optional: auto-complete projects when no active actions remain (OFF by default)
    # (We can add a flag later, e.g. --auto-complete-projects)

    master["actions"] = actions
    master["projects"] = projects
    save_master(base_dir, master)

    print(f"Sync complete. Marked completed: {completed_actions} actions, {completed_projects} projects.")
    return 0
