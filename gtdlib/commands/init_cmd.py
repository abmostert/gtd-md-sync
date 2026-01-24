
from __future__ import annotations

from pathlib import Path

from gtdlib.store import (
    MASTER_FILENAME,
    VIEW_FILES,
    VIEWS_DIRNAME,
    utc_now_iso,
    write_json_if_missing,
    write_text_if_missing,
)


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
            "version": 1,
        },
        "projects": {},
        "actions": {},
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
