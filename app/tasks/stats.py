"""Задача агрегации статистики по task_runs."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.celery_app import celery_app
from app.db_sync import SyncSessionLocal
from app.models.task_run import TaskRun, TaskStatus


@celery_app.task(name="app.tasks.stats.compute_task_stats")
def compute_task_stats(period_hours: int) -> dict:
    """
    Считает количество задач за последние period_hours часов по статусам.

    Вызывается через POST /tasks/stats.
    """
    since = datetime.now(UTC) - timedelta(hours=period_hours)

    with SyncSessionLocal() as db:
        rows = db.execute(
            select(TaskRun.status, func.count())
            .where(TaskRun.created_at >= since)
            .group_by(TaskRun.status)
        ).all()

    by_status = {status.value: count for status, count in rows}
    total = sum(by_status.values())

    return {
        "period_hours": period_hours,
        "since": since.isoformat(),
        "total": total,
        "queued": by_status.get(TaskStatus.queued.value, 0),
        "running": by_status.get(TaskStatus.running.value, 0),
        "success": by_status.get(TaskStatus.success.value, 0),
        "failed": by_status.get(TaskStatus.failed.value, 0),
    }
