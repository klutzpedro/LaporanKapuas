#!/usr/bin/env bash
# =============================================================================
#  SCRIPT HARDENING VPS - SUMMARY GEOSPASIKA BAIS TNI
#  Target  : Ubuntu 22.04 / 24.04 LTS
#  Web     : Nginx (port 80, 443)
#  SSH     : Port 22 (password auth tetap aktif - AMAN dari lockout)
#  Mode    : SAFE - tidak akan mengunci Anda keluar dari VPS
# =============================================================================
#
#  CARA PAKAI:
#    1) Login ke VPS sebagai root atau user dengan sudo
#    2) wget atau copy script ini ke VPS, contoh:
#         nano vps-hardening.sh   (paste isi script, lalu Ctrl+O, Enter, Ctrl+X)
#    3) Beri izin eksekusi:
#         chmod +x vps-hardening.sh
#    4) Jalankan:
#         sudo ./vps-hardening.sh
#
# =============================================================================

set -e  # Stop jika ada error

# Warna terminal
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; }

# Pastikan dijalankan sebagai root/sudo
if [ "$EUID" -ne 0 ]; then
  err "Harap jalankan dengan sudo: sudo ./vps-hardening.sh"
  exit 1
fi

echo ""
echo "============================================================"
echo "  HARDENING VPS - BAIS TNI SUMMARY GEOSPASIKA"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------------
# 1. UPDATE SISTEM
# -----------------------------------------------------------------------------
log "Step 1/7: Update sistem & install paket dasar..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y ufw fail2ban unattended-upgrades apt-listchanges \
    curl wget net-tools htop iputils-ping ca-certificates

# -----------------------------------------------------------------------------
# 2. UFW FIREWALL (SSH, HTTP, HTTPS)
# -----------------------------------------------------------------------------
log "Step 2/7: Konfigurasi UFW Firewall..."

# Reset rule lama (aman, default deny incoming, allow outgoing)
ufw --force reset

# Default policy
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (port 22) - PENTING agar tidak ke-lockout
ufw allow 22/tcp comment 'SSH'

# Allow HTTP & HTTPS untuk Nginx
ufw allow 80/tcp  comment 'HTTP Nginx'
ufw allow 443/tcp comment 'HTTPS Nginx'

# Rate limit SSH (max 6 connections / 30 detik per IP)
ufw limit 22/tcp comment 'SSH rate limit'

# Aktifkan UFW
ufw --force enable

ufw status verbose
log "UFW aktif. SSH, HTTP, HTTPS sudah dibuka."

# -----------------------------------------------------------------------------
# 3. FAIL2BAN (Anti brute-force SSH & Nginx)
# -----------------------------------------------------------------------------
log "Step 3/7: Konfigurasi Fail2Ban..."

cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
# Ban IP selama 1 jam setelah 5x gagal dalam 10 menit
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

# IP whitelist (jangan pernah ban diri sendiri / IP lokal)
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled  = true
port     = 22
filter   = sshd
logpath  = %(sshd_log)s
maxretry = 5
bantime  = 2h

[nginx-http-auth]
enabled = true
port    = http,https
logpath = /var/log/nginx/error.log

[nginx-botsearch]
enabled = true
port    = http,https
logpath = /var/log/nginx/access.log
maxretry = 2
EOF

systemctl enable fail2ban
systemctl restart fail2ban
sleep 2
fail2ban-client status
log "Fail2Ban aktif - SSH & Nginx terlindungi dari brute-force."

# -----------------------------------------------------------------------------
# 4. AUTO SECURITY UPDATES
# -----------------------------------------------------------------------------
log "Step 4/7: Aktifkan auto security updates..."

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

# Hanya install patch keamanan, jangan auto upgrade major version
sed -i 's|//\s*"\${distro_id}:\${distro_codename}-security";|"${distro_id}:${distro_codename}-security";|' \
    /etc/apt/apt.conf.d/50unattended-upgrades || true

systemctl enable unattended-upgrades
systemctl restart unattended-upgrades
log "Auto security updates aktif."

# -----------------------------------------------------------------------------
# 5. KERNEL HARDENING (sysctl)
# -----------------------------------------------------------------------------
log "Step 5/7: Kernel hardening (anti DDoS / spoofing)..."

cat > /etc/sysctl.d/99-bais-hardening.conf <<'EOF'
# Anti IP spoofing
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP broadcast (anti smurf attack)
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# Disable IP source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Log suspicious packets (martians)
net.ipv4.conf.all.log_martians = 1

# Protect against TIME-WAIT assassination
net.ipv4.tcp_rfc1337 = 1
EOF

sysctl -p /etc/sysctl.d/99-bais-hardening.conf >/dev/null
log "Kernel hardening diterapkan."

# -----------------------------------------------------------------------------
# 6. SSH HARDENING (TANPA disable password - AMAN)
# -----------------------------------------------------------------------------
log "Step 6/7: SSH hardening (mode AMAN - password tetap aktif)..."

# Backup sshd_config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d-%H%M%S)

# Hardening minimal yang AMAN (tidak akan mengunci Anda):
# - Disable root login langsung (gunakan sudo dari user biasa)
#   --> JIKA Anda hanya punya user root, baris ini akan di-COMMENT agar tidak lockout
# - Disable empty password
# - Set max auth tries

HAS_NON_ROOT_USER=$(awk -F: '($3>=1000)&&($3<65534){print $1}' /etc/passwd | head -n1)

if [ -n "$HAS_NON_ROOT_USER" ]; then
  log "Ditemukan user non-root: $HAS_NON_ROOT_USER. Aman untuk disable root login."
  sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
else
  warn "Hanya ada user root. PermitRootLogin TIDAK di-disable untuk mencegah lockout."
  warn "Buat user baru dulu sebelum disable root login (instruksi di akhir script)."
fi

sed -i 's/^#*PermitEmptyPasswords.*/PermitEmptyPasswords no/' /etc/ssh/sshd_config
sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/^#*ClientAliveInterval.*/ClientAliveInterval 300/' /etc/ssh/sshd_config
sed -i 's/^#*ClientAliveCountMax.*/ClientAliveCountMax 2/' /etc/ssh/sshd_config
sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config

# PASSWORD AUTH SENGAJA TETAP AKTIF agar Anda tidak ke-lockout
# Setelah Anda setup SSH key, baru disable manual (instruksi di akhir)

# Test config sebelum restart
if sshd -t; then
  systemctl restart ssh || systemctl restart sshd
  log "SSH config valid & service di-restart."
else
  err "sshd_config error! Restore backup..."
  cp /etc/ssh/sshd_config.bak.* /etc/ssh/sshd_config
  exit 1
fi

# -----------------------------------------------------------------------------
# 7. DISABLE SERVICE TIDAK DIPAKAI
# -----------------------------------------------------------------------------
log "Step 7/7: Disable service yang tidak diperlukan..."

# Disable service umum yang tidak diperlukan untuk web server
for svc in avahi-daemon cups bluetooth; do
  if systemctl is-enabled "$svc" >/dev/null 2>&1; then
    systemctl disable --now "$svc" 2>/dev/null || true
    log "Disabled: $svc"
  fi
done

# -----------------------------------------------------------------------------
# RINGKASAN & LANGKAH SELANJUTNYA
# -----------------------------------------------------------------------------
echo ""
echo "============================================================"
echo -e "${GREEN}  HARDENING SELESAI - VPS LEBIH AMAN${NC}"
echo "============================================================"
echo ""
echo " Status Layanan:"
ufw status numbered | head -n 15
echo ""
fail2ban-client status sshd 2>/dev/null || true
echo ""
echo "============================================================"
echo -e "${YELLOW}  LANGKAH OPSIONAL (LAKUKAN MANUAL SETELAH INI)${NC}"
echo "============================================================"
echo ""
echo " A. SETUP SSH KEY (sangat direkomendasikan):"
echo "    Di KOMPUTER LOKAL Anda (bukan VPS), jalankan:"
echo "      ssh-keygen -t ed25519 -C \"bais-vps\""
echo "      ssh-copy-id root@IP_VPS_ANDA"
echo ""
echo " B. SETELAH SSH KEY berhasil dipakai login, BARU disable password:"
echo "      sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config"
echo "      sudo systemctl restart ssh"
echo ""
echo " C. BUAT USER NON-ROOT (jika belum ada):"
echo "      adduser deploy"
echo "      usermod -aG sudo deploy"
echo ""
echo " D. CEK FAIL2BAN BERKALA:"
echo "      sudo fail2ban-client status sshd"
echo "      sudo fail2ban-client status nginx-botsearch"
echo ""
echo " E. UNBAN IP (kalau tidak sengaja ke-block):"
echo "      sudo fail2ban-client set sshd unbanip <IP_ADDRESS>"
echo ""
echo " F. CEK FIREWALL:"
echo "      sudo ufw status verbose"
echo ""
echo "============================================================"
echo -e "${GREEN}  Hardening aktif. Aplikasi BAIS Anda lebih terlindungi.${NC}"
echo "============================================================"
