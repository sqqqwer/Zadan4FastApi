FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app/services/saga

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY shared/pyproject.toml /app/shared/pyproject.toml
COPY shared/shared /app/shared/shared
COPY services/saga/pyproject.toml ./

RUN poetry install --only main --no-root

COPY services/saga/saga ./saga
COPY services/saga/alembic.ini ./
COPY services/saga/alembic ./alembic

EXPOSE 8000

CMD ["uvicorn", "saga.main:app", "--host", "0.0.0.0", "--port", "8000"]
