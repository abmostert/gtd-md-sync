from __future__ import annotations

import json
from pathlib import Path


def append_metric_event(base_dir: Path, event: dict) -> None:
    """
    Append one event to metrics.jsonl.

    metrics.jsonl is treated as an append-only event log.
    """
    path = base_dir / "metrics.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")