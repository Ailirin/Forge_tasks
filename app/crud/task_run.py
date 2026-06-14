"""CRUD для task_runs: асинхронный слой (FastAPI)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_run import TaskRun, TaskStatus


async def create_task_run(
    db: AsyncSession,
    *,
    celery_task_id: str,
    task_name: str,
    payload: dict | None = None,
) -> TaskRun:
    """Создаёт запись со статусом queued."""
    task_run = TaskRun(
        celery_task_id=celery_task_id,
        task_name=task_name,
        status=TaskStatus.queued,
        payload=payload,
    )
    db.add(task_run)
    await db.commit()
    await db.refresh(task_run)
    return task_run


async def get_task_run_by_celery_id(
    db: AsyncSession,
    celery_task_id: str,
) -> TaskRun | None:
    """Ищет задачу по UUID из Celery."""
    result = await db.execute(
        select(TaskRun).where(TaskRun.celery_task_id == celery_task_id)
    )
    return result.scalar_one_or_none()


async def update_task_run_status(
    db: AsyncSession,
    task_run: TaskRun,
    *,
    status: TaskStatus,
    result: dict | None = None,
    error: str | None = None,
) -> TaskRun:
    """Обновляет статус и опционально result/error."""
    task_run.status = status
    if result is not None:
        task_run.result = result
    if error is not None:
        task_run.error = error

    await db.commit()
    await db.refresh(task_run)
    return task_run
