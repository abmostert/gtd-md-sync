from __future__ import annotations

from pathlib import Path
import re

from gtdlib.store import load_master, save_master, utc_now_iso, VIEWS_DIRNAME

ID_COMMENT_RE = re.compile(r"<!--\s*id:(?P<id>[^>]+?)\s*-->")
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.*)$")


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


def cmd_sync(base_dir: Path) -> int:
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

    # Optional: auto-complete projects when no active actions remain (OFF by default)
    # (We can add a flag later, e.g. --auto-complete-projects)

    master["actions"] = actions
    master["projects"] = projects
    save_master(base_dir, master)

    print(f"Sync complete. Marked completed: {completed_actions} actions, {completed_projects} projects.")
    return 0
