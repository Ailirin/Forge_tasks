"""Тесты HTTP-эндпоинтов FastAPI (с моками БД и Celery)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models.task_run import TaskRun, TaskStatus


@pytest.fixture
def client(mock_db: AsyncMock, sample_task_run: TaskRun):
    """TestClient с подменённой зависимостью get_db."""
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client: TestClient):
    """GET /health возвращает status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("app.main.process_item")
def test_enqueue_process_task(
    mock_process_item: MagicMock,
    client: TestClient,
    mock_db: AsyncMock,
    sample_task_run: TaskRun,
):
    """POST /tasks/process создаёт запись и вызывает apply_async с тем же task_id."""
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

    async def fake_create(*_args, **kwargs):
        sample_task_run.celery_task_id = kwargs["celery_task_id"]
        return sample_task_run

    with patch("app.main.task_run_crud.create_task_run", new=AsyncMock(side_effect=fake_create)):
        response = client.post(
            "/tasks/process",
            json={"item_id": 1, "message": "test"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert uuid.UUID(body["task_id"])
    mock_process_item.apply_async.assert_called_once()
    call_kwargs = mock_process_item.apply_async.call_args.kwargs
    assert call_kwargs["args"] == [1, "test"]
    assert call_kwargs["task_id"] == body["task_id"]


@patch("app.main.compute_task_stats")
def test_enqueue_stats_task(
    mock_compute_task_stats: MagicMock,
    client: TestClient,
    mock_db: AsyncMock,
    sample_task_run: TaskRun,
):
    """POST /tasks/stats ставит задачу compute_task_stats в очередь."""
    sample_task_run.task_name = "app.tasks.stats.compute_task_stats"

    async def fake_create(*_args, **kwargs):
        sample_task_run.celery_task_id = kwargs["celery_task_id"]
        sample_task_run.task_name = kwargs["task_name"]
        return sample_task_run

    with patch("app.main.task_run_crud.create_task_run", new=AsyncMock(side_effect=fake_create)):
        response = client.post("/tasks/stats", json={"period_hours": 24})

    assert response.status_code == 200
    body = response.json()
    mock_compute_task_stats.apply_async.assert_called_once_with(
        args=[24],
        task_id=body["task_id"],
    )


def test_get_task_status_found(
    client: TestClient,
    mock_db: AsyncMock,
    sample_task_run: TaskRun,
    task_id: str,
):
    """GET /tasks/{id} возвращает данные существующей задачи."""
    sample_task_run.status = TaskStatus.success
    sample_task_run.result = {"status": "done"}

    with patch(
        "app.main.task_run_crud.get_task_run_by_celery_id",
        new=AsyncMock(return_value=sample_task_run),
    ):
        response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["status"] == "success"
    assert body["result"] == {"status": "done"}


def test_get_task_status_not_found(client: TestClient):
    """GET /tasks/{id} возвращает 404 для неизвестного id."""
    with patch(
        "app.main.task_run_crud.get_task_run_by_celery_id",
        new=AsyncMock(return_value=None),
    ):
        response = client.get("/tasks/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
