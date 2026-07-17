#!/bin/sh
set -e

alembic upgrade head

if [ "${SEED_ON_STARTUP:-false}" = "true" ]; then
    python -m app.db.seed
fi

exec gunicorn app.main:app \
    --worker-class uvicorn_worker.UvicornWorker \
    --workers "${GUNICORN_WORKERS:-4}" \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
