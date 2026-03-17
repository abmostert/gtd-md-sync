from __future__ import annotations
from gtdlib.store import ensure_config, DEFAULT_FOCUS_CONFIG
from gtdlib.rules.contexts import normalize_context


def get_contexts(base_dir):

    cfg = ensure_config(base_dir)

    contexts = [normalize_context(c) for c in cfg.get("contexts", [])]

    return sorted(set(contexts))

def get_focus_config(base_dir):
    cfg = ensure_config(base_dir) or {}
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
