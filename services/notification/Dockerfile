FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app/services/notification

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY shared/pyproject.toml /app/shared/pyproject.toml
COPY shared/shared /app/shared/shared
COPY services/notification/pyproject.toml ./

RUN poetry install --only main --no-root

COPY services/notification/notification ./notification
COPY services/notification/alembic.ini ./
COPY services/notification/alembic ./alembic

CMD ["python", "-m", "notification.main_consumer"]
