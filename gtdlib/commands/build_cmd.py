from __future__ import annotations

from pathlib import Path
from collections import defaultdict

from gtdlib.store import load_master, VIEWS_DIRNAME
from gtdlib.rules.projects import (
    count_actions_by_state,
    is_project_stalled,
)
from gtdlib.commands.build_project_notes import build_project_notes

def cmd_build(base_dir: Path) -> int:
    """
    Generate Markdown GTD views from master.json.
    Writes stable IDs into Markdown as HTML comments so sync can map edits back.
    """

    master = load_master(base_dir)
    views_dir = base_dir / VIEWS_DIRNAME

    if not views_dir.exists():
        raise FileNotFoundError(
            f"{VIEWS_DIRNAME}/ not found in {base_dir}. Run `gtd init` first."
        )

    actions = master.get("actions", {})
    projects = master.get("projects", {})

    _build_next_actions(views_dir, actions, projects)
    _build_projects(views_dir, projects, actions)
    _build_someday(views_dir, projects, actions)
    _build_waiting_for(views_dir, actions, projects)
    _build_agenda(views_dir, actions, projects)
    _build_stalled_projects(views_dir, actions, projects)
    build_project_notes(base_dir, projects, actions)

    print("Views rebuilt.")
    return 0


def _id_comment(item_id: str) -> str:
    return f"<!-- id:{item_id} -->"


# -------------------------
# View builders
# -------------------------

def _build_next_actions(views_dir: Path, actions: dict, projects: dict) -> None:
    # Group ACTIVE actions by context
    by_context: dict[str, list[tuple[str, dict]]] = defaultdict(list)

    for aid, action in actions.items():
        if action.get("state") == "active":
            ctx = action.get("context", "inbox")
            by_context[ctx].append((aid, action))

    lines: list[str] = ["# Next Actions\n"]

    for context in sorted(by_context):
        lines.append(f"## @{context}\n")
        # stable ordering: due date then title
        items = sorted(
            by_context[context],
            key=lambda t: ((t[1].get("due") or "9999-12-31"), t[1].get("title", "")),
        )
        for aid, a in items:
            title = (a.get("title") or "").strip()
            due_prefix = f"(due {a['due']}) " if a.get("due") else ""
            proj_prefix = ""
            pid = a.get("project")
            if pid and pid in projects:
                proj_title = (projects[pid].get("title") or "").strip()
                if proj_title:
                    proj_prefix = f"[{proj_title}] "

            lines.append(f"- [ ] {due_prefix}{proj_prefix}{title} {_id_comment(aid)}")

        lines.append("")

    (views_dir / "next_actions.md").write_text(
        "\n".join(lines).strip() + "\n",
        encoding="utf-8",
    )


def _build_projects(views_dir: Path, projects: dict, actions: dict) -> None:
    """
    Projects view shows ACTIVE projects with:
      - Active actions count
      - Waiting items count
    (So you don't miss waiting-for work.)
    """
    lines: list[str] = ["# Projects\n"]

    for pid, project in sorted(projects.items(), key=lambda t: (t[1].get("title", "") or "").lower()):
        lifecycle = (project.get("lifecycle") or "live").strip().lower()
        if lifecycle != "live":
            continue

        if (project.get("state") or "").strip().lower() != "active":
            continue

        counts = count_actions_by_state(actions, pid)
        n_active = counts.get("active", 0)
        n_waiting = counts.get("waiting", 0)

        due = f" (due {project['due']})" if project.get("due") else ""
        lines.append(f"## {project.get('title','')}{due} {_id_comment(pid)}")
        lines.append(f"- Active actions: {n_active}")
        lines.append(f"- Waiting items: {n_waiting}")
        lines.append("")

    (views_dir / "projects.md").write_text(
        "\n".join(lines).strip() + "\n",
        encoding="utf-8",
    )


def _build_someday(views_dir: Path, projects: dict, actions: dict) -> None:
    lines: list[str] = ["# Someday / Maybe\n"]

        
    someday_projects = [
        (pid, p)
        for pid, p in projects.items()
        if (p.get("lifecycle") or "live").strip().lower() == "live"
        and (p.get("state") or "").strip().lower() == "someday"
    ]
    
    someday_actions: list[tuple[str, dict]] = []

    for aid, a in actions.items():
        if a.get("state") != "someday":
            continue

        pid = a.get("project")

        # Standalone someday actions are allowed.
        if not pid:
            someday_actions.append((aid, a))
            continue

        project = projects.get(pid)
        if not project:
            continue

        lifecycle = (project.get("lifecycle") or "live").strip().lower()
        if lifecycle != "live":
            continue

        someday_actions.append((aid, a))

    if someday_projects:
        lines.append("## Projects\n")
        for pid, p in sorted(someday_projects, key=lambda t: (t[1].get("title", "") or "").lower()):
            lines.append(f"- {p.get('title','')} {_id_comment(pid)}")
        lines.append("")

    if someday_actions:
        lines.append("## Actions\n")
        for aid, a in sorted(someday_actions, key=lambda t: (t[1].get("title", "") or "").lower()):
            lines.append(f"- {a.get('title','')} {_id_comment(aid)}")
        lines.append("")

    (views_dir / "someday.md").write_text(
        "\n".join(lines).strip() + "\n",
        encoding="utf-8",
    )


def _build_waiting_for(views_dir: Path, actions: dict, projects: dict) -> None:
    lines: list[str] = ["# Waiting For", ""]

    items: list[tuple[str, dict]] = []

    for aid, a in actions.items():
        if a.get("state") != "waiting":
            continue

        pid = a.get("project")

        # Standalone waiting-for items are allowed.
        if not pid:
            items.append((aid, a))
            continue

        project = projects.get(pid)
        if not project:
            continue

        lifecycle = (project.get("lifecycle") or "live").strip().lower()
        if lifecycle != "live":
            continue

        if (project.get("state") or "active").strip().lower() != "active":
            continue

        items.append((aid, a))

    if not items:
        lines.append("_No waiting items._")
        (views_dir / "waiting_for.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    # Group by waiting_for
    groups: dict[str, list[tuple[str, dict]]] = {}
    for aid, a in items:
        who = (a.get("waiting_for") or "Unspecified").strip()
        groups.setdefault(who, []).append((aid, a))

    for who in sorted(groups.keys(), key=str.lower):
        lines.append(f"## {who}")
        lines.append("")
        for aid, a in sorted(
            groups[who],
            key=lambda t: ((t[1].get("due") or "9999-12-31"), (t[1].get("title") or "")),
        ):
            title = (a.get("title") or "").strip()

            proj_label = ""
            pid = a.get("project")
            if pid and pid in projects:
                ptitle = (projects[pid].get("title") or "").strip()
                if ptitle:
                    proj_label = f" [{ptitle}]"

            due = f" (due {a['due']})" if a.get("due") else ""
            lines.append(f"- [ ] {title}{proj_label}{due} {_id_comment(aid)}")

        lines.append("")

    (views_dir / "waiting_for.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _build_agenda(views_dir: Path, actions: dict, projects: dict) -> None:
    lines: list[str] = ["# Agenda", ""]

    agenda_items: list[tuple[str, dict]] = []
    for aid, a in actions.items():
        if a.get("state") != "active":
            continue
        ctx = (a.get("context") or "").strip()
        if ctx.startswith("agenda_"):
            agenda_items.append((aid, a))

    if not agenda_items:
        lines.append("_No agenda items._")
        (views_dir / "agenda.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    groups: dict[str, list[tuple[str, dict]]] = {}
    for aid, a in agenda_items:
        ctx = (a.get("context") or "").strip()
        who = ctx[len("agenda_"):].strip() or "unspecified"
        groups.setdefault(who, []).append((aid, a))

    for who in sorted(groups.keys(), key=str.lower):
        lines.append(f"## {who}")
        lines.append("")
        items = sorted(
            groups[who],
            key=lambda t: ((t[1].get("due") or "9999-12-31"), (t[1].get("title") or "")),
        )
        for aid, a in items:
            due = f" (due {a['due']})" if a.get("due") else ""
            proj_label = ""
            pid = a.get("project")
            if pid and pid in projects:
                pt = (projects[pid].get("title") or "").strip()
                if pt:
                    proj_label = f" [{pt}]"
            lines.append(f"- [ ] {a.get('title','')}{proj_label}{due} {_id_comment(aid)}")
        lines.append("")

    (views_dir / "agenda.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _build_stalled_projects(views_dir: Path, actions: dict, projects: dict) -> None:
    lines: list[str] = ["# Stalled Projects", ""]

    stalled: list[tuple[str, dict]] = []
    for pid, p in projects.items():
        if is_project_stalled(projects, actions, pid):
            stalled.append((pid, p))

    if not stalled:
        lines.append("_No stalled projects._")
        (views_dir / "stalled_projects.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    stalled.sort(key=lambda t: (t[1].get("due") or "9999-12-31", t[1].get("title") or ""))

    for pid, p in stalled:
        title = (p.get("title") or "").strip()
        due = p.get("due")
        due_suffix = f" (due {due})" if due else ""
        lines.append(f"- {title}{due_suffix} {_id_comment(pid)}")

    (views_dir / "stalled_projects.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


