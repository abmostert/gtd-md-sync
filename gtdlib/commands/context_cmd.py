from __future__ import annotations

from pathlib import Path

from gtdlib.store import ensure_config, save_config, normalize_context


def cmd_context_list(base_dir: Path) -> int:
    cfg = ensure_config(base_dir)
    contexts = sorted(set(normalize_context(c) for c in cfg.get("contexts", [])))
    if not contexts:
        print("No contexts configured.")
        return 0
    print("Contexts:")
    for c in contexts:
        print(f"- {c}")
    return 0


def cmd_context_add(base_dir: Path, name: str) -> int:
    cfg = ensure_config(base_dir)
    contexts = set(normalize_context(c) for c in cfg.get("contexts", []))
    n = normalize_context(name)
    if not n:
        print("Context name cannot be empty.")
        return 2
    if n in contexts:
        print(f"Context already exists: {n}")
        return 0
    contexts.add(n)
    cfg["contexts"] = sorted(contexts)
    save_config(base_dir, cfg)
    print(f"Added context: {n}")
    return 0


def cmd_context_drop(base_dir: Path, name: str) -> int:
    cfg = ensure_config(base_dir)
    contexts = set(normalize_context(c) for c in cfg.get("contexts", []))
    n = normalize_context(name)
    if n not in contexts:
        print(f"Context not found: {n}")
        return 2

    # Safety: never allow removing inbox unless you really want to.
    if n == "inbox":
        print("Refusing to drop 'inbox' (safety default).")
        return 2

    contexts.remove(n)
    cfg["contexts"] = sorted(contexts)
    save_config(base_dir, cfg)
    print(f"Dropped context: {n}")
    return 0
