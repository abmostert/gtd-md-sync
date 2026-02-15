from __future__ import annotations

from typing import Optional, Set


def choose_project_id(
    projects: dict,
    *,
    allow_states: Optional[Set[str]] = None,
) -> str | None:
    """
    Let the user optionally associate something with a project.

    Returns:
      - project_id (e.g. "p_abcd1234") if chosen
      - None if user chooses 0/blank (standalone) or there are no eligible projects

    allow_states:
      If provided, only projects whose `state` (lowercased) is in allow_states are shown.
      Example: allow_states={"active"}
    """
    rows: list[tuple[str, str]] = []

    for pid, p in (projects or {}).items():
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
        raw = input("Choose project (number): ").strip()
        if raw == "" or raw == "0":
            return None

        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(rows):
                return rows[idx - 1][0]

        print("Invalid choice. Enter 0 for none, or a number from the list.")
