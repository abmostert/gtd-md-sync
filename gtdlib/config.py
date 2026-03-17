from gtdlib.store import ensure_config
from gtdlib.rules.contexts import normalize_context
from __future__ import annotations

DEFAULT_FOCUS_CONFIG = {
    "enabled": True,
    "max_items": 12,
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

def get_contexts(base_dir):

    cfg = ensure_config(base_dir)

    contexts = [normalize_context(c) for c in cfg.get("contexts", [])]

    return sorted(set(contexts))

def get_focus_config(base_dir):
    cfg = load_config(base_dir) or {}
    focus = cfg.get("focus") or {}

    result = {
        "enabled": focus.get("enabled", DEFAULT_FOCUS_CONFIG["enabled"]),
        "max_items": focus.get("max_items", DEFAULT_FOCUS_CONFIG["max_items"]),
        "weights": dict(DEFAULT_FOCUS_CONFIG["weights"]),
    }

    weights = focus.get("weights") or {}
    for k, v in weights.items():
        if k in result["weights"]:
            result["weights"][k] = float(v)

    result["max_items"] = int(result["max_items"])
    if result["max_items"] < 1:
        result["max_items"] = 1

    return result
