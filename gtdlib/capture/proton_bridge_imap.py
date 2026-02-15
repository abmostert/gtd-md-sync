from __future__ import annotations

import getpass

from dataclasses import dataclass
from pathlib import Path

from gtdlib.store import ensure_config
from gtdlib.capture.imap_client import fetch_from_imap, CapturedEmail


@dataclass
class ProtonBridgeConfig:
    host: str
    port: int
    username: str
    password: str
    folder: str
    starttls: bool = True
    tls_verify: bool = False



def load_proton_bridge_config(base_dir: Path) -> ProtonBridgeConfig:
    cfg = ensure_config(base_dir)
    capture = cfg.get("capture", {}) if isinstance(cfg.get("capture", {}), dict) else {}

    imap = capture.get("imap", {}) if isinstance(capture.get("imap", {}), dict) else {}

    host = str(imap.get("host", "127.0.0.1"))
    port = int(imap.get("port", 1143))
    username = str(imap.get("username", "")).strip()
    password = str(imap.get("password", "")).strip()
    folder = str(imap.get("folder", "")).strip()
    starttls = bool(imap.get("starttls", True))
    tls_verify = bool(imap.get("tls_verify", False))

    if not password:
    password = getpass.getpass(
        prompt=f"Proton Bridge IMAP password for {username}: "
    ) 


    if not username or not folder:
        raise ValueError(
            "Missing capture IMAP settings in config.json. Expected:\n"
            '  "capture": { "imap": { "host": "127.0.0.1", "port": 1143, '
            '"username": "...", "password": "...", "folder": "..." } }'
        )

    return ProtonBridgeConfig(host=host, port=port, username=username, password=password, folder=folder, starttls=starttls,
        tls_verify=tls_verify)


def fetch_capture_emails(base_dir: Path, attachments_dir: Path, limit: int = 50) -> list[CapturedEmail]:
    cfg = load_proton_bridge_config(base_dir)
    return fetch_from_imap(
        host=cfg.host,
        port=cfg.port,
        username=cfg.username,
        password=cfg.password,
        folder=cfg.folder,
        out_attachments_dir=attachments_dir,
        limit=limit,
        search_query="ALL",
        starttls=cfg.starttls,
        tls_verify=cfg.tls_verify,
    )

