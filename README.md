# gtd-md-sync

A small, local-first **Getting Things Done (GTD)** command-line tool that keeps a single source of truth in JSON and generates human-friendly Markdown views for daily use — with reliable round-trip sync back into the data.

This tool is designed for people who want:

- a **transparent data model**
- **plain text Markdown** for day-to-day work (including mobile)
- no vendor lock-in
- explicit, predictable workflows
- full ownership of their GTD system

---

## Core idea

- **Truth lives in `master.json`**
- **Markdown files are views, not data**
- You work from Markdown
- The tool syncs completed items back into JSON
- Views are regenerated safely at any time

```text
add / edit → master.json → build → views/*.md
                                    ↑
                                   sync
```

---

## Features (current version)

### Core GTD functionality

- Projects with explicit outcomes
- Multiple parallel Next Actions per project
- Standalone actions (not tied to a project)
- Someday / Maybe items
- Waiting For items with explicit tracking
- Agenda lists for meetings and people
- Automatic detection of stalled projects

### Markdown views generated

- `views/next_actions.md` — active actions grouped by context
- `views/projects.md` — all projects overview
- `views/someday.md` — someday / maybe items
- `views/waiting_for.md` — items waiting on external input
- `views/agenda.md` — meeting/person-specific agenda items
- `views/stalled_projects.md` — active projects with no next action

### Workflow automation

- Stable IDs embedded in Markdown (safe round-trip sync)
- Tick checkboxes in Markdown and sync back to JSON
- Automatic prompt to add next actions when projects stall
- Enforced context list to prevent fragmentation
- Explicit project editing and action creation tools

### Design and reliability

- Fully local, Python standard library only
- No background processes
- Explicit commands — nothing happens silently
- Data stored in simple, readable JSON
- Safe to sync Markdown via cloud storage (Proton, Google Drive, Dropbox, etc.)

---

## Installation

Clone the repository and create a virtual environment:

```bash
git clone <repo-url>
cd gtd-md-sync
python3 -m venv .venv
source .venv/bin/activate
```

No external dependencies required.

---

## Usage

### 1. Initialise a GTD workspace

Choose where your GTD data should live (recommended: outside the repo):

```bash
python3 gtd.py init --dir ~/GTD
```

Creates:

- `master.json` — database
- `config.json` — context configuration
- `views/` — Markdown output folder

---

### 2. Manage contexts

Contexts define where actions can be performed.

List contexts:

```bash
python3 gtd.py context --dir ~/GTD list
```

Add context:

```bash
python3 gtd.py context --dir ~/GTD add home
python3 gtd.py context --dir ~/GTD add work
python3 gtd.py context --dir ~/GTD add agenda_team
```

Drop context:

```bash
python3 gtd.py context --dir ~/GTD drop errands
```

Contexts are enforced when adding actions.

---

### 3. Add items

```bash
python3 gtd.py add --dir ~/GTD
```

You can create:

- standalone actions
- project-linked actions
- new projects with initial next action
- waiting-for items
- someday items
- agenda items (using agenda_* contexts)

---

### 4. Edit projects and add actions

List projects:

```bash
python3 gtd.py project list --dir ~/GTD
```

Edit project and optionally add actions:

```bash
python3 gtd.py project edit --dir ~/GTD
```

You can change:

- title
- state (active / someday / completed / dropped)
- due date
- notes
- add one or more next actions

---

### 5. Build Markdown views

```bash
python3 gtd.py build --dir ~/GTD
```

Generates all Markdown views:

```
views/
  next_actions.md
  projects.md
  someday.md
  waiting_for.md
  agenda.md
  stalled_projects.md
```

These files are safe to:

- read daily
- reorder
- sync via cloud storage
- check off tasks

---

### 6. Complete actions and sync back

In any Markdown view:

- tick checkbox `[x]`, or
- append `XXX` to a line

Then sync:

```bash
python3 gtd.py sync --dir ~/GTD
python3 gtd.py build --dir ~/GTD
```

Sync will:

- mark items completed in JSON
- detect stalled projects
- optionally prompt for next actions

---

## Recommended daily workflow

Typical loop:

```bash
python3 gtd.py build --dir ~/GTD
```

Work from:

- next_actions.md
- agenda.md
- waiting_for.md

After completing items:

```bash
python3 gtd.py sync --dir ~/GTD
python3 gtd.py build --dir ~/GTD
```

---

## File structure overview

Workspace example:

```
~/GTD/
  master.json
  config.json
  views/
    next_actions.md
    projects.md
    someday.md
    waiting_for.md
    agenda.md
    stalled_projects.md
```

Repository example:

```
gtd-md-sync/
  gtd.py
  gtdlib/
  README.md
```

---

## Design principles

This tool follows strict design constraints:

- **Single source of truth**: master.json
- **Markdown is a view layer**
- **No hidden automation**
- **Fully inspectable and understandable**
- **Local-first and tool-agnostic**
- **Safe schema evolution**

The system is designed to remain usable and understandable indefinitely.

---

## Status

This is a functional, production-usable GTD system.

Currently implemented:

- full GTD capture and clarify workflow
- projects and next actions
- waiting-for tracking
- agenda lists
- stalled project detection
- project editing
- safe Markdown sync

Planned improvements:

- improved project search and filtering
- richer project editing display
- review assistant commands
- schema versioning and migrations
- optional cloud sync helpers

---

## License

Apache License 2.0
