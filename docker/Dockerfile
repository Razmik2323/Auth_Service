FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

FROM base AS dev

COPY pyproject.toml ./
RUN uv sync --no-install-project
COPY app ./app
COPY tests ./tests
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS runtime

RUN groupadd -r app && useradd -r -g app -m app
COPY pyproject.toml ./
RUN uv sync --no-install-project --no-dev
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R app:app /app
USER app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
