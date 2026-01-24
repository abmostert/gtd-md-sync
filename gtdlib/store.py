
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

MASTER_FILENAME = "master.json"
VIEWS_DIRNAME = "views"

# Starter view files (you can expand later)
VIEW_FILES: dict[str, str] = {
    "next_actions.md": "# Next Actions\n\n",
    "projects.md": "# Projects\n\n",
    "someday.md": "# Someday / Maybe\n\n",
}


def utc_now_iso() -> str:
    """UTC timestamp in ISO 8601 format with 'Z'."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    """Create a short unique-ish ID like a_3f9c2a1b or p_d0a41c7e."""
    return f"{prefix}_{uuid4().hex[:8]}"


def load_master(base_dir: Path) -> dict:
    master_path = base_dir / MASTER_FILENAME
    if not master_path.exists():
        raise FileNotFoundError(
            f"No {MASTER_FILENAME} found in {base_dir}. Run `python3 gtd.py init --dir <path>` first."
        )
    return json.loads(master_path.read_text(encoding="utf-8"))


def save_master(base_dir: Path, master: dict) -> None:
    master_path = base_dir / MASTER_FILENAME
    master.setdefault("meta", {})
    master["meta"]["updated"] = utc_now_iso()
    master_path.write_text(
        json.dumps(master, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_json_if_missing(path: Path, data: dict) -> bool:
    """Write JSON only if the file doesn't exist. Returns True if created."""
    if path.exists():
        return False
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def write_text_if_missing(path: Path, text: str) -> bool:
    """Write text only if the file doesn't exist. Returns True if created."""
    if path.exists():
        return False
    path.write_text(text, encoding="utf-8")
    return True


def prompt(text: str, default: str | None = None) -> str:
    """
    Simple input() wrapper with optional default.
    Empty input returns default (if provided).
    """
    if default is None:
        return input(text).strip()
    s = input(f"{text} [{default}] ").strip()
    return s if s else default


def prompt_optional_date(text: str) -> str | None:
    """Accept YYYY-MM-DD or empty for None. (No strict validation in v1.)"""
    s = input(f"{text} (YYYY-MM-DD, or blank): ").strip()
    return s or None
