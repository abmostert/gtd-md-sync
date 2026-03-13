from __future__ import annotations

from pathlib import Path

from gtdlib.store import (
    load_master,
    save_master,
    utc_now_iso,
    VIEWS_DIRNAME,
    new_id,
)
from gtdlib.config import get_contexts
from gtdlib.prompts.action_prompts import (
    prompt_action_draft,
    render_action_preview,
)
from gtdlib.rules.projects import is_project_stalled
from gtdlib.parsing.markdown import (
    extract_completions_from_markdown,
    prune_checked_top_level_tasks,
)
from gtdlib.parsing.project_notes import parse_project_notes
from gtdlib.prompts.stalled_project_prompts import prompt_next_action_for_stalled_project
from gtdlib.rules.contexts import normalize_context



def _merge_completions(dst: dict[str, bool], src: dict[str, bool]) -> None:
    """
    Merge completion maps from multiple files.

    Rule: True wins. Never overwrite an existing True with False.
    """
    for k, v in src.items():
        if v:
            dst[k] = True
        else:
            dst.setdefault(k, False)

def _draft_action_already_exists(
    actions: dict,
    *,
    project_id: str,
    state: str,
    title: str,
    context,
    due,
    waiting_for,
) -> bool:
    """
    Return True if an equivalent action already exists.

    This makes repeated sync runs idempotent for draft actions that have not yet
    been rewritten into @project_notes.md with real action IDs by build.
    """
    norm_title = (title or "").strip()
    norm_context = context or None
    norm_due = due or None
    norm_waiting_for = waiting_for or None

    for a in actions.values():
        if (a.get("project") or "") != project_id:
            continue
        if (a.get("state") or "") != state:
            continue
        if (a.get("title") or "").strip() != norm_title:
            continue
        if (a.get("context") or None) != norm_context:
            continue
        if (a.get("due") or None) != norm_due:
            continue
        if (a.get("waiting_for") or None) != norm_waiting_for:
            continue
        return True

    return False

def _apply_existing_action_edit(actions: dict, action_edit) -> bool:
    """
    Apply a section-based edit for an existing action parsed from @project_notes.md.

    Returns True if an action was found and updated, else False.
    """
    aid = getattr(action_edit, "action_id", None)
    if not aid or aid not in actions:
        return False

    action = actions[aid]
    # Never resurrect completed actions from project notes.
    # Completion from generated views should win over stale placement in @project_notes.md.
    if (action.get("state") or "").strip().lower() == "completed":
        return False
    
    section = (getattr(action_edit, "section", "") or "").strip().lower()
    title = (getattr(action_edit, "title", "") or "").strip()
    due = (getattr(action_edit, "due", "") or "").strip() or None
    notes = getattr(action_edit, "notes", None)
    context_raw = (getattr(action_edit, "context", "") or "").strip()
    waiting_for_raw = (getattr(action_edit, "waiting_for", "") or "").strip()

    if title:
        action["title"] = title

    action["due"] = due
    if notes is not None:
        action["notes"] = str(notes)

    if section == "active":
        action["state"] = "active"
        action["waiting_for"] = None
        action["context"] = normalize_context(context_raw) if context_raw else "inbox"
        action["waiting_since"] = None

    elif section == "agenda":
        action["state"] = "active"
        action["waiting_for"] = None
        who = normalize_context(context_raw) if context_raw else "unspecified"
        action["context"] = f"agenda_{who}"
        action["waiting_since"] = None

    elif section == "someday":
        action["state"] = "someday"
        action["waiting_for"] = None
        action["context"] = normalize_context(context_raw) if context_raw else "inbox"
        action["waiting_since"] = None

    elif section == "waiting":
        action["state"] = "waiting"
        action["context"] = None
        action["waiting_for"] = waiting_for_raw or "unspecified"
        if not action.get("waiting_since"):
            action["waiting_since"] = utc_now_iso()

    else:
        return False

    action["last_touched"] = utc_now_iso()
    return True


def cmd_sync(base_dir: Path, *, prompt_next: bool = True) -> int:
    """
    Read checkbox completions from Markdown views and update master.json.
    """
    views_dir = base_dir / VIEWS_DIRNAME
    if not views_dir.exists():
        raise FileNotFoundError(f"{VIEWS_DIRNAME}/ not found in {base_dir}. Run `init` first.")

    master = load_master(base_dir)
    actions: dict = master.get("actions", {})
    projects: dict = master.get("projects", {})

    # Read relevant view files
    view_files = [
        views_dir / "next_actions.md",
        views_dir / "projects.md",
        views_dir / "someday.md",
        views_dir / "waiting_for.md",
        views_dir / "agenda.md",
    ]

    completion_map: dict[str, bool] = {}
    for fp in view_files:
        if fp.exists():
            _merge_completions(completion_map, extract_completions_from_markdown(fp.read_text(encoding="utf-8")))

    now = utc_now_iso()
    completed_actions = 0
    completed_projects = 0

    # Scan project notes for checkbox completions as well.
    projects_dir = base_dir / "projects"
    if projects_dir.exists():
        for folder in projects_dir.iterdir():
            if not folder.is_dir():
                continue
            pn = folder / "@project_notes.md"
            if pn.exists():
                _merge_completions(
                    completion_map,
                    extract_completions_from_markdown(pn.read_text(encoding="utf-8")),
                )
  

    # Apply completions
    for item_id, done in completion_map.items():
        if not done:
            continue

        if item_id.startswith("a_") and item_id in actions:
            a = actions[item_id]
            if a.get("state") != "completed":
                a["state"] = "completed"
                a["completed"] = now
                a["last_touched"] = now
                a["waiting_since"] = None
                a["waiting_for"] = None
                completed_actions += 1

        elif item_id.startswith("p_") and item_id in projects:
            p = projects[item_id]
            if p.get("state") != "completed":
                p["state"] = "completed"
                p["completed"] = now
                completed_projects += 1


    inbox_md = base_dir / "inbox" / "inbox.md"
    if inbox_md.exists():
        new_text, removed = prune_checked_top_level_tasks(inbox_md.read_text(encoding="utf-8"))
        if removed:
            inbox_md.write_text(new_text, encoding="utf-8")
            print(f"Pruned {removed} checked capture item(s) from inbox/inbox.md")


    master["actions"] = actions
    master["projects"] = projects

        # -------------------------
    # Import project notes edits (project_notes.md -> master.json)
    #   - updates project fields: outcome / notes / agenda_notes
    #   - imports NEW draft actions (checkbox lines without <!-- id:... -->)
    # -------------------------

    project_notes_root = base_dir / "projects"

    if project_notes_root.exists():
        updated_projects = 0
        created_actions = 0
        updated_existing_actions = 0

        for fp in project_notes_root.rglob("@project_notes.md"):
            try:
                txt = fp.read_text(encoding="utf-8")
            except Exception:
                continue

            edits = parse_project_notes(txt)
            if not edits:
                continue

            pid = edits.project_id
            if pid not in projects:
                continue

            now = utc_now_iso()

            # ---- project field edits ----
            p = projects[pid]
            changed = False

            if (p.get("outcome") or "") != edits.outcome:
                p["outcome"] = edits.outcome
                changed = True

            if (p.get("notes") or "") != edits.notes:
                p["notes"] = edits.notes
                changed = True

            if (p.get("agenda_notes") or "") != edits.agenda_notes:
                p["agenda_notes"] = edits.agenda_notes
                changed = True

            if changed:
                projects[pid] = p
                updated_projects += 1

            # ---- EXISTING actions moved between sections / edited in project notes ----
            updated_existing_actions = 0
            for ea in getattr(edits, "existing_actions", []) or []:
                if _apply_existing_action_edit(actions, ea):
                    updated_existing_actions += 1

            
            # ---- NEW draft actions (no id marker in the file) ----
            # parse_project_notes() should provide edits.draft_actions: list[DraftAction]
            for da in getattr(edits, "draft_actions", []) or []:
                section = (getattr(da, "section", "") or "").strip().lower()
                title = (getattr(da, "title", "") or "").strip()
                if not title:
                    continue

                if section == "active":
                    state = "active"
                    waiting_for = None
                    ctx_raw = (getattr(da, "context", "") or "").strip()
                    context = normalize_context(ctx_raw) if ctx_raw else "inbox"

                elif section == "agenda":
                    state = "active"
                    waiting_for = None
                    ctx_raw = (getattr(da, "context", "") or "").strip()
                    who = normalize_context(ctx_raw) if ctx_raw else "unspecified"
                    context = f"agenda_{who}"

                elif section == "someday":
                    state = "someday"
                    waiting_for = None
                    ctx_raw = (getattr(da, "context", "") or "").strip()
                    context = normalize_context(ctx_raw) if ctx_raw else "inbox"

                elif section == "waiting":
                    state = "waiting"
                    wf_raw = (getattr(da, "waiting_for", "") or "").strip()
                    waiting_for = wf_raw or "unspecified"

                    # waiting items do not need a context (and should not use reserved words)
                    context = None

                else:
                    continue

                due_raw = (getattr(da, "due", "") or "").strip()
                notes_raw = getattr(da, "notes", "") or ""
                due = due_raw or None

                if _draft_action_already_exists(
                    actions,
                    project_id=pid,
                    state=state,
                    title=title,
                    context=context,
                    due=due,
                    waiting_for=waiting_for,
                ):
                    continue

                aid = new_id("a")
                actions[aid] = {
                    "title": title,
                    "project": pid,
                    "state": state,
                    "context": context,
                    "waiting_for": waiting_for,
                    "created": now,
                    "last_touched": now,
                    "waiting_since": now if state == "waiting" else None,
                    "due": due,
                    "notes": str(notes_raw),
                }
                created_actions += 1

        if updated_projects:
            print(f"Imported edits from {updated_projects} project note file(s).")
        if updated_existing_actions:
            print(f"Updated {updated_existing_actions} existing action(s) from project notes.")
        if created_actions:
            print(f"Created {created_actions} action(s) from draft items in project notes.")

        # Prompt for next actions on stalled active projects
    if prompt_next:
        contexts = get_contexts(base_dir)

        for pid in projects.keys():
            if is_project_stalled(projects, actions, pid):
                proj = projects.get(pid, {})
                title = (proj.get("title") or pid).strip()

                prompt_next_action_for_stalled_project(
                    base_dir=base_dir,
                    project_id=pid,
                    project_title=title,
                    contexts=contexts,
                    actions=actions,
                )
    
    save_master(base_dir, master)

    print(f"Sync complete. Marked completed: {completed_actions} actions, {completed_projects} projects.")
    return 0
