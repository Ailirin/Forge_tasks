"""Конфигурация приложения из переменных окружения (.env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки FastAPI, PostgreSQL, RabbitMQ и Celery."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "forge-tasks"
    app_env: str = "development"
    debug: bool = True

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str

    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672

    celery_broker_url: str
    celery_result_backend: str = "rpc://"
    timezone: str = "Europe/Moscow"

    @property
    def database_url_sync(self) -> str:
        """URL для синхронного драйвера (Celery worker, Alembic)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")


settings = Settings()
