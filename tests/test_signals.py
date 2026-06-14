"""Тесты вспомогательных функций celery_signals."""

from app.celery_signals import _normalize_result


def test_normalize_result_dict():
    """dict возвращается без изменений."""
    assert _normalize_result({"a": 1}) == {"a": 1}


def test_normalize_result_scalar():
    """Скалярные значения оборачиваются в {"value": ...}."""
    assert _normalize_result("heartbeat ok") == {"value": "heartbeat ok"}
