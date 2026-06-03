#!/bin/bash
# Backup MongoDB manual
# Usage: sudo bash backup-mongo.sh
set -e
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

[ "$EUID" -ne 0 ] && { echo "Jalankan dengan sudo"; exit 1; }

BACKEND_ENV="/var/www/LaporanKapuas/backend/.env"
MONGO_URL=$(grep '^MONGO_URL=' "$BACKEND_ENV" | cut -d'=' -f2- | tr -d '"')
DB_NAME=$(grep '^DB_NAME=' "$BACKEND_ENV" | cut -d'=' -f2 | tr -d '"')

[ -z "$MONGO_URL" ] && { echo "MONGO_URL tidak ditemukan di $BACKEND_ENV"; exit 1; }

BACKUP_DIR="/backup"
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
OUT_DIR="$BACKUP_DIR/mongo_$TS"

echo -e "${YELLOW}Backup database '$DB_NAME' → $BACKUP_DIR/bais_$TS.tar.gz${NC}"
mongodump --uri="$MONGO_URL" --out="$OUT_DIR" --quiet
tar -czf "$BACKUP_DIR/bais_$TS.tar.gz" -C "$BACKUP_DIR" "mongo_$TS"
rm -rf "$OUT_DIR"

# Retention: keep last 30 backups
ls -1t "$BACKUP_DIR"/bais_*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm -f

SIZE=$(du -h "$BACKUP_DIR/bais_$TS.tar.gz" | cut -f1)
echo -e "${GREEN}✅ Backup: $BACKUP_DIR/bais_$TS.tar.gz ($SIZE)${NC}"

echo ""
echo "Untuk restore nanti:"
echo "  tar -xzf $BACKUP_DIR/bais_$TS.tar.gz -C /tmp"
echo "  mongorestore --uri=\"$MONGO_URL\" --drop /tmp/mongo_$TS"
