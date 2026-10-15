# gtd-md-sync

A local-first Getting Things Done (GTD) command-line system built around a simple principle:

> **`master.json` is the source of truth; Markdown is the working interface.**

The application stores structured GTD data locally, generates human-readable Markdown views, and synchronises supported edits and checkbox completions back into the underlying JSON data.

It is designed for people who want:

- full control over their data
- plain-text and Markdown workflows
- predictable, explicit behaviour
- no vendor lock-in
- cross-platform operation
- a system that works well inside Dropbox, Syncthing, or another file-sync service
- GTD structure without requiring a proprietary task-management application
- visibility into both workload size and psychological workload

The project is implemented in Python and currently uses only the Python standard library.

---

# Core architecture

The basic data flow is:

```text
capture / add / edit
        ↓
    master.json
        ↓
      build
        ↓
 Markdown views
        ↓
      sync
        ↓
    master.json
```

The important distinction is:

```text
master.json     authoritative structured state
Markdown        generated and partially editable interface
metrics.jsonl   append-only historical metric events
archive_bundle.jsonl
                retained completed-project history
```

Nothing updates silently in the background.

The user explicitly runs commands such as:

```bash
./gtd.py --dir ~/Dropbox/GTD add
./gtd.py --dir ~/Dropbox/GTD build
./gtd.py --dir ~/Dropbox/GTD sync
```

This makes changes visible, deterministic, and recoverable.

---

# Repository structure

The codebase is divided into relatively small modules with distinct responsibilities:

```text
gtd-md-sync/
├── gtd.py
├── gtdlib/
│   ├── commands/
│   │   ├── add_cmd.py
│   │   ├── build_cmd.py
│   │   ├── build_project_notes.py
│   │   ├── capture_cmd.py
│   │   ├── context_cmd.py
│   │   ├── init_cmd.py
│   │   ├── project_cmd.py
│   │   ├── someday_cmd.py
│   │   └── sync_cmd.py
│   │
│   ├── prompts/
│   ├── parsing/
│   ├── rules/
│   │   ├── visibility.py
│   │   ├── projects.py
│   │   ├── project_folders.py
│   │   ├── scoring.py
│   │   └── ...
│   │
│   ├── capture/
│   ├── metrics/
│   │   ├── log.py
│   │   └── weekly.py
│   │
│   ├── config.py
│   └── store.py
│
├── README.md
└── LICENSE
```

The broad separation is:

- `commands/` — CLI orchestration
- `prompts/` — interactive user input
- `rules/` — reusable business logic
- `parsing/` — Markdown parsing
- `capture/` — email/IMAP ingestion
- `metrics/` — snapshots, historical events, and weekly reporting
- `store.py` — persistence, IDs, timestamps, and schema migration
- `config.py` — contexts and Focus configuration

---

# Workspace structure

A typical workspace might live at:

```text
~/Dropbox/GTD/
```

The workspace can contain:

```text
GTD/
├── master.json
├── config.json
├── metrics.jsonl
├── archive_bundle.jsonl
│
├── views/
│   ├── focus.md
│   ├── next_actions.md
│   ├── projects.md
│   ├── someday.md
│   ├── waiting_for.md
│   ├── agenda.md
│   ├── stalled_projects.md
│   └── metrics.md
│
├── inbox/
│   ├── inbox.md
│   └── attachments/
│
├── projects/
│   └── <project-slug>__p_xxxxxxxx/
│       └── @project_notes.md
│
├── review/
│   └── <project-slug>__p_xxxxxxxx/
│       ├── @project_notes.md
│       └── @debrief.md
│
├── trash/
│   └── <project-slug>__p_xxxxxxxx/
│
└── archives/
    └── <project-slug>__p_xxxxxxxx/
```

Stable IDs are embedded in folder names and Markdown comments.

Examples:

```text
p_3c2815e1
a_d3996cea
```

and:

```markdown
<!-- id:a_d3996cea -->
```

These IDs allow Markdown and JSON to remain linked even when titles change.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/abmostert/gtd-md-sync.git
cd gtd-md-sync
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No external Python packages are currently required.

You can run the application either as:

```bash
python3 gtd.py ...
```

or, where executable permissions are set:

```bash
./gtd.py ...
```

---

# Initialise a workspace

```bash
./gtd.py --dir ~/Dropbox/GTD init
```

The `--dir` argument is global and identifies the GTD workspace.

The usual command pattern is:

```bash
./gtd.py --dir <workspace> <command>
```

For example:

```bash
./gtd.py --dir ~/Dropbox/GTD add
./gtd.py --dir ~/Dropbox/GTD build
./gtd.py --dir ~/Dropbox/GTD sync
```

---

# GTD data model

The main GTD entities are:

- projects
- active next actions
- waiting-for actions
- agenda actions
- Someday / Maybe actions
- Someday / Maybe projects
- completed actions
- completed projects
- trashed projects

Projects and actions have stable IDs.

The master file is schema-versioned and upgraded through idempotent migrations as the data model evolves.

Current data includes bookkeeping fields such as:

```text
created
last_touched
activated_at
completed
trashed_at
lifecycle
lifetime_action_count
```

depending on entity type and state.

---

# Actions

Actions can currently exist in states including:

```text
active
waiting
someday
completed
```

Active actions normally have a context such as:

```text
work
home
computer
errands
inbox
```

Waiting actions use:

```text
state = waiting
waiting_for = <person or thing>
```

Agenda items are represented as active actions using an agenda context.

For example:

```text
agenda_kathryne
```

---

# Action activation

Actions have an `activated_at` field.

This records when an action most recently entered the active workload.

For newly created actions:

```text
Active   → activated_at = created
Waiting  → activated_at = created
Someday  → activated_at = null
```

When a Someday action later returns to Active or Waiting:

```text
activated_at = current timestamp
```

Normal transitions between Active and Waiting do not reset the activation timestamp.

This allows weekly workload metrics to distinguish between:

- old work already present
- newly activated work
- Someday items that have only now entered the working system

---

# Projects

Projects represent outcomes requiring more than one action or requiring persistent project-level organisation.

A project can include:

- title
- outcome
- due date
- notes
- agenda notes
- state
- lifecycle
- activation timestamp
- lifetime action count

Project folders use stable IDs:

```text
projects/
└── prepare-paper__p_12345678/
```

---

# Project notes

Active project folders contain:

```text
@project_notes.md
```

This provides a Markdown working interface for:

- project outcome
- notes
- agenda notes
- active actions
- waiting actions
- Someday actions
- agenda items
- completed-action history

Existing actions retain stable IDs.

New checkbox items written into supported sections without an ID can be imported as new actions during `sync`.

Repeated syncs are designed to avoid duplicating the same draft action.

---

# Project activation

Projects also have an `activated_at` field.

For new projects:

```text
Active project   → activated_at = created
Someday project  → activated_at = null
```

When a Someday project becomes Active:

```text
activated_at = current timestamp
```

If it later returns to Someday and is activated again, the timestamp is deliberately overwritten with the latest activation.

This supports weekly measurement of projects actually entering the active workload.

---

# Lifetime project size

Each project maintains:

```text
lifetime_action_count
```

This represents the total number of actions ever associated with the project.

Deleting or completing an action does not reduce this value.

The metric is used to classify completed/cleared projects by approximate size:

```text
Small    1–5 lifetime actions
Medium   6–15 lifetime actions
Large    16+ lifetime actions
```

This makes it possible to distinguish clearing several tiny projects from completing a genuinely large body of work.

---

# Adding actions and projects

Run:

```bash
./gtd.py --dir ~/Dropbox/GTD add
```

The interactive workflow supports creating:

- standalone actions
- active projects
- Someday projects
- active actions
- waiting actions
- Someday actions

Full prompting can be requested with:

```bash
./gtd.py --dir ~/Dropbox/GTD add --full
```

When a new active project is created, its first action is created as part of the same workflow.

Project `lifetime_action_count` begins at `1`.

A Someday project starts with:

```text
lifetime_action_count = 0
```

---

# Editing projects

Run:

```bash
./gtd.py --dir ~/Dropbox/GTD project edit
```

Project editing can change project fields and can add additional actions.

When a Someday project is activated and has no active, waiting, or agenda progress path, the CLI prompts:

```text
This project has no progress path.
Add a next action now? [Y/n]:
```

If no action is added, the project remains active and is detected as stalled.

---

# Direct action editing

There is currently no dedicated CLI equivalent of:

```text
gtd action edit
```

State changes for existing project actions can be made through supported edits in `@project_notes.md` followed by `sync`.

A direct interactive action-edit command is a planned improvement.

---

# Building Markdown views

Generate all views with:

```bash
./gtd.py --dir ~/Dropbox/GTD build
```

`build` projects the current master data into Markdown.

Generated views include:

```text
views/focus.md
views/next_actions.md
views/projects.md
views/someday.md
views/waiting_for.md
views/agenda.md
views/stalled_projects.md
views/metrics.md
```

Project note files are also rebuilt or maintained as part of the project workflow.

Markdown entries include stable ID comments so supported changes can be mapped back to `master.json`.

---

# Next Actions view

`views/next_actions.md` contains visible executable next actions grouped by context.

Typical entry:

```markdown
- [ ] (due 2026-10-20) [Project title] Finish the next section <!-- id:a_12345678 -->
```

Completing the checkbox and running `sync` marks the action complete in `master.json`.

---

# Focus view

`views/focus.md` provides a scored subset of executable Next Actions.

The same underlying visibility rules are used as for Next Actions, but actions are ranked using a configurable Focus score.

The score can include:

- action due-date urgency
- action overdue pressure
- project due-date urgency
- project overdue pressure
- action age
- action/project due-date tension
- explicit overdue bonus

Configuration lives in `config.json`.

A Focus entry may look like:

```markdown
- [ ] (due 2026-10-20) [Project title] Finish the next section {score: 65.39} <!-- id:a_12345678 -->
```

Overdue and due-today actions can be made mandatory in the Focus view.

A configurable per-context cap limits the number of lower-priority items displayed.

The scoring logic is shared with the psychological-weight metric so Focus and metrics do not use competing definitions of workload.

---

# Waiting For

Waiting actions appear in:

```text
views/waiting_for.md
```

They remain part of the outstanding action backlog but do not contribute to executable psychological weight.

A Waiting item stores:

```text
state = waiting
waiting_for = <person or thing>
waiting_since = <timestamp>
```

When moved back into executable Next Actions, its psychological burden is reflected automatically in the live weight total.

---

# Agenda

Agenda items appear in:

```text
views/agenda.md
```

Agenda actions count as a valid progress path for a project and therefore prevent an active project from being classified as stalled.

Agenda items are included in the outstanding action backlog but do not contribute to Focus psychological weight.

---

# Someday / Maybe

Someday projects and actions appear in:

```text
views/someday.md
```

Someday items are deliberately excluded from the active workload.

They do not contribute to:

- outstanding active action count
- Focus weight

When reactivated, their `activated_at` timestamp records the new entry into the working system.

Someday items can also be deleted through the dedicated Someday workflow.

---

# Stalled projects

A project is stalled when it is:

- live
- active
- and has no visible progress path

A progress path can include:

- executable Next Action
- Waiting action
- Agenda action

Stalled projects appear in:

```text
views/stalled_projects.md
```

During normal sync, the application can prompt the user to add a next action.

Disable that prompt with:

```bash
./gtd.py --dir ~/Dropbox/GTD sync --no-prompt-next
```

---

# Synchronisation

Run:

```bash
./gtd.py --dir ~/Dropbox/GTD sync
```

The sync process can:

- read checked items from generated views
- mark actions complete
- mark supported project completions
- prune processed capture items
- import supported changes from `@project_notes.md`
- import new draft actions from project notes
- move existing project actions between supported sections
- maintain activation timestamps
- update waiting fields
- detect stalled projects
- optionally prompt for a next action

The conceptual loop is:

```text
Markdown
   ↓
 sync
   ↓
master.json
   ↓
 build
   ↓
Markdown
```

Completed actions are not resurrected by stale copies remaining in project notes.

---

# Project lifecycle

Projects have both a GTD state and a lifecycle.

The lifecycle distinguishes active working folders from completed review folders and deleted material.

The main lifecycle is:

```text
projects/
    ↓ project complete
review/
    ↓ archive-finalize
archives/
```

and:

```text
projects/
    ↓ soft delete
trash/
    ↓ trash-purge
permanently removed
```

---

# Completing a project

Run:

```bash
./gtd.py --dir ~/Dropbox/GTD project complete
```

A completed project:

1. moves from `projects/` to `review/`
2. receives a completion timestamp
3. changes lifecycle to `review`
4. gets an `@debrief.md`
5. retains its project notes
6. creates a standalone review action reminding the user to review the project folder

The review action is itself a normal active action and receives an activation timestamp.

Any remaining executable psychological weight associated with the project is recorded as cleared before the project leaves the live workload.

---

# Archive finalisation

After review, run:

```bash
./gtd.py --dir ~/Dropbox/GTD project archive-finalize
```

The archive-finalisation process preserves historical project data in:

```text
archive_bundle.jsonl
```

The archive record includes:

- project data
- associated actions
- project notes
- debrief
- folder information
- archive timestamp

The project folder is moved to:

```text
archives/
```

and the project and associated actions can then be removed from the live `master.json`.

This preserves completed-project history without keeping inactive projects in the operational data set.

---

# Soft deletion and trash

Run:

```bash
./gtd.py --dir ~/Dropbox/GTD project delete
```

Normal deletion is a soft delete.

The project folder is moved to:

```text
trash/
```

and receives:

```text
lifecycle = trash
trashed_at = <timestamp>
```

The project is no longer considered live.

Associated unfinished actions therefore disappear from the active workload.

Their psychological weight is recorded as cleared when the project is moved to trash.

The default trash retention period is 28 days.

Preview purge candidates with:

```bash
./gtd.py --dir ~/Dropbox/GTD project trash-purge --dry-run
```

Purge eligible trash with:

```bash
./gtd.py --dir ~/Dropbox/GTD project trash-purge
```

or specify another retention period:

```bash
./gtd.py --dir ~/Dropbox/GTD project trash-purge --days 60
```

Before permanent purge, the metrics history preserves project information and associated actions required for historical reporting.

---

# Hard deletion

A project can also be permanently removed immediately:

```bash
./gtd.py --dir ~/Dropbox/GTD project delete --hard
```

Hard deletion is intentionally different from ordinary trashing.

It means:

> this project should not remain part of the historical record.

The project, folder, and associated actions are deleted immediately.

Hard-deleted projects and actions are intentionally excluded from historical metrics.

Use this for erroneous, accidental, test, or otherwise unwanted records rather than normal GTD project closure.

---

# Weekly metrics

The system generates:

```text
views/metrics.md
```

The view currently covers the current week plus the previous five weeks.

The metrics system uses append-only history and weekly snapshots so that denominators are not continuously rewritten as work changes.

The current tables are:

1. Projects
2. Projects Cleared by Size
3. Action Backlog
4. Psychological Weight

Early rows created before a metric or snapshot field existed may show `—`.

These naturally age out of the six-week view.

---

# Weekly snapshots

The first relevant mutation of a week creates a `week_snapshot` event in:

```text
metrics.jsonl
```

A snapshot freezes opening values such as:

```text
active_projects
outstanding_actions
outstanding_weight
```

A snapshot is idempotent: once the week has a snapshot, later commands reuse it rather than changing the denominator.

Weeks are currently represented by Monday start dates.

---

# Project metrics

The Projects table contains:

```text
Week
Start Projects
Projects Cleared
% Cleared
Projects Added
```

## Start Projects

The number of live active projects frozen at the start of the week.

## Projects Cleared

A project is counted as cleared when it is deliberately:

- completed, or
- soft-deleted to trash

Hard deletion is deliberately excluded.

## % Cleared

```text
Projects Cleared
---------------- × 100
 Start Projects
```

## Projects Added

Projects entering the active workload during the week, based on `activated_at`.

---

# Projects Cleared by Size

Cleared projects are grouped using `lifetime_action_count`:

```text
1–5 actions
6–15 actions
16+ actions
```

This gives additional context to the raw project-clearance count.

---

# Action Backlog metrics

The Action Backlog table contains:

```text
Week
Start Actions
Actions Cleared
% Cleared
Actions Added
```

## Outstanding actions

The backlog includes visible:

- active Next Actions
- Waiting actions
- Agenda actions

It excludes:

- Someday actions
- completed actions
- actions hidden because their project is no longer live

Future inactive/tickler behaviour can be incorporated when that feature exists.

## Start Actions

Frozen in the weekly snapshot.

## Actions Added

Actions entering the active workload during the week.

The `activated_at` timestamp is used rather than simply `created`.

This means an old Someday action activated this week counts as new workload this week.

## Actions Cleared

Actions genuinely removed from the active backlog through:

- action completion
- completion of their parent project
- soft deletion of their parent project

Moving an action to Someday is not treated as successful clearance.

Hard-deleted actions are intentionally absent from historical metrics.

## % Cleared

```text
Actions Cleared
--------------- × 100
 Start Actions
```

The denominator remains frozen even if new actions are added during the week.

---

# Psychological Weight

Raw action counts do not describe how mentally burdensome a workload feels.

The system therefore also measures **psychological weight** using the same scoring function used by `focus.md`.

Only executable visible Next Actions contribute psychological weight.

Waiting and Agenda actions remain part of the backlog count but have zero executable psychological weight.

The table contains:

```text
Week
Start Weight
Weight Cleared
% Weight Cleared
Weight Added
```

## Start Weight

The sum of all visible executable Next Action Focus scores at the start of the week.

This value is frozen in the weekly snapshot.

## Weight Cleared

When an executable action leaves the workload, its score is captured at that moment.

This can occur when:

- an action is completed
- an executable action becomes Waiting
- an executable action becomes Someday
- an executable action becomes Agenda
- its project is completed
- its project is soft-deleted

This records the actual psychological burden removed rather than trying to reconstruct an old score later.

## Weight Added

Psychological weight can increase even when no new actions are created.

For example, an existing action can become heavier because:

- it ages
- its due date approaches
- its project due date approaches
- it moves from Waiting/Someday into executable work

Therefore Weight Added is calculated through the accounting identity:

```text
Weight Added
=
End Weight
+ Weight Cleared
- Start Weight
```

For the current week, End Weight is calculated live.

For completed historical weeks, the next week's opening snapshot supplies the ending weight.

This automatically captures both:

- genuinely new work
- increased pressure on work that already existed

## % Weight Cleared

```text
Weight Cleared
-------------- × 100
 Start Weight
```

---

# Metrics history

Historical metric events are stored in:

```text
metrics.jsonl
```

Examples include:

```text
week_snapshot
project_purged
weight_cleared
```

Completed-project actions are retained in:

```text
archive_bundle.jsonl
```

Soft-deleted projects eventually purged from trash preserve sufficient associated-action information in the metrics history for later reconstruction.

The metrics system deliberately avoids fabricating historical data where reliable records do not exist.

---

# Focus scoring

Focus scoring is configured in `config.json`.

The default configuration includes weights for concepts such as:

```text
action_due
action_overdue_slope
project_due
project_overdue_slope
age
tension
overdue_bonus
```

Focus scoring is date-based rather than continuously increasing during the day.

This means psychological weight can change from one day to another as deadlines approach or items age, but does not continuously drift hour by hour.

---

# Context management

List contexts:

```bash
./gtd.py --dir ~/Dropbox/GTD context list
```

Add one:

```bash
./gtd.py --dir ~/Dropbox/GTD context add errands
```

Remove one:

```bash
./gtd.py --dir ~/Dropbox/GTD context drop errands
```

Contexts are validated during action creation.

Reserved workflow concepts such as Waiting are states rather than ordinary contexts.

---

# Email capture

The capture subsystem can ingest email through IMAP-compatible sources.

Run:

```bash
./gtd.py --dir ~/Dropbox/GTD capture
```

or limit the number retrieved:

```bash
./gtd.py --dir ~/Dropbox/GTD capture --limit 50
```

Captured messages are written into:

```text
inbox/inbox.md
```

Attachments can be stored under:

```text
inbox/attachments/
```

A typical capture flow is:

```text
email
  ↓
capture
  ↓
inbox/inbox.md
  ↓
clarify
  ↓
add project/action or discard
```

Checked top-level capture items are pruned during sync.

---

# Proton Bridge / IMAP configuration

A local Proton Bridge setup can use a configuration similar to:

```json
{
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

If the password is omitted or empty, the program can request it interactively rather than storing it permanently.

Other IMAP-compatible providers can use the same general capture architecture.

---

# Typical daily workflow

A simple working loop is:

```bash
./gtd.py --dir ~/Dropbox/GTD capture

./gtd.py --dir ~/Dropbox/GTD add

./gtd.py --dir ~/Dropbox/GTD build
```

Work from:

```text
views/focus.md
views/next_actions.md
views/waiting_for.md
views/agenda.md
```

Tick completed items.

Then:

```bash
./gtd.py --dir ~/Dropbox/GTD sync
./gtd.py --dir ~/Dropbox/GTD build
```

The explicit build/sync cycle is intentional.

---

# Typical project workflow

Create:

```text
new project
    ↓
projects/<slug>__<pid>/
    ↓
@project_notes.md
```

Execute work and add actions.

Then:

```text
project complete
    ↓
review/
    ↓
@debrief.md
    ↓
archive-finalize
    ↓
archives/
+ archive_bundle.jsonl
```

For abandoned or invalid-but-historically-real projects:

```text
project delete
    ↓
trash/
    ↓
retention period
    ↓
trash-purge
```

For records that should never have existed:

```text
project delete --hard
    ↓
removed without historical retention
```

---

# Recommended storage

The workspace is designed to work well inside a synchronised directory such as:

```text
Dropbox
Syncthing
Google Drive
OneDrive
```

A typical setup is:

```text
~/Dropbox/GTD/
```

This allows the same Markdown workspace to be accessed from multiple machines or mobile devices while keeping the application itself local.

Because `master.json` remains authoritative, care should still be taken to avoid simultaneously editing the same workspace from multiple machines before filesystem synchronisation has completed.

---

# Design principles

The project follows several deliberate principles.

## Local first

The user owns the data.

The core GTD system does not require a hosted task-management service.

## JSON is truth

Structured state lives in `master.json`.

Markdown is a projection and working interface rather than an independent competing database.

## Stable identity

Projects and actions use permanent IDs instead of relying on mutable titles.

## Explicit operations

Important changes happen through visible commands.

There is no hidden daemon silently rewriting the task system.

## Human judgement, deterministic bookkeeping

The program automates mechanical work such as:

- IDs
- file generation
- counts
- lifecycle movement
- historical snapshots
- metrics

It leaves semantic decisions such as what constitutes a project, outcome, context, or next action to the user.

## Historical data where meaningful

Completed and legitimately deleted work can be retained for reporting.

Hard deletion intentionally remains outside historical accounting.

## Shared business rules

Visibility and Focus scoring logic are reused rather than independently reimplemented for different views and metrics.

---

# Current limitations

The system is actively evolving.

Notable current limitations include:

- no direct `action edit` CLI command
- state changes for existing actions rely primarily on supported project-note editing
- early historical metric rows may be incomplete because the snapshot and activation systems were introduced after existing data already existed
- psychological-weight historical accuracy begins only once `weight_cleared` events are available
- weekly metrics currently use a fixed six-week table rather than graphical control charts
- tickler/future-action handling is not yet part of the active backlog implementation

---

# Planned improvements

Likely next improvements include:

- direct CLI action editing:
  - Active
  - Waiting
  - Someday / Maybe
  - context
  - waiting-for
  - due date
- control-chart and trend visualisations for weekly metrics
- dependency-free SVG charts
- richer weekly-review reporting
- additional capture providers
- continued Markdown parser hardening
- improved automated validation/testing
- possible tickler/future-action support
- optional reporting/AI summarisation over completed actions and projects

---

# Status

The project is functional and used as a real GTD workflow.

Implemented capabilities include:

- local JSON source of truth
- generated Markdown interface
- stable project and action IDs
- Next Actions
- Focus scoring
- Projects
- Someday / Maybe
- Waiting For
- Agenda
- stalled project detection
- project note files
- draft-action import from project notes
- project completion and review
- debrief files
- archive finalisation
- trash and purge lifecycle
- hard deletion
- email capture
- schema migrations
- lifetime project action counts
- activation timestamps
- weekly project metrics
- weekly action-backlog metrics
- psychological workload metrics
- historical event logging

---

# License

Apache License 2.0
