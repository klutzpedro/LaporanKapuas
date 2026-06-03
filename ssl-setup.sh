#!/bin/bash
# Setup HTTPS via Let's Encrypt
# Usage: sudo bash ssl-setup.sh domain.bapak.com
set -e
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

[ "$EUID" -ne 0 ] && { echo "Jalankan dengan sudo"; exit 1; }
DOMAIN="$1"
[ -z "$DOMAIN" ] && { echo "Usage: sudo bash ssl-setup.sh <domain>"; exit 1; }

# Cek domain sudah point ke server ini
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short "$DOMAIN" | tail -1)
if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
    echo -e "${YELLOW}⚠️  Domain $DOMAIN belum point ke server ini${NC}"
    echo "   Server IP: $SERVER_IP"
    echo "   Domain IP: $DOMAIN_IP"
    echo "Set A record di DNS provider Bapak dulu, tunggu propagasi (5-30 menit)."
    exit 1
fi

DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot python3-certbot-nginx
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" --redirect

# Update backend .env
BACKEND_ENV="/var/www/LaporanKapuas/backend/.env"
if grep -q "^ALLOWED_ORIGINS=" "$BACKEND_ENV"; then
    sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://$DOMAIN|" "$BACKEND_ENV"
else
    echo "ALLOWED_ORIGINS=https://$DOMAIN" >> "$BACKEND_ENV"
fi

# Update frontend .env (kalau ada)
FE_ENV="/var/www/LaporanKapuas/frontend/.env"
if [ -f "$FE_ENV" ]; then
    sed -i "s|^REACT_APP_BACKEND_URL=.*|REACT_APP_BACKEND_URL=https://$DOMAIN|" "$FE_ENV"
    echo -e "${YELLOW}Frontend .env di-update. Rebuild diperlukan:${NC}"
    echo "   cd /var/www/LaporanKapuas/frontend && yarn build && sudo systemctl reload nginx"
fi

supervisorctl restart bais-backend
echo -e "${GREEN}✅ HTTPS aktif di https://$DOMAIN${NC}"
echo "   Auto-renewal sudah terpasang via certbot cron"
