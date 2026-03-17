from __future__ import annotations

from pathlib import Path
from collections import defaultdict
from gtdlib.store import load_master, VIEWS_DIRNAME
from gtdlib.rules.projects import (
    count_actions_by_state,
    is_project_stalled,
)
from gtdlib.commands.build_project_notes import build_project_notes
from gtdlib.rules.visibility import (
    is_active_project,
    is_someday_project,
    is_visible_agenda_action,
    is_visible_next_action,
    is_visible_someday_action,
    is_visible_waiting_action,
)
import math
from datetime import date
from gtdlib.config import get_focus_config


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
    _build_focus(views_dir, actions, projects, base_dir)
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

def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s).strip())
    except Exception:
        return None


def _days_until(target: date | None, today: date) -> int | None:
    if target is None:
        return None
    return (target - today).days


def _action_age_days(action: dict, today: date) -> int:
    created = _parse_iso_date((action.get("created") or "")[:10])
    last_touched = _parse_iso_date((action.get("last_touched") or "")[:10])

    basis = created or last_touched
    if basis is None:
        return 0

    age = (today - basis).days
    return max(age, 0)


def _score_next_action(action: dict, project: dict | None, today: date, weights: dict) -> float:
    action_due = _parse_iso_date(action.get("due"))
    project_due = _parse_iso_date(project.get("due")) if project else None

    d_a = _days_until(action_due, today)
    d_p = _days_until(project_due, today)
    age_days = _action_age_days(action, today)

    score = 0.0

    # Action due urgency
    if d_a is not None:
        if d_a >= 0:
            score += weights["action_due"] / (d_a + 1.0)
        else:
            score += weights["action_due"] + weights["action_overdue_slope"] * abs(d_a)

    # Project due urgency
    if d_p is not None:
        if d_p >= 0:
            score += weights["project_due"] / (d_p + 1.0)
        else:
            score += weights["project_due"] + weights["project_overdue_slope"] * abs(d_p)

    # Age / stagnation pressure
    score += weights["age"] * math.log(age_days + 1.0)

    # Action/project tension
    if d_a is not None and d_p is not None and d_p > d_a:
        score += weights["tension"] * ((d_p - d_a) / (d_p + 1.0))

    # Explicit overdue bonus
    if d_a is not None and d_a < 0:
        score += weights["overdue_bonus"]

    return score



# -------------------------
# View builders
# -------------------------

def _collect_visible_next_actions(actions: dict, projects: dict) -> list[tuple[str, dict]]:
    return [
        (aid, action)
        for aid, action in actions.items()
        if is_visible_next_action(action, projects)
    ]


def _build_next_actions(views_dir: Path, actions: dict, projects: dict) -> None:
    lines: list[str] = ["# Next Actions", ""]

    items = _collect_visible_next_actions(actions, projects)

    if not items:
        lines.append("_No next actions._")
        (views_dir / "next_actions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    by_context: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for aid, action in items:
        ctx = (action.get("context") or "inbox").strip()
        by_context[ctx].append((aid, action))

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

def _build_focus(views_dir: Path, actions: dict, projects: dict, base_dir: Path) -> None:
    focus_cfg = get_focus_config(base_dir)
    if not focus_cfg.get("enabled", True):
        return

    lines: list[str] = ["# Focus", ""]

    items = _collect_visible_next_actions(actions, projects)
    if not items:
        lines.append("_No focused next actions._")
        (views_dir / "focus.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    today = date.today()
    scored: list[tuple[str, dict, float]] = []

    for aid, action in items:
        pid = action.get("project")
        project = projects.get(pid) if pid else None
        score = _score_next_action(action, project, today, focus_cfg["weights"])
        scored.append((aid, action, score))

    scored.sort(
        key=lambda t: (
            -t[2],
            (t[1].get("due") or "9999-12-31"),
            (t[1].get("title") or "").lower(),
        )
    )

    top_n = focus_cfg["max_items"]
    shortlisted = scored[:top_n]

    by_context: dict[str, list[tuple[str, dict, float]]] = defaultdict(list)
    for aid, action, score in shortlisted:
        ctx = (action.get("context") or "inbox").strip()
        by_context[ctx].append((aid, action, score))

    for ctx in sorted(by_context.keys(), key=str.lower):
        lines.append(f"## {ctx}")
        lines.append("")

        items_in_context = sorted(
            by_context[ctx],
            key=lambda t: (-t[2], (t[1].get("due") or "9999-12-31"), (t[1].get("title") or "").lower()),
        )

        for aid, action, score in items_in_context:
            due = f" (due {action['due']})" if action.get("due") else ""
            proj_label = ""
            pid = action.get("project")
            if pid and pid in projects:
                pt = (projects[pid].get("title") or "").strip()
                if pt:
                    proj_label = f" [{pt}]"

            lines.append(
                f"- [ ] {action.get('title','')}{proj_label}{due} {{score: {score:.2f}}} {_id_comment(aid)}"
            )
        lines.append("")

    (views_dir / "focus.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

def _build_projects(views_dir: Path, projects: dict, actions: dict) -> None:
    """
    Projects view shows ACTIVE projects with:
      - Active actions count
      - Waiting items count
    (So you don't miss waiting-for work.)
    """
    lines: list[str] = ["# Projects\n"]

    for pid, project in sorted(projects.items(), key=lambda t: (t[1].get("title", "") or "").lower()):
        if not is_active_project(project):
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
        if is_someday_project(p)
    ]
    
    someday_actions: list[tuple[str, dict]] = [
        (aid, a)
        for aid, a in actions.items()
        if is_visible_someday_action(a, projects)
    ]

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

        
    items: list[tuple[str, dict]] = [
        (aid, a)
        for aid, a in actions.items()
        if is_visible_waiting_action(a, projects)
    ]

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

    agenda_items: list[tuple[str, dict]] = [
        (aid, a)
        for aid, a in actions.items()
        if is_visible_agenda_action(a, projects)
    ]

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


