#!/usr/bin/env bash
# Generate a self-signed TLS certificate for initial deployment.
# Replace with Let's Encrypt in production:
#   certbot certonly --standalone -d yourdomain.com
#   cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/certs/
#   cp /etc/letsencrypt/live/yourdomain.com/privkey.pem  nginx/certs/

set -euo pipefail

CERT_DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -newkey rsa:4096 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out    "$CERT_DIR/fullchain.pem" \
    -days   365 \
    -subj   "/C=US/ST=State/L=City/O=Networking Brain/CN=localhost"

echo "Self-signed certificate written to $CERT_DIR"
echo "Replace with Let's Encrypt certs for production!"
