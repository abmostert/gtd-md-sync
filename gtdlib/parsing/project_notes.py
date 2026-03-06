from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

ID_COMMENT_RE = re.compile(r"<!--\s*id:(?P<id>[^>]+?)\s*-->")
H2_RE = re.compile(r"^\s*##\s+(?P<title>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.*)$")
META_RE = re.compile(r"^\s{2,}-\s*(?P<key>[a-zA-Z0-9_]+)\s*:\s*(?P<val>.*)\s*$")


@dataclass
class DraftAction:
    section: str          # "active" | "waiting" | "someday" | "agenda"
    title: str
    context: Optional[str] = None
    due: Optional[str] = None
    notes: Optional[str] = None
    waiting_for: Optional[str] = None


@dataclass
class ProjectNotesEdits:
    project_id: str
    outcome: str
    notes: str
    agenda_notes: str
    draft_actions: list[DraftAction]


def _normalize_heading(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _strip_trailing_whitespace_lines(text: str) -> str:
    return (text or "").strip("\n").rstrip()


def _map_section(h2: str) -> Optional[str]:
    """
    Map H2 headings to action sections we support for draft capture.
    """
    k = _normalize_heading(h2)
    if k == "active actions":
        return "active"
    if k == "waiting for":
        return "waiting"
    if k == "someday actions":
        return "someday"
    if k in ("agenda", "agenda actions"):
        return "agenda"
    return None


def parse_project_notes(text: str) -> Optional[ProjectNotesEdits]:
    """
    Extract edits from a single project notes file.

    Recognized text sections:
      - Outcome -> project["outcome"]
      - Additional notes -> project["notes"]
      - Agenda notes -> project["agenda_notes"]

    Also recognizes new draft actions under:
      - Active actions
      - Waiting for
      - Someday actions

    A "new draft action" is a checkbox line WITHOUT an <!-- id:... --> marker.
    Recommended pattern:
      - [ ] draft: Title
        - context: work
        - due: 2026-02-22
        - waiting_for: Bob
        - notes: ...
    """
    if not text:
        return None

    m = ID_COMMENT_RE.search(text)
    if not m:
        return None
    pid = m.group("id").strip()

    lines = text.splitlines()

    # Collect raw H2 blocks
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

    # Parse draft actions from the three action sections
    draft_actions: list[DraftAction] = []

    for h2_name, block_lines in sections.items():
        sec = _map_section(h2_name)
        if not sec:
            continue

        i = 0
        while i < len(block_lines):
            line = block_lines[i]

            # Only consider checkbox lines
            mcb = CHECKBOX_RE.match(line)
            if not mcb:
                i += 1
                continue

            text_part = mcb.group("text") or ""

            # If this line already has an id comment, it's an existing action; skip.
            if ID_COMMENT_RE.search(line):
                i += 1
                continue

            # Title handling: allow optional "draft:" prefix
            title = text_part.strip()
            if title.lower().startswith("draft:"):
                title = title[len("draft:"):].strip()

            if not title:
                i += 1
                continue

            da = DraftAction(section=sec, title=title)

            # Consume indented meta lines until next checkbox or next header-ish line
            j = i + 1
            while j < len(block_lines):
                nxt = block_lines[j]

                # stop if we hit another checkbox (new action) or a new heading
                if CHECKBOX_RE.match(nxt):
                    break
                if H2_RE.match(nxt):
                    break

                mm = META_RE.match(nxt)
                if mm:
                    key = (mm.group("key") or "").strip().lower()
                    val = (mm.group("val") or "").strip()
                    if key == "context":
                        da.context = val or None
                    elif key == "due":
                        da.due = val or None
                    elif key in ("waiting_for", "waiting"):
                        da.waiting_for = val or None
                    elif key == "notes":
                        da.notes = val or None

                j += 1

            draft_actions.append(da)
            i = j  # continue after metadata block

    return ProjectNotesEdits(
        project_id=pid,
        outcome=outcome,
        notes=notes,
        agenda_notes=agenda,
        draft_actions=draft_actions,
    )

