FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/bridgeline ./bridgeline
COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/migrations ./migrations

FROM base AS test

COPY apps/api/tests ./tests
COPY packages/schemas ./packages/schemas

RUN pip install --no-cache-dir ".[dev]"
RUN ruff format --check bridgeline tests migrations
RUN ruff check bridgeline tests migrations
RUN mypy bridgeline tests
RUN pytest

FROM base AS runtime

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn bridgeline.main:app --host 0.0.0.0 --port 8000"]
