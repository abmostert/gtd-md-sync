from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

ID_COMMENT_RE = re.compile(r"<!--\s*id:(?P<id>[^>]+?)\s*-->")
H2_RE = re.compile(r"^\s*##\s+(?P<title>.+?)\s*$")


@dataclass
class ProjectNotesEdits:
    project_id: str
    outcome: str
    notes: str
    agenda_notes: str


def _normalize_heading(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _strip_trailing_whitespace_lines(text: str) -> str:
    # keep internal newlines; just trim outer space
    return (text or "").strip("\n").rstrip()


def parse_project_notes(text: str) -> Optional[ProjectNotesEdits]:
    """
    Extract edits from a single project_notes.md file.

    Recognized sections (H2):
      - Outcome -> project["outcome"]
      - Additional notes -> project["notes"]
      - Agenda notes -> project["agenda_notes"]

    Returns None if no project id found.
    """
    if not text:
        return None

    # Find project id from header line: "# Title <!-- id:p_xxx -->"
    m = ID_COMMENT_RE.search(text)
    if not m:
        return None
    pid = m.group("id").strip()

    # Slice into H2 sections
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current: Optional[str] = None

    for line in lines:
        mh = H2_RE.match(line)
        if mh:
            current = _normalize_heading(mh.group("title"))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)

    def get_block(*names: str) -> str:
        for nm in names:
            key = _normalize_heading(nm)
            if key in sections:
                return _strip_trailing_whitespace_lines("\n".join(sections[key]))
        return ""

    outcome = get_block("Outcome")
    notes = get_block("Additional notes", "Additional Notes")
    agenda = get_block("Agenda notes", "Agenda Notes")

    return ProjectNotesEdits(
        project_id=pid,
        outcome=outcome,
        notes=notes,
        agenda_notes=agenda,
    )
