"""Примеры Celery-задач: фоновая по API и заглушки для Beat."""

import time

from app.celery_app import celery_app


@celery_app.task(name="app.tasks.example.process_item")
def process_item(item_id: int, message: str) -> dict:
    """Демо фоновой задачи, вызываемой через POST /tasks/process."""
    time.sleep(2)  # имитация работы
    return {"item_id": item_id, "message": message, "status": "done"}


@celery_app.task(name="app.tasks.example.heartbeat")
def heartbeat() -> str:
    """Служебная периодическая задача для проверки Beat (не трекается в БД)."""
    return "heartbeat ok"


@celery_app.task(name="app.tasks.example.cleanup")
def cleanup() -> str:
    """Устаревшая заглушка; заменена на maintenance.purge_old_task_runs."""
    return "cleanup done"
