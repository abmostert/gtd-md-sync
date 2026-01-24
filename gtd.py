#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from gtdlib.commands.add_cmd import cmd_add
from gtdlib.commands.init_cmd import cmd_init
from gtdlib.commands.build_cmd import cmd_build
from gtdlib.commands.sync_cmd import cmd_sync


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
        return cmd_sync(base_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
