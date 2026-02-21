from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECTS_ROOT = "projects"
REVIEW_ROOT = "review"
TRASH_ROOT = "trash"
ARCHIVES_ROOT = "archives"

PROJECT_NOTES_NAME = "@project_notes.md"
DEBRIEF_NAME = "@debrief.md"


@dataclass(frozen=True)
class ProjectFolderMatch:
    root_name: str        # e.g. "projects"
    path: Path            # full path to folder


def _matches_pid(dir_name: str, project_id: str) -> bool:
    # your convention: <snakecase>__p_1f99eaef
    return dir_name.endswith(f"__{project_id}")


def find_project_folder(base_dir: Path, project_id: str) -> ProjectFolderMatch | None:
    """
    Search for a project folder matching '*__{project_id}' under known roots.
    Returns the first match in priority order.
    """
    roots = [PROJECTS_ROOT, REVIEW_ROOT, TRASH_ROOT, ARCHIVES_ROOT]
    for root in roots:
        root_path = base_dir / root
        if not root_path.exists():
            continue
        for child in root_path.iterdir():
            if child.is_dir() and _matches_pid(child.name, project_id):
                return ProjectFolderMatch(root_name=root, path=child)
    return None


def ensure_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def ensure_project_notes_exists(project_folder: Path, project_id: str, title: str) -> Path:
    """
    Ensure @project_notes.md exists. Create a minimal skeleton if missing.
    """
    fp = project_folder / PROJECT_NOTES_NAME
    ensure_file(
        fp,
        f"# {title} <!-- id:{project_id} -->\n\n"
        "## Outcome\n\n\n"
        "## Status\n"
        "- State: active\n"
        "- Due: None\n\n",
    )
    return fp


def ensure_debrief_exists(project_folder: Path, project_id: str, title: str) -> Path:
    """
    Create @debrief.md when a project enters review. Never overwritten.
    """
    fp = project_folder / DEBRIEF_NAME
    ensure_file(
        fp,
        f"# Debrief: {title} <!-- id:{project_id} -->\n\n"
        "## Status\n\n"
        "- Review action: (tick in next_actions when done)\n\n"
        "## Files moved to deep storage\n\n"
        "- \n\n"
        "## Notes\n\n"
        "- \n",
    )
    return fp
