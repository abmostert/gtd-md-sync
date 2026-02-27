#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from gtdlib.commands.add_cmd import cmd_add
from gtdlib.commands.init_cmd import cmd_init
from gtdlib.commands.build_cmd import cmd_build
from gtdlib.commands.sync_cmd import cmd_sync
from gtdlib.commands.context_cmd import cmd_context_list, cmd_context_add, cmd_context_drop
from gtdlib.commands.capture_cmd import cmd_capture
from gtdlib.commands.project_cmd import (
    cmd_project_list,
    cmd_project_edit,
    cmd_project_complete,
    cmd_project_delete,
    cmd_project_archive_finalize,
    cmd_project_trash_purge,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gtd",
        description="GTD Markdown generator + sync (prototype)",
    )

    # Global workspace directory (applies to all commands)
    parser.add_argument(
        "--dir",
        default=".",
        help="GTD workspace directory (default: current directory)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create master.json + views/ with starter Markdown files")

    p_add = sub.add_parser("add", help="Interactive add (project/action)")
    p_add.add_argument("--full", action="store_true", help="Use full prompts (ask all fields). Default is quick mode.")

    p_build = sub.add_parser("build", help="Generate Markdown views from master.json")

    p_sync = sub.add_parser("sync", help="Import checkbox completions from Markdown into master.json")
    p_sync.add_argument("--no-prompt-next", action="store_true", help="Do not prompt for next actions after sync")

    p_context = sub.add_parser("context", help="Manage allowed contexts")
    subc = p_context.add_subparsers(dest="context_cmd", required=True)

    subc.add_parser("list", help="List contexts")

    p_c_add = subc.add_parser("add", help="Add a context")
    p_c_add.add_argument("name", help="Context name (e.g. errands)")

    p_c_drop = subc.add_parser("drop", help="Drop a context")
    p_c_drop.add_argument("name", help="Context name to remove")

    p_project = sub.add_parser("project", help="Project operations")
    proj = p_project.add_subparsers(dest="proj_cmd", required=True)

    p_proj_list = proj.add_parser("list", help="List projects")
    p_proj_list.add_argument("--state", default="", help="Filter by state (active/someday/completed)")

    p_proj_edit = proj.add_parser("edit", help="Edit a project")

    p_proj_complete = proj.add_parser("complete", help="Mark a project completed and move folder to review/")
    # no args yet

    p_proj_delete = proj.add_parser("delete", help="Move project folder to trash/ (soft delete) or permanently delete")
    p_proj_delete.add_argument("--hard", action="store_true", help="Permanently delete immediately")

    p_proj_archive = proj.add_parser("archive-finalize", help="Finalize review: archive folder + remove from master.json")

    p_proj_purge = proj.add_parser("trash-purge", help="Purge trashed projects older than N days")
    p_proj_purge.add_argument("--dry-run", action="store_true", help="Show what would be purged without deleting")
    p_proj_purge.add_argument("--days", type=int, default=28, help="Retention period in days (default: 28)")

    p_capture = sub.add_parser("capture", help="Fetch capture emails into inbox/inbox.md")
    p_capture.add_argument("--limit", type=int, default=50, help="Max emails to fetch (default: 50)")

    args = parser.parse_args()
    base_dir = Path(args.dir).expanduser().resolve()

    if args.cmd == "init":
        return cmd_init(base_dir)

    if args.cmd == "add":
        return cmd_add(base_dir)

    if args.cmd == "build":
        return cmd_build(base_dir)

    if args.cmd == "sync":
        return cmd_sync(base_dir, prompt_next=not args.no_prompt_next)

    if args.cmd == "context":
        if args.context_cmd == "list":
            return cmd_context_list(base_dir)
        if args.context_cmd == "add":
            return cmd_context_add(base_dir, args.name)
        if args.context_cmd == "drop":
            return cmd_context_drop(base_dir, args.name)

    if args.cmd == "project":
        if args.proj_cmd == "list":
            state = args.state.strip() or None
            return cmd_project_list(base_dir, state=state)
        if args.proj_cmd == "edit":
            return cmd_project_edit(base_dir)
        if args.proj_cmd == "complete":
            return cmd_project_complete(base_dir)
        if args.proj_cmd == "delete":
            return cmd_project_delete(base_dir, hard=bool(args.hard))
        if args.proj_cmd == "archive-finalize":
            return cmd_project_archive_finalize(base_dir)
        if args.proj_cmd == "trash-purge":
            return cmd_project_trash_purge(base_dir, dry_run=bool(args.dry_run), days=int(args.days))

    if args.cmd == "capture":
        return cmd_capture(base_dir, limit=args.limit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
