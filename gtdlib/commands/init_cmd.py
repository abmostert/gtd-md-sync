from __future__ import annotations

from pathlib import Path

from gtdlib.store import (
    VIEWS_DIRNAME,
    ensure_config,
    load_master,
    save_master,
    MASTER_SCHEMA_VERSION,
)


def cmd_init(base_dir: Path) -> int:
    """
    Initialize a GTD workspace in `base_dir`.

    Creates (if missing):
      - master.json
      - config.json
      - views/ (generated markdown views)
      - inbox/inbox.md (capture processing list)
      - inbox/attachments/ (saved email attachments)

    Does NOT overwrite existing master.json or config.json.
    Views may be (re)generated later via `gtd build`.
    """
    base_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # Core data files
    # -------------------------
    # config.json: create if missing (do NOT override)
    cfg = ensure_config(base_dir)

    # master.json: create if missing (do NOT override)
    master_path = base_dir / "master.json"
    if not master_path.exists():
        master = {
            "meta": {
                "version": MASTER_SCHEMA_VERSION,
            }
            "projects": {},
            "actions": {},
        }
        save_master(base_dir, master)
    else:
        # sanity: can we load it?
        _ = load_master(base_dir)

    # -------------------------
    # Workspace folders
    # -------------------------
    views_dir = base_dir / VIEWS_DIRNAME
    views_dir.mkdir(parents=True, exist_ok=True)

    inbox_dir = base_dir / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    attachments_dir = inbox_dir / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # Seed inbox file (capture processing)
    # -------------------------
    inbox_md = inbox_dir / "inbox.md"
    if not inbox_md.exists():
        inbox_md.write_text(
            "# Inbox\n\n"
            "> Temporary capture list. Tick items as you process them.\n"
            "> `gtd sync` will prune checked items from this file.\n\n",
            encoding="utf-8",
        )

    # -------------------------
    # Seed view files (optional convenience)
    # -------------------------
    # Don’t force-build if you prefer init to be minimal.
    # But it’s safe to generate empty views now (views are disposable).
    try:
        from gtdlib.commands.build_cmd import cmd_build
        cmd_build(base_dir)
    except Exception as e:
        print(f"Init note: could not build initial views ({e}). You can run `gtd build` later.")

    # -------------------------
    # Friendly summary
    # -------------------------
    print("Initialized GTD workspace:")
    print(f"  Base:        {base_dir}")
    print(f"  master.json:  {base_dir / 'master.json'}")
    print(f"  config.json:  {base_dir / 'config.json'}")
    print(f"  views/:       {views_dir}")
    print(f"  inbox/:       {inbox_dir}")
    print(f"  attachments/: {attachments_dir}")

    return 0

