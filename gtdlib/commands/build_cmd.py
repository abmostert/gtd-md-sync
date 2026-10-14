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
from datetime import date, datetime, timezone
from gtdlib.config import get_focus_config
from gtdlib.rules.scoring import (
    days_until,
    due_bucket,
    parse_iso_date,
    score_next_action,
)
from gtdlib.metrics.weekly import (
    render_project_metrics_markdown,
    week_start_for,
)


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

    current_week_start = week_start_for(
        datetime.now(timezone.utc)
    )

    metrics_text = render_project_metrics_markdown(
        base_dir,
        master,
        current_week_start,
    )

    (views_dir / "metrics.md").write_text(
        metrics_text,
        encoding="utf-8",
    )

    print("Views rebuilt.")
    return 0


def _id_comment(item_id: str) -> str:
    return f"<!-- id:{item_id} -->"





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
        score = score_next_action(action, project, today, focus_cfg["weights"])
        scored.append((aid, action, score))

    context_cap = focus_cfg["context_cap"]
    include_overdue = focus_cfg["include_overdue"]
    include_due_today = focus_cfg["include_due_today"]

    # Split into mandatory vs remaining
    mandatory: list[tuple[str, dict, float]] = []
    remaining: list[tuple[str, dict, float]] = []

    for aid, action, score in scored:
        due_dt = parse_iso_date(action.get("due"))
        d = days_until(due_dt, today)

        is_overdue = d is not None and d < 0
        is_due_today = d is not None and d == 0

        if (include_overdue and is_overdue) or (include_due_today and is_due_today):
            mandatory.append((aid, action, score))
        else:
            remaining.append((aid, action, score))

    # Group mandatory items by context
    by_context: dict[str, list[tuple[str, dict, float]]] = defaultdict(list)
    selected_ids: set[str] = set()

    for aid, action, score in mandatory:
        ctx = (action.get("context") or "inbox").strip()
        by_context[ctx].append((aid, action, score))
        selected_ids.add(aid)

    # Sort remaining items by score desc, then due, then title
    remaining.sort(
        key=lambda t: (
            -t[2],
            (t[1].get("due") or "9999-12-31"),
            (t[1].get("title") or "").lower(),
        )
    )

    # Per-context fill up to cap, but mandatory items can exceed the cap
    for aid, action, score in remaining:
        if aid in selected_ids:
            continue

        ctx = (action.get("context") or "inbox").strip()
        current_count = len(by_context.get(ctx, []))

        if current_count >= context_cap:
            continue

        by_context[ctx].append((aid, action, score))
        selected_ids.add(aid)

    if not by_context:
        lines.append("_No focused next actions._")
        (views_dir / "focus.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    for ctx in sorted(by_context.keys(), key=str.lower):
        lines.append(f"## {ctx}")
        lines.append("")

        items_in_context = sorted(
            by_context[ctx],
            key=lambda t: (
                due_bucket(t[1], today),
                -t[2],
                (t[1].get("title") or "").lower(),
            ),
        )

        for aid, action, score in items_in_context:
            title = action.get("title", "")
            due_prefix = f"(due {action['due']}) " if action.get("due") else ""

            proj_prefix = ""
            pid = action.get("project")
            if pid and pid in projects:
                pt = (projects[pid].get("title") or "").strip()
                if pt:
                    proj_prefix = f"[{pt}] "

            lines.append(
                f"- [ ] {due_prefix}{proj_prefix}{title} {{score: {score:.2f}}} {_id_comment(aid)}"
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
    lines: list[str] = ["# Someday / Maybe", ""]

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

    # -------------------------
    # SOMEDAY PROJECTS
    # -------------------------
    if someday_projects:
        lines.append("## Projects")
        lines.append("")

        by_category: dict[str, list[tuple[str, dict]]] = defaultdict(list)

        for pid, project in someday_projects:
            category = (project.get("category") or "").strip()

            if not category:
                category = "Uncategorized"

            by_category[category].append((pid, project))

        # Named categories first, Uncategorized last
        category_names = sorted(
            [c for c in by_category if c != "Uncategorized"],
            key=str.lower,
        )

        if "Uncategorized" in by_category:
            category_names.append("Uncategorized")

        for category in category_names:
            lines.append(f"### {category}")
            lines.append("")

            items = sorted(
                by_category[category],
                key=lambda t: (t[1].get("title", "") or "").lower(),
            )

            for pid, project in items:
                title = (project.get("title") or "").strip()
                lines.append(f"- {title} {_id_comment(pid)}")

            lines.append("")

    # -------------------------
    # SOMEDAY ACTIONS
    # -------------------------
    if someday_actions:
        lines.append("## Actions")
        lines.append("")

        for aid, action in sorted(
            someday_actions,
            key=lambda t: (t[1].get("title", "") or "").lower(),
        ):
            title = (action.get("title") or "").strip()
            lines.append(f"- {title} {_id_comment(aid)}")

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


