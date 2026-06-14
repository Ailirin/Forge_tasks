"""Асинхронное подключение к PostgreSQL для FastAPI."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.settings import settings


class Base(DeclarativeBase):
    """Базовый класс ORM-моделей."""


engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Зависимость FastAPI: выдаёт async-сессию на время запроса."""
    async with async_session() as session:
        yield session
