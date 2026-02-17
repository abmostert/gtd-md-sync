from __future__ import annotations

from pathlib import Path

from gtdlib.store import load_master, new_id, save_master, utc_now_iso
from gtdlib.config import get_contexts

from gtdlib.prompts.action_prompts import prompt_action_draft, render_action_preview
from gtdlib.prompts.confirm import confirm_save_redo_cancel
from gtdlib.prompts.selectors import choose_project_id

from gtdlib.prompts.project_prompts import prompt_project_draft, render_project_preview
from gtdlib.commands.build_project_notes import ensure_project_notes_for_project




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
        # -------------------------
    # PROJECT BRANCH
    # -------------------------
    # If we reach here, kind == "p"
    while True:
        try:
            project_draft = prompt_project_draft(base_dir, now_iso=now, default_state="active")
        except ValueError as e:
            print(str(e))
            continue

        # Create IDs early so the previews show the real IDs
        pid = new_id("p")
        aid = new_id("a")

        # First next action: reuse your unified action prompt
        try:
            first_action_draft = prompt_action_draft(
                base_dir,
                contexts,
                now_iso=now,
                project_id=pid,
                default_state="active",
                ask_context_when_waiting=False,
            )
        except ValueError as e:
            print(str(e))
            # let them redo the whole project flow
            continue

        # Preview
        render_project_preview(pid, project_draft)
        print("--- First action preview ---")
        print(f"Action ID:  {aid}")
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

        # Create/update project folder + project_notes.md immediately (active projects only)
        try:
            ensure_project_notes_for_project(
                base_dir=base_dir,
                pid=pid,
                project=project_draft,
                actions=master.get("actions", {}),
            )
        except Exception as e:
            # Non-fatal: project creation succeeded; notes creation can be repaired via `gtd build`
            print(f"Note: could not write project notes file ({e}). Run `gtd build` to regenerate.")

        
        print(f"Added project {pid}: {project_draft['title']}")
        print(f"Added first action {aid}: {first_action_draft['title']}")
        return 0



