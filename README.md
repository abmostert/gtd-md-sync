# gtd-md-sync

A local-first **Getting Things Done (GTD)** command-line system that keeps a single source of truth in JSON and generates clean Markdown views for daily use — with reliable round-trip sync and email capture support.

This system is designed for people who want:

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
│   └── stalled_projects.md
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

# Setup workspace

Choose workspace location (example uses Dropbox):

```bash
python3 gtd.py init --dir ~/Dropbox/GTD
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

---

# Capture emails into inbox

Capture new emails:

```bash
python3 gtd.py capture --dir ~/Dropbox/GTD
```

This creates or updates:

```
inbox/inbox.md
inbox/attachments/
```

Example:

```
- [ ] Register bank details for Medicare
  attachments:
  - attachments/file.pdf
```

Process inbox.md manually:

- convert into next actions
- convert into projects
- delete irrelevant items
- mark processed items with `[x]`

Then sync:

```bash
python3 gtd.py sync --dir ~/Dropbox/GTD
```

Processed items are removed from inbox.md.

---

# Adding actions and projects

Interactive add:

```bash
python3 gtd.py add --dir ~/Dropbox/GTD
```

Supports:

- standalone actions
- projects with next actions
- someday items
- waiting items

Supports multiple actions per project.

---

# Build Markdown views

Generate updated views:

```bash
python3 gtd.py build --dir ~/Dropbox/GTD
```

Creates:

```
views/next_actions.md
views/projects.md
views/someday.md
views/waiting_for.md
views/stalled_projects.md
```

---

# Completing actions

Mark complete in Markdown:

```
- [x] Do something important
```

Then sync:

```bash
python3 gtd.py sync --dir ~/Dropbox/GTD
```

System will:

- mark action completed
- remove from next actions
- detect stalled projects
- prompt for new next actions if needed

---

# Waiting For workflow

When adding an action, choose state:

```
waiting
```

These appear in:

```
views/waiting_for.md
```

Once complete, mark `[x]` and sync.

---

# Stalled project detection

If a project has no active next actions, it appears in:

```
views/stalled_projects.md
```

Sync will prompt:

```
Project stalled: Publish paper
Add a next action now? [Y/n]
```

---

# Editing projects

List projects:

```bash
python3 gtd.py project --dir ~/Dropbox/GTD list
```

Edit project:

```bash
python3 gtd.py project --dir ~/Dropbox/GTD edit
```

Supports:

- rename
- change state
- change due date
- add notes

---

# Managing contexts

List:

```bash
python3 gtd.py context --dir ~/Dropbox/GTD list
```

Add:

```bash
python3 gtd.py context --dir ~/Dropbox/GTD add work
```

Drop:

```bash
python3 gtd.py context --dir ~/Dropbox/GTD drop errands
```

Contexts are enforced when adding actions.

---

# Sync model

The system follows explicit sync:

```
Markdown → sync → master.json → build → Markdown
```

Nothing happens automatically. This ensures safety and transparency.

---

# Email capture setup (Proton Bridge example)

Example config.json:

```json
"capture": {
  "enabled": true,
  "imap_host": "127.0.0.1",
  "imap_port": 1143,
  "imap_user": "your@email.com",
  "imap_password": "bridge_password",
  "folder": "Stuff Capture"
}
```

---

# Recommended storage

Use Dropbox, Google Drive, or similar:

```
~/Dropbox/GTD/
```

This allows:

- mobile access
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

---

# Status

Functional and used in production workflow.

Supports:

- full GTD workflow
- email capture
- multi-machine sync
- waiting-for tracking
- stalled project detection

---

# Future improvements

Planned:

- project notes files
- archive system
- review workflows
- automated capture polling
- schema versioning and migration
- optional automatic build after sync

---

# License

Apache License 2.0
