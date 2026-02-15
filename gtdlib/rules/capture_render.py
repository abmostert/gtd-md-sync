from __future__ import annotations

from pathlib import Path
from typing import Iterable

from gtdlib.capture.imap_client import CapturedEmail


def render_capture_inbox_md(items: list[CapturedEmail], inbox_md: Path, base_dir: Path) -> int:
    """
    Overwrite inbox_md with a simple checklist representation:
      - [ ] SUBJECT
        body line(s)
        attachments:
        - attachments/...
    Returns count of items written.
    """
    inbox_md.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    for it in items:
        lines.append(f"- [ ] {it.subject}")

        body = (it.body_text or "").strip()
        if body:
            # indent body by two spaces (markdown list continuation)
            for bl in body.splitlines():
                if bl.strip():
                    lines.append(f"  {bl.rstrip()}")
            lines.append("")

        if it.attachments:
            lines.append("  attachments:")
            for p in it.attachments:
                rel = p
                try:
                    rel = p.relative_to(base_dir)
                except Exception:
                    pass
                lines.append(f"  - {rel.as_posix()}")
            lines.append("")

    inbox_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return len(items)
