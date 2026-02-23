from __future__ import annotations

from pathlib import Path

from gtdlib.store import PROJECTS_DIRNAME


def _slugify(title: str) -> str:
    import re
    s = (title or "").strip().lower()
    s = s.replace("-", "_").replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:60] or "project"

def _project_root_for_lifecycle(base_dir: Path, lifecycle: str) -> Path | None:
    """
    Where should the project folder live for this lifecycle?
    - live   -> projects/
    - review -> review/
    - trash  -> trash/
    - archive -> (not in workspace; project removed from master)
    """
    lc = (lifecycle or "live").strip().lower()

    if lc == "live":
        return base_dir / PROJECTS_DIRNAME
    if lc == "review":
        return base_dir / "review"
    if lc == "trash":
        return base_dir / "trash"
    return None


def ensure_project_notes_for_project(base_dir: Path, pid: str, project: dict, actions: dict) -> Path | None:
    """
    Create/update the project folder + @project_notes.md for ONE project.

    Rules:
    - Skip someday projects (no folder by design).
    - Write to a lifecycle-appropriate root (projects/, review/, trash/).
    """
    state = (project.get("state") or "").strip().lower()
    if state == "someday":
        return None

    lifecycle = (project.get("lifecycle") or "live").strip().lower()
    root = _project_root_for_lifecycle(base_dir, lifecycle)
    if root is None:
        return None

    root.mkdir(parents=True, exist_ok=True)

    title = (project.get("title") or pid).strip()
    outcome = (project.get("outcome") or "").strip()
    notes = (project.get("notes") or "").strip()
    agenda_notes = (project.get("agenda_notes") or "").strip()

    slug = _slugify(title)
    folder_name = f"{slug}__{pid}"
    proj_dir = root / folder_name
    proj_dir.mkdir(parents=True, exist_ok=True)

    file_path = proj_dir / "@project_notes.md"

    lines: list[str] = []

    lines.append(f"# {title} <!-- id:{pid} -->")
    lines.append("")

    # Outcome
    lines.append("## Outcome")
    lines.append(outcome or "")
    lines.append("")

    # Status
    lines.append("## Status")
    lines.append(f"- State: {project.get('state')}")
    lines.append(f"- Lifecycle: {project.get('lifecycle') or 'live'}")
    lines.append(f"- Due: {project.get('due')}")
    lines.append("")

    # Additional Notes
    lines.append("## Additional notes")
    lines.append(notes or "")
    lines.append("")

    # Agenda Notes
    lines.append("## Agenda notes")
    lines.append(agenda_notes or "")
    lines.append("")

    # Sections
    sections = {
        "active": "## Active actions",
        "waiting": "## Waiting for",
        "someday": "## Someday actions",
    }

    for st, header in sections.items():
        lines.append(header)
        lines.append("")
        for aid, a in actions.items():
            if a.get("project") != pid:
                continue
            if (a.get("state") or "").strip().lower() != st:
                continue

            title_a = (a.get("title") or "").strip()
            lines.append(f"- [ ] {title_a} <!-- id:{aid} -->")

            if st == "waiting":
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
        if (a.get("state") or "").strip().lower() != "completed":
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
    return file_path

def build_project_notes(base_dir: Path, projects: dict, actions: dict) -> None:

    for pid, p in projects.items():
        ensure_project_notes_for_project(base_dir, pid, p, actions)
