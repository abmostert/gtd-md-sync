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


def _prune_checked_inbox_md(inbox_md: Path) -> int:
    """
    Remove any top-level '- [x]' items and their indented continuation lines.
    Returns number of removed items.
    """
    if not inbox_md.exists():
        return 0

    lines = inbox_md.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    removed = 0
    i = 0

    def is_top_item(line: str) -> bool:
        s = line.lstrip("\ufeff")
        return s.startswith("- [")  # top-level list item

    while i < len(lines):
        line = lines[i]
        s = line.lstrip("\ufeff")

        if s.startswith("- [x]") or s.startswith("- [X]"):
            removed += 1
            i += 1
            # skip continuation lines until next top-level item or EOF
            while i < len(lines) and (not is_top_item(lines[i]) and lines[i].strip() != "- [ ]" ):
                # continuation lines usually start with two spaces, but we just skip until next '- ['
                if is_top_item(lines[i]):
                    break
                i += 1
            # also skip blank lines immediately following the item block
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            continue

        out.append(line)
        i += 1

    inbox_md.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return removed


def _prompt_action_state() -> str:
    raw = input("State (active/waiting/someday) [active]: ").strip().lower()
    return raw or "active"


def _prompt_waiting_for() -> str | None:
    who = input("Waiting for (person/thing): ").strip()
    return who or None


def _create_next_action_for_project(master: dict, base_dir, project_id: str, actions: dict) -> str | None:
    projects = master.get("projects", {})
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

           
    # IMPORTANT: state first (matches add flow)
    state = _prompt_action_state()
    if state not in {"active", "waiting", "someday"}:
        print("Invalid state. Using active.")
        state = "active"

    context = None
    if state == "waiting":
        waiting_for = _prompt_waiting_for()
    else:
    # Then context (must be a real context, not "waiting_for")
        context = _choose_context_from_config(base_dir)

    due = _prompt_due_date()

    aid = new_id("a")
    now = utc_now_iso()

    action = {
        "title": a_title,
        "context": context,
        "state": state,
        "project": project_id,
        "created": now,
        "last_touched": now,
        "waiting_since": now if state == "waiting" else None,
        "waiting_for": waiting_for,   # NEW FIELD
        "due": due,
        "notes": "",
    }

    actions[aid] = action
    return aid



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

        if cand in {"waiting_for", "waiting"}:
            print("'waiting_for' is not a context (it's a state). Choose a real context like work/home/virtual.")
            continue

        
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
        views_dir / "waiting_for.md",
        views_dir / "agenda.md",
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
            if _count_active_actions_for_project(actions, pid) == 0:
                _create_next_action_for_project(master, base_dir, pid, actions)

    # Also prune completed capture items from inbox/inbox.md (no IDs; purely structural)
    pruned = _prune_checked_inbox_md(base_dir / "inbox" / "inbox.md")
    if pruned:
        print(f"Pruned {pruned} checked capture item(s) from inbox/inbox.md")


    # Optional: auto-complete projects when no active actions remain (OFF by default)
    # (We can add a flag later, e.g. --auto-complete-projects)

    master["actions"] = actions
    master["projects"] = projects
    save_master(base_dir, master)

    print(f"Sync complete. Marked completed: {completed_actions} actions, {completed_projects} projects.")
    return 0
