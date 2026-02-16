# gtd-md-sync

A local-first Getting Things Done (GTD) command-line system that keeps a single source of truth in JSON and generates clean Markdown views for daily use — with reliable round-trip sync and email capture support.

Designed for people who want:

- full control over their data
- plain text workflows compatible with Linux, Windows, macOS, and mobile
- no vendor lock-in
- predictable, explicit behaviour
- structured GTD workflows with minimal friction

---

# Core idea

The architecture follows one simple rule:

- **Truth lives in `master.json`**
- **Markdown files are generated views**
- You work from Markdown
- The system syncs changes back into JSON

```
add / capture → master.json → build → views/*.md
                                  ↑
                                 sync
```
The system is explicit and deterministic. Nothing updates automatically.
---
# Architecture
The codebase is modular and layered:
```
gtdlib/
├── commands/     # CLI orchestration
├── prompts/      # user interaction logic
├── rules/        # business logic (pure)
├── parsing/      # markdown parsing
├── capture/      # email integration
├── store.py      # persistence layer
```
Design principles:

- Single source of truth (master.json)
- Markdown views are projections
- Strict separation of concerns
- Deterministic build/sync cycle
- Provider-agnostic capture system

---

# Workspace structure

Example workspace (stored in Dropbox or any sync folder):

```
~/Dropbox/GTD/
│
├── master.json
├── config.json
│
├── views/
│   ├── next_actions.md
│   ├── projects.md
│   ├── someday.md
│   ├── waiting_for.md
│   ├── stalled_projects.md
│   └── agenda.md
│
├── inbox/
│   ├── inbox.md
│   └── attachments/

```

Repository structure:

```
gtd-md-sync/
├── gtd.py
├── gtdlib/
│   ├── commands/
│   ├── prompts/
│   ├── rules/
│   ├── parsing/
│   └── capture/

```

---

# Features

## Core GTD

- Projects
- Next actions
- Someday / Maybe
- Waiting For
- Stalled project detection
- Explicit sync and build workflow

## Email capture (via IMAP / Proton Bridge / Gmail / etc)

- Capture emails directly into inbox.md
- Save attachments automatically
- Process inbox using GTD clarify workflow
- Checked items automatically removed
- Emails optionally deleted from capture folder

## System features

- Fully local
- Plain Markdown views
- Explicit, transparent data model
- Safe sync model using stable IDs
- Cross-platform (Linux, Windows, macOS)

---

# Installation

Clone the repository:

```bash
git clone <repo-url>
cd gtd-md-sync
```

Create environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No external Python dependencies required.

---

# CLI usage and global workspace directory

```--dir``` is a global argument that specifies your GTD workspace directory.
Use this pattern consistently:
```
python3 gtd.py --dir ~/Dropbox/GTD <command> [command-options]
```
Examples:
```
python3 gtd.py --dir ~/Dropbox/GTD init
python3 gtd.py --dir ~/Dropbox/GTD add
python3 gtd.py --dir ~/Dropbox/GTD build
python3 gtd.py --dir ~/Dropbox/GTD sync
python3 gtd.py --dir ~/Dropbox/GTD context list
python3 gtd.py --dir ~/Dropbox/GTD project list
python3 gtd.py --dir ~/Dropbox/GTD capture --limit 50
```

---

# Setup workspace

Choose workspace location (example uses Dropbox):

```bash
python3 gtd.py --dir ~/Dropbox/GTD init
```

This creates:

```
master.json
config.json
views/
inbox/
```

---

# Core workflow

Daily cycle:

```
capture → clarify → build → execute → sync → repeat
```
Suggested command loop:
```
python3 gtd.py --dir ~/Dropbox/GTD capture
python3 gtd.py --dir ~/Dropbox/GTD add
python3 gtd.py --dir ~/Dropbox/GTD build
# work from Markdown
python3 gtd.py --dir ~/Dropbox/GTD sync
python3 gtd.py --dir ~/Dropbox/GTD build
```

---

# Capture emails into inbox

Capture new emails:

```bash
python3 gtd.py --dir ~/Dropbox/GTD capture
```

This updates:

- ```inbox/inbox.md```
- ```inbox/attachments/```

Example ```inbox/attachements/```:

```
- [ ] Register bank details for Medicare
  attachments:
  - inbox/attachments/20260216_120102_Subject_file.pdf
```

Clarify manually in ```inbox/inbox.md```:

- convert items into next actions or projects (via ```add```)
- delete irrelevant items
- mark processed items with ```[x]```

Then sync to prune checked inbox items:

```bash
python3 gtd.py --dir ~/Dropbox/GTD sync
```

Processed items are removed from inbox.md.

---

# Adding actions and projects

Interactive add:

```bash
python3 gtd.py --dir ~/Dropbox/GTD add
```

Supports:

- standalone actions
- projects with next actions
- someday items
- waiting items

Supports multiple actions per project.

---

# Build Markdown views

Generate updated views from ```master.json```:

```bash
python3 gtd.py --dir ~/Dropbox/GTD build
```

Creates/updates:

```
views/next_actions.md
views/projects.md
views/someday.md
views/waiting_for.md
views/agenda.md
views/stalled_projects.md
```

---

# Completing actions

Mark complete in Markdown view by ticking the checkbox:

```
- [x] Do something important
```

Then sync:

```bash
python3 gtd.py --dir ~/Dropbox/GTD sync
```

System will:

- mark action completed/projects as completed in ```master.json```
- remove from next actions from relevant views on next ```build```
- optionally prompt for stalled projects
To disable stalled-project prompting:
```
python3 gtd.py --dir ~/Dropbox/GTD sync --no-prompt-next
```

---

# Waiting For workflow

When adding an action, choose state:

```
waiting
```

You will be prompted for a ```waiting_for``` value (person/thing). Waiting actions appear in:

```
views/waiting_for.md
```

To complete: tick the item in ```waiting_for.md``` and run ```sync```.

---

# Stalled project detection

A project is considered stalled if it is active and has no open actions (no active and no waiting).

Stalled projects appear in:

```
views/stalled_projects.md
```

During sync (unless disabled), the system prompts:

```
Project stalled: Publish paper
Add a next action now? [Y/n]
```
If you add a next action, it is written to ```master.json``` immediately and will appear in views after ```build```.

---

# Project operations

List projects:

```bash
python3 gtd.py --dir ~/Dropbox/GTD project list
```
Filter by state:
```
python3 gtd.py --dir ~/Dropbox/GTD project list --state active
python3 gtd.py --dir ~/Dropbox/GTD project list --state someday
python3 gtd.py --dir ~/Dropbox/GTD project list --state completed
python3 gtd.py --dir ~/Dropbox/GTD project list --state dropped
```

Edit a project:

```bash
python3 gtd.py --dir ~/Dropbox/GTD project edit
```

Supports:

- rename
- change state
- change due date
- add/edit notes
- add an additional action to the project

---

# Context Management

List:

```bash
python3 gtd.py --dir ~/Dropbox/GTD context list
```

Add a context:

```bash
python3 gtd.py --dir ~/Dropbox/GTD context add work
```

Drop a context:

```bash
python3 gtd.py --dir ~/Dropbox/GTD context drop errands
```

Contexts are enforced when adding active actions.
Waiting actions use ```state=waiting``` and appear in ```waiting_for.md```.

---

# Sync model

The system follows explicit, deterministic sync loop:

```
Markdown → sync → master.json → build → Markdown
```

Nothing happens automatically. This ensures safety and transparency.

---

# Email capture setup (Proton Bridge example)

Example config.json:

```json
{
  "contexts": ["inbox", "home", "work", "phone", "computer", "errands", "agenda"],
  "capture": {
    "imap": {
      "host": "127.0.0.1",
      "port": 1143,
      "username": "your@email.com",
      "password": "",
      "folder": "Stuff Capture",
      "starttls": true,
      "tls_verify": false
    }
  }
}
```
Notes:
- If ```password``` is empty, the system will prompt securely at runtime.
- Proton Bridge commonly uses ```127.0.0.1:1143``` with STARTTLS.

---

# Recommended storage

Use Dropbox, Google Drive, Syncthing or similar:

```
~/Dropbox/GTD/
```

This allows:

- mobile access (read/edit Markdown)
- cross-machine sync
- offline reliability

---

# Design principles

- JSON is the source of truth
- Markdown is the user interface
- Explicit over implicit
- Local-first
- Fully transparent
- Safe, recoverable workflows
- Clear separation of concerns:
  - ```commands/``` orchestration
  - ```prompts/``` user interaction
  - ```rules/``` business logic
  - ```parsing/``` markdown parsing
  - ```capture/``` external integration

---

# Status

Functional and used in production workflow.

Supports:

- full GTD workflow
- email capture via IMAP/Proton Bridge
- multi-machine workspace sync
- waiting-for tracking
- stalled project detection and prompting

---

# Future improvements

Planned:

- project notes files and richer project editing
- action editing
- archive system for completed items
- review workflows
- multi-capture providers (e.g. Gmail IMAP, file drop, API capture)
- improved Markdown parsing robustness
- optional automatic build after sync

---

# License

Apache License 2.0
