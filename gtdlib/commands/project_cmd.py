from __future__ import annotations

from pathlib import Path

from gtdlib.store import (
    load_master,
    save_master,
    prompt,
    prompt_optional_date,
    utc_now_iso,
    ensure_config,
    normalize_context,
)
from gtdlib.prompts.action_prompts import prompt_action_draft, render_action_preview
from gtdlib.rules.projects import count_actions_by_state
from gtdlib.prompts.selectors import choose_project_id



def cmd_project_list(base_dir: Path, *, state: str | None = None) -> int:
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    want_state = (state or "").strip().lower() if state else None

    rows: list[tuple[str, str, str]] = []
    for pid, p in projects.items():
        st = (p.get("state") or "unknown").strip().lower()
        if want_state and st != want_state:
            continue
        title = (p.get("title") or "").strip() or pid
        rows.append((pid, title, st))

    if not rows:
        print("No projects.")
        return 0

    rows.sort(key=lambda t: (t[2], t[1].lower()))

    print("\nProjects:")
    for pid, title, st in rows:
        counts = count_actions_by_state(actions, pid)
        active = counts.get("active", 0)
        waiting = counts.get("waiting", 0)
        someday = counts.get("someday", 0)
        due = projects.get(pid, {}).get("due")
        due_s = f", due {due}" if due else ""
        print(f"- {title} ({st}{due_s}) — actions: active={active}, waiting={waiting}, someday={someday} [{pid}]")

    return 0


def cmd_project_edit(base_dir: Path) -> int:
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    pid = choose_project_id(projects)
    if not pid:
        print("Cancelled.")
        return 0

    p = projects.get(pid)
    if not p:
        print("Project not found.")
        return 2

    # Show summary
    title = (p.get("title") or pid).strip()
    state = (p.get("state") or "unknown").strip().lower()
    due = p.get("due")
    notes = p.get("notes") or ""
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
    if choice == "3" or choice == "":
        print("Cancelled.")
        return 0

    now = utc_now_iso()

    # ---- 1) edit fields ----
    if choice == "1":
        new_title = prompt("Title", default=title)
        new_state = prompt("State (active/someday/completed/dropped)", default=state).strip().lower()
        if new_state not in {"active", "someday", "completed", "dropped"}:
            print("Invalid state. No changes saved.")
            return 2

        new_due = prompt_optional_date("Due date")
        new_notes = prompt("Notes", default=notes)

        p["title"] = new_title
        p["state"] = new_state
        p["due"] = new_due
        p["notes"] = new_notes
        p["reviewed"] = p.get("reviewed")  # keep existing field if present

        projects[pid] = p
        master["projects"] = projects
        save_master(base_dir, master)
        print("Project updated.")
        return 0

    # ---- 2) add action ----
    if choice == "2":
        cfg = ensure_config(base_dir)
        contexts = [normalize_context(c) for c in cfg.get("contexts", [])]
        contexts = sorted(set(contexts))

        try:
            draft = prompt_action_draft(
                base_dir,
                contexts,
                now_iso=now,
                project_id=pid,
                default_state="active",
                ask_context_when_waiting=False,
            )
        except ValueError as e:
            print(str(e))
            return 2

        render_action_preview(draft)
        confirm = input("Save this action? [Y/n]: ").strip().lower()
        if confirm in ("n", "no"):
            print("Cancelled. Not saved.")
            return 0

        # allocate a new action id via store.new_id if you prefer,
        # but prompt_action_draft returns the dict only, so we assign id here.
        from gtdlib.store import new_id
        aid = new_id("a")
        actions[aid] = draft

        master["actions"] = actions
        save_master(base_dir, master)
        print(f"Added action {aid} to project {pid}.")
        return 0

    print("Invalid choice.")
    return 2

