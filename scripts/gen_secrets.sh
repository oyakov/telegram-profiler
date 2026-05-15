#!/usr/bin/env bash
# Generate all required secrets for the production .env
# Run once on the server: bash scripts/gen_secrets.sh >> .env

set -euo pipefail

echo ""
echo "# === Generated secrets $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 40)"
echo "REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "API_KEY=$(openssl rand -hex 32)"
echo ""
echo "# Copy the above into your .env and fill in the remaining values."
