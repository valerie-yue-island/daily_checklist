# Daily Checklist — Design (v1, manual)

## Goal
A personal daily checklist website. Each day the user records what was done
and what is planned. Unfinished tasks always surface at the top as a priority
queue. v1 is manual (click to add/check/annotate) and runs locally. Later:
v2 adds an AI chat box (Claude API) that turns free-text daily updates into
task changes; v3 deploys to AWS for other users.

## Stack
- Python 3.10, FastAPI, SQLAlchemy 2.0.
- SQLite locally (`checklist.db`), configurable via `DATABASE_URL` so AWS can
  use PostgreSQL (RDS) without code changes.
- Plain HTML/CSS/JS frontend served by FastAPI from `app/static/`.

## Data model
`tasks`
| field | type | notes |
|---|---|---|
| id | int | PK |
| title | text | required, non-empty |
| progress | int 0–100 | status is derived from it |
| important | bool | default false |
| planned_date | date, nullable | the day the user intends to do it |
| created_at | datetime | set once |
| updated_at | datetime | bumped on any edit or new note |
| completed_at | datetime, nullable | set when progress reaches 100, cleared below 100 |

`task_notes`: id, task_id (FK, cascade delete), text, created_at.
Adding a note bumps the task's `updated_at`. Notes are an append-only log.

Derived status: 0 → `todo`, 1–99 → `in_progress`, 100 → `done`.
Checking the checkbox sets progress to 100; unchecking sets it to 0.

## Queue rules (`app/queue.py`, pure functions, no DB/web dependency)
Given tasks and `today`, split into three groups:
1. **today** — not done, and `planned_date` is null or ≤ today.
   Sorted: important first, then oldest `created_at` first, then id.
   Tasks with `planned_date < today` are flagged `overdue`.
2. **upcoming** — not done, `planned_date > today`.
   Sorted: `planned_date` ascending, then important first, then `created_at`.
3. **done** — progress 100. Sorted: most recent `completed_at` first.

## API (JSON)
- `GET /api/tasks` → `{today: [...], upcoming: [...], done: [...]}`; each
  task includes status, overdue flag and notes (newest first).
- `POST /api/tasks` `{title, important?, planned_date?, progress?}` → 201 task
- `PATCH /api/tasks/{id}` any of `{title, progress, important, planned_date}` → task
- `DELETE /api/tasks/{id}` → 204
- `POST /api/tasks/{id}/notes` `{text}` → 201 note
- 404 for unknown ids; 422 for invalid input (empty title/note, progress
  outside 0–100).

## Page (`/`)
Top to bottom: add-task bar (title, optional date with "Tomorrow" shortcut,
important star); Today queue; Upcoming grouped by date; Done (collapsed).
Each row: checkbox, star, title (editable), progress bar (click to set, quick
25/50/75 buttons), created/updated dates, overdue tag, notes toggle with log
and add-note box, delete (with confirm).

## Testing
- `tests/test_queue.py`: grouping, ordering, overdue, status derivation.
- `tests/test_api.py`: CRUD, notes, timestamps, validation, 404s — against an
  in-memory SQLite database.

## Out of scope for v1
AI chat box, user accounts, tags/categories, AWS deployment.
