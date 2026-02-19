from __future__ import annotations

import imaplib
import os
import re
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from typing import Iterable




@dataclass
class CapturedEmail:
    uid: str
    subject: str
    body_text: str
    attachments: list[Path]

def _quote_mailbox(name: str) -> str:
    """
    IMAP mailbox names with spaces (and some specials) must be quoted.
    """
    s = (name or "").strip()

    # Escape backslashes and quotes inside quoted-string
    s_esc = s.replace("\\", "\\\\").replace('"', r"\"")

    # Quote if it contains spaces or common IMAP delimiter-ish chars
    if any(ch in s for ch in (" ", "(", ")", "{", "}", "%", "*")):
        return f'"{s_esc}"'

    return s


def _connect_imap(host: str, port: int, *, starttls: bool, tls_verify: bool):
    """
    Connect to IMAP.

    - If starttls=True: connect plaintext then upgrade via STARTTLS (common for Bridge on 1143).
    - If starttls=False: connect using IMAP4_SSL (for servers speaking SSL immediately).
    """
    if starttls:
        m = imaplib.IMAP4(host, port)
        if tls_verify:
            ctx = ssl.create_default_context()
        else:
            ctx = ssl._create_unverified_context()
        m.starttls(ssl_context=ctx)
        return m

    # direct SSL
    if tls_verify:
        ctx = ssl.create_default_context()
    else:
        ctx = ssl._create_unverified_context()
    try:
        return imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
    except TypeError:
        # older python fallback
        return imaplib.IMAP4_SSL(host, port)




def _safe_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^A-Za-z0-9._ -]+", "", s)
    s = s.strip().replace(" ", "_")
    return s[:120] if s else "attachment"


def _decode_subject(msg: Message) -> str:
    # Keep it simple: email lib handles most decoding for us when using .get()
    subj = msg.get("Subject", "") or ""
    return subj.strip() or "(no subject)"


def _extract_text(msg: Message) -> str:
    """
    Prefer text/plain. Fall back to stripped text/html (very basic).
    """
    if msg.is_multipart():
        parts = list(msg.walk())
    else:
        parts = [msg]

    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    for p in parts:
        ctype = (p.get_content_type() or "").lower()
        disp = (p.get("Content-Disposition") or "").lower()

        # skip attachments
        if "attachment" in disp:
            continue

        payload = p.get_payload(decode=True)
        if payload is None:
            continue

        charset = p.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, errors="replace")
        except LookupError:
            text = payload.decode("utf-8", errors="replace")

        if ctype == "text/plain":
            t = text.strip()
            if t:
                plain_chunks.append(t)
        elif ctype == "text/html":
            t = _strip_html(text).strip()
            if t:
                html_chunks.append(t)

    if plain_chunks:
        return "\n\n".join(plain_chunks).strip()

    if html_chunks:
        return "\n\n".join(html_chunks).strip()

    return ""


def _strip_html(html: str) -> str:
    """
    A deliberately minimal HTML → text stripper.
    Not perfect, but avoids giant font/style blobs.
    """
    s = html or ""
    # remove script/style blocks
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", s)
    # replace <br> and <p> with newlines
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>", "\n\n", s)
    # strip tags
    s = re.sub(r"(?s)<.*?>", "", s)
    # unescape basic entities
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    # collapse whitespace
    s = re.sub(r"\r", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def _save_attachments(msg: Message, attachments_dir: Path, subject: str) -> list[Path]:
    attachments_dir.mkdir(parents=True, exist_ok=True)

    out: list[Path] = []
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    for part in msg.walk():
        disp = (part.get("Content-Disposition") or "").lower()
        if "attachment" not in disp:
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            continue

        filename = part.get_filename() or "attachment"
        filename = _safe_filename(filename)

        subj = _safe_filename(subject)
        base = f"{ts}_{subj}_{filename}" if subj else f"{ts}_{filename}"
        fp = attachments_dir / base

        # avoid overwrite
        if fp.exists():
            root, ext = os.path.splitext(fp.name)
            fp = attachments_dir / f"{root}_01{ext}"

        fp.write_bytes(payload)
        out.append(fp)

    return out

def _imap_delete_uid(m: imaplib.IMAP4, uid: str) -> None:
    # Mark deleted and expunge
    typ, _ = m.uid("store", uid, "+FLAGS", r"(\Deleted)")
    if typ != "OK":
        raise RuntimeError(f"Failed to mark uid {uid} as deleted")
    typ, _ = m.expunge()
    if typ != "OK":
        raise RuntimeError("Failed to expunge deleted messages")


def _imap_move_uid(m: imaplib.IMAP4, uid: str, dest_folder: str) -> None:
    """
    Try UID MOVE if supported, else COPY + DELETE fallback.
    """
    dest = _quote_mailbox(dest_folder)

    # Try MOVE first (RFC 6851). Some servers support it.
    typ, _ = m.uid("move", uid, dest)
    if typ == "OK":
        return

    # Fallback: COPY then delete+expunge
    typ, _ = m.uid("copy", uid, dest)
    if typ != "OK":
        raise RuntimeError(f"Failed to move uid {uid}: MOVE and COPY both failed")
    _imap_delete_uid(m, uid)



def fetch_from_imap(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    folder: str,
    out_attachments_dir: Path,
    limit: int = 50,
    search_query: str = "ALL",
    starttls: bool = True,
    tls_verify: bool = False,
    post_fetch: str = "none",   # "none" | "move" | "delete"
    move_to: str | None = None

) -> list[CapturedEmail]:
    """
    Fetch messages from IMAP folder using UID fetch.

    Notes:
    - Proton Bridge commonly exposes IMAP on 1143 with STARTTLS.
    - If tls_verify=False (default), we skip certificate verification (ok for localhost Bridge).
    - This does NOT delete or move messages. It just reads them.
    """
    m = None

    try:
        m = _connect_imap(host, port, starttls=starttls, tls_verify=tls_verify)
        m.login(username, password)

        mailbox = _quote_mailbox(folder)
        readonly = (post_fetch == "none")
        typ, _ = m.select(mailbox, readonly=readonly)

        if typ != "OK":
            raise RuntimeError(f"Failed to select folder: {folder}")

        typ, data = m.uid("search", None, search_query)
        if typ != "OK":
            raise RuntimeError("IMAP search failed")

        uids = (data[0] or b"").split()
        if not uids:
            return []

        # newest first
        uids = list(reversed(uids))[:limit]

        total_found = len((data[0] or b"").split())
        total_processing = len(uids)
        print(f"[capture] Found {total_found} message(s). Processing {total_processing}...")

        # Determine 10% step (minimum 1 to avoid division issues)
        progress_step = max(1, total_processing // 10)

        t0 = time.perf_counter()

        results: list[CapturedEmail] = []
        for idx, uid_b in enumerate(uids, start=1):

            uid = uid_b.decode("utf-8", errors="replace")
            
            if idx == 1 or idx % progress_step == 0 or idx == total_processing:
                percent = int((idx / total_processing) * 100)
                print(f"[capture] {percent}% ({idx}/{total_processing})")
            
            typ, msg_data = m.uid("fetch", uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue

            raw = msg_data[0][1]
            msg = message_from_bytes(raw)

            subject = _decode_subject(msg)
            body = _extract_text(msg)
            atts = _save_attachments(msg, out_attachments_dir, subject)

            results.append(CapturedEmail(uid=uid, subject=subject, body_text=body, attachments=atts))

            # Post-fetch handling to prevent re-capture loops
            if post_fetch != "none":
                if post_fetch == "move":
                    if not move_to:
                        raise RuntimeError("post_fetch=move requires move_to folder")
                    _imap_move_uid(m, uid, move_to)
                elif post_fetch == "delete":
                    _imap_delete_uid(m, uid)
                else:
                    raise RuntimeError(f"Unknown post_fetch mode: {post_fetch}")

        elapsed = time.perf_counter() - t0
        avg = (elapsed / len(results)) if results else 0.0
        print(f"[capture] Done. Processed {len(results)} message(s) in {elapsed:.1f}s ({avg:.2f}s/msg)")


        return results

    finally:
        if m is not None:
            try:
                m.logout()
            except Exception:
                pass

