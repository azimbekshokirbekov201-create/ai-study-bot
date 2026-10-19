#!/bin/sh
set -eu

# Render free web services do not support pre-deploy commands.
# Run migrations and idempotent seed on startup for one test instance.
echo "Applying database migrations..."
alembic upgrade head
echo "Seeding initial curriculum..."
python -m scripts.seed
echo "Starting AI Study Bot web service..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --timeout-graceful-shutdown 90 --no-access-log --no-proxy-headers
