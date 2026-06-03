#!/usr/bin/env bash
# =============================================================================
#  SCRIPT SETUP HTTPS / SSL Let's Encrypt - BAIS TNI SUMMARY GEOSPASIKA
#  Target  : Ubuntu 22.04 / 24.04 LTS dengan Nginx
#  Purpose : HTTPS gratis & auto-renewal via Certbot
# =============================================================================
#
#  PRASYARAT:
#    1. Domain (mis. bais-summary.example.com) sudah di-pointing
#       A record ke IP VPS Anda (cek: dig +short bais-summary.example.com)
#    2. Nginx sudah running dan reverse-proxy ke FastAPI:8001 + React:3000
#    3. Port 80 & 443 sudah dibuka di UFW (sudah dilakukan oleh vps-hardening.sh)
#
#  CARA PAKAI:
#    sudo ./vps-ssl-setup.sh
#    (script akan tanya domain & email)
#
#  ATAU non-interaktif:
#    sudo DOMAIN=bais.example.com EMAIL=admin@example.com ./vps-ssl-setup.sh
#
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
  err "Jalankan dengan sudo: sudo ./vps-ssl-setup.sh"
  exit 1
fi

echo ""
echo "============================================================"
echo "  SETUP HTTPS / SSL Let's Encrypt"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------------
# 1. INPUT DOMAIN & EMAIL
# -----------------------------------------------------------------------------
if [ -z "$DOMAIN" ]; then
  read -p "Domain Anda (contoh: bais-summary.example.com): " DOMAIN
fi
if [ -z "$EMAIL" ]; then
  read -p "Email Anda (untuk notifikasi expired SSL): " EMAIL
fi

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  err "Domain dan email wajib diisi."
  exit 1
fi

log "Domain : $DOMAIN"
log "Email  : $EMAIL"

# -----------------------------------------------------------------------------
# 2. CEK DNS POINTING
# -----------------------------------------------------------------------------
log "Step 1/6: Cek DNS pointing..."

VPS_IP=$(curl -s -4 ifconfig.me || curl -s -4 icanhazip.com)
DOMAIN_IP=$(dig +short "$DOMAIN" | tail -n1)

echo "  IP VPS    : $VPS_IP"
echo "  IP Domain : $DOMAIN_IP"

if [ "$VPS_IP" != "$DOMAIN_IP" ]; then
  warn "IP domain ($DOMAIN_IP) BELUM sama dengan IP VPS ($VPS_IP)."
  warn "Pastikan A record domain $DOMAIN → $VPS_IP di panel DNS Anda."
  warn "DNS propagation bisa butuh 5-30 menit setelah ubah."
  read -p "Lanjut tetap? (y/N): " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    exit 1
  fi
else
  log "DNS sudah pointing ke VPS dengan benar."
fi

# -----------------------------------------------------------------------------
# 3. INSTALL CERTBOT
# -----------------------------------------------------------------------------
log "Step 2/6: Install Certbot + Nginx plugin..."

apt-get update -y
apt-get install -y certbot python3-certbot-nginx

log "Certbot ter-install: $(certbot --version)"

# -----------------------------------------------------------------------------
# 4. CEK NGINX & KONFIGURASI DASAR
# -----------------------------------------------------------------------------
log "Step 3/6: Cek Nginx config..."

if ! systemctl is-active --quiet nginx; then
  err "Nginx tidak running. Start dulu: sudo systemctl start nginx"
  exit 1
fi

NGINX_CONF="/etc/nginx/sites-available/bais"
if [ ! -f "$NGINX_CONF" ]; then
  warn "$NGINX_CONF tidak ditemukan. Membuat config baru..."
  
  cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    # Frontend React (port 3000)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
    }

    # Backend FastAPI (port 8001) - semua /api prefix
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        client_max_body_size 50M;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
EOF
  
  ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/bais
  # Disable default Nginx welcome page
  rm -f /etc/nginx/sites-enabled/default
  
  log "Nginx config dibuat: $NGINX_CONF"
else
  log "Nginx config sudah ada: $NGINX_CONF"
  # Pastikan server_name sudah benar
  if ! grep -q "server_name $DOMAIN" "$NGINX_CONF"; then
    warn "server_name di $NGINX_CONF belum cocok dengan $DOMAIN."
    warn "Anda mungkin perlu update manual."
  fi
fi

# Test config
if ! nginx -t; then
  err "Nginx config error! Cek manual: sudo nginx -t"
  exit 1
fi

systemctl reload nginx
log "Nginx config valid & reloaded."

# -----------------------------------------------------------------------------
# 5. ISSUE SSL CERTIFICATE via Certbot
# -----------------------------------------------------------------------------
log "Step 4/6: Issue SSL certificate via Let's Encrypt..."
echo ""

certbot --nginx \
  -d "$DOMAIN" \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  --redirect \
  --hsts \
  --staple-ocsp

log "Certificate berhasil di-issue & auto-redirect HTTP→HTTPS aktif."

# -----------------------------------------------------------------------------
# 6. CEK AUTO-RENEWAL
# -----------------------------------------------------------------------------
log "Step 5/6: Verifikasi auto-renewal..."

systemctl enable certbot.timer
systemctl start certbot.timer

# Dry run renewal (tidak benar-benar renew, hanya simulasi)
certbot renew --dry-run

log "Auto-renewal aktif (cek tiap 12 jam via certbot.timer)."

# -----------------------------------------------------------------------------
# 7. TAMBAHAN: SECURITY HEADERS LANJUTAN
# -----------------------------------------------------------------------------
log "Step 6/6: Tambah security headers extra..."

SSL_SNIPPET="/etc/nginx/snippets/ssl-extra.conf"
cat > "$SSL_SNIPPET" <<'EOF'
# Security headers lanjutan
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# Hide Nginx version
server_tokens off;

# SSL ciphers (modern)
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
EOF

# Include ke server block 443 jika belum
if ! grep -q "include snippets/ssl-extra.conf" "$NGINX_CONF"; then
  # Sisipkan tepat setelah baris listen 443
  sed -i "/listen 443 ssl/a\    include snippets/ssl-extra.conf;" "$NGINX_CONF" || true
fi

nginx -t && systemctl reload nginx
log "Security headers ditambahkan."

# -----------------------------------------------------------------------------
# RINGKASAN
# -----------------------------------------------------------------------------
echo ""
echo "============================================================"
echo -e "${GREEN}  HTTPS / SSL SIAP${NC}"
echo "============================================================"
echo ""
echo " Domain        : https://$DOMAIN"
echo " Cert location : /etc/letsencrypt/live/$DOMAIN/"
echo " Auto-renew    : certbot.timer (tiap 12 jam, renew jika <30 hari)"
echo " HTTP→HTTPS    : redirect otomatis"
echo " HSTS          : aktif (browser paksa HTTPS)"
echo ""
echo " VERIFIKASI:"
echo "   curl -I https://$DOMAIN"
echo "   buka di browser: https://$DOMAIN"
echo ""
echo " UPDATE FRONTEND .env:"
echo "   Pastikan frontend/.env di VPS:"
echo "     REACT_APP_BACKEND_URL=https://$DOMAIN"
echo ""
echo "   Lalu rebuild frontend:"
echo "     cd /path/ke/frontend && yarn build"
echo "     sudo supervisorctl restart bais-frontend"
echo ""
echo " CEK GRADE SSL (opsional):"
echo "   https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
echo "============================================================"
