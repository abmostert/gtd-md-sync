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
        "context_cap": focus.get("context_cap", DEFAULT_FOCUS_CONFIG["context_cap"]),
        "include_overdue": focus.get("include_overdue", DEFAULT_FOCUS_CONFIG["include_overdue"]),
        "include_due_today": focus.get("include_due_today", DEFAULT_FOCUS_CONFIG["include_due_today"]),
        "weights": dict(DEFAULT_FOCUS_CONFIG["weights"]),
    }

    weights = focus.get("weights") or {}
    for k, v in weights.items():
        if k in result["weights"]:
            result["weights"][k] = float(v)

    result["context_cap"] = int(result["context_cap"])
    if result["context_cap"] < 1:
        result["context_cap"] = 1

    result["enabled"] = bool(result["enabled"])
    result["include_overdue"] = bool(result["include_overdue"])
    result["include_due_today"] = bool(result["include_due_today"])

    return result
