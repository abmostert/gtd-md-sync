# gtdlib/capture/proton_bridge_imap.py
from __future__ import annotations

import imaplib
import email
from email.header import decode_header
from email.message import Message
from pathlib import Path
from datetime import datetime, timezone
import getpass
import re


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out: list[str] = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(chunk))
    return "".join(out).strip()


def _extract_text_body(msg: Message) -> str:
    # Prefer text/plain; fallback to empty
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace").strip()
        return ""
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace").strip()


_filename_bad = re.compile(r"[^A-Za-z0-9.\-_ ]+")
def _safe_filename(name: str) -> str:
    name = name.strip().replace("/", "_").replace("\\", "_")
    name = _filename_bad.sub("_", name)
    if not name:
        name = "attachment"
    return name


def _save_attachments(msg: Message, attachments_dir: Path) -> list[str]:
    attachments_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    i = 0

    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue

        i += 1
        fn = _safe_filename(_decode_mime_header(filename))
        data = part.get_payload(decode=True)
        if not data:
            continue

        out_name = f"{stamp}_{i:02d}_{fn}"
        out_path = attachments_dir / out_name
        out_path.write_bytes(data)
        saved.append(out_name)

    return saved


def capture_folder_to_inbox_md(
    *,
    host: str,
    port: int,
    username: str,
    mailbox: str,
    inbox_md: Path,
    attachments_dir: Path,
    password: str | None = None,
    capture_unseen_only: bool = True,
    dry_run: bool = False,
) -> int:
    """
    Fetch emails from `mailbox`, append minimal entries to inbox_md, save attachments,
    then delete emails from the mailbox (expunge). Returns number of captured messages.
    """
    if password is None:
        password = getpass.getpass("Bridge password: ")

    inbox_md.parent.mkdir(parents=True, exist_ok=True)
    attachments_dir.mkdir(parents=True, exist_ok=True)
    inbox_md.touch(exist_ok=True)

    m = imaplib.IMAP4(host, port)
    try:
        m.login(username, password)

        typ, _ = m.select(f'"{mailbox}"')
        if typ != "OK":
            raise RuntimeError(f"Could not select mailbox: {mailbox}")

        search_crit = "UNSEEN" if capture_unseen_only else "ALL"
        typ, data = m.search(None, search_crit)
        if typ != "OK":
            return 0

        msg_nums = [x for x in (data[0] or b"").split() if x]
        captured = 0

        for num in msg_nums:
            typ, fetched = m.fetch(num, "(RFC822)")
            if typ != "OK" or not fetched or not fetched[0]:
                continue

            raw = fetched[0][1]
            msg = email.message_from_bytes(raw)

            subject = _decode_mime_header(msg.get("Subject")) or "(no subject)"
            body = _extract_text_body(msg)
            saved_files = _save_attachments(msg, attachments_dir)

            if not dry_run:
                with inbox_md.open("a", encoding="utf-8") as f:
                    f.write(f"- [ ] {subject}\n")
                    if body:
                        for line in body.splitlines():
                            if line.strip():
                                f.write(f"  {line.rstrip()}\n")
                    if saved_files:
                        f.write("  attachments:\n")
                        for fn in saved_files:
                            f.write(f"  - attachments/{fn}\n")
                    f.write("\n")

                # delete the email from the capture folder
                m.store(num, "+FLAGS", r"(\Deleted)")
            captured += 1

        if not dry_run and captured:
            m.expunge()

        return captured

    finally:
        try:
            m.logout()
        except Exception:
            pass
