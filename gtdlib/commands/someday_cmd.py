from __future__ import annotations

from pathlib import Path

from gtdlib.store import load_master, save_master, ensure_config, save_config
from gtdlib.rules.project_folders import find_project_folder
from gtdlib.rules.visibility import (
    is_someday_project,
    is_visible_someday_action,
)


def cmd_someday_category_list(base_dir: Path) -> int:
    cfg = ensure_config(base_dir)

    categories = cfg.get("someday_categories", [])
    if not isinstance(categories, list):
        categories = []

    categories = sorted(
        {
            str(c).strip().lower()
            for c in categories
            if str(c).strip()
        }
    )

    if not categories:
        print("No Someday / Maybe categories configured.")
        return 0

    print("\nSomeday / Maybe categories:\n")

    for number, category in enumerate(categories, start=1):
        print(f"  {number}. {category}")

    return 0


def cmd_someday_category_create(base_dir: Path) -> int:
    cfg = ensure_config(base_dir)

    raw = input("New Someday / Maybe category: ").strip()

    if not raw:
        print("Cancelled.")
        return 0

    category = raw.lower().replace("-", "_").replace(" ", "_")

    while "__" in category:
        category = category.replace("__", "_")

    category = category.strip("_")

    if not category:
        print("Error: category name cannot be blank.")
        return 2

    if not all(ch.isalnum() or ch == "_" for ch in category):
        print("Error: category name must contain only letters, numbers, and underscores.")
        return 2

    categories = cfg.get("someday_categories", [])
    if not isinstance(categories, list):
        categories = []

    normalized = {
        str(c).strip().lower()
        for c in categories
        if str(c).strip()
    }

    if category in normalized:
        print(f"Category already exists: {category}")
        return 0

    normalized.add(category)

    cfg["someday_categories"] = sorted(normalized)
    save_config(base_dir, cfg)

    print(f"Added Someday / Maybe category: {category}")
    return 0


def cmd_someday_category_delete(base_dir: Path) -> int:
    cfg = ensure_config(base_dir)

    categories = cfg.get("someday_categories", [])
    if not isinstance(categories, list):
        categories = []

    categories = sorted(
        {
            str(c).strip().lower()
            for c in categories
            if str(c).strip()
        }
    )

    if not categories:
        print("No Someday / Maybe categories configured.")
        return 0

    print("\nSomeday / Maybe categories:\n")

    for number, category in enumerate(categories, start=1):
        print(f"  {number}. {category}")

    print("  0. Cancel")

    while True:
        raw = input("\nDelete which category? ").strip()

        if raw in {"", "0"}:
            print("Cancelled.")
            return 0

        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(categories):
                break

        print(f"Invalid choice. Enter 0-{len(categories)}.")

    category = categories[choice - 1]

    answer = input(
        f"Delete Someday / Maybe category '{category}'? [y/N]: "
    ).strip().lower()

    if answer not in {"y", "yes"}:
        print("Cancelled.")
        return 0

    remaining = [c for c in categories if c != category]

    cfg["someday_categories"] = remaining
    save_config(base_dir, cfg)

    print(f"Deleted Someday / Maybe category: {category}")
    return 0


def cmd_someday_delete(base_dir: Path) -> int:
    """
    Delete an item from Someday / Maybe.

    Eligible items:
      - live projects whose state is "someday"
      - visible actions whose state is "someday"

    Deleting a someday project also deletes all actions associated with it.
    """

    master = load_master(base_dir)

    projects: dict = master.get("projects", {})
    actions: dict = master.get("actions", {})

    items: list[tuple[str, str, str]] = []

    # Someday projects
    for pid, project in projects.items():
        if not is_someday_project(project):
            continue

        title = (project.get("title") or pid).strip()
        items.append(("project", pid, title))

    # Someday actions
    for aid, action in actions.items():
        if not is_visible_someday_action(action, projects):
            continue

        # If the parent project is itself Someday / Maybe, do not list
        # its actions separately. The project entry already represents
        # the entire deferred project and deleting it removes its actions.
        pid = action.get("project")

        if pid and pid in projects:
            if is_someday_project(projects[pid]):
                continue

        title = (action.get("title") or aid).strip()
        items.append(("action", aid, title))

    if not items:
        print("No Someday / Maybe items found.")
        return 0

    # Projects first, then actions; alphabetical within each group
    items.sort(
        key=lambda row: (
            0 if row[0] == "project" else 1,
            row[2].lower(),
        )
    )

    print("\nSomeday / Maybe:")
    print()

    for number, (kind, item_id, title) in enumerate(items, start=1):
        if kind == "project":
            print(f"  {number}. [PROJECT] {title} ({item_id})")
            continue

        action = actions[item_id]
        pid = action.get("project")

        if pid and pid in projects:
            project_title = (projects[pid].get("title") or pid).strip()
            location = f"project: {project_title}"
        else:
            location = "standalone"

        print(
            f"  {number}. [ACTION] {title} "
            f"[{location}] ({item_id})"
        )

    print("  0. Cancel")

    while True:
        raw = input("\nDelete which item? ").strip()

        if raw in {"", "0"}:
            print("Cancelled.")
            return 0

        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(items):
                break

        print(f"Invalid choice. Enter 0-{len(items)}.")

    kind, item_id, title = items[choice - 1]

    print()
    print(f"Selected: [{kind.upper()}] {title}")

    answer = input("Permanently delete this Someday / Maybe item? [y/N]: ").strip().lower()

    if answer not in {"y", "yes"}:
        print("Cancelled.")
        return 0

    # -------------------------
    # DELETE ACTION
    # -------------------------
    if kind == "action":
        actions.pop(item_id, None)

        master["actions"] = actions
        save_master(base_dir, master)

        print(f"Deleted someday action {item_id}: {title}")
        print("Run `gtd build` to refresh the Markdown views.")
        return 0

    # -------------------------
    # DELETE PROJECT
    # -------------------------

    # Someday projects normally do not have folders.
    # Refuse deletion if one unexpectedly exists so that no files
    # are accidentally orphaned.
    folder = find_project_folder(base_dir, item_id)

    if folder:
        print()
        print("Not deleted.")
        print("This Someday project unexpectedly has a project folder:")
        print(f"  {folder.path}")
        print("Its files have been left untouched.")
        return 2

    # Remove every action associated with the project, regardless of state.
    associated_actions = [
        aid
        for aid, action in actions.items()
        if action.get("project") == item_id
    ]

    for aid in associated_actions:
        actions.pop(aid, None)

    projects.pop(item_id, None)

    master["projects"] = projects
    master["actions"] = actions
    save_master(base_dir, master)

    print(f"Deleted someday project {item_id}: {title}")

    if associated_actions:
        print(
            f"Also deleted {len(associated_actions)} action(s) "
            "associated with the project."
        )

    print("Run `gtd build` to refresh the Markdown views.")
    return 0