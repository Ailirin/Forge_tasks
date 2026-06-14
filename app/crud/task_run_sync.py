"""CRUD для task_runs: синхронный слой (Celery signals, задачи worker)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task_run import TaskRun, TaskStatus


def get_task_run_by_celery_id(db: Session, celery_task_id: str) -> TaskRun | None:
    """Ищет задачу по UUID из Celery."""
    return db.scalar(
        select(TaskRun).where(TaskRun.celery_task_id == celery_task_id)
    )


def create_task_run(
    db: Session,
    *,
    celery_task_id: str,
    task_name: str,
    status: TaskStatus = TaskStatus.queued,
    payload: dict | None = None,
) -> TaskRun:
    """Создаёт запись с заданным начальным статусом."""
    task_run = TaskRun(
        celery_task_id=celery_task_id,
        task_name=task_name,
        status=status,
        payload=payload,
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)
    return task_run


def update_task_run_status(
    db: Session,
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

    db.commit()
    db.refresh(task_run)
    return task_run
