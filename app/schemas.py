from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
NoteText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Progress = Annotated[int, Field(ge=0, le=100)]


class TaskCreate(BaseModel):
    title: Title
    important: bool = False
    planned_date: date | None = None
    progress: Progress = 0


class TaskUpdate(BaseModel):
    """Only fields the client sends are applied; planned_date may be set to null."""
    title: Title | None = None
    important: bool | None = None
    planned_date: date | None = None
    progress: Progress | None = None


class NoteCreate(BaseModel):
    text: NoteText


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    created_at: datetime


class TaskOut(BaseModel):
    id: int
    title: str
    progress: int
    status: str
    important: bool
    planned_date: date | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    overdue: bool
    notes: list[NoteOut]


class QueueOut(BaseModel):
    today: list[TaskOut]
    upcoming: list[TaskOut]
    done: list[TaskOut]
