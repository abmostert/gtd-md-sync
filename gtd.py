#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


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

    # Stubs for later
    sub.add_parser("add", help="Interactive add (project/action)")
    sub.add_parser("build", help="Generate Markdown views from master.json")
    sub.add_parser("sync", help="Import checkbox completions from Markdown into master.json")

    args = parser.parse_args()

    if args.cmd == "init":
        base_dir = Path(args.dir).expanduser().resolve()
        return cmd_init(base_dir)

    # For now, keep these as placeholders
    print(f"Command received: {args.cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

