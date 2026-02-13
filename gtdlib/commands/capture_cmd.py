# gtdlib/commands/capture_cmd.py
from __future__ import annotations

from pathlib import Path

from gtdlib.store import ensure_config
from gtdlib.capture.proton_bridge_imap import capture_folder_to_inbox_md


def cmd_capture(base_dir: Path, *, dry_run: bool = False, all_mail: bool = False) -> int:
    """
    Capture emails from Proton Bridge into inbox/inbox.md (workspace data),
    save attachments to inbox/attachments, then delete the emails from the capture folder.
    """
    cfg = ensure_config(base_dir)
    cap = cfg.get("capture") or {}

    host = cap.get("imap_host", "127.0.0.1")
    port = int(cap.get("imap_port", 1143))
    user = cap.get("imap_user")
    mailbox = cap.get("folder")

    if not user:
        raise RuntimeError("config.json missing capture.imap_user")
    if not mailbox:
        raise RuntimeError("config.json missing capture.folder (e.g. 'Folders/Stuff Capture')")

    inbox_md = base_dir / "inbox" / "inbox.md"
    attachments_dir = base_dir / "inbox" / "attachments"

    n = capture_folder_to_inbox_md(
        host=host,
        port=port,
        username=user,
        mailbox=mailbox,
        inbox_md=inbox_md,
        attachments_dir=attachments_dir,
        capture_unseen_only=(not all_mail),
        dry_run=dry_run,
    )

    print(f"Captured {n} email(s) into {inbox_md}")
    return 0
