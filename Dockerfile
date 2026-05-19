# ── Stage 1: compile Python wheels ───────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ARG REQUIREMENTS_FILE=requirements.txt
WORKDIR /build
COPY requirements*.txt ./
RUN pip install --no-cache-dir --prefix=/install -r ${REQUIREMENTS_FILE}

# ── Stage 2: lean runtime image ──────────────────────────────────────────────
FROM python:3.12-slim

# libpq5: asyncpg runtime; curl: healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /install /usr/local

RUN groupadd --system appgroup && useradd --system --gid appgroup --no-create-home appuser

COPY . .

RUN mkdir -p sessions uploads /tmp/prometheus_multiproc_dir \
    && chown -R appuser:appgroup /app sessions uploads /tmp/prometheus_multiproc_dir

RUN chmod +x scripts/entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/stats/health || exit 1

CMD ["scripts/entrypoint.sh"]
