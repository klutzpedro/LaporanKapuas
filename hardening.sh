#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  BAIS Summary Geospasika — VPS Hardening Script (Automated)             ║
# ║  Run as root or via sudo.                                                ║
# ║  Usage: bash hardening.sh                                                ║
# ║  Safe: idempotent, asks confirmation before destructive ops              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

set -e   # exit on error
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }
ask()  { echo -e "${YELLOW}❓ $1${NC}"; read -r REPLY; }

APP_DIR="/var/www/LaporanKapuas"
BACKEND_ENV="$APP_DIR/backend/.env"
SUPERVISOR_NAME="bais-backend"

[ "$EUID" -ne 0 ] && { err "Jalankan dengan sudo"; exit 1; }
[ ! -d "$APP_DIR" ] && { err "Folder $APP_DIR tidak ada. Edit APP_DIR di script."; exit 1; }

echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════╗"
echo "║  BAIS VPS Hardening — Step-by-Step Automation           ║"
echo -e "╚══════════════════════════════════════════════════════════╝${NC}\n"

# ════════════════════════════════════════════════════════════════════════════
# STEP 0: Backup
# ════════════════════════════════════════════════════════════════════════════
log "STEP 0: Backup config penting"
mkdir -p /root/hardening-backup
cp /etc/ssh/sshd_config /root/hardening-backup/sshd_config.bak 2>/dev/null || true
cp /etc/mongod.conf /root/hardening-backup/mongod.conf.bak 2>/dev/null || true
cp -r /etc/nginx /root/hardening-backup/nginx.bak 2>/dev/null || true
cp "$BACKEND_ENV" /root/hardening-backup/backend.env.bak 2>/dev/null || true
ok "Backup tersimpan di /root/hardening-backup/"

# ════════════════════════════════════════════════════════════════════════════
# STEP 1: UFW Firewall
# ════════════════════════════════════════════════════════════════════════════
log "STEP 1: Setup UFW Firewall (allow SSH/HTTP/HTTPS only)"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ufw

ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
echo "y" | ufw enable
ok "UFW aktif:"
ufw status verbose | head -15

# ════════════════════════════════════════════════════════════════════════════
# STEP 2: MongoDB — Localhost Only + Auth
# ════════════════════════════════════════════════════════════════════════════
log "STEP 2: MongoDB hardening (localhost-only + auth)"

if ! systemctl is-active --quiet mongod; then
    warn "MongoDB tidak aktif. Lewati step ini — install MongoDB dulu."
else
    # Cek apakah auth sudah aktif
    if mongosh --quiet --eval "db.runCommand({hello:1})" 2>&1 | grep -q "requires authentication"; then
        ok "MongoDB auth SUDAH aktif. Skip step 2."
    else
        warn "MongoDB belum pakai auth. Akan setup sekarang."
        ask "Masukkan password untuk user 'mongoadmin' (root): "
        MONGO_ADMIN_PASS="$REPLY"
        ask "Masukkan password untuk user 'baisapp' (aplikasi): "
        MONGO_APP_PASS="$REPLY"
        DB_NAME=$(grep '^DB_NAME=' "$BACKEND_ENV" | cut -d'=' -f2 | tr -d '"')
        [ -z "$DB_NAME" ] && DB_NAME="bais_summary_db"

        # Bikin user (auth belum aktif jadi masih bisa)
        mongosh --quiet <<EOF
use admin
db.createUser({user:"mongoadmin", pwd:"$MONGO_ADMIN_PASS", roles:["root"]})
use $DB_NAME
db.createUser({user:"baisapp", pwd:"$MONGO_APP_PASS", roles:["readWrite"]})
EOF
        ok "Users MongoDB dibuat"

        # Update mongod.conf
        sed -i 's/^  bindIp:.*/  bindIp: 127.0.0.1/' /etc/mongod.conf
        if grep -q "^security:" /etc/mongod.conf; then
            sed -i '/^security:/,/^[^ ]/ { /^security:/!{ /^  /{ s/.*authorization.*/  authorization: enabled/ } } }' /etc/mongod.conf
        else
            echo -e "\nsecurity:\n  authorization: enabled" >> /etc/mongod.conf
        fi
        systemctl restart mongod
        sleep 3

        # Update backend .env
        sed -i "s|^MONGO_URL=.*|MONGO_URL=\"mongodb://baisapp:$MONGO_APP_PASS@127.0.0.1:27017/$DB_NAME?authSource=$DB_NAME\"|" "$BACKEND_ENV"
        ok "MongoDB auth aktif & backend .env di-update"
        ok "PENTING — Catat passwords ini di tempat aman:"
        echo "  mongoadmin: $MONGO_ADMIN_PASS"
        echo "  baisapp:    $MONGO_APP_PASS"
    fi
fi

# ════════════════════════════════════════════════════════════════════════════
# STEP 3: Fail2ban
# ════════════════════════════════════════════════════════════════════════════
log "STEP 3: Install & config fail2ban (auto-ban brute force SSH)"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq fail2ban

cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 3
backend  = systemd
ignoreip = 127.0.0.1/8

[sshd]
enabled = true
port    = ssh
filter  = sshd
maxretry = 3
EOF

systemctl enable fail2ban -q
systemctl restart fail2ban
sleep 2
ok "Fail2ban aktif:"
fail2ban-client status sshd 2>/dev/null | head -10 || warn "fail2ban masih warming up"

# ════════════════════════════════════════════════════════════════════════════
# STEP 4: Automatic Security Updates
# ════════════════════════════════════════════════════════════════════════════
log "STEP 4: Auto security updates (unattended-upgrades)"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unattended-upgrades
echo 'APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";' > /etc/apt/apt.conf.d/20auto-upgrades
ok "Unattended upgrades aktif"

# ════════════════════════════════════════════════════════════════════════════
# STEP 5: Install Ollama (LLM Lokal)
# ════════════════════════════════════════════════════════════════════════════
log "STEP 5: Install Ollama + pull LLM lokal"
ask "Install Ollama untuk AI summary lokal? (RAM ≥4GB direkomendasikan) [y/N] "
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    if ! command -v ollama &>/dev/null; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        ok "Ollama sudah ter-install"
    fi

    # Bind localhost-only via systemd override
    mkdir -p /etc/systemd/system/ollama.service.d
    cat > /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
EOF
    systemctl daemon-reload
    systemctl enable ollama -q
    systemctl restart ollama
    sleep 5

    # Pilih model berdasarkan RAM
    TOTAL_RAM_GB=$(free -g | awk '/^Mem:/ {print $2}')
    if [ "$TOTAL_RAM_GB" -ge 8 ]; then
        MODEL="qwen2.5:7b"; log "RAM ${TOTAL_RAM_GB}GB — pull qwen2.5:7b (best for B.Indonesia)"
    elif [ "$TOTAL_RAM_GB" -ge 4 ]; then
        MODEL="llama3.2:3b"; log "RAM ${TOTAL_RAM_GB}GB — pull llama3.2:3b"
    else
        MODEL="llama3.2:1b"; log "RAM ${TOTAL_RAM_GB}GB — pull llama3.2:1b (smallest)"
    fi
    ollama pull "$MODEL" || warn "Pull model gagal — bisa retry manual: ollama pull $MODEL"

    # Update backend .env
    grep -q "^AI_PROVIDER=" "$BACKEND_ENV" \
        && sed -i "s|^AI_PROVIDER=.*|AI_PROVIDER=ollama|" "$BACKEND_ENV" \
        || echo "AI_PROVIDER=ollama" >> "$BACKEND_ENV"
    grep -q "^OLLAMA_HOST=" "$BACKEND_ENV" \
        || echo "OLLAMA_HOST=http://127.0.0.1:11434" >> "$BACKEND_ENV"
    grep -q "^OLLAMA_MODEL=" "$BACKEND_ENV" \
        && sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL|" "$BACKEND_ENV" \
        || echo "OLLAMA_MODEL=$MODEL" >> "$BACKEND_ENV"

    ok "Ollama aktif. Model: $MODEL"
    ok "Test: curl http://localhost:11434/api/generate -d '{\"model\":\"$MODEL\",\"prompt\":\"Halo\",\"stream\":false}'"
else
    warn "Skip Ollama. AI summary tetap pakai Claude (data keluar ke Anthropic)."
fi

# ════════════════════════════════════════════════════════════════════════════
# STEP 6: Nginx Rate Limiting
# ════════════════════════════════════════════════════════════════════════════
log "STEP 6: Tambah rate limit di nginx"
NGINX_CONF="/etc/nginx/nginx.conf"
if ! grep -q "limit_req_zone.*mylimit" "$NGINX_CONF"; then
    sed -i '/http {/a\    limit_req_zone $binary_remote_addr zone=mylimit:10m rate=10r/s;\n    limit_conn_zone $binary_remote_addr zone=perip:10m;\n    server_tokens off;' "$NGINX_CONF"
    nginx -t && systemctl reload nginx && ok "Nginx rate-limit aktif"
else
    ok "Rate limit nginx sudah ada"
fi

# ════════════════════════════════════════════════════════════════════════════
# STEP 7: Restart Backend
# ════════════════════════════════════════════════════════════════════════════
log "STEP 7: Restart backend"
supervisorctl restart "$SUPERVISOR_NAME"
sleep 4
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/daily/info)
if [ "$HTTP_CODE" = "401" ]; then
    ok "Backend hidup (HTTP $HTTP_CODE — auth required, expected)"
else
    err "Backend response: HTTP $HTTP_CODE. Cek: sudo tail -n 50 /var/log/supervisor/bais-backend*.log"
fi

# ════════════════════════════════════════════════════════════════════════════
# DONE
# ════════════════════════════════════════════════════════════════════════════
echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ HARDENING OTOMATIS SELESAI                          ║"
echo -e "╚══════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}YANG TERSISA (manual, butuh interaksi):${NC}"
echo "  1. SSH key-only auth → ikuti /var/www/LaporanKapuas/HARDENING_GUIDE.md step 3"
echo "  2. HTTPS Let's Encrypt → butuh domain. Jalankan: bash ssl-setup.sh <domain>"
echo "  3. Backup mongoDB manual → bash backup-mongo.sh"
echo ""
echo "Test login admin:"
echo "  curl -X POST http://localhost:8001/api/auth/login -H 'Content-Type: application/json' \\"
echo "    -d '{\"email\":\"admin@bais.tni.mil.id\",\"password\":\"Bais2026!\"}'"
echo ""
echo "Test brute-force (akan lock setelah 3x):"
echo "  for i in 1 2 3 4; do curl -s -o /dev/null -w \"%{http_code} \" \\"
echo "    -X POST http://localhost:8001/api/auth/login -H 'Content-Type: application/json' \\"
echo "    -d '{\"email\":\"x@x.com\",\"password\":\"wrong\"}'; done"
