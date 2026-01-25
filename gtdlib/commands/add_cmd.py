
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


def cmd_add(base_dir: Path) -> int:
    """
    Interactive add command.

    - Adds either an action or a project to master.json.
    - For projects, enforces entering the first next action (your GTD rule).
    - Includes a preview + confirm step: Save / Redo / Cancel.
    """

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
            title = prompt("Action title: ")
            if not title:
                print("Action title is required.")
                continue

            context = choose_context(contexts)
            state = prompt("State (active/someday/waiting/completed/dropped): ", default="active")
            due = prompt_optional_date("Due date")
            notes = prompt("Notes (optional): ", default="")

            draft = {
                "title": title,
                "project": None,
                "state": state,
                "context": context,
                "created": now,
                "last_touched": now,
                "waiting_since": now if state == "waiting" else None,
                "due": due,
                "notes": notes,
            }

            print("\n--- Action preview ---")
            print(f"Title:   {draft['title']}")
            print(f"State:   {draft['state']}")
            print(f"Context: {draft['context']}")
            print(f"Due:     {draft['due']}")
            print(f"Notes:   {draft['notes']}")
            print("----------------------\n")

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
            print(f"Added action {aid}: {title}")
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

        first_action = prompt("First next action for this project: ")
        if not first_action:
            print("First next action is required for a project.")
            continue

        first_context = prompt("Context for that next action: ", default="inbox")
        first_due = prompt_optional_date("Due date for that next action")
        first_notes = prompt("Notes for that next action (optional): ", default="")

        pid = new_id("p")
        aid = new_id("a")

        project_draft = {
            "title": project_title,
            "state": project_state,
            "created": now,
            "reviewed": None,
            "due": project_due,
            "notes": project_notes,
        }

        action_state = "active" if project_state == "active" else project_state
        action_draft = {
            "title": first_action,
            "project": pid,
            "state": action_state,
            "context": first_context,
            "created": now,
            "last_touched": now,
            "waiting_since": now if action_state == "waiting" else None,
            "due": first_due,
            "notes": first_notes,
        }

        print("\n--- Project preview ---")
        print(f"Project ID:    {pid}")
        print(f"Title:         {project_draft['title']}")
        print(f"State:         {project_draft['state']}")
        print(f"Due:           {project_draft['due']}")
        print(f"Notes:         {project_draft['notes']}")
        print("\n--- First action preview ---")
        print(f"Action ID:     {aid}")
        print(f"Title:         {action_draft['title']}")
        print(f"State:         {action_draft['state']}")
        print(f"Context:       {action_draft['context']}")
        print(f"Due:           {action_draft['due']}")
        print(f"Notes:         {action_draft['notes']}")
        print("----------------------------\n")

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
