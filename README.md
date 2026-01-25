# gtd-md-sync


A small, local-first **Getting Things Done (GTD)** command-line tool that keeps a single source of truth in JSON and generates human-friendly Markdown views for daily use — with reliable round-trip sync back into the data.

This tool is designed for people who want:

- a **transparent data model**
- **plain text Markdown** for day-to-day work (including mobile)
- no vendor lock-in
- explicit, predictable workflows

---

## Core idea

- **Truth lives in `master.json`**
- **Markdown files are views, not data**
- You work from Markdown
- The tool syncs completed items back into JSON

```text
add → master.json → build → views/*.md
                              ↑
                             sync
```

---

## Features (v1)

- Projects, actions, and Someday/Maybe items
- Stable IDs embedded in Markdown (safe sync)
- Context-based Next Actions lists
- Project labels shown next to actions
- Explicit build and sync steps (no background magic)
- Configurable, enforced context list
- Fully local, Python standard library only

---

## Installation

Clone the repository and create a virtual environment:

```bash
git clone <repo-url>
cd gtd-md-sync
python3 -m venv .venv
source .venv/bin/activate
```

No external Python dependencies are required.

---

## Usage

### 1. Initialise a GTD workspace

Choose where your GTD data should live (outside the repo):

```bash
python3 gtd.py init --dir ~/GTD
```

This creates:

- `master.json` — the database
- `views/` — generated Markdown views
- `config.json` — contexts and future settings

---

### 2. Manage contexts

List available contexts:

```bash
python3 gtd.py context --dir ~/GTD list
```

Add a new context:

```bash
python3 gtd.py context --dir ~/GTD add deep_work
```

Drop a context:

```bash
python3 gtd.py context --dir ~/GTD drop agenda
```

Contexts are enforced when adding actions.

---

### 3. Add items

```bash
python3 gtd.py add --dir ~/GTD
```

You can add:

- standalone actions
- projects (with an initial next action)
- Someday / Maybe items

---

### 4. Build Markdown views

```bash
python3 gtd.py build --dir ~/GTD
```

This generates:

- `views/next_actions.md`
- `views/projects.md`
- `views/someday.md`

These files are intended to be:

- read daily
- reordered freely
- ticked off
- synced via cloud storage if desired

---

### 5. Complete actions and sync back

In the Markdown files:

- tick a checkbox `[x]`, or
- append `XXX` to a line

Then run:

```bash
python3 gtd.py sync --dir ~/GTD
python3 gtd.py build --dir ~/GTD
```

Completed items are removed from active views.

---

## Design principles

- **One source of truth**: JSON, not Markdown
- **Views are disposable**
- **Explicit commands over automation**
- **Schema evolves additively**
- **Failure-safe over clever**

This is a tool you should be able to understand completely by reading the files it creates.

---

## Status

This is an early but fully functional prototype used for real GTD workflows.

Planned improvements:

- activate / drop commands
- schema versioning and migrations
- weekly review helpers
- additional views (waiting, overdue, etc.)

---

## License

Apache License 2.0