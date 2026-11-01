FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app/services/tasks

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY shared/pyproject.toml /app/shared/pyproject.toml
COPY shared/shared /app/shared/shared

COPY services/tasks/pyproject.toml services/tasks/poetry.lock ./

RUN poetry install --only main --no-root

COPY services/tasks/tasks ./tasks
COPY services/tasks/alembic.ini ./
COPY services/tasks/alembic ./alembic

EXPOSE 8000

CMD ["uvicorn", "tasks.main:app", "--host", "0.0.0.0", "--port", "8000"]
