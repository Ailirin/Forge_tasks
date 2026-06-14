"""HTTP API: постановка задач в очередь и получение их статуса."""

import uuid

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import task_run as task_run_crud
from app.db import get_db
from app.schemas.task_run import StatsRequest, TaskRequest, TaskResponse, TaskRunRead
from app.settings import settings
from app.tasks.example import process_item
from app.tasks.stats import compute_task_stats

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/health")
async def health():
    """Проверка, что API запущен."""
    return {"status": "ok", "app": settings.app_name}


@app.post("/tasks/process", response_model=TaskResponse)
async def enqueue_process_task(
    payload: TaskRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ставит демо-задачу process_item в очередь Celery.

    Сначала создаёт запись в БД (status=queued), затем apply_async с тем же task_id,
    чтобы избежать гонки с celery_signals.
    """
    task_id = str(uuid.uuid4())

    await task_run_crud.create_task_run(
        db,
        celery_task_id=task_id,
        task_name="app.tasks.example.process_item",
        payload=payload.model_dump(),
    )

    process_item.apply_async(
        args=[payload.item_id, payload.message],
        task_id=task_id,
    )

    return TaskResponse(task_id=task_id, status="queued")


@app.post("/tasks/stats", response_model=TaskResponse)
async def enqueue_stats_task(
    payload: StatsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ставит задачу подсчёта статистики по task_runs за указанный период."""
    task_id = str(uuid.uuid4())

    await task_run_crud.create_task_run(
        db,
        celery_task_id=task_id,
        task_name="app.tasks.stats.compute_task_stats",
        payload=payload.model_dump(),
    )

    compute_task_stats.apply_async(
        args=[payload.period_hours],
        task_id=task_id,
    )

    return TaskResponse(task_id=task_id, status="queued")


@app.get("/tasks/{task_id}", response_model=TaskRunRead)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Возвращает статус и результат задачи по celery task_id."""
    task_run = await task_run_crud.get_task_run_by_celery_id(db, task_id)
    if task_run is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskRunRead(
        task_id=task_run.celery_task_id,
        task_name=task_run.task_name,
        status=task_run.status,
        payload=task_run.payload,
        result=task_run.result,
        error=task_run.error,
        created_at=task_run.created_at,
        updated_at=task_run.updated_at,
    )
