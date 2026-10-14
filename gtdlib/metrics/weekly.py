from __future__ import annotations

import json
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

from gtdlib.config import get_focus_config
from gtdlib.metrics.log import append_metric_event
from gtdlib.rules.scoring import score_next_action
from gtdlib.rules.visibility import (
    is_visible_agenda_action,
    is_visible_next_action,
    is_visible_waiting_action,
)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    text = str(value).strip()

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def get_cleared_projects(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """
    Return projects cleared in the half-open interval:

        start <= cleared_at < end

    Sources:
      1. review/trash projects still present in master.json
      2. project_purged events for projects no longer in master.json

    Deduplication is by project_id.

    Current master.json records take precedence over historical purge events.
    """

    cleared_by_id: dict[str, dict] = {}

    projects = master.get("projects", {})

    # ------------------------------------------------------------
    # Current projects still present in master.json
    # ------------------------------------------------------------

    if isinstance(projects, dict):
        for pid, project in projects.items():
            if not isinstance(project, dict):
                continue

            lifecycle = str(
                project.get("lifecycle") or "live"
            ).strip().lower()

            if lifecycle == "review":
                cleared_at_raw = project.get("completed")
                clearance_type = "completed"

            elif lifecycle == "trash":
                cleared_at_raw = project.get("trashed_at")
                clearance_type = "deleted"

            else:
                continue

            cleared_at = _parse_timestamp(cleared_at_raw)

            if cleared_at is None:
                continue

            if not (start <= cleared_at < end):
                continue

            cleared_by_id[pid] = {
                "project_id": pid,
                "project_title": (
                    project.get("title") or ""
                ).strip(),
                "clearance_type": clearance_type,
                "cleared_at": cleared_at,
                "lifetime_action_count": int(
                    project.get("lifetime_action_count", 0)
                ),
                "source": "master",
            }

    # ------------------------------------------------------------
    # Historical projects already purged from master.json
    # ------------------------------------------------------------

    metrics_path = base_dir / "metrics.jsonl"

    if metrics_path.exists():
        with metrics_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("event") != "project_purged":
                    continue

                pid = event.get("project_id")

                if not pid:
                    continue

                # master.json wins if the same project is present there
                if pid in cleared_by_id:
                    continue

                completed_raw = event.get("completed")
                trashed_raw = event.get("trashed_at")

                if completed_raw:
                    cleared_at_raw = completed_raw
                    clearance_type = "completed"

                elif trashed_raw:
                    cleared_at_raw = trashed_raw
                    clearance_type = "deleted"

                else:
                    continue

                cleared_at = _parse_timestamp(cleared_at_raw)

                if cleared_at is None:
                    continue

                if not (start <= cleared_at < end):
                    continue

                lifetime_count = event.get(
                    "lifetime_action_count"
                )

                # Older purge events predate lifetime_action_count.
                if lifetime_count is None:
                    lifetime_count = event.get("n_actions", 0)

                cleared_by_id[pid] = {
                    "project_id": pid,
                    "project_title": (
                        event.get("project_title") or ""
                    ).strip(),
                    "clearance_type": clearance_type,
                    "cleared_at": cleared_at,
                    "lifetime_action_count": int(
                        lifetime_count or 0
                    ),
                    "source": "metrics",
                }

    return sorted(
        cleared_by_id.values(),
        key=lambda item: item["cleared_at"],
    )

def summarize_cleared_project_sizes(
    cleared_projects: list[dict],
) -> dict[str, int]:
    """
    Count cleared projects by lifetime action count.

    Buckets:
      small  = 1-5 actions
      medium = 6-15 actions
      large  = 16+ actions
    """
    counts = {
        "small": 0,
        "medium": 0,
        "large": 0,
    }

    for project in cleared_projects:
        n_actions = int(
            project.get("lifetime_action_count", 0)
        )

        if 1 <= n_actions <= 5:
            counts["small"] += 1

        elif 6 <= n_actions <= 15:
            counts["medium"] += 1

        elif n_actions >= 16:
            counts["large"] += 1

    return counts

def week_start_for(moment: datetime) -> datetime:
    """
    Return Monday 00:00 UTC for the week containing moment.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    moment = moment.astimezone(timezone.utc)

    monday = moment - timedelta(days=moment.weekday())

    return monday.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def count_outstanding_actions(master: dict) -> int:
    """
    Count actions currently contributing to the active workload:

      - visible next actions
      - visible waiting-for actions
      - visible agenda actions

    Someday and completed actions are excluded.
    """

    projects = master.get("projects", {})
    actions = master.get("actions", {})

    if not isinstance(projects, dict):
        projects = {}

    if not isinstance(actions, dict):
        return 0

    count = 0

    for action in actions.values():
        if not isinstance(action, dict):
            continue

        if (
            is_visible_next_action(action, projects)
            or is_visible_waiting_action(action, projects)
            or is_visible_agenda_action(action, projects)
        ):
            count += 1

    return count


def action_weight_at(
    base_dir: Path,
    action: dict,
    project: dict | None,
    moment: datetime,
) -> float:
    """
    Calculate an action's Focus score at a specific moment.
    """

    focus_cfg = get_focus_config(base_dir)

    return float(
        score_next_action(
            action,
            project,
            moment.date(),
            focus_cfg["weights"],
        )
    )

def total_outstanding_weight(
    base_dir: Path,
    master: dict,
    today: date | None = None,
) -> float:
    """
    Sum Focus scores for all visible executable next actions.

    Waiting and agenda actions do not contribute psychological weight.
    """

    projects = master.get("projects", {})
    actions = master.get("actions", {})

    if not isinstance(projects, dict):
        projects = {}

    if not isinstance(actions, dict):
        return 0.0

    if today is None:
        today = date.today()

    focus_cfg = get_focus_config(base_dir)
    weights = focus_cfg["weights"]

    total = 0.0

    for action in actions.values():
        if not isinstance(action, dict):
            continue

        if not is_visible_next_action(action, projects):
            continue

        pid = action.get("project")
        project = projects.get(pid) if pid else None

        total += score_next_action(
            action,
            project,
            today,
            weights,
        )

    return total

def count_active_projects(master: dict) -> int:
    """
    Count projects that are currently active and live.
    """
    projects = master.get("projects", {})

    if not isinstance(projects, dict):
        return 0

    count = 0

    for project in projects.values():
        if not isinstance(project, dict):
            continue

        state = str(
            project.get("state") or ""
        ).strip().lower()

        lifecycle = str(
            project.get("lifecycle") or "live"
        ).strip().lower()

        if state == "active" and lifecycle == "live":
            count += 1

    return count

def get_week_snapshot(
    base_dir: Path,
    week_start: datetime,
) -> dict | None:
    """
    Return the existing snapshot for week_start, if present.
    """
    metrics_path = base_dir / "metrics.jsonl"

    if not metrics_path.exists():
        return None

    week_key = week_start.date().isoformat()

    with metrics_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("event") != "week_snapshot":
                continue

            if event.get("week_start") == week_key:
                return event

    return None

def ensure_week_snapshot(
    base_dir: Path,
    master: dict,
    now: datetime | None = None,
) -> dict:
    """
    Ensure that one start-of-week snapshot exists for the current week.

    The first call during a week freezes the denominator before the
    command making the call changes GTD state.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    start = week_start_for(now)

    existing = get_week_snapshot(
        base_dir,
        start,
    )

    if existing is not None:
        return existing

    snapshot = {
        "event": "week_snapshot",
        "week_start": start.date().isoformat(),
        "at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "active_projects": count_active_projects(master),
        "outstanding_actions": count_outstanding_actions(master),
        "outstanding_weight": total_outstanding_weight(
            base_dir,
            master,
        ),
    }

    append_metric_event(
        base_dir,
        snapshot,
    )

    return snapshot

def get_projects_added(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """
    Return projects created in the half-open interval:

        start <= created_at < end

    Sources:
      1. projects still present in master.json
      2. project_purged events for projects no longer in master.json

    Deduplication is by project_id.
    """

    added_by_id: dict[str, dict] = {}

    projects = master.get("projects", {})

    if isinstance(projects, dict):
        for pid, project in projects.items():
            if not isinstance(project, dict):
                continue

            created_at = _parse_timestamp(
                project.get("created")
            )

            if created_at is None:
                continue

            if not (start <= created_at < end):
                continue

            added_by_id[pid] = {
                "project_id": pid,
                "project_title": (
                    project.get("title") or ""
                ).strip(),
                "created_at": created_at,
                "source": "master",
            }

    metrics_path = base_dir / "metrics.jsonl"

    if metrics_path.exists():
        with metrics_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("event") != "project_purged":
                    continue

                pid = event.get("project_id")

                if not pid:
                    continue

                if pid in added_by_id:
                    continue

                created_at = _parse_timestamp(
                    event.get("created")
                )

                if created_at is None:
                    continue

                if not (start <= created_at < end):
                    continue

                added_by_id[pid] = {
                    "project_id": pid,
                    "project_title": (
                        event.get("project_title") or ""
                    ).strip(),
                    "created_at": created_at,
                    "source": "metrics",
                }

    return sorted(
        added_by_id.values(),
        key=lambda item: item["created_at"],
    )

def get_projects_added(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """
    Return projects whose most recent activation falls within:

        start <= activated_at < end

    Sources:
      1. projects still present in master.json
      2. project_purged events

    Deduplicated by project_id.
    """

    added_by_id: dict[str, dict] = {}

    projects = master.get("projects", {})

    if isinstance(projects, dict):
        for pid, project in projects.items():
            if not isinstance(project, dict):
                continue

            activated_at = _parse_timestamp(
                project.get("activated_at")
            )

            if activated_at is None:
                continue

            if not (start <= activated_at < end):
                continue

            added_by_id[pid] = {
                "project_id": pid,
                "project_title": (
                    project.get("title") or ""
                ).strip(),
                "activated_at": activated_at,
                "source": "master",
            }

    metrics_path = base_dir / "metrics.jsonl"

    if metrics_path.exists():
        with metrics_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("event") != "project_purged":
                    continue

                pid = event.get("project_id")

                if not pid:
                    continue

                if pid in added_by_id:
                    continue

                activated_at = _parse_timestamp(
                    event.get("activated_at")
                )

                if activated_at is None:
                    continue

                if not (start <= activated_at < end):
                    continue

                added_by_id[pid] = {
                    "project_id": pid,
                    "project_title": (
                        event.get("project_title") or ""
                    ).strip(),
                    "activated_at": activated_at,
                    "source": "metrics",
                }

    return sorted(
        added_by_id.values(),
        key=lambda item: item["activated_at"],
    )

def summarize_project_metrics(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> dict:
    snapshot = get_week_snapshot(
        base_dir,
        start,
    )

    cleared = get_cleared_projects(
        base_dir,
        master,
        start,
        end,
    )

    added = get_projects_added(
        base_dir,
        master,
        start,
        end,
    )

    sizes = summarize_cleared_project_sizes(
        cleared
    )

    start_projects = None

    if snapshot is not None:
        value = snapshot.get("active_projects")
        if value is not None:
            start_projects = int(value)

    cleared_count = len(cleared)
    added_count = len(added)

    cleared_pct = None

    if start_projects:
        cleared_pct = (
            cleared_count
            / start_projects
            * 100.0
        )

    return {
        "start_projects": start_projects,
        "projects_cleared": cleared_count,
        "percent_cleared": cleared_pct,
        "projects_added": added_count,
        "small_cleared": sizes["small"],
        "medium_cleared": sizes["medium"],
        "large_cleared": sizes["large"],
    }

def summarize_action_metrics(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> dict:
    snapshot = get_week_snapshot(
        base_dir,
        start,
    )

    added = get_actions_added(
        base_dir,
        master,
        start,
        end,
    )

    cleared = get_actions_cleared(
        base_dir,
        master,
        start,
        end,
    )

    start_actions = None

    if snapshot is not None:
        value = snapshot.get("outstanding_actions")

        if value is not None:
            start_actions = int(value)

    cleared_count = len(cleared)
    added_count = len(added)

    cleared_pct = None

    if start_actions:
        cleared_pct = (
            cleared_count
            / start_actions
            * 100.0
        )

    return {
        "start_actions": start_actions,
        "actions_cleared": cleared_count,
        "percent_cleared": cleared_pct,
        "actions_added": added_count,
    }

def iter_week_starts(
    current_week_start: datetime,
    n_weeks: int = 6,
) -> list[datetime]:
    return [
        current_week_start - timedelta(weeks=offset)
        for offset in reversed(range(n_weeks))
    ]

def render_project_metrics_markdown(
    base_dir: Path,
    master: dict,
    current_week_start: datetime,
    n_weeks: int = 6,
) -> str:
    lines: list[str] = []

    week_starts = iter_week_starts(
        current_week_start,
        n_weeks=n_weeks,
    )

    lines.append("# Metrics")
    lines.append("")
    lines.append("## Projects")
    lines.append("")
    lines.append(
        "| Week | Start Projects | Projects Cleared | % Cleared | Projects Added |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|"
    )

    summaries: list[tuple[datetime, dict]] = []

    for start in week_starts:
        end = start + timedelta(days=7)

        summary = summarize_project_metrics(
            base_dir,
            master,
            start,
            end,
        )

        summaries.append(
            (start, summary)
        )

        start_projects = summary["start_projects"]

        start_text = (
            str(start_projects)
            if start_projects is not None
            else "—"
        )

        pct = summary["percent_cleared"]

        pct_text = (
            f"{pct:.1f}%"
            if pct is not None
            else "—"
        )

        lines.append(
            "| "
            f"{start.date().isoformat()} | "
            f"{start_text} | "
            f"{summary['projects_cleared']} | "
            f"{pct_text} | "
            f"{summary['projects_added']} |"
        )

    lines.append("")
    lines.append("## Projects Cleared by Size")
    lines.append("")
    lines.append(
        "| Week | 1–5 Actions | 6–15 Actions | 16+ Actions |"
    )
    lines.append(
        "|---|---:|---:|---:|"
    )

    for start, summary in summaries:
        lines.append(
            "| "
            f"{start.date().isoformat()} | "
            f"{summary['small_cleared']} | "
            f"{summary['medium_cleared']} | "
            f"{summary['large_cleared']} |"
        )

    lines.append("")

    lines.append("")
    lines.append("## Action Backlog")
    lines.append("")
    lines.append(
        "| Week | Start Actions | Actions Cleared | % Cleared | Actions Added |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|"
    )

    for start in week_starts:
        end = start + timedelta(weeks=1)

        summary = summarize_action_metrics(
            base_dir,
            master,
            start,
            end,
        )

        start_actions = (
            str(summary["start_actions"])
            if summary["start_actions"] is not None
            else "—"
        )

        percent_cleared = (
            f'{summary["percent_cleared"]:.1f}%'
            if summary["percent_cleared"] is not None
            else "—"
        )

        lines.append(
            "| "
            f"{start.date().isoformat()} | "
            f"{start_actions} | "
            f'{summary["actions_cleared"]} | '
            f"{percent_cleared} | "
            f'{summary["actions_added"]} |'
        )


    lines.append("")
    lines.append("## Psychological Weight")
    lines.append("")
    lines.append(
        "| Week | Start Weight | Weight Cleared | % Weight Cleared | Weight Added |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|"
    )

    for start in week_starts:
        end = start + timedelta(weeks=1)

        summary = summarize_weight_metrics(
            base_dir,
            master,
            start,
            end,
        )

        start_weight = (
            f'{summary["start_weight"]:.1f}'
            if summary["start_weight"] is not None
            else "—"
        )

        weight_cleared = (
            f'{summary["weight_cleared"]:.1f}'
        )

        percent_cleared = (
            f'{summary["percent_cleared"]:.1f}%'
            if summary["percent_cleared"] is not None
            else "—"
        )

        weight_added = (
            f'{summary["weight_added"]:.1f}'
            if summary["weight_added"] is not None
            else "—"
        )

        lines.append(
            "| "
            f"{start.date().isoformat()} | "
            f"{start_weight} | "
            f"{weight_cleared} | "
            f"{percent_cleared} | "
            f"{weight_added} |"
        )

    return "\n".join(lines)

def _collect_historical_actions(
    base_dir: Path,
    master: dict,
) -> dict[str, dict]:
    """
    Collect actions from all retained historical sources.

    Source priority:
      1. master.json
      2. archive_bundle.jsonl
      3. project_purged events in metrics.jsonl

    Each result contains:
      action_id
      action
      project
      source
    """

    records: dict[str, dict] = {}

    projects = master.get("projects", {})
    actions = master.get("actions", {})

    if not isinstance(projects, dict):
        projects = {}

    if isinstance(actions, dict):
        for aid, action in actions.items():
            if not isinstance(action, dict):
                continue

            pid = action.get("project")
            project = projects.get(pid) if pid else None

            records[aid] = {
                "action_id": aid,
                "action": action,
                "project": project,
                "source": "master",
            }

    # ------------------------------------------------------------
    # Completed projects removed from master by archive-finalize
    # ------------------------------------------------------------

    archive_path = base_dir / "archive_bundle.jsonl"

    if archive_path.exists():
        with archive_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                project = record.get("project")
                archived_actions = record.get("actions")

                if not isinstance(archived_actions, dict):
                    continue

                for aid, action in archived_actions.items():
                    if aid in records:
                        continue

                    if not isinstance(action, dict):
                        continue

                    records[aid] = {
                        "action_id": aid,
                        "action": action,
                        "project": project if isinstance(project, dict) else None,
                        "source": "archive",
                    }

    # ------------------------------------------------------------
    # Soft-deleted projects eventually purged from trash
    # ------------------------------------------------------------

    metrics_path = base_dir / "metrics.jsonl"

    if metrics_path.exists():
        with metrics_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("event") != "project_purged":
                    continue

                purged_actions = event.get("actions")

                if not isinstance(purged_actions, dict):
                    continue

                project = {
                    "completed": event.get("completed"),
                    "trashed_at": event.get("trashed_at"),
                }

                for aid, action in purged_actions.items():
                    if aid in records:
                        continue

                    if not isinstance(action, dict):
                        continue

                    records[aid] = {
                        "action_id": aid,
                        "action": action,
                        "project": project,
                        "source": "metrics",
                    }

    return records

def get_actions_added(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """
    Return actions activated into the workload during:

        start <= activated_at < end

    For older retained records that pre-date activated_at, created is used
    as a best-effort fallback only for actions whose retained state shows
    they were active/waiting/completed rather than Someday.
    """

    records = _collect_historical_actions(
        base_dir,
        master,
    )

    added: list[dict] = []

    for aid, record in records.items():
        action = record["action"]

        activated_raw = action.get("activated_at")

        if not activated_raw:
            state = str(
                action.get("state") or ""
            ).strip().lower()

            if state in {"active", "waiting", "completed"}:
                activated_raw = action.get("created")

        activated_at = _parse_timestamp(activated_raw)

        if activated_at is None:
            continue

        if not (start <= activated_at < end):
            continue

        added.append(
            {
                "action_id": aid,
                "title": (action.get("title") or "").strip(),
                "activated_at": activated_at,
                "source": record["source"],
            }
        )

    added.sort(
        key=lambda row: row["activated_at"]
    )

    return added

def get_actions_cleared(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """
    Return actions genuinely cleared during:

        start <= cleared_at < end

    Clearance can occur by:

      1. action completion
      2. completion of its parent project
      3. soft deletion of its parent project

    Moving an action to Someday is intentionally not treated as clearance.

    Hard-deleted projects/actions are intentionally absent from history.
    """

    records = _collect_historical_actions(
        base_dir,
        master,
    )

    cleared: list[dict] = []

    for aid, record in records.items():
        action = record["action"]
        project = record.get("project")

        candidates: list[tuple[datetime, str]] = []

        completed_at = _parse_timestamp(
            action.get("completed")
        )

        if completed_at is not None:
            candidates.append(
                (completed_at, "completed")
            )

        # Only actions that actually belonged to the active workload
        # should be cleared merely because their parent project closed.
        state = str(
            action.get("state") or ""
        ).strip().lower()

        activated_raw = action.get("activated_at")

        if not activated_raw and state in {
            "active",
            "waiting",
            "completed",
        }:
            activated_raw = action.get("created")

        activated_at = _parse_timestamp(
            activated_raw
        )

        if (
            activated_at is not None
            and isinstance(project, dict)
            and state != "someday"
        ):
            project_completed = _parse_timestamp(
                project.get("completed")
            )

            project_trashed = _parse_timestamp(
                project.get("trashed_at")
            )

            if project_completed is not None:
                candidates.append(
                    (
                        project_completed,
                        "project_completed",
                    )
                )

            if project_trashed is not None:
                candidates.append(
                    (
                        project_trashed,
                        "project_deleted",
                    )
                )

        if not candidates:
            continue

        # If an action was completed before its project was closed,
        # its own completion is the real clearance event.
        cleared_at, clearance_type = min(
            candidates,
            key=lambda item: item[0],
        )

        if not (start <= cleared_at < end):
            continue

        cleared.append(
            {
                "action_id": aid,
                "title": (action.get("title") or "").strip(),
                "cleared_at": cleared_at,
                "clearance_type": clearance_type,
                "source": record["source"],
            }
        )

    cleared.sort(
        key=lambda row: row["cleared_at"]
    )

    return cleared

def get_weight_cleared(
    base_dir: Path,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """
    Return psychological-weight clearance events in:

        start <= at < end
    """

    path = base_dir / "metrics.jsonl"

    if not path.exists():
        return []

    events: list[dict] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("event") != "weight_cleared":
                continue

            at = _parse_timestamp(event.get("at"))

            if at is None:
                continue

            if not (start <= at < end):
                continue

            try:
                weight = float(event.get("weight", 0.0))
            except (TypeError, ValueError):
                continue

            events.append(
                {
                    **event,
                    "at": at,
                    "weight": weight,
                }
            )

    events.sort(key=lambda event: event["at"])

    return events

def summarize_weight_metrics(
    base_dir: Path,
    master: dict,
    start: datetime,
    end: datetime,
) -> dict:
    """
    Summarize psychological-weight movement for one week.

    Accounting identity:

        Weight Added
        = End Weight + Weight Cleared - Start Weight

    For the current week, End Weight is the live current weight.

    For a completed historical week, the following week's snapshot
    supplies the ending weight.
    """

    snapshot = get_week_snapshot(
        base_dir,
        start,
    )

    start_weight = None

    if snapshot is not None:
        value = snapshot.get("outstanding_weight")

        if value is not None:
            start_weight = float(value)

    cleared_events = get_weight_cleared(
        base_dir,
        start,
        end,
    )

    weight_cleared = sum(
        event["weight"]
        for event in cleared_events
    )

    current_week_start = week_start_for(
        datetime.now(timezone.utc)
    )

    end_weight = None

    if start == current_week_start:
        end_weight = total_outstanding_weight(
            base_dir,
            master,
        )

    else:
        next_snapshot = get_week_snapshot(
            base_dir,
            end,
        )

        if next_snapshot is not None:
            value = next_snapshot.get(
                "outstanding_weight"
            )

            if value is not None:
                end_weight = float(value)

    weight_added = None
    percent_cleared = None

    if (
        start_weight is not None
        and end_weight is not None
    ):
        weight_added = (
            end_weight
            + weight_cleared
            - start_weight
        )

    if start_weight is not None and start_weight > 0:
        percent_cleared = (
            weight_cleared
            / start_weight
            * 100.0
        )

    return {
        "start_weight": start_weight,
        "weight_cleared": weight_cleared,
        "percent_cleared": percent_cleared,
        "weight_added": weight_added,
        "end_weight": end_weight,
    }

