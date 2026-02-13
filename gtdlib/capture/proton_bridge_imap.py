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
import html as _html

_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style).*?>.*?</\1>")
_TAG_RE = re.compile(r"(?s)<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")

def _html_to_text(s: str) -> str:
    if not s:
        return ""

    # remove scripts/styles
    s = _SCRIPT_STYLE_RE.sub("", s)

    # convert common block-ish tags to newlines
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|tr|li|h1|h2|h3|h4|h5|h6)>", "\n", s)
    s = re.sub(r"(?i)<hr\b.*?>", "\n---\n", s)

    # strip remaining tags
    s = _TAG_RE.sub("", s)

    # unescape entities
    s = _html.unescape(s)

    # normalize whitespace
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _WS_RE.sub(" ", s)
    s = "\n".join(line.strip() for line in s.splitlines())
    s = _MULTI_NL_RE.sub("\n\n", s).strip()

    # remove common Proton footer noise
    s = re.sub(r"(?i)sent with proton mail.*$", "", s).strip()

    # hard cut quoted/reply chains (simple heuristic)
    cut_markers = [
        "\nFrom:",
        "\n-----Original Message-----",
        "\nOn ",
        "\nSent:",
    ]
    for m in cut_markers:
        idx = s.find(m)
        if idx != -1 and idx > 0:
            s = s[:idx].rstrip()
            break

    return s.strip()


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
    # Prefer text/plain, otherwise convert text/html to plain.
    text_plain = ""
    text_html = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue

            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except LookupError:
                decoded = payload.decode("utf-8", errors="replace")

            if ctype == "text/plain" and not text_plain:
                text_plain = decoded.strip()
            elif ctype == "text/html" and not text_html:
                text_html = decoded.strip()
    else:
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        try:
            decoded = payload.decode(charset, errors="replace")
        except LookupError:
            decoded = payload.decode("utf-8", errors="replace")

        # guess if it's html-ish
        if "<html" in decoded.lower() or "<div" in decoded.lower() or "<br" in decoded.lower():
            text_html = decoded.strip()
        else:
            text_plain = decoded.strip()

    if text_plain:
        return text_plain

    if text_html:
        return _html_to_text(text_html)

    return ""



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
            MAX_LINES = 20
            MAX_CHARS = 2000
            lines = [ln for ln in body.splitlines() if ln.strip()]
            body = "\n".join(lines[:MAX_LINES])[:MAX_CHARS].strip()

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
