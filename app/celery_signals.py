"""Синхронизация статусов Celery-задач с таблицей task_runs в PostgreSQL."""

from celery.signals import task_failure, task_prerun, task_success

from app.crud import task_run_sync as crud
from app.db_sync import SyncSessionLocal
from app.models.task_run import TaskStatus


def _normalize_result(result) -> dict:
    """Приводит результат задачи к dict для хранения в JSONB."""
    if isinstance(result, dict):
        return result
    return {"value": result}


# Задачи, для которых не создаём записи в БД (шумные служебные)
SKIP_TRACKING = {
    "app.tasks.example.heartbeat",
}


@task_prerun.connect
def on_task_prerun(task_id, task, args, kwargs, **extra):
    """
    Перед выполнением: создаёт запись или переводит queued → running.

    Для API-задач запись уже создана в main.py; для Beat-задач — создаётся здесь.
    """
    if task.name in SKIP_TRACKING:
        return

    with SyncSessionLocal() as db:
        task_run = crud.get_task_run_by_celery_id(db, task_id)

        if task_run is None:
            crud.create_task_run(
                db,
                celery_task_id=task_id,
                task_name=task.name,
                status=TaskStatus.running,
                payload={"args": args, "kwargs": kwargs},
            )
        elif task_run.status == TaskStatus.queued:
            crud.update_task_run_status(db, task_run, status=TaskStatus.running)


@task_success.connect
def on_task_success(sender=None, result=None, **extra):
    """После успеха: сохраняет result и статус success."""
    task_id = extra.get("task_id") or getattr(getattr(sender, "request", None), "id", None)
    if not task_id:
        return

    with SyncSessionLocal() as db:
        task_run = crud.get_task_run_by_celery_id(db, task_id)
        if task_run is None:
            return

        crud.update_task_run_status(
            db,
            task_run,
            status=TaskStatus.success,
            result=_normalize_result(result),
        )


@task_failure.connect
def on_task_failure(task_id, exception, sender, **extra):
    """После ошибки: сохраняет текст исключения и статус failed."""
    with SyncSessionLocal() as db:
        task_run = crud.get_task_run_by_celery_id(db, task_id)
        if task_run is None:
            return

        crud.update_task_run_status(
            db,
            task_run,
            status=TaskStatus.failed,
            error=str(exception),
        )
