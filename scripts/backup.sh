#!/bin/bash
set -e

BACKUP_DIR="/backups"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="crm_backup_${TIMESTAMP}.sql.gz"

echo "Creating backup: ${FILENAME}"
pg_dump -U "${POSTGRES_USER:-crm}" "${POSTGRES_DB:-crm}" | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "Removing backups older than ${RETAIN_DAYS} days..."
find "${BACKUP_DIR}" -name "crm_backup_*.sql.gz" -mtime "+${RETAIN_DAYS}" -delete

echo "Backup complete. Current backups:"
ls -lh "${BACKUP_DIR}"/crm_backup_*.sql.gz 2>/dev/null || echo "  (none)"
