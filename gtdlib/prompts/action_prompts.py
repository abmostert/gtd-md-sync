# gtdlib/prompts/action_prompts.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

from gtdlib.store import prompt, prompt_optional_date, normalize_context


_RESERVED_CONTEXTS = {"waiting_for", "waiting"}


def _clean_contexts(contexts: list[str]) -> list[str]:
    """Normalize + de-duplicate contexts, and remove reserved names."""
    cleaned = []
    for c in contexts:
        c2 = normalize_context(c)
        if not c2:
            continue
        if c2 in _RESERVED_CONTEXTS:
            continue
        cleaned.append(c2)
    return sorted(set(cleaned))


def choose_context(contexts: list[str]) -> str:
    """
    Force selection from configured contexts.
    User can type the number or exact context name.
    Blocks reserved words like 'waiting_for'.
    """
    contexts = _clean_contexts(contexts)
    if not contexts:
        raise RuntimeError("No contexts configured. Add contexts with `gtd context add ...`.")

    print("\nAvailable contexts:")
    for i, c in enumerate(contexts, start=1):
        print(f"  {i}. {c}")

    while True:
        raw = input("Choose context (number or name): ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(contexts):
                return contexts[idx - 1]
        else:
            cand = normalize_context(raw)
            if cand in _RESERVED_CONTEXTS:
                print("'waiting_for' is not a context (it's a state). Choose a real context like work/home/virtual.")
                continue
            if cand in contexts:
                return cand

        print("Invalid context. Choose a number from the list or type an exact context name.")


def prompt_action_state(*, default: str = "active") -> str:
    """
    Prompt for action state. Loops until valid.
    """
    while True:
        state = prompt("State (active/waiting/someday): ", default=default).strip().lower()
        if state in {"active", "waiting", "someday"}:
            return state
        print("Invalid state. Use active, waiting, or someday.")


def prompt_waiting_for() -> str:
    """
    Prompt for waiting_for. Never returns empty; defaults to 'unspecified'.
    """
    waiting_for = prompt("Waiting for (person/thing): ", default="unspecified").strip()
    return waiting_for or "unspecified"


def prompt_action_draft(
    base_dir: Path,
    contexts: list[str],
    *,
    now_iso: str,
    project_id: Optional[str] = None,
    default_state: str = "active",
    ask_context_when_waiting: bool = False,
) -> dict:
    """
    Canonical interactive prompt for creating an action dict.

    Returns an action dict ready to be inserted into master["actions"][aid].
    ID is not assigned here (caller assigns).
    """
    title = prompt("Action title: ").strip()
    if not title:
        raise ValueError("Action title is required.")

    state = prompt_action_state(default=default_state)

    waiting_for = None
    context = None

    if state == "waiting":
        waiting_for = prompt_waiting_for()
        if ask_context_when_waiting:
            context = choose_context(contexts)
    else:
        context = choose_context(contexts)

    due = prompt_optional_date("Due date")
    notes = prompt("Notes (optional): ", default="").strip()

    action = {
        "title": title,
        "project": project_id,
        "state": state,
        "context": context,
        "waiting_for": waiting_for,
        "created": now_iso,
        "last_touched": now_iso,
        "waiting_since": now_iso if state == "waiting" else None,
        "due": due,
        "notes": notes,
    }

    return action
