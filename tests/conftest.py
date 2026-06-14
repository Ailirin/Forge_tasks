"""Общие фикстуры pytest: тестовые task_id и mock-объекты TaskRun."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.models.task_run import TaskRun, TaskStatus


@pytest.fixture
def task_id() -> str:
    """Случайный UUID задачи Celery."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_task_run(task_id: str) -> TaskRun:
    """Пример записи task_runs для тестов API."""
    now = datetime.now(UTC)
    return TaskRun(
        id=1,
        celery_task_id=task_id,
        task_name="app.tasks.example.process_item",
        status=TaskStatus.queued,
        payload={"item_id": 1, "message": "test"},
        result=None,
        error=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_db() -> AsyncMock:
    """Подмена async-сессии SQLAlchemy."""
    return AsyncMock()
