from __future__ import annotations

from pathlib import Path

from gtdlib.capture.proton_bridge_imap import fetch_capture_emails
from gtdlib.rules.capture_render import render_capture_inbox_md


def cmd_capture(base_dir: Path, *, limit: int = 50) -> int:
    """
    Fetch capture emails via configured IMAP (Proton Bridge currently),
    save attachments, and generate inbox/inbox.md.
    """
    inbox_dir = base_dir / "inbox"
    attachments_dir = inbox_dir / "attachments"
    inbox_md = inbox_dir / "inbox.md"

    try:
        items = fetch_capture_emails(base_dir, attachments_dir, limit=limit)
    except ValueError as e:
        print(f"Capture config error: {e}")
        return 2
    except Exception as e:
        print(f"Capture failed: {e}")
        return 1

    n = render_capture_inbox_md(items, inbox_md, base_dir)
    print(f"Capture complete. Wrote {n} item(s) to {inbox_md}")
    return 0
