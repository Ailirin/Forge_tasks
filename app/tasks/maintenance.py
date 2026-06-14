"""Служебные задачи обслуживания БД."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from app.celery_app import celery_app
from app.db_sync import SyncSessionLocal
from app.models.task_run import TaskRun


@celery_app.task(name="app.tasks.maintenance.purge_old_task_runs")
def purge_old_task_runs(retention_days: int = 30) -> dict:
    """
    Удаляет записи task_runs старше retention_days дней.

    Запускается по расписанию Celery Beat (ежедневно в 03:00).
    """
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    with SyncSessionLocal() as db:
        count_before = db.scalar(
            select(func.count()).select_from(TaskRun).where(TaskRun.created_at < cutoff)
        )

        db.execute(delete(TaskRun).where(TaskRun.created_at < cutoff))
        db.commit()

    return {
        "retention_days": retention_days,
        "cutoff": cutoff.isoformat(),
        "deleted": count_before or 0,
    }
