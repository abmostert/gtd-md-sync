from __future__ import annotations

import re
from typing import Any


# Allow: letters, numbers, underscores. (You already normalize to snake-ish.)
# This prevents spaces and punctuation from silently creating weird contexts.
_CONTEXT_RE = re.compile(r"^[a-z0-9_]+$")


def normalize_context(name: str) -> str:
    """
    Normalize user input to a canonical context key.

    Rules:
    - strip whitespace
    - lower
    - spaces/hyphens -> underscores
    - collapse multiple underscores
    - strip leading/trailing underscores
    """
    s = (name or "").strip().lower()
    s = s.replace("-", "_").replace(" ", "_")
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s


def validate_context_name(name: str) -> str:
    """
    Return normalized name if valid, otherwise raise ValueError.
    """
    s = normalize_context(name)
    if not s:
        raise ValueError("Context name cannot be blank.")
    if not _CONTEXT_RE.match(s):
        raise ValueError("Context name must contain only letters, numbers, and underscores.")
    return s


def get_contexts(cfg: dict[str, Any]) -> list[str]:
    """
    Return sorted unique normalized contexts from config dict.
    """
    raw = cfg.get("contexts", [])
    if not isinstance(raw, list):
        raw = []
    contexts = [normalize_context(str(x)) for x in raw]
    contexts = [c for c in contexts if c]  # drop blanks
    return sorted(set(contexts))


def set_contexts(cfg: dict[str, Any], contexts: list[str]) -> dict[str, Any]:
    """
    Set contexts in cfg (normalized, sorted unique).
    """
    cleaned = [validate_context_name(c) for c in contexts]
    cfg["contexts"] = sorted(set(cleaned))
    return cfg


def add_context(cfg: dict[str, Any], name: str) -> tuple[dict[str, Any], bool, str]:
    """
    Add a context. Returns (cfg, changed?, normalized_name).
    """
    n = validate_context_name(name)
    existing = set(get_contexts(cfg))
    if n in existing:
        return cfg, False, n
    existing.add(n)
    cfg["contexts"] = sorted(existing)
    return cfg, True, n


def drop_context(cfg: dict[str, Any], name: str) -> tuple[dict[str, Any], bool, str]:
    """
    Drop a context. Returns (cfg, changed?, normalized_name).
    """
    n = validate_context_name(name)
    existing = set(get_contexts(cfg))
    if n not in existing:
        return cfg, False, n
    existing.remove(n)
    cfg["contexts"] = sorted(existing)
    return cfg, True, n
