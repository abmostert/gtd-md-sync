
from gtdlib.store import prompt, normalize_context
from gtdlib.config import get_contexts


def choose_project_id(projects: dict, allow_states=None):
    rows = []

    for pid, p in projects.items():
        state = (p.get("state") or "").strip().lower()
        if allow_states and state not in allow_states:
            continue

        title = p.get("title") or pid
        rows.append((pid, title))

    rows.sort(key=lambda t: t[1].lower())

    print("\nAssociate with project?")
    print("  0. None")

    for i, (_, title) in enumerate(rows, start=1):
        print(f"  {i}. {title}")

    while True:
        raw = input("Choose project: ").strip()
        if raw in ("", "0"):
            return None

        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(rows):
                return rows[idx - 1][0]

        print("Invalid choice.")
