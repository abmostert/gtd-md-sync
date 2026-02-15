from __future__ import annotations

import re
from dataclasses import dataclass


# Matches: <!-- id:a_deadbeef -->
ID_COMMENT_RE = re.compile(r"<!--\s*id:(?P<id>[^>]+?)\s*-->")

# Matches markdown task items: - [ ] text, * [x] text, + [X] text
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.*)$")


def normalize_item_id(raw: str) -> str:
    """
    Normalise an id extracted from Markdown.

    Handles common escaping cases (e.g. some renderers insert backslashes
    before underscores: a\\_deadbeef).
    """
    s = (raw or "").strip()
    s = s.replace("\\_", "_")
    # strip BOM if it somehow got into the id (rare)
    s = s.lstrip("\ufeff")
    return s


def extract_completions_from_markdown(text: str) -> dict[str, bool]:
    """
    Returns mapping: { item_id: done_bool }

    Only considers lines containing an <!-- id:... --> marker.
    done_bool True if:
      - checkbox is [x] or [X], OR
      - the line contains 'XXX' anywhere (user marker)
    """
    results: dict[str, bool] = {}

    for line in (text or "").splitlines():
        m_id = ID_COMMENT_RE.search(line)
        if not m_id:
            continue

        item_id = normalize_item_id(m_id.group("id"))

        done = False
        norm_line = line.lstrip("\ufeff")

        m_cb = CHECKBOX_RE.match(norm_line)
        if m_cb:
            done = (m_cb.group("mark").lower() == "x")

        if "XXX" in line:
            done = True

        results[item_id] = done

    return results


def prune_checked_top_level_tasks(text: str) -> tuple[str, int]:
    """
    Removes top-level '- [x]' / '- [X]' items and their continuation lines.

    This is intended for inbox/inbox.md (capture list) where items have no IDs.
    Returns: (new_text, removed_count)
    """
    lines = (text or "").splitlines()
    out: list[str] = []
    removed = 0
    i = 0

    def is_top_item(line: str) -> bool:
        s = line.lstrip("\ufeff")
        return s.startswith("- [") or s.startswith("* [") or s.startswith("+ [")

    while i < len(lines):
        line = lines[i]
        s = line.lstrip("\ufeff")

        if s.startswith("- [x]") or s.startswith("- [X]") or s.startswith("* [x]") or s.startswith("* [X]") or s.startswith("+ [x]") or s.startswith("+ [X]"):
            removed += 1
            i += 1

            # skip continuation lines until next top-level list item or EOF
            while i < len(lines) and not is_top_item(lines[i]):
                i += 1

            # skip blank lines immediately following the removed block
            while i < len(lines) and lines[i].strip() == "":
                i += 1

            continue

        out.append(line)
        i += 1

    new_text = "\n".join(out).rstrip() + "\n"
    return new_text, removed

