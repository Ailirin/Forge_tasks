"""Тесты задачи purge_old_task_runs."""

from unittest.mock import MagicMock, patch

from app.tasks.maintenance import purge_old_task_runs


def test_purge_old_task_runs_deletes_and_returns_count():
    """Возвращает количество удалённых записей и коммитит транзакцию."""
    mock_db = MagicMock()
    mock_db.scalar.return_value = 5

    with patch("app.tasks.maintenance.SyncSessionLocal") as session_cls:
        session_cls.return_value.__enter__.return_value = mock_db
        result = purge_old_task_runs(retention_days=30)

    assert result["retention_days"] == 30
    assert result["deleted"] == 5
    assert "cutoff" in result
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


def test_purge_old_task_runs_zero_when_nothing_to_delete():
    """Если scalar вернул None, deleted=0."""
    mock_db = MagicMock()
    mock_db.scalar.return_value = None

    with patch("app.tasks.maintenance.SyncSessionLocal") as session_cls:
        session_cls.return_value.__enter__.return_value = mock_db
        result = purge_old_task_runs(retention_days=7)

    assert result["deleted"] == 0
