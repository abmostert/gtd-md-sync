#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


MASTER_FILENAME = "master.json"
VIEWS_DIRNAME = "views"

VIEW_FILES = {
    "next_actions.md": "# Next Actions\n\n",
    "projects.md": "# Projects\n\n",
    "someday.md": "# Someday / Maybe\n\n",
    "focus.md": "# Focus\n\n",
}


def utc_now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_master(base_dir: Path) -> dict:
    master_path = base_dir / MASTER_FILENAME
    if not master_path.exists():
        raise FileNotFoundError(
            f"No {MASTER_FILENAME} found in {base_dir}. Run `gtd init` first."
        )
    return json.loads(master_path.read_text(encoding="utf-8"))


def save_master(base_dir: Path, master: dict) -> None:
    master_path = base_dir / MASTER_FILENAME
    master.setdefault("meta", {})
    master["meta"]["updated"] = utc_now_iso()
    master_path.write_text(
        json.dumps(master, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def new_id(prefix: str) -> str:
    """Create a short unique-ish ID like a_3f9c2a1b or p_d0a41c7e."""
    return f"{prefix}_{uuid4().hex[:8]}"


def prompt(text: str, default: str | None = None) -> str:
    """
    Simple input() wrapper with optional default.
    Empty input returns default (if provided).
    """
    if default is None:
        return input(text).strip()
    s = input(f"{text} [{default}] ").strip()
    return s if s else default


def prompt_optional_date(text: str) -> str | None:
    """Accept YYYY-MM-DD or empty for None. (No strict validation in v1.)"""
    s = input(f"{text} (YYYY-MM-DD, or blank): ").strip()
    return s or None


def cmd_add(base_dir: Path) -> int:
    """
    Interactive add command.

    - Adds either an action or a project to master.json.
    - For projects, enforces entering the first next action (your GTD rule).
    - Includes a preview + confirm step: Save / Redo / Cancel.
    """

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

            context = prompt("Context (e.g. home/work/phone/computer): ", default="inbox")
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

        # Draft objects (do not write yet)
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

        # Keep state consistent: if project isn't active, first action matches.
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

        # Commit both drafts
        master.setdefault("projects", {})[pid] = project_draft
        master.setdefault("actions", {})[aid] = action_draft

        save_master(base_dir, master)
        print(f"Added project {pid}: {project_title}")
        print(f"Added first action {aid}: {first_action}")
        return 0


def write_text_if_missing(path: Path, content: str) -> bool:
    """
    Write a text file only if it doesn't already exist.
    Returns True if created, False if skipped.
    """
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def write_json_if_missing(path: Path, obj: dict) -> bool:
    """
    Write a JSON file only if it doesn't already exist.
    Returns True if created, False if skipped.
    """
    if path.exists():
        return False
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True



def cmd_init(base_dir: Path) -> int:
    """
    Initialize a new GTD workspace in base_dir:
    - master.json
    - views/ directory
    - starter markdown view files
    """
    created_anything = False

    # 1) Ensure views/ exists
    views_dir = base_dir / VIEWS_DIRNAME
    if not views_dir.exists():
        views_dir.mkdir(parents=True)
        print(f"Created folder: {views_dir}")
        created_anything = True
    else:
        print(f"Folder exists:  {views_dir}")

    # 2) Create master.json if missing
    master_path = base_dir / MASTER_FILENAME
    empty_master = {
        "meta": {
            "created": utc_now_iso(),
            "updated": utc_now_iso(),
            "version": 1
        },
        "projects": {},
        "actions": {}
    }
    if write_json_if_missing(master_path, empty_master):
        print(f"Created file:   {master_path}")
        created_anything = True
    else:
        print(f"File exists:    {master_path}")

    # 3) Create view files if missing
    for filename, starter in VIEW_FILES.items():
        p = views_dir / filename
        if write_text_if_missing(p, starter):
            print(f"Created file:   {p}")
            created_anything = True
        else:
            print(f"File exists:    {p}")

    if not created_anything:
        print("Nothing to do — workspace already initialized.")
    else:
        print("Init complete.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gtd",
        description="GTD Markdown generator + sync (prototype)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create master.json + views/ with starter Markdown files")
    p_init.add_argument(
        "--dir",
        default=".",
        help="Directory to initialize in (default: current directory)"
    )

    p_add = sub.add_parser("add", help="Interactive add (project/action)")
    p_add.add_argument("--dir", default=".", help="GTD workspace directory (default: current directory)")

    
    # Stubs for later
    sub.add_parser("build", help="Generate Markdown views from master.json")
    sub.add_parser("sync", help="Import checkbox completions from Markdown into master.json")

    args = parser.parse_args()

    if args.cmd == "init":
        base_dir = Path(args.dir).expanduser().resolve()
        return cmd_init(base_dir)

    if args.cmd == "add":
        base_dir = Path(args.dir).expanduser().resolve()
        return cmd_add(base_dir)


    # For now, keep these as placeholders
    print(f"Command received: {args.cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

