from __future__ import annotations

from pathlib import Path
from datetime import date

from gtdlib.store import (
    load_master,
    save_master,
    new_id,
    prompt,
    prompt_optional_date,
    utc_now_iso,
    ensure_config,
    normalize_context,
)


def _choose_context_from_config(base_dir: Path) -> str:
    cfg = ensure_config(base_dir)
    contexts = [normalize_context(c) for c in cfg.get("contexts", [])]
    contexts = sorted(set(contexts))
    if not contexts:
        raise RuntimeError("No contexts configured. Add contexts with `gtd context add ...`.")

    print("\nAvailable contexts:")
    for i, c in enumerate(contexts, start=1):
        print(f"  {i}. {c}")

    while True:
        raw = input("Choose context (number or name): ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(contexts):
                return contexts[idx - 1]
        cand = normalize_context(raw)
        if cand in contexts:
            return cand
        print("Invalid context. Choose a number or exact context name.")


def _pick_project(projects: dict, *, allow_states: set[str]) -> str | None:
    rows: list[tuple[str, str, str]] = []
    for pid, p in projects.items():
        st = (p.get("state") or "").strip().lower()
        if st not in allow_states:
            continue
        title = (p.get("title") or "").strip() or pid
        due = (p.get("due") or "")
        rows.append((pid, title, due))

    if not rows:
        print("No projects found for the selected states.")
        return None

    rows.sort(key=lambda t: (t[2] or "9999-12-31", t[1].lower()))

    filt = input("Filter (optional substring, blank for all): ").strip().lower()
    if filt:
        rows = [r for r in rows if filt in r[1].lower()]
        if not rows:
            print("No projects match that filter.")
            return None

    print("\nProjects:")
    for i, (pid, title, due) in enumerate(rows, start=1):
        due_s = f" (due {due})" if due else ""
        print(f"  {i}. {title}{due_s} [{pid}]")

    while True:
        raw = input("Choose project (number, blank to cancel): ").strip()
        if raw == "":
            return None
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(rows):
                return rows[idx - 1][0]
        print("Invalid choice.")


def cmd_project_list(base_dir: Path) -> int:
    master = load_master(base_dir)
    projects = master.get("projects", {})

    if not projects:
        print("No projects.")
        return 0

    rows = []
    for pid, p in projects.items():
        title = (p.get("title") or "").strip() or pid
        state = (p.get("state") or "").strip()
        due = p.get("due") or ""
        rows.append((due or "9999-12-31", title.lower(), pid, title, state, due))

    rows.sort()
    for _, __, pid, title, state, due in rows:
        due_s = f" (due {due})" if due else ""
        print(f"- {title} [{state}]{due_s} ({pid})")
    return 0


def cmd_project_edit(base_dir: Path) -> int:
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    # Default: edit active projects
    pid = _pick_project(projects, allow_states={"active", "someday"})
    if not pid:
        print("Cancelled.")
        return 0

    p = projects[pid]

    print("\nCurrent project:")
    print(f"  ID:    {pid}")
    print(f"  Title: {p.get('title','')}")
    print(f"  State: {p.get('state','')}")
    print(f"  Due:   {p.get('due')}")
    print(f"  Notes: {p.get('notes','')}")

    # --- edits (blank keeps existing) ---
    new_title = input("New title (blank = keep): ").strip()
    if new_title:
        p["title"] = new_title

    new_state = input("New state [active/someday/completed/dropped] (blank = keep): ").strip().lower()
    if new_state:
        if new_state not in {"active", "someday", "completed", "dropped"}:
            print("Invalid state; keeping existing.")
        else:
            p["state"] = new_state

    raw_due = input("New due date YYYY-MM-DD (blank = keep, '-' = clear): ").strip()
    if raw_due == "-":
        p["due"] = None
    elif raw_due:
        try:
            date.fromisoformat(raw_due)
            p["due"] = raw_due
        except ValueError:
            print("Invalid date; keeping existing.")

    new_notes = input("New notes (blank = keep): ").strip()
    if new_notes:
        p["notes"] = new_notes

    # --- optionally add actions ---
    while True:
        ans = input("Add an action to this project now? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            break

        title = prompt("Action title: ")
        if not title:
            print("Action title required.")
            continue

        context = _choose_context_from_config(base_dir)
        due = prompt_optional_date("Due date")
        notes = prompt("Notes (optional): ", default="")

        now = utc_now_iso()
        aid = new_id("a")
        actions[aid] = {
            "title": title,
            "project": pid,
            "state": "active",
            "context": context,
            "created": now,
            "last_touched": now,
            "waiting_since": None,
            "waiting_for": None,
            "due": due,
            "notes": notes,
        }
        print(f"Added action {aid}")

    # Save
    projects[pid] = p
    master["projects"] = projects
    master["actions"] = actions
    save_master(base_dir, master)

    print("Project updated.")
    return 0
