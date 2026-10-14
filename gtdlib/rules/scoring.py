from __future__ import annotations

import math
from datetime import date


def parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None

    try:
        return date.fromisoformat(str(s).strip())
    except Exception:
        return None


def days_until(target: date | None, today: date) -> int | None:
    if target is None:
        return None

    return (target - today).days


def action_age_days(action: dict, today: date) -> int:
    created = parse_iso_date((action.get("created") or "")[:10])
    last_touched = parse_iso_date((action.get("last_touched") or "")[:10])

    basis = created or last_touched

    if basis is None:
        return 0

    age = (today - basis).days
    return max(age, 0)


def due_bucket(action: dict, today: date) -> tuple[int, int]:
    """
    Return a sorting bucket for focus rendering.

    Lower bucket number = higher urgency.

    0 = overdue
    1 = due today
    2 = everything else
    """
    due_dt = parse_iso_date(action.get("due"))
    d = days_until(due_dt, today)

    if d is None:
        return (2, 999999)

    if d < 0:
        return (0, d)

    if d == 0:
        return (1, d)

    return (2, d)


def score_next_action(
    action: dict,
    project: dict | None,
    today: date,
    weights: dict,
) -> float:
    """
    Calculate the psychological / execution weight of a next action.

    This is shared by Focus and the metrics system so the scoring
    formula has one source of truth.
    """
    action_due = parse_iso_date(action.get("due"))
    project_due = parse_iso_date(project.get("due")) if project else None

    d_a = days_until(action_due, today)
    d_p = days_until(project_due, today)
    age_days = action_age_days(action, today)

    score = 0.0

    # Action due urgency
    if d_a is not None:
        if d_a >= 0:
            score += weights["action_due"] / (d_a + 1.0)
        else:
            score += (
                weights["action_due"]
                + weights["action_overdue_slope"] * abs(d_a)
            )

    # Project due urgency
    if d_p is not None:
        if d_p >= 0:
            score += weights["project_due"] / (d_p + 1.0)
        else:
            score += (
                weights["project_due"]
                + weights["project_overdue_slope"] * abs(d_p)
            )

    # Age / stagnation pressure
    score += weights["age"] * math.log(age_days + 1.0)

    # Action/project tension
    if (
        d_a is not None
        and d_p is not None
        and d_p > 0
        and d_p > d_a
    ):
        score += (
            weights["tension"]
            * ((d_p - d_a) / (d_p + 1.0))
        )

    # Explicit overdue bonus
    if d_a is not None and d_a < 0:
        score += weights["overdue_bonus"]

    return score