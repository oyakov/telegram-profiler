FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user before installing deps
RUN groupadd --system appgroup && useradd --system --gid appgroup --no-create-home appuser

# Install Python deps as root (no home dir issues)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create writable directories and hand them to appuser
RUN mkdir -p sessions uploads /tmp/prometheus_multiproc_dir \
    && chown -R appuser:appgroup /app sessions uploads /tmp/prometheus_multiproc_dir

RUN chmod +x scripts/entrypoint.sh

USER appuser

EXPOSE 8000

# Health check — nginx depends_on only waits for container start, not uvicorn
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/stats/health || exit 1

CMD ["scripts/entrypoint.sh"]
