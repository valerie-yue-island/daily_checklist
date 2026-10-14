"""Priority-queue rules for tasks. Pure functions: no database or web code.

Works on any object with: id, progress, important, planned_date,
created_at, completed_at.
"""
from datetime import date, datetime


def status_for(progress: int) -> str:
    if progress >= 100:
        return "done"
    if progress > 0:
        return "in_progress"
    return "todo"


def is_overdue(task, today: date) -> bool:
    return (
        task.progress < 100
        and task.planned_date is not None
        and task.planned_date < today
    )


def build_queue(tasks, today: date) -> dict[str, list]:
    today_group, upcoming, done = [], [], []
    for task in tasks:
        if task.progress >= 100:
            done.append(task)
        elif task.planned_date is not None and task.planned_date > today:
            upcoming.append(task)
        else:
            today_group.append(task)

    today_group.sort(key=lambda t: (not t.important, t.created_at, t.id))
    upcoming.sort(key=lambda t: (t.planned_date, not t.important, t.created_at, t.id))
    done.sort(key=lambda t: (t.completed_at or datetime.min, t.id), reverse=True)
    return {"today": today_group, "upcoming": upcoming, "done": done}
