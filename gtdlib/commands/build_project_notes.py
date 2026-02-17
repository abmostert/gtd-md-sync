from __future__ import annotations

from pathlib import Path
from datetime import datetime

from gtdlib.store import PROJECTS_DIRNAME
from gtdlib.rules.projects import iter_actions_for_project
from gtdlib.rules.projects import count_actions_by_state


def _slugify(title: str) -> str:
    import re
    s = (title or "").strip().lower()
    s = s.replace("-", "_").replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:60] or "project"


def build_project_notes(base_dir: Path, projects: dict, actions: dict) -> None:
    projects_dir = base_dir / PROJECTS_DIRNAME
    projects_dir.mkdir(parents=True, exist_ok=True)

    for pid, p in projects.items():
        if (p.get("state") or "").strip().lower() != "active":
                continue

        title = (p.get("title") or pid).strip()
        slug = _slugify(title)
        folder_name = f"{slug}__{pid}"
        proj_dir = projects_dir / folder_name
        proj_dir.mkdir(parents=True, exist_ok=True)

        file_path = proj_dir / "project_notes.md"

        lines: list[str] = []

        lines.append(f"# {title} <!-- id:{pid} -->")
        lines.append("")

               # Outcome
        lines.append("## Outcome")
        lines.append(p.get("notes") or "")
        lines.append("")

        # Status
        lines.append("## Status")
        lines.append(f"- State: {p.get('state')}")
        lines.append(f"- Due: {p.get('due')}")
        lines.append("")

        # Sections
        sections = {
            "active": "## Active actions",
            "waiting": "## Waiting for",
            "someday": "## Someday actions",
        }

        for state, header in sections.items():
            lines.append(header)
            lines.append("")
            for aid, a in actions.items():
                if a.get("project") != pid:
                    continue
                if a.get("state") != state:
                    continue

                lines.append(f"- [{'x' if a.get('state') == 'completed' else ' '}] {a.get('title')} <!-- id:{aid} -->")

                if state == "waiting":
                    lines.append(f"  - waiting_for: {a.get('waiting_for')}")
                else:
                    lines.append(f"  - context: {a.get('context')}")

                if a.get("due"):
                    lines.append(f"  - due: {a.get('due')}")

                if a.get("notes"):
                    lines.append(f"  - notes: {a.get('notes')}")

                lines.append("")

            lines.append("")

        # Completed archive
        lines.append("## Completed actions (archive)")
        lines.append("")
        for aid, a in actions.items():
            if a.get("project") != pid:
                continue
            if a.get("state") != "completed":
                continue

            lines.append(f"- [x] {a.get('title')} <!-- id:{aid} -->")
            lines.append(f"  - created: {a.get('created')}")
            if a.get("due"):
                lines.append(f"  - due: {a.get('due')}")
            lines.append(f"  - completed: {a.get('completed')}")
            if a.get("notes"):
                lines.append(f"  - notes: {a.get('notes')}")
            lines.append("")

         # Instruction block
        lines.append("<!--")
        lines.append("HOW TO ADD A NEW ACTION")
        lines.append("")
        lines.append("Add a checkbox under the correct section without an id marker.")
        lines.append("")
        lines.append("Example:")
        lines.append("")
        lines.append("- [ ] draft: Example action title")
        lines.append("  - context: work")
        lines.append("  - due: 2026-02-22")
        lines.append("  - notes: optional notes")
        lines.append("")
        lines.append("Run `gtd sync` to assign an ID automatically.")
        lines.append("-->")
        lines.append("")

        file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
