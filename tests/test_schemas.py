"""Тесты Pydantic-схем запросов."""

import pytest
from pydantic import ValidationError

from app.schemas.task_run import StatsRequest, TaskRequest


def test_task_request_valid():
    """TaskRequest принимает item_id и message."""
    req = TaskRequest(item_id=1, message="hello")
    assert req.item_id == 1
    assert req.message == "hello"


def test_stats_request_default():
    """StatsRequest по умолчанию period_hours=24."""
    req = StatsRequest()
    assert req.period_hours == 24


def test_stats_request_rejects_zero():
    """StatsRequest отклоняет period_hours < 1."""
    with pytest.raises(ValidationError):
        StatsRequest(period_hours=0)


def test_stats_request_rejects_too_large():
    """StatsRequest отклоняет period_hours > 720."""
    with pytest.raises(ValidationError):
        StatsRequest(period_hours=721)
