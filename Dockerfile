FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make entrypoint executable
RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000 8501

# Default command (can be overridden in docker-compose.yml)
CMD ["scripts/entrypoint.sh"]
