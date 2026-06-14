"""Инициализация Celery: брокер, задачи и расписание Beat."""

from celery import Celery
from celery.schedules import crontab

from app.settings import settings
import app.celery_signals  # noqa: F401 — регистрирует обработчики сигналов

celery_app = Celery(
    "forge_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.example",
        "app.tasks.stats",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
)

# Периодические задачи (запускает отдельный процесс celery beat)
celery_app.conf.beat_schedule = {
    "purge-old-task-runs": {
        "task": "app.tasks.maintenance.purge_old_task_runs",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"retention_days": 30},
    },
}
