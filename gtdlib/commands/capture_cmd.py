from __future__ import annotations

from pathlib import Path

from gtdlib.capture.proton_bridge_imap import fetch_capture_emails
from gtdlib.rules.capture_render import render_capture_inbox_md


def cmd_capture(base_dir: Path, *, limit: int = 50) -> int:
    """
    Fetch capture emails via configured IMAP.

    Each email is committed locally before the remote message is moved or
    deleted. Attachments are saved and verified before the inbox entry is
    written.
    """
    inbox_dir = base_dir / "inbox"
    attachments_dir = inbox_dir / "attachments"
    inbox_md = inbox_dir / "inbox.md"

    committed = 0

    def commit_item(item) -> None:
        nonlocal committed

        n = render_capture_inbox_md(
            [item],
            inbox_md,
            base_dir,
        )

        committed += n

        if n:
            print(
                f"[capture] saved locally: "
                f"{item.subject} (uid {item.uid})"
            )
        else:
            print(
                f"[capture] already captured locally: "
                f"{item.subject} (uid {item.uid})"
            )

    try:
        items = fetch_capture_emails(
            base_dir,
            attachments_dir,
            limit=limit,
            on_captured=commit_item,
        )

    except ValueError as e:
        print(f"Capture config error: {e}")
        return 2

    except Exception as e:
        print(f"Capture failed: {e}")
        return 1

    print(
        f"Capture complete. "
        f"Wrote {committed} new item(s) to {inbox_md}; "
        f"processed {len(items)} email(s)."
    )

    return 0
