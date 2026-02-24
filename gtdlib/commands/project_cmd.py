from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

from gtdlib.store import load_master, save_master, utc_now_iso, new_id
from gtdlib.prompts.selectors import choose_project_id
from gtdlib.prompts.project_prompts import prompt_project_edit
from gtdlib.prompts.action_prompts import prompt_action_draft, render_action_preview
from gtdlib.prompts.project_edit_prompts import choose_project_edit_operation
from gtdlib.config import get_contexts
from gtdlib.rules.projects import count_actions_by_state
from gtdlib.rules.project_folders import (
    find_project_folder,
    ensure_project_notes_exists,
    ensure_debrief_exists,
    PROJECTS_ROOT,
    REVIEW_ROOT,
    TRASH_ROOT,
    ARCHIVES_ROOT,
)
from gtdlib.rules.schema import PROJECT_LIFECYCLES  # if you named it differently, adjust
from gtdlib.commands.build_project_notes import ensure_project_notes_for_project

def cmd_project_list(base_dir: Path, *, state: str | None = None) -> int:
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    want_state = (state or "").strip().lower() if state else None

    rows: list[tuple[str, str, str]] = []
    for pid, p in projects.items():
        st = (p.get("state") or "unknown").strip().lower()
        if want_state and st != want_state:
            continue
        title = (p.get("title") or "").strip() or pid
        rows.append((pid, title, st))

    if not rows:
        print("No projects.")
        return 0

    rows.sort(key=lambda t: (t[2], t[1].lower()))

    print("\nProjects:")
    for pid, title, st in rows:
        counts = count_actions_by_state(actions, pid)
        active = counts.get("active", 0)
        waiting = counts.get("waiting", 0)
        someday = counts.get("someday", 0)
        due = projects.get(pid, {}).get("due")
        due_s = f", due {due}" if due else ""
        print(f"- {title} ({st}{due_s}) — actions: active={active}, waiting={waiting}, someday={someday} [{pid}]")

    return 0


def cmd_project_edit(base_dir: Path) -> int:
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    pid = choose_project_id(projects)
    if not pid:
        print("Cancelled.")
        return 0

    p = projects.get(pid)
    if not p:
        print("Project not found.")
        return 2

    op = choose_project_edit_operation(pid=pid, project=p, actions=actions)
    if op == "cancel":
        print("Cancelled.")
        return 0

    # ---- edit fields ----
    if op == "edit_fields":
        try:
            updated = prompt_project_edit(p)
        except ValueError as e:
            print(f"Error: {e}")
            return 2

        old_state = (p.get("state") or "").strip().lower()
        new_state = (updated.get("state") or "").strip().lower()

        now = utc_now_iso()
        if old_state != "completed" and new_state == "completed":
            updated["completed"] = now

        projects[pid] = updated
        master["projects"] = projects
        save_master(base_dir, master)
        print("Project updated.")
        return 0

    # ---- add action ----
    if op == "add_action":
        contexts = get_contexts(base_dir)
        now = utc_now_iso()

        try:
            draft = prompt_action_draft(
                base_dir,
                contexts,
                now_iso=now,
                project_id=pid,
                default_state="active",
                ask_context_when_waiting=False,
            )
        except ValueError as e:
            print(str(e))
            return 2

        render_action_preview(draft)
        confirm = input("Save this action? [Y/n]: ").strip().lower()
        if confirm in ("n", "no"):
            print("Cancelled. Not saved.")
            return 0

        aid = new_id("a")
        actions[aid] = draft
        master["actions"] = actions
        save_master(base_dir, master)
        print(f"Added action {aid} to project {pid}.")
        return 0

    print("Invalid choice.")
    return 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _confirm(prompt_text: str, *, default_yes: bool = False) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    ans = input(f"{prompt_text} {suffix}: ").strip().lower()
    if not ans:
        return default_yes
    return ans in ("y", "yes")


def _slug_folder_name(title: str) -> str:
    # keep it conservative; your system already generates these
    s = (title or "").strip().lower()
    out = []
    prev_us = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        else:
            if not prev_us:
                out.append("_")
                prev_us = True
    slug = "".join(out).strip("_")
    return slug or "project"


def _project_display(pid: str, p: dict) -> str:
    title = (p.get("title") or pid).strip()
    state = (p.get("state") or "unknown").strip().lower()
    lifecycle = (p.get("lifecycle") or "live").strip().lower()
    return f"{title} ({state}, lifecycle={lifecycle}) [{pid}]"


def cmd_project_complete(base_dir: Path) -> int:
    """
    Complete a project and move its folder to review/.
    Only folder-backed live projects are eligible:
      - state == active
      - lifecycle == live
      - folder exists under projects/
    """
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    # Build eligible list
    eligible: dict[str, dict] = {}
    for pid, p in projects.items():
        if (p.get("state") or "").strip().lower() != "active":
            continue
        if (p.get("lifecycle") or "live").strip().lower() != "live":
            continue
        match = find_project_folder(base_dir, pid)
        if not match or match.root_name != PROJECTS_ROOT:
            continue
        eligible[pid] = p

    if not eligible:
        print("No eligible active folder-backed projects to complete.")
        return 0

    pid = choose_project_id(eligible, allow_states=None)
    if not pid:
        print("Cancelled.")
        return 0

    p = projects.get(pid)
    if not p:
        print("Project not found.")
        return 2

    match = find_project_folder(base_dir, pid)
    if not match:
        print("Project folder not found; cannot complete.")
        return 2
    if match.root_name != PROJECTS_ROOT:
        print(f"Project folder is not in '{PROJECTS_ROOT}/' (found in '{match.root_name}/').")
        return 2

    title = (p.get("title") or pid).strip()
    print("\nWill move to review:")
    print(f"  {match.path}")
    if not _confirm(f"Mark completed + move '{title}' to review?", default_yes=False):
        print("Cancelled.")
        return 0

    # Move folder
    review_root = base_dir / REVIEW_ROOT
    review_root.mkdir(parents=True, exist_ok=True)

    dest = review_root / match.path.name
    if dest.exists():
        print(f"Error: destination already exists: {dest}")
        return 2

    match.path.rename(dest)

    # Ensure files
    ensure_project_notes_exists(dest, pid, title)
    ensure_debrief_exists(dest, pid, title)

    # Update master
    now = _now_iso()
    p["state"] = "completed"
    p["lifecycle"] = "review"
    p["completed"] = p.get("completed") or now
    projects[pid] = p

    # Create review action (standalone)
    aid = new_id("a")
    actions[aid] = {
        "title": f"Review project folder: {title} [{pid}]",
        "project": None,
        "state": "active",
        "context": "inbox",
        "waiting_for": None,
        "created": now,
        "last_touched": now,
        "waiting_since": None,
        "due": None,
        "notes": f"Folder moved to: {dest}",
    }

    master["projects"] = projects
    master["actions"] = actions
    save_master(base_dir, master)

    print(f"Moved to review: {dest}")
    print(f"Created review action: {aid}")
    return 0


def cmd_project_delete(base_dir: Path, *, hard: bool = False) -> int:
    """
    Soft delete: move project folder to trash/, set lifecycle=trash, trashed_at timestamp.
    Hard delete: permanently delete folder + remove project+actions immediately.
    Only folder-backed projects are eligible (projects/ or review/ or trash/).
    """
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    # eligible = any project that has a folder (excluding someday by implication)
    eligible: dict[str, dict] = {}
    for pid, p in projects.items():
        if (p.get("state") or "").strip().lower() == "someday":
            continue
        match = find_project_folder(base_dir, pid)
        if match and match.root_name in {PROJECTS_ROOT, REVIEW_ROOT, TRASH_ROOT}:
            eligible[pid] = p

    if not eligible:
        print("No eligible folder-backed projects found to delete.")
        return 0

    pid = choose_project_id(eligible, allow_states=None)
    if not pid:
        print("Cancelled.")
        return 0

    p = projects.get(pid)
    if not p:
        print("Project not found.")
        return 2

    match = find_project_folder(base_dir, pid)
    if not match:
        print("Project folder not found.")
        return 2

    title = (p.get("title") or pid).strip()

    if hard:
        print("\nHARD DELETE (permanent):")
        print(f"  Project: {_project_display(pid, p)}")
        print(f"  Folder:  {match.path}")
        confirm_pid = input(f"Type the project id to permanently delete ({pid}): ").strip()
        if confirm_pid != pid:
            print("Cancelled (id did not match).")
            return 0

        # delete folder tree
        import shutil
        shutil.rmtree(match.path)

        # remove from master
        projects.pop(pid, None)
        # remove associated actions
        to_del = [aid for aid, a in actions.items() if a.get("project") == pid]
        for aid in to_del:
            actions.pop(aid, None)

        master["projects"] = projects
        master["actions"] = actions
        save_master(base_dir, master)

        print(f"Permanently deleted project {pid} and {len(to_del)} associated action(s).")
        return 0

    # soft delete
    print("\nSOFT DELETE (move to trash):")
    print(f"  Project: {_project_display(pid, p)}")
    print(f"  Folder:  {match.path}")
    if not _confirm(f"Move '{title}' to trash (retained for 28 days)?", default_yes=False):
        print("Cancelled.")
        return 0

    trash_root = base_dir / TRASH_ROOT
    trash_root.mkdir(parents=True, exist_ok=True)

    dest = trash_root / match.path.name
    if dest.exists():
        print(f"Error: destination already exists: {dest}")
        return 2

    match.path.rename(dest)

    now = _now_iso()
    p["lifecycle"] = "trash"
    p["trashed_at"] = now
    projects[pid] = p

    master["projects"] = projects
    save_master(base_dir, master)

    print(f"Moved to trash: {dest}")
    return 0


def cmd_project_archive_finalize(base_dir: Path) -> int:
    """
    Finalize review:
      - eligible: lifecycle == review AND folder exists in review/
      - move folder to archives/
      - write archive record to archive_bundle.jsonl (append)
      - remove project + associated actions from master.json
    """
    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    eligible: dict[str, dict] = {}
    for pid, p in projects.items():
        if (p.get("lifecycle") or "live").strip().lower() != "review":
            continue
        match = find_project_folder(base_dir, pid)
        if match and match.root_name == REVIEW_ROOT:
            eligible[pid] = p

    if not eligible:
        print("No projects in review lifecycle to archive-finalize.")
        return 0

    pid = choose_project_id(projects, allow_lifecycles={"review"}, show_ids=True)
    if not pid:
        print("Cancelled.")
        return 0

    p = projects.get(pid)
    if not p:
        print("Project not found.")
        return 2

    match = find_project_folder(base_dir, pid)
    if not match or match.root_name != REVIEW_ROOT:
        print("Project folder not found in review/.")
        return 2

    ensure_project_notes_for_project(base_dir, pid, projects[pid], actions)
    
    written = ensure_project_notes_for_project(base_dir, pid, projects[pid], actions)
    print("Refreshed notes:", written)
    
    title = (p.get("title") or pid).strip()

    print("\nArchive-finalize will:")
    print(f"  - move folder: {match.path} -> {base_dir / ARCHIVES_ROOT / match.path.name}")
    print("  - remove project + associated actions from master.json")
    if not _confirm(f"Finalize archive for '{title}'?", default_yes=False):
        print("Cancelled.")
        return 0

    # read review artifacts (raw)
    project_notes = ""
    debrief = ""
    pn = match.path / "@project_notes.md"
    db = match.path / "@debrief.md"
    if pn.exists():
        project_notes = pn.read_text(encoding="utf-8", errors="replace")
    if db.exists():
        debrief = db.read_text(encoding="utf-8", errors="replace")

    # gather associated actions
    assoc_actions = {aid: a for aid, a in actions.items() if a.get("project") == pid}

    # append to archive bundle
    import json
    archive_path = base_dir / "archive_bundle.jsonl"
    record = {
        "archived_at": _now_iso(),
        "project_id": pid,
        "project": p,
        "actions": assoc_actions,
        "project_notes_md": project_notes,
        "debrief_md": debrief,
        "folder_name": match.path.name,
    }
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text("", encoding="utf-8") if not archive_path.exists() else None
    with archive_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # move folder
    archives_root = base_dir / ARCHIVES_ROOT
    archives_root.mkdir(parents=True, exist_ok=True)
    dest = archives_root / match.path.name
    if dest.exists():
        print(f"Error: destination already exists: {dest}")
        return 2
    match.path.rename(dest)

    # remove from master
    projects.pop(pid, None)
    for aid in list(assoc_actions.keys()):
        actions.pop(aid, None)

    master["projects"] = projects
    master["actions"] = actions
    save_master(base_dir, master)

    print(f"Archived to: {dest}")
    print(f"Archive record appended to: {archive_path}")
    return 0


def cmd_project_trash_purge(base_dir: Path, *, dry_run: bool = False, days: int = 28) -> int:
    """
    Purge trashed projects older than N days.
    Manual command (not part of sync).
    Records metrics in metrics.jsonl (append) for soft purges.
    """
    if days <= 0:
        print("days must be > 0")
        return 2

    master = load_master(base_dir)
    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    candidates: list[tuple[str, dict, Path]] = []
    for pid, p in projects.items():
        if (p.get("lifecycle") or "live").strip().lower() != "trash":
            continue
        trashed_at = (p.get("trashed_at") or "").strip()
        if not trashed_at:
            continue
        try:
            # parse ISO with Z
            ts = trashed_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
        except Exception:
            continue
        if dt > cutoff:
            continue

        match = find_project_folder(base_dir, pid)
        if not match or match.root_name != TRASH_ROOT:
            continue
        candidates.append((pid, p, match.path))

    if not candidates:
        print("No trashed projects eligible for purge.")
        return 0

    print(f"Trash purge candidates (older than {days} days):")
    for pid, p, path in candidates:
        print(f"- {_project_display(pid, p)}")
        print(f"  folder: {path}")

    if dry_run:
        print("Dry run: no changes made.")
        return 0

    if not _confirm("Proceed to permanently delete these projects?", default_yes=False):
        print("Cancelled.")
        return 0

    import json, shutil

    metrics_path = base_dir / "metrics.jsonl"
    with metrics_path.open("a", encoding="utf-8") as mf:
        for pid, p, path in candidates:
            # metrics event
            assoc = [a for a in actions.values() if a.get("project") == pid]
            event = {
                "event": "project_purged",
                "at": _now_iso(),
                "project_id": pid,
                "project_title": (p.get("title") or "").strip(),
                "completed": p.get("completed"),
                "trashed_at": p.get("trashed_at"),
                "n_actions": len(assoc),
            }
            mf.write(json.dumps(event, ensure_ascii=False) + "\n")

            # delete folder
            shutil.rmtree(path, ignore_errors=True)

            # remove from master
            projects.pop(pid, None)
            for aid in [aid for aid, a in actions.items() if a.get("project") == pid]:
                actions.pop(aid, None)

    master["projects"] = projects
    master["actions"] = actions
    save_master(base_dir, master)

    print(f"Purged {len(candidates)} project(s). Metrics appended to {metrics_path}.")
    return 0
