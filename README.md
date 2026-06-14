# forge-tasks

Сервис фоновых и периодических задач на **FastAPI**, **PostgreSQL**, **Celery** и **RabbitMQ**.

Поддерживает два сценария:

- **Фоновые задачи по API** — клиент вызывает HTTP-ручку, задача уходит в очередь и выполняется worker'ом.
- **Задачи по расписанию** — Celery Beat ставит задачи в очередь по cron (например, ежедневная очистка старых записей).

Статусы и результаты всех задач хранятся в PostgreSQL (таблица `task_runs`).

---

## Стек

| Компонент | Назначение |
|-----------|------------|
| FastAPI | HTTP API |
| PostgreSQL | Хранение истории запусков задач |
| Celery | Очередь и исполнение задач |
| RabbitMQ | Брокер сообщений для Celery |
| Alembic | Миграции схемы БД |
| uv | Управление зависимостями Python |

---

## Архитектура

```mermaid
flowchart LR
    Client[Клиент / Swagger]
    API[FastAPI api]
    DB[(PostgreSQL)]
    RMQ[RabbitMQ]
    Worker[Celery Worker]
    Beat[Celery Beat]

    Client -->|POST /tasks/*| API
    Client -->|GET /tasks/id| API
    API -->|asyncpg| DB
    API -->|apply_async| RMQ
    Beat -->|по расписанию| RMQ
    RMQ --> Worker
    Worker -->|psycopg2 + signals| DB
```

### Жизненный цикл задачи по API

1. Клиент вызывает `POST /tasks/...`.
2. API генерирует `task_id`, создаёт запись в `task_runs` со статусом `queued`.
3. API ставит задачу в RabbitMQ через `apply_async(task_id=...)`.
4. Worker забирает задачу; сигнал `task_prerun` переводит статус в `running`.
5. После выполнения сигнал `task_success` или `task_failure` пишет результат в БД.
6. Клиент опрашивает `GET /tasks/{task_id}`.

> Запись в БД создаётся **до** постановки в очередь, чтобы избежать гонки с `celery_signals`.

### Периодические задачи

Celery Beat по расписанию из `beat_schedule` ставит задачу в очередь. API не участвует. Запись в `task_runs` создаётся в `task_prerun`, если её ещё нет.

---

## Структура проекта

```
forge-tasks/
├── app/
│   ├── main.py              # FastAPI: эндпоинты
│   ├── settings.py          # Настройки из .env
│   ├── db.py                # Async SQLAlchemy (API)
│   ├── db_sync.py           # Sync SQLAlchemy (Celery)
│   ├── celery_app.py        # Celery + beat_schedule
│   ├── celery_signals.py    # Синхронизация статусов с БД
│   ├── crud/                # Операции с task_runs
│   ├── models/              # ORM-модели
│   ├── schemas/             # Pydantic-схемы API
│   └── tasks/               # Celery-задачи
│       ├── example.py       # Демо process_item
│       ├── stats.py         # Статистика по task_runs
│       └── maintenance.py   # Очистка старых записей
├── alembic/                 # Миграции
├── tests/                   # pytest
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

---

## Требования

- Python **3.14+**
- [uv](https://docs.astral.sh/uv/)
- Docker и Docker Compose (для полного запуска в контейнерах)

---

## Быстрый старт (Docker — рекомендуется)

Один `docker compose up` поднимает всё: Postgres, RabbitMQ, миграции, API, worker и beat.

### 1. Настройка окружения

```powershell
copy .env.example .env
```

Файл `.env` нужен для учётных данных Postgres и RabbitMQ. В Docker Compose хосты `postgres` и `rabbitmq` подставляются автоматически.

### 2. Запуск

```powershell
docker compose up -d --build
```

Поднимутся сервисы:

| Сервис | Порт | Описание |
|--------|------|----------|
| `api` | 8000 | FastAPI |
| `postgres` | 5432 | PostgreSQL |
| `rabbitmq` | 5672, 15672 | Брокер + веб-UI |
| `celery-worker` | — | Исполнитель задач |
| `celery-beat` | — | Планировщик |
| `migrate` | — | Одноразово: `alembic upgrade head` |

### 3. Проверка

- API: http://localhost:8000/docs
- Health: http://localhost:8000/health
- RabbitMQ UI: http://localhost:15672 (логин/пароль из `.env`, по умолчанию `guest` / `guest`)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

### 4. Полезные команды Docker

```powershell
# Логи всех сервисов
docker compose logs -f

# Логи worker
docker compose logs -f celery-worker

# Остановить
docker compose down

# Пересобрать после изменений кода
docker compose up -d --build
```

> Перед `docker compose up` остановите локальные uvicorn / worker / beat, если они уже запущены — иначе конфликт порта 8000 и дублирование Beat.

---

## Локальная разработка (гибридный режим)

Удобно, когда нужен `--reload` у API и быстрая итерация по коду.

### 1. Только инфраструктура в Docker

```powershell
docker compose up -d postgres rabbitmq
```

### 2. Зависимости и миграции

```powershell
uv sync
uv run alembic upgrade head
```

В `.env` должны быть хосты `localhost` (как в `.env.example`).

### 3. Три процесса в отдельных терминалах

**Терминал 1 — API:**

```powershell
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Терминал 2 — Worker:**

```powershell
# Linux / macOS
uv run celery -A app.celery_app worker --loglevel=info

# Windows (prefork нестабилен — используйте solo)
uv run celery -A app.celery_app worker --loglevel=info --pool=solo
```

**Терминал 3 — Beat:**

```powershell
uv run celery -A app.celery_app beat --loglevel=info
```

> **Beat должен быть один** на всё окружение. Два Beat-процесса = дублирование периодических задач.

---

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `APP_NAME` | Имя приложения | `forge-tasks` |
| `DEBUG` | SQL-логи SQLAlchemy | `true` |
| `DATABASE_URL` | Async URL PostgreSQL | `postgresql+asyncpg://app:app@localhost:5432/app` |
| `CELERY_BROKER_URL` | URL RabbitMQ | `amqp://guest:guest@localhost:5672//` |
| `CELERY_RESULT_BACKEND` | Бэкенд результатов Celery | `rpc://` |
| `TIMEZONE` | Часовой пояс Beat | `Europe/Moscow` |
| `POSTGRES_*` | Параметры Postgres | см. `.env.example` |
| `RABBITMQ_*` | Параметры RabbitMQ | см. `.env.example` |

Файл `.env` **не коммитьте** в git. Используйте `.env.example` как шаблон.

---

## API

Документация Swagger: http://localhost:8000/docs

### `GET /health`

Проверка, что API жив.

### `POST /tasks/process`

Демо фоновой задачи `process_item`.

**Тело запроса:**

```json
{
  "item_id": 1,
  "message": "тестовое сообщение"
}
```

**Ответ:**

```json
{
  "task_id": "uuid",
  "status": "queued"
}
```

### `POST /tasks/stats`

Задача подсчёта статистики по `task_runs` за последние N часов.

**Тело запроса:**

```json
{
  "period_hours": 24
}
```

Допустимый диапазон: **1–720** часов.

### `GET /tasks/{task_id}`

Статус и результат задачи.

**Пример ответа:**

```json
{
  "task_id": "uuid",
  "task_name": "app.tasks.example.process_item",
  "status": "success",
  "payload": {"item_id": 1, "message": "тест"},
  "result": {"item_id": 1, "message": "тест", "status": "done"},
  "error": null,
  "created_at": "2026-06-14T12:00:00Z",
  "updated_at": "2026-06-14T12:00:02Z"
}
```

### Примеры вызова (PowerShell)

```powershell
# Поставить задачу
$r = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/tasks/process" `
  -ContentType "application/json" `
  -Body '{"item_id": 1, "message": "test"}'

# Подождать выполнения (~3 сек для process_item)
Start-Sleep -Seconds 3

# Получить статус
Invoke-RestMethod -Uri "http://localhost:8000/tasks/$($r.task_id)"
```

> В PowerShell `curl` — это алиас `Invoke-WebRequest`. Для Unix-curl используйте `curl.exe` или `Invoke-RestMethod`.

---

## Celery-задачи

### По API (фоновые)

| Задача | Эндпоинт | Описание |
|--------|----------|----------|
| `app.tasks.example.process_item` | `POST /tasks/process` | Демо обработка item |
| `app.tasks.stats.compute_task_stats` | `POST /tasks/stats` | Статистика по task_runs |

### По расписанию (Beat)

| Задача | Расписание | Описание |
|--------|------------|----------|
| `app.tasks.maintenance.purge_old_task_runs` | Ежедневно в 03:00 | Удаление записей старше 30 дней |

Расписание задаётся в `app/celery_app.py` → `beat_schedule`.

### Ручной запуск задачи (Windows)

`celery call` в PowerShell часто ломает JSON. Надёжный способ:

```powershell
uv run python -c "from app.tasks.maintenance import purge_old_task_runs; r = purge_old_task_runs.delay(retention_days=1); print(r.id)"
```

---

## Как добавить новую задачу

### Фоновая задача по API

1. Создайте функцию с `@celery_app.task` в `app/tasks/`.
2. Добавьте модуль в `include` в `app/celery_app.py`.
3. Добавьте Pydantic-схему в `app/schemas/`.
4. Добавьте эндпоинт в `app/main.py` по шаблону:

```python
task_id = str(uuid.uuid4())
await task_run_crud.create_task_run(db, celery_task_id=task_id, task_name="...", payload=...)
my_task.apply_async(args=[...], task_id=task_id)
return TaskResponse(task_id=task_id, status="queued")
```

5. Перезапустите worker (в Docker: `docker compose up -d --build celery-worker`).

### Периодическая задача

1. Создайте `@celery_app.task` в `app/tasks/`.
2. Добавьте запись в `beat_schedule` в `app/celery_app.py`.
3. Перезапустите worker и beat.

### Служебные задачи без записи в БД

Добавьте имя задачи в `SKIP_TRACKING` в `app/celery_signals.py` (как у `heartbeat`).

---

## Миграции

```powershell
# Применить все миграции
uv run alembic upgrade head

# Создать новую миграцию после изменения моделей
uv run alembic revision --autogenerate -m "описание"
```

В Docker миграции применяет сервис `migrate` при каждом `docker compose up`.

---

## Тесты

```powershell
uv sync --group dev
uv run pytest -v
```

Тесты используют моки БД и Celery — для запуска **не нужны** Postgres и RabbitMQ.

| Файл | Что проверяет |
|------|---------------|
| `tests/test_api.py` | HTTP-эндпоинты |
| `tests/test_schemas.py` | Валидация Pydantic |
| `tests/test_signals.py` | Нормализация результатов |
| `tests/test_tasks_stats.py` | Задача статистики |
| `tests/test_tasks_maintenance.py` | Задача очистки |

---

## Модель данных `task_runs`

| Поле | Тип | Описание |
|------|-----|----------|
| `celery_task_id` | UUID | Идентификатор задачи Celery |
| `task_name` | string | Полное имя задачи |
| `status` | enum | `queued` → `running` → `success` / `failed` |
| `payload` | JSONB | Входные данные |
| `result` | JSONB | Результат выполнения |
| `error` | text | Текст ошибки |
| `created_at` | timestamp | Время создания |
| `updated_at` | timestamp | Время последнего обновления |

---

## Частые проблемы

### Worker на Windows падает с `PermissionError` / `Неверный дескриптор`

Celery prefork на Windows нестабилен. Запускайте worker с `--pool=solo`:

```powershell
uv run celery -A app.celery_app worker --loglevel=info --pool=solo
```

В Docker (Linux) `solo` не нужен.

### `UniqueViolationError` при POST /tasks/*

Гонка между API и `celery_signals`. В проекте решено через предварительное создание записи и `apply_async(task_id=...)`. Убедитесь, что используете актуальный `main.py`.

### Много записей `heartbeat` в БД

Задача `heartbeat` из примеров может засорять таблицу. Она в `SKIP_TRACKING` и не пишется в БД. Старые записи удаляет `purge_old_task_runs`.

### `celery call --kwargs` не работает в PowerShell

Используйте Python-однострочник (см. раздел «Ручной запуск задачи»).

### Порт 8000 занят

Остановите локальный uvicorn или предыдущий контейнер `forge_api`:

```powershell
docker compose down
```

---

## Лицензия

Проект учебный / внутренний. Уточните лицензию при публикации.
