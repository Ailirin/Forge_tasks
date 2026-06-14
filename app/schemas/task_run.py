"""Pydantic-схемы запросов и ответов API."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task_run import TaskStatus


class TaskRequest(BaseModel):
    """Тело запроса для демо-задачи process_item."""

    item_id: int
    message: str


class TaskResponse(BaseModel):
    """Ответ при постановке задачи в очередь."""

    task_id: str
    status: str


class TaskRunRead(BaseModel):
    """Полная информация о задаче для GET /tasks/{task_id}."""

    task_id: str
    task_name: str
    status: TaskStatus
    payload: dict | None
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatsRequest(BaseModel):
    """Параметры задачи статистики: окно в часах (от 1 до 720)."""

    period_hours: int = Field(default=24, ge=1, le=720)
