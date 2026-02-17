
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from gtdlib.rules.contexts import normalize_context



MASTER_FILENAME = "master.json"
CONFIG_FILENAME = "config.json"
VIEWS_DIRNAME = "views"
PROJECTS_DIRNAME = "projects"


# Starter view files (you can expand later)
VIEW_FILES: dict[str, str] = {
    "next_actions.md": "# Next Actions\n\n",
    "projects.md": "# Projects\n\n",
    "someday.md": "# Someday / Maybe\n\n",
}

# Starter contexts (you can modify later)
DEFAULT_CONTEXTS = [
    "inbox",
    "home",
    "work",
    "phone",
    "computer",
    "errands",
    "agenda",
]



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


def load_config(base_dir: Path) -> dict:
    """
    Load config.json from the GTD workspace directory.
    If missing, returns a default config (doesn't write).
    """
    cfg_path = base_dir / CONFIG_FILENAME
    if not cfg_path.exists():
        return {"contexts": list(DEFAULT_CONTEXTS)}
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def save_config(base_dir: Path, cfg: dict) -> None:
    cfg_path = base_dir / CONFIG_FILENAME
    cfg_path.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def ensure_config(base_dir: Path) -> dict:
    """
    Ensure config.json exists. If not, create it with defaults.
    Returns the loaded config.
    """
    cfg_path = base_dir / CONFIG_FILENAME
    if not cfg_path.exists():
        cfg = {"contexts": list(DEFAULT_CONTEXTS)}
        save_config(base_dir, cfg)
        return cfg
    return load_config(base_dir)


