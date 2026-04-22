#!/bin/bash
set -e

echo "=== Networking Brain — Starting ==="

# Wait for postgres
echo "Waiting for PostgreSQL..."
until python -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(
        host=os.environ.get('POSTGRES_HOST', 'postgres'),
        port=int(os.environ.get('POSTGRES_PORT', 5432)),
        user=os.environ.get('POSTGRES_USER', 'crm'),
        password=os.environ.get('POSTGRES_PASSWORD', 'changeme'),
        database=os.environ.get('POSTGRES_DB', 'crm'),
    )
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
    echo "  PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready."

# Run migrations
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

if [ "$SERVICE_TYPE" = "worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A src.pipeline.celery_app worker \
        --loglevel="${LOG_LEVEL:-info}" \
        --concurrency="${CELERY_CONCURRENCY:-2}" \
        -Q default,connectors,processing
elif [ "$SERVICE_TYPE" = "beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A src.pipeline.celery_app beat \
        --loglevel="${LOG_LEVEL:-info}"
else
    # Start FastAPI
    echo "Starting FastAPI on port 8000..."
    exec uvicorn src.api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level "${LOG_LEVEL_LOWER}"
fi
