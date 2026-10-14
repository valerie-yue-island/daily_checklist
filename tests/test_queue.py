from dataclasses import dataclass
from datetime import date, datetime

from app.queue import build_queue, is_overdue, status_for


@dataclass
class FakeTask:
    id: int
    progress: int = 0
    important: bool = False
    planned_date: date | None = None
    created_at: datetime = datetime(2026, 10, 1)
    completed_at: datetime | None = None


TODAY = date(2026, 10, 13)


def ids(tasks):
    return [t.id for t in tasks]


def test_status_derived_from_progress():
    assert status_for(0) == "todo"
    assert status_for(1) == "in_progress"
    assert status_for(99) == "in_progress"
    assert status_for(100) == "done"


def test_tasks_split_into_today_upcoming_done():
    no_date = FakeTask(1)
    due_today = FakeTask(2, planned_date=TODAY)
    past_due = FakeTask(3, planned_date=date(2026, 10, 10))
    tomorrow = FakeTask(4, planned_date=date(2026, 10, 14))
    finished = FakeTask(5, progress=100, completed_at=datetime(2026, 10, 12))

    q = build_queue([no_date, due_today, past_due, tomorrow, finished], TODAY)

    assert set(ids(q["today"])) == {1, 2, 3}
    assert ids(q["upcoming"]) == [4]
    assert ids(q["done"]) == [5]


def test_partially_done_task_stays_in_today():
    q = build_queue([FakeTask(1, progress=60)], TODAY)
    assert ids(q["today"]) == [1]


def test_today_sorted_important_first_then_oldest_created():
    old = FakeTask(1, created_at=datetime(2026, 10, 1))
    new = FakeTask(2, created_at=datetime(2026, 10, 12))
    new_important = FakeTask(3, important=True, created_at=datetime(2026, 10, 12))
    old_important = FakeTask(4, important=True, created_at=datetime(2026, 10, 2))

    q = build_queue([new, old, new_important, old_important], TODAY)

    assert ids(q["today"]) == [4, 3, 1, 2]


def test_upcoming_sorted_by_planned_date_then_important():
    later = FakeTask(1, planned_date=date(2026, 10, 20))
    soon = FakeTask(2, planned_date=date(2026, 10, 14))
    soon_important = FakeTask(3, important=True, planned_date=date(2026, 10, 14),
                              created_at=datetime(2026, 10, 12))

    q = build_queue([later, soon, soon_important], TODAY)

    assert ids(q["upcoming"]) == [3, 2, 1]


def test_done_sorted_most_recently_completed_first():
    a = FakeTask(1, progress=100, completed_at=datetime(2026, 10, 10))
    b = FakeTask(2, progress=100, completed_at=datetime(2026, 10, 12))

    q = build_queue([a, b], TODAY)

    assert ids(q["done"]) == [2, 1]


def test_overdue_only_for_unfinished_tasks_planned_before_today():
    assert is_overdue(FakeTask(1, planned_date=date(2026, 10, 12)), TODAY)
    assert not is_overdue(FakeTask(2, planned_date=TODAY), TODAY)
    assert not is_overdue(FakeTask(3), TODAY)
    assert not is_overdue(
        FakeTask(4, progress=100, planned_date=date(2026, 10, 1),
                 completed_at=datetime(2026, 10, 2)),
        TODAY,
    )
