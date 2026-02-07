#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from gtdlib.commands.add_cmd import cmd_add
from gtdlib.commands.init_cmd import cmd_init
from gtdlib.commands.build_cmd import cmd_build
from gtdlib.commands.sync_cmd import cmd_sync
from gtdlib.commands.context_cmd import cmd_context_list, cmd_context_add, cmd_context_drop
from gtdlib.commands.project_cmd import cmd_project_list, cmd_project_edit



def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gtd",
        description="GTD Markdown generator + sync (prototype)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create master.json + views/ with starter Markdown files")
    p_init.add_argument("--dir", default=".", help="Directory to initialize in (default: current directory)")

    p_add = sub.add_parser("add", help="Interactive add (project/action)")
    p_add.add_argument("--dir", default=".", help="GTD workspace directory (default: current directory)")

    p_build = sub.add_parser("build", help="Generate Markdown views from master.json")
    p_build.add_argument("--dir", default=".", help="GTD workspace directory (default: current directory)")

    p_sync = sub.add_parser("sync", help="Import checkbox completions from Markdown into master.json")
    p_sync.add_argument("--dir", default=".", help="GTD workspace directory (default: current directory)")
    p_sync.add_argument("--no-prompt-next", action="store_true", help="Do not prompt for next actions after sync")

    p_context = sub.add_parser("context", help="Manage allowed contexts")
    p_context.add_argument("--dir", default=".", help="GTD workspace directory (default: current directory)")
    subc = p_context.add_subparsers(dest="context_cmd", required=True)

    p_c_list = subc.add_parser("list", help="List contexts")

    p_c_add = subc.add_parser("add", help="Add a context")
    p_c_add.add_argument("name", help="Context name (e.g. errands)")

    p_c_drop = subc.add_parser("drop", help="Drop a context")
    p_c_drop.add_argument("name", help="Context name to remove")

    p_project = sub.add_parser("project", help="Project operations")
    p_project.add_argument("--dir", default=".", help="GTD workspace directory (default: current directory)")
    proj = p_project.add_subparsers(dest="proj_cmd", required=True)

    p_proj_list = proj.add_parser("list", help="List projects")
    p_proj_edit = proj.add_parser("edit", help="Edit a project")


    args = parser.parse_args()

    if args.cmd == "init":
        base_dir = Path(args.dir).expanduser().resolve()
        return cmd_init(base_dir)

    if args.cmd == "add":
        base_dir = Path(args.dir).expanduser().resolve()
        return cmd_add(base_dir)

    if args.cmd == "build":
        base_dir = Path(args.dir).expanduser().resolve()
        return cmd_build(base_dir)


    if args.cmd == "sync":
        base_dir = Path(args.dir).expanduser().resolve()
        return cmd_sync(base_dir, prompt_next=not args.no_prompt_next)

    if args.cmd == "context":
        base_dir = Path(args.dir).expanduser().resolve()
        if args.context_cmd == "list":
            return cmd_context_list(base_dir)
        if args.context_cmd == "add":
            return cmd_context_add(base_dir, args.name)
        if args.context_cmd == "drop":
            return cmd_context_drop(base_dir, args.name)

    if args.cmd == "project":
        base_dir = Path(args.dir).expanduser().resolve()
        if args.proj_cmd == "list":
            return cmd_project_list(base_dir)
        if args.proj_cmd == "edit":
            return cmd_project_edit(base_dir)



    return 0


if __name__ == "__main__":
    raise SystemExit(main())
