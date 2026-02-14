
from __future__ import annotations
from pathlib import Path
from gtdlib.store import (
    load_master,
    new_id,
    prompt,
    prompt_optional_date,
    save_master,
    utc_now_iso,
    ensure_config,
    normalize_context,
)
from gtdlib.prompts.action_prompts import prompt_action_draft, render_action_preview

def cmd_add(base_dir: Path) -> int:
    """
    Interactive add command.

    - Adds either an action or a project to master.json.
    - For projects, enforces entering the first next action (your GTD rule).
    - Includes a preview + confirm step: Save / Redo / Cancel.
    """

    def choose_project_id(projects: dict, *, allow_states: set[str] | None = None) -> str | None:
        """
        Return a project_id (e.g. 'p_abcd1234') or None for standalone.
        allow_states: if provided, only show projects whose state is in allow_states.
        """
        # Filter projects for display
        rows: list[tuple[str, str]] = []
        for pid, p in projects.items():
            state = (p.get("state") or "").strip().lower()
            if allow_states and state not in allow_states:
                continue
            title = (p.get("title") or "").strip()
            if not title:
                title = pid
            rows.append((pid, title))

        rows.sort(key=lambda t: t[1].lower())

        print("\nAssociate this action with a project?")
        print("  0. None (standalone action)")
        if not rows:
            return None

        for i, (_, title) in enumerate(rows, start=1):
            print(f"  {i}. {title}")

        while True:
            raw = input("Choose project (number): ").strip()
            if raw == "" or raw == "0":
                return None
            if raw.isdigit():
                idx = int(raw)
                if 1 <= idx <= len(rows):
                    return rows[idx - 1][0]
            print("Invalid choice. Enter 0 for none, or a number from the list.")
    
    def choose_context(contexts: list[str]) -> str:
        """
        Force selection from configured contexts.
        User can type the number or exact context name.
        """
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
            else:
                cand = normalize_context(raw)
                if cand in {"waiting_for", "waiting"}:
                    print("'waiting_for' is not a context (it's a state). Choose a real context like work/home/virtual.")
                    continue
                if cand in contexts:
                    return cand
            print("Invalid context. Choose a number from the list or type an exact context name.")

    def confirm_or_redo() -> str:
        """
        Returns:
          's' = save
          'r' = redo
          'c' = cancel (exit without saving)
        """
        while True:
            choice = input("Save (s), redo (r), or cancel (c)? [s] ").strip().lower()
            if choice == "":
                return "s"
            if choice in {"s", "r", "c"}:
                return choice
            print("Please enter s, r, or c.")

    master = load_master(base_dir)

    cfg = ensure_config(base_dir)
    contexts = [normalize_context(c) for c in cfg.get("contexts", [])]
    contexts = sorted(set(contexts))

    now = utc_now_iso()

    kind = prompt("Add (a)ction or (p)roject? ", default="a").lower()
    if kind not in {"a", "p"}:
        print("Cancelled: please enter 'a' or 'p'.")
        return 2

    # -------------------------
    # ACTION BRANCH
    # -------------------------
    if kind == "a":
    while True:
        project_id = choose_project_id(master.get("projects", {}), allow_states={"active"})

        try:
            draft = prompt_action_draft(
                base_dir,
                contexts,
                now_iso=now,
                project_id=project_id,
                default_state="active",
                ask_context_when_waiting=False,
            )
        except ValueError as e:
            print(str(e))
            continue

        render_action_preview(draft)

        decision = confirm_or_redo()
        if decision == "c":
            print("Cancelled. Nothing saved.")
            return 0
        if decision == "r":
            print("Redoing...\n")
            continue

        aid = new_id("a")
        master.setdefault("actions", {})[aid] = draft
        save_master(base_dir, master)
        print(f"Added action {aid}: {draft['title']}")
        return 0

    # -------------------------
    # PROJECT BRANCH
    # -------------------------
    # If we reach here, kind == "p"
    while True:
        project_title = prompt("Project title (outcome): ")
        if not project_title:
            print("Project title is required.")
            continue

        project_state = prompt("Project state (active/someday/completed/dropped): ", default="active")
        project_due = prompt_optional_date("Project due date")
        project_notes = prompt("Project notes (optional): ", default="")

        project_draft = {
            "title": project_title,
            "state": project_state,
            "created": now,
            "reviewed": None,
            "due": project_due,
            "notes": project_notes,
        }

        try:
            action_draft = prompt_action_draft(
            base_dir,
            contexts,
            now_iso=now,
            project_id=None,  # set after pid exists
            default_state=("active" if project_state == "active" else "someday"),
            ask_context_when_waiting=False,
        )
        except ValueError as e:
            print(str(e))
            continue

        pid = new_id("p")
        aid = new_id("a")

        action_draft["project"] = pid

        render_action_preview(action_draft)

        decision = confirm_or_redo()
        if decision == "c":
            print("Cancelled. Nothing saved.")
            return 0
        if decision == "r":
            print("Redoing...\n")
            continue

        master.setdefault("projects", {})[pid] = project_draft
        master.setdefault("actions", {})[aid] = action_draft

        save_master(base_dir, master)
        print(f"Added project {pid}: {project_title}")
        print(f"Added first action {aid}: {first_action}")
        return 0
