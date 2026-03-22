
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from gtdlib.rules.contexts import normalize_context

MASTER_SCHEMA_VERSION = 2
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

DEFAULT_FOCUS_CONFIG = {
    "enabled": True,
    "context_cap": 5,
    "include_overdue": True,
    "include_due_today": True,
    "weights": {
        "action_due": 40.0,
        "action_overdue_slope": 3.0,
        "project_due": 20.0,
        "project_overdue_slope": 2.0,
        "age": 6.0,
        "tension": 10.0,
        "overdue_bonus": 15.0,
    },
}

def ensure_master_schema(master: dict) -> tuple[dict, bool]:
    """
    Idempotently upgrade master dict in-memory to the latest schema.
    Returns (master, changed).
    """
    changed = False
    master.setdefault("meta", {})
    meta = master["meta"]

    meta.setdefault("version", 1)

    current = meta.get("schema_version")
    if not isinstance(current, int):
        current = 1

    if current < 2:
        # v2 adds project.outcome and project.agenda_notes
        projects = master.get("projects", {})
        if isinstance(projects, dict):
            for _, p in projects.items():
                if not isinstance(p, dict):
                    continue
                if "outcome" not in p:
                    p["outcome"] = ""
                    changed = True
                if "agenda_notes" not in p:
                    p["agenda_notes"] = ""
                    changed = True

        meta["schema_version"] = 2
        changed = True

    return master, changed


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
    master = json.loads(master_path.read_text(encoding="utf-8"))
    master, _changed = ensure_master_schema(master)
    return master


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
        cfg = {
            "contexts": list(DEFAULT_CONTEXTS), 
            "focus": json.loads(json.dumps(DEFAULT_FOCUS_CONFIG))  
        }
        save_config(base_dir, cfg)
        return cfg
    if "context_cap" not in focus:
        focus["context_cap"] = DEFAULT_FOCUS_CONFIG["context_cap"]
        changed = True

    if "include_overdue" not in focus:
        focus["include_overdue"] = DEFAULT_FOCUS_CONFIG["include_overdue"]
        changed = True

    if "include_due_today" not in focus:
        focus["include_due_today"] = DEFAULT_FOCUS_CONFIG["include_due_today"]
        changed = True
    
    return load_config(base_dir)


