import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Task, TaskNote
from app.queue import build_queue, is_overdue, status_for
from app.schemas import NoteCreate, NoteOut, QueueOut, TaskCreate, TaskOut, TaskUpdate

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_DATABASE_URL = "sqlite:///./checklist.db"


def _make_engine(database_url: str):
    if database_url.startswith("sqlite"):
        kwargs = {"connect_args": {"check_same_thread": False}}
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(database_url, **kwargs)
    return create_engine(database_url)


def _set_progress(task: Task, progress: int, now: datetime) -> None:
    if progress >= 100 and task.progress < 100:
        task.completed_at = now
    elif progress < 100:
        task.completed_at = None
    task.progress = progress


def create_app(database_url: str | None = None,
               clock: Callable[[], datetime] = datetime.now) -> FastAPI:
    engine = _make_engine(database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    app = FastAPI(title="Daily Checklist")

    def get_db():
        with SessionLocal() as db:
            yield db

    def get_task(task_id: int, db: Session = Depends(get_db)) -> Task:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    def to_out(task: Task) -> TaskOut:
        return TaskOut(
            id=task.id,
            title=task.title,
            progress=task.progress,
            status=status_for(task.progress),
            important=task.important,
            planned_date=task.planned_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            overdue=is_overdue(task, clock().date()),
            notes=[NoteOut.model_validate(n) for n in task.notes],
        )

    @app.get("/api/tasks", response_model=QueueOut)
    def list_tasks(db: Session = Depends(get_db)):
        tasks = db.scalars(select(Task).options(selectinload(Task.notes))).all()
        queue = build_queue(tasks, clock().date())
        return {group: [to_out(t) for t in items] for group, items in queue.items()}

    @app.post("/api/tasks", response_model=TaskOut, status_code=201)
    def create_task(body: TaskCreate, db: Session = Depends(get_db)):
        now = clock()
        task = Task(title=body.title, important=body.important,
                    planned_date=body.planned_date, progress=0,
                    created_at=now, updated_at=now)
        _set_progress(task, body.progress, now)
        db.add(task)
        db.commit()
        db.refresh(task)
        return to_out(task)

    @app.patch("/api/tasks/{task_id}", response_model=TaskOut)
    def update_task(body: TaskUpdate, task: Task = Depends(get_task),
                    db: Session = Depends(get_db)):
        now = clock()
        fields = body.model_fields_set
        if "title" in fields and body.title is not None:
            task.title = body.title
        if "important" in fields and body.important is not None:
            task.important = body.important
        if "planned_date" in fields:
            task.planned_date = body.planned_date
        if "progress" in fields and body.progress is not None:
            _set_progress(task, body.progress, now)
        task.updated_at = now
        db.commit()
        db.refresh(task)
        return to_out(task)

    @app.delete("/api/tasks/{task_id}", status_code=204)
    def delete_task(task: Task = Depends(get_task), db: Session = Depends(get_db)):
        db.delete(task)
        db.commit()
        return Response(status_code=204)

    @app.post("/api/tasks/{task_id}/notes", response_model=NoteOut, status_code=201)
    def add_note(body: NoteCreate, task: Task = Depends(get_task),
                 db: Session = Depends(get_db)):
        now = clock()
        note = TaskNote(task_id=task.id, text=body.text, created_at=now)
        db.add(note)
        task.updated_at = now
        db.commit()
        db.refresh(note)
        return note

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app

