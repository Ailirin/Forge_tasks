"""Тесты задачи compute_task_stats."""

from unittest.mock import MagicMock, patch

from app.models.task_run import TaskStatus
from app.tasks.stats import compute_task_stats


def test_compute_task_stats_counts_by_status():
    """Агрегирует количество задач по статусам."""
    mock_db = MagicMock()
    mock_db.execute.return_value.all.return_value = [
        (TaskStatus.success, 3),
        (TaskStatus.failed, 1),
    ]

    with patch("app.tasks.stats.SyncSessionLocal") as session_cls:
        session_cls.return_value.__enter__.return_value = mock_db
        result = compute_task_stats(24)

    assert result["period_hours"] == 24
    assert result["total"] == 4
    assert result["success"] == 3
    assert result["failed"] == 1
    assert result["queued"] == 0
    assert result["running"] == 0
    assert "since" in result


def test_compute_task_stats_empty_db():
    """Пустая БД даёт total=0."""
    mock_db = MagicMock()
    mock_db.execute.return_value.all.return_value = []

    with patch("app.tasks.stats.SyncSessionLocal") as session_cls:
        session_cls.return_value.__enter__.return_value = mock_db
        result = compute_task_stats(1)

    assert result["total"] == 0
    assert result["success"] == 0
