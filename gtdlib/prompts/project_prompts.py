
from __future__ import annotations

from typing import Iterable


def choose_project_id(
    projects: dict,
    *,
    allow_states: set[str] | None = None,
    prompt_text: str = "Choose project (number): ",
) -> str | None:
    """
    Return a project_id (e.g. 'p_abcd1234') or None for standalone.

    - Shows "0. None" option
    - Optionally filters projects by state (allow_states)
    - Returns the selected project_id, or None if user chooses 0/blank
    """
    rows: list[tuple[str, str]] = []
    for pid, p in projects.items():
        state = (p.get("state") or "").strip().lower()
        if allow_states and state not in allow_states:
            continue

        title = (p.get("title") or "").strip() or pid
        rows.append((pid, title))

    rows.sort(key=lambda t: t[1].lower())

    print("\nAssociate this action with a project?")
    print("  0. None (standalone action)")
    if not rows:
        return None

    for i, (_, title) in enumerate(rows, start=1):
        print(f"  {i}. {title}")

    while True:
        raw = input(prompt_text).strip()
        if raw == "" or raw == "0":
            return None
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(rows):
                return rows[idx - 1][0]
        print("Invalid choice. Enter 0 for none, or a number from the list.")
