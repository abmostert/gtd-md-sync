from __future__ import annotations

from pathlib import Path
from collections import defaultdict

from gtdlib.store import (
    load_master,
    VIEWS_DIRNAME,
)


def cmd_build(base_dir: Path) -> int:
    """
    Generate Markdown GTD views from master.json.
    This command is read-only with respect to GTD state.
    """

    master = load_master(base_dir)
    views_dir = base_dir / VIEWS_DIRNAME

    if not views_dir.exists():
        raise FileNotFoundError(
            f"{VIEWS_DIRNAME}/ not found in {base_dir}. Run `gtd init` first."
        )

    actions = master.get("actions", {})
    projects = master.get("projects", {})

    _build_next_actions(views_dir, actions)
    _build_projects(views_dir, projects, actions)
    _build_someday(views_dir, projects, actions)

    print("Views rebuilt.")
    return 0


# -------------------------
# View builders
# -------------------------

def _build_next_actions(views_dir: Path, actions: dict) -> None:
    by_context: dict[str, list[dict]] = defaultdict(list)

    for action in actions.values():
        if action["state"] == "active":
            ctx = action.get("context", "inbox")
            by_context[ctx].append(action)

    lines = ["# Next Actions\n"]

    for context in sorted(by_context):
        lines.append(f"## @{context}\n")
        for a in by_context[context]:
            due = f" (due {a['due']})" if a.get("due") else ""
            lines.append(f"- [ ] {a['title']}{due}")
        lines.append("")

    (views_dir / "next_actions.md").write_text(
        "\n".join(lines).strip() + "\n",
        encoding="utf-8",
    )


def _build_projects(views_dir: Path, projects: dict, actions: dict) -> None:
    lines = ["# Projects\n"]

    for pid, project in projects.items():
        if project["state"] != "active":
            continue

        active_actions = [
            a for a in actions.values()
            if a.get("project") == pid and a["state"] == "active"
        ]

        due = f" (due {project['due']})" if project.get("due") else ""
        lines.append(f"## {project['title']}{due}")
        lines.append(f"- Active actions: {len(active_actions)}")
        lines.append("")

    (views_dir / "projects.md").write_text(
        "\n".join(lines).strip() + "\n",
        encoding="utf-8",
    )


def _build_someday(views_dir: Path, projects: dict, actions: dict) -> None:
    lines = ["# Someday / Maybe\n"]

    if any(p["state"] == "someday" for p in projects.values()):
        lines.append("## Projects\n")
        for project in projects.values():
            if project["state"] == "someday":
                lines.append(f"- {project['title']}")
        lines.append("")

    if any(a["state"] == "someday" for a in actions.values()):
        lines.append("## Actions\n")
        for action in actions.values():
            if action["state"] == "someday":
                lines.append(f"- {action['title']}")
        lines.append("")

    (views_dir / "someday.md").write_text(
        "\n".join(lines).strip() + "\n",
        encoding="utf-8",
    )
