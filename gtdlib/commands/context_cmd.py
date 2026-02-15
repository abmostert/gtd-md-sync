from __future__ import annotations

from pathlib import Path

from gtdlib.store import ensure_config, save_config  # if your store has save_config; if not, see note below
from gtdlib.rules.contexts import get_contexts, add_context, drop_context


def cmd_context_list(base_dir: Path) -> int:
    cfg = ensure_config(base_dir)
    contexts = get_contexts(cfg)

    if not contexts:
        print("No contexts configured.")
        print("Add one with: gtd context add <name>")
        return 0

    for c in contexts:
        print(c)
    return 0


def cmd_context_add(base_dir: Path, name: str) -> int:
    cfg = ensure_config(base_dir)
    try:
        cfg, changed, norm = add_context(cfg, name)
    except ValueError as e:
        print(f"Error: {e}")
        return 2

    if changed:
        save_config(base_dir, cfg)
        print(f"Added context: {norm}")
    else:
        print(f"Context already exists: {norm}")
    return 0


def cmd_context_drop(base_dir: Path, name: str) -> int:
    cfg = ensure_config(base_dir)
    try:
        cfg, changed, norm = drop_context(cfg, name)
    except ValueError as e:
        print(f"Error: {e}")
        return 2

    if changed:
        save_config(base_dir, cfg)
        print(f"Dropped context: {norm}")
    else:
        print(f"Context not found: {norm}")
    return 0

