from __future__ import annotations

from pathlib import Path

from gtdlib.store import load_master, new_id, save_master, utc_now_iso
from gtdlib.config import get_contexts

from gtdlib.prompts.action_prompts import prompt_action_draft, render_action_preview
from gtdlib.prompts.confirm import confirm_save_redo_cancel
from gtdlib.prompts.selectors import choose_project_id


def cmd_add(base_dir: Path) -> int:
    """
    Interactive add command.

    - Adds either an action or a project to master.json.
    - Uses shared prompting in gtdlib/prompts to keep behavior consistent
      across add + sync-stalled prompts.
    - Includes preview + confirm step: Save / Redo / Cancel.
    """
    master = load_master(base_dir)
    now = utc_now_iso()

    # Contexts are enforced by config (except for waiting actions)
    contexts = get_contexts(base_dir)

    kind = input("Add (a)ction or (p)roject? [a] ").strip().lower() or "a"
    if kind not in {"a", "p"}:
        print("Cancelled: please enter 'a' or 'p'.")
        return 2

    # -------------------------
    # ACTION BRANCH
    # -------------------------
    if kind == "a":
        while True:
            # optional project association (active projects only)
            project_id = choose_project_id(
                master.get("projects", {}),
                allow_states={"active"},
            )

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
                continue

            render_action_preview(draft)

            decision = confirm_save_redo_cancel()
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
        project_title = input("Project title (outcome): ").strip()
        if not project_title:
            print("Project title is required.")
            continue

        project_state = input("Project state (active/someday/completed/dropped): [active] ").strip().lower() or "active"
        if project_state not in {"active", "someday", "completed", "dropped"}:
            print("Invalid project state.")
            continue

        project_due = prompt_optional_date("Due date")
        project_notes = input("Project notes (optional): ").strip()

        # IMPORTANT: first next action for the project (shared prompt flow)
        try:
            first_action_draft = prompt_action_draft(
                base_dir=base_dir,
                contexts=contexts,
                now_iso=now,
                project_id=None,  # set after pid exists
                default_state=("active" if project_state == "active" else "someday"),
                ask_context_when_waiting=False,
            )
        except ValueError as e:
            print(str(e))
            continue

        # Create IDs
        pid = new_id("p")
        aid = new_id("a")

        # Attach project id onto action draft
        first_action_draft["project"] = pid

        project_draft = {
            "title": project_title,
            "state": project_state,
            "created": now,
            "reviewed": None,
            "due": project_due,
            "notes": project_notes,
        }

        print("\n--- Project preview ---")
        print(f"Project ID:    {pid}")
        print(f"Title:         {project_draft['title']}")
        print(f"State:         {project_draft['state']}")
        print(f"Due:           {project_draft.get('due')}")
        print(f"Notes:         {project_draft.get('notes')}")
        print("\n--- First action preview ---")
        print(f"Action ID:     {aid}")
        render_action_preview(first_action_draft)

        decision = confirm_save_redo_cancel()
        if decision == "c":
            print("Cancelled. Nothing saved.")
            return 0
        if decision == "r":
            print("Redoing...\n")
            continue

        master.setdefault("projects", {})[pid] = project_draft
        master.setdefault("actions", {})[aid] = first_action_draft
        save_master(base_dir, master)

        print(f"Added project {pid}: {project_title}")
        print(f"Added first action {aid}: {first_action_draft['title']}")
        return 0

