from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 10, 13, 9, 0, 0)

    def __call__(self):
        return self.current

    def advance(self, **kwargs):
        self.current += timedelta(**kwargs)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def client(clock):
    app = create_app("sqlite://", clock=clock)
    with TestClient(app) as c:
        yield c


def create(client, **body):
    body.setdefault("title", "Task")
    r = client.post("/api/tasks", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_index_page_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Daily Checklist" in r.text


def test_create_task_defaults(client):
    t = create(client, title="Write report")
    assert t["title"] == "Write report"
    assert t["progress"] == 0
    assert t["status"] == "todo"
    assert t["important"] is False
    assert t["planned_date"] is None
    assert t["created_at"] == t["updated_at"] == "2026-10-13T09:00:00"
    assert t["completed_at"] is None
    assert t["notes"] == []
    assert t["overdue"] is False


def test_create_rejects_blank_title(client):
    r = client.post("/api/tasks", json={"title": "   "})
    assert r.status_code == 422


def test_list_groups_tasks(client):
    a = create(client, title="today one")
    b = create(client, title="tomorrow", planned_date="2026-10-14")
    c = create(client, title="finished", progress=100)

    data = client.get("/api/tasks").json()

    assert [t["id"] for t in data["today"]] == [a["id"]]
    assert [t["id"] for t in data["upcoming"]] == [b["id"]]
    assert [t["id"] for t in data["done"]] == [c["id"]]


def test_overdue_flag_in_list(client):
    create(client, title="late", planned_date="2026-10-10")
    data = client.get("/api/tasks").json()
    assert data["today"][0]["overdue"] is True


def test_patch_progress_updates_status_and_timestamps(client, clock):
    t = create(client)
    clock.advance(hours=1)

    r = client.patch(f"/api/tasks/{t['id']}", json={"progress": 40})
    t2 = r.json()
    assert t2["progress"] == 40
    assert t2["status"] == "in_progress"
    assert t2["updated_at"] == "2026-10-13T10:00:00"
    assert t2["created_at"] == "2026-10-13T09:00:00"
    assert t2["completed_at"] is None

    clock.advance(hours=1)
    t3 = client.patch(f"/api/tasks/{t['id']}", json={"progress": 100}).json()
    assert t3["status"] == "done"
    assert t3["completed_at"] == "2026-10-13T11:00:00"

    t4 = client.patch(f"/api/tasks/{t['id']}", json={"progress": 0}).json()
    assert t4["status"] == "todo"
    assert t4["completed_at"] is None


def test_patch_rejects_progress_out_of_range(client):
    t = create(client)
    assert client.patch(f"/api/tasks/{t['id']}", json={"progress": 101}).status_code == 422
    assert client.patch(f"/api/tasks/{t['id']}", json={"progress": -1}).status_code == 422


def test_patch_title_important_and_clear_date(client):
    t = create(client, planned_date="2026-10-20")
    t2 = client.patch(
        f"/api/tasks/{t['id']}",
        json={"title": "Renamed", "important": True, "planned_date": None},
    ).json()
    assert t2["title"] == "Renamed"
    assert t2["important"] is True
    assert t2["planned_date"] is None


def test_patch_without_planned_date_keeps_it(client):
    t = create(client, planned_date="2026-10-20")
    t2 = client.patch(f"/api/tasks/{t['id']}", json={"title": "x"}).json()
    assert t2["planned_date"] == "2026-10-20"


def test_add_note_bumps_updated_at_and_lists_newest_first(client, clock):
    t = create(client)
    clock.advance(minutes=5)
    r = client.post(f"/api/tasks/{t['id']}/notes", json={"text": "did chapter 1"})
    assert r.status_code == 201
    clock.advance(minutes=5)
    client.post(f"/api/tasks/{t['id']}/notes", json={"text": "did chapter 2"})

    task = client.get("/api/tasks").json()["today"][0]
    assert [n["text"] for n in task["notes"]] == ["did chapter 2", "did chapter 1"]
    assert task["updated_at"] == "2026-10-13T09:10:00"


def test_add_blank_note_rejected(client):
    t = create(client)
    r = client.post(f"/api/tasks/{t['id']}/notes", json={"text": ""})
    assert r.status_code == 422


def test_delete_task_removes_it_and_its_notes(client):
    t = create(client)
    client.post(f"/api/tasks/{t['id']}/notes", json={"text": "n"})
    assert client.delete(f"/api/tasks/{t['id']}").status_code == 204
    data = client.get("/api/tasks").json()
    assert data == {"today": [], "upcoming": [], "done": []}


def test_unknown_task_returns_404(client):
    assert client.patch("/api/tasks/999", json={"progress": 10}).status_code == 404
    assert client.delete("/api/tasks/999").status_code == 404
    assert client.post("/api/tasks/999/notes", json={"text": "x"}).status_code == 404
