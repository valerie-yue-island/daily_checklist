# Daily Checklist

A personal daily checklist with a priority queue: unfinished tasks always stay
on top, each task has a progress bar, created/updated dates, and a log of
progress notes.

## Run it locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn --factory app.main:create_app --reload
```

Then open http://localhost:8000.

Tasks are saved in `checklist.db` (SQLite) in this folder. To use a different
database, set `DATABASE_URL`, e.g.
`DATABASE_URL=postgresql+psycopg://user:pass@host/db` (install a Postgres
driver such as `psycopg[binary]` first).

## Using it

- **Add** a task at the top. Pick a date (or click *Tomorrow*) to plan it for
  later; it waits in *Upcoming* and moves into *Today* on that date.
- **★** marks a task important — important tasks sort first.
- **Progress bar**: click anywhere on it (or use 25/50/75) to record partial
  progress. Checking the box sets 100% and moves the task to *Done*;
  unchecking sets it back to 0%.
- **Notes**: open *Show notes* to log what you did ("read pages 1–20").
- **Edit** a title by double-clicking it. **remove** deletes a task.
- **Look & feel**: the page is styled like a hand-drawn restaurant menu. The
  two dots in the top-right switch the ink between tomato red and blueberry
  blue; **✦ animations** turns the doodle animations on/off (it starts from
  your system's reduce-motion setting and remembers your choice).

### Queue order
1. **Today** — unfinished, due today, overdue, or undated. Important first,
   then oldest first. Overdue tasks are tagged.
2. **Upcoming** — unfinished with a future date, by date.
3. **Done** — most recently finished first.

## Tests

```bash
.venv/bin/pytest
```

## Roadmap
- v2: AI chat box — describe your day in plain words, Claude updates the list.
- v3: Deploy to AWS (PostgreSQL on RDS), with accounts for other users.

Design spec: `docs/superpowers/specs/2026-10-13-daily-checklist-design.md`.
