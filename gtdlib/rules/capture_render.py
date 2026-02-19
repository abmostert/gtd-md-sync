from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from gtdlib.capture.imap_client import CapturedEmail

_UID_RE = re.compile(r"<!--\s*uid:(?P<uid>[^>]+?)\s*-->")

def _extract_existing_uids(text: str) -> set[str]:
    uids: set[str] = set()
    for line in (text or "").splitlines():
        m = _UID_RE.search(line)
        if m:
            uids.add(m.group("uid").strip())
    return uids


def render_capture_inbox_md(items: list[CapturedEmail], inbox_md: Path, base_dir: Path) -> int:
    """
    Merge capture items into inbox_md as checklist items.

    - Preserves existing inbox.md content
    - Appends only NEW items (deduped by IMAP UID)
    - Writes a stable UID marker per item so repeated captures don't duplicate
    Returns count of NEW items appended.
    """
    inbox_md.parent.mkdir(parents=True, exist_ok=True)

    existing_text = ""
    if inbox_md.exists():
        existing_text = inbox_md.read_text(encoding="utf-8")

    existing_uids = _extract_existing_uids(existing_text)

    lines: list[str] = []
    new_count = 0

    for it in items:
        if it.uid and it.uid in existing_uids:
            continue

        subj = it.subject or "(no subject)"
        lines.append(f"- [ ] {subj} <!-- uid:{it.uid} -->")

        body = (it.body_text or "").strip()
        if body:
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

        new_count += 1

    # If no new items, leave file untouched
    if new_count == 0:
        return 0

    # Ensure file has a header if it was empty/missing
    if not existing_text.strip():
        existing_text = (
            "# Inbox\n\n"
            "> Temporary capture list. Tick items as you process them.\n"
            "> `gtd sync` will prune checked capture items from this file.\n\n"
        )

    merged = existing_text.rstrip() + "\n\n" + "\n".join(lines).rstrip() + "\n"
    inbox_md.write_text(merged, encoding="utf-8")
    return new_count
