# 🛡️ VPS HARDENING GUIDE — BAIS Summary Geospasika

Panduan langkah-demi-langkah hardening VPS Bapak (`187.77.115.220`). Ikuti **berurutan**. Setiap step bisa dijalankan independent — kalau ada error, stop dan kabari.

> ⚠️ **KRITIS**: Untuk step SSH key (#3), **JANGAN logout dari sesi SSH saat ini**. Buka terminal baru untuk test. Kalau lock-out, gunakan VNC console dari panel VPS Bapak.

---

## 0️⃣ Sebelum Mulai — Backup

```bash
# Backup config penting
sudo mkdir -p /root/hardening-backup
sudo cp /etc/ssh/sshd_config /root/hardening-backup/sshd_config.bak
sudo cp /etc/mongod.conf /root/hardening-backup/mongod.conf.bak 2>/dev/null || true
sudo cp -r /etc/nginx /root/hardening-backup/nginx.bak 2>/dev/null || true
echo "✅ Backup config di /root/hardening-backup/"
```

---

## 1️⃣ UFW Firewall — Buka Hanya Port yang Perlu

```bash
sudo apt update && sudo apt install -y ufw

# Default: deny incoming, allow outgoing
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (sebelum enable!! — kalau tidak, locked out)
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP & HTTPS (untuk aplikasi)
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Aktifkan
sudo ufw --force enable
sudo ufw status verbose
```

✅ Verifikasi: port 8001 (backend) & 27017 (MongoDB) **TIDAK** muncul di `ufw status` — itu artinya hanya bisa diakses dari localhost.

---

## 2️⃣ MongoDB — Localhost Only + Auth Password

### 2a. Bind ke localhost (paling penting!)

```bash
sudo nano /etc/mongod.conf
```

Pastikan bagian `net:` seperti ini:

```yaml
net:
  port: 27017
  bindIp: 127.0.0.1     # ← HANYA localhost (TIDAK 0.0.0.0)

security:
  authorization: enabled
```

### 2b. Bikin admin & app user MongoDB

```bash
# Sementara matikan auth dulu untuk bikin user awal
sudo nano /etc/mongod.conf
# Comment dulu baris "authorization: enabled" → "# authorization: enabled"
sudo systemctl restart mongod
sleep 3

# Connect
mongosh

# Di mongosh:
use admin
db.createUser({user:"mongoadmin", pwd:"PASSWORD_KUAT_DISINI", roles:["root"]})
use bais_summary_db
db.createUser({user:"baisapp", pwd:"PASSWORD_APP_DISINI", roles:["readWrite"]})
exit
```

### 2c. Aktifkan auth & update connection string

```bash
sudo nano /etc/mongod.conf
# Hapus comment di baris "authorization: enabled"
sudo systemctl restart mongod

# Update backend .env
sudo nano /var/www/LaporanKapuas/backend/.env
```

Ubah baris MONGO_URL:
```
MONGO_URL=mongodb://baisapp:PASSWORD_APP_DISINI@127.0.0.1:27017/bais_summary_db?authSource=bais_summary_db
```

```bash
sudo supervisorctl restart bais-backend
sudo supervisorctl status bais-backend
```

✅ Test: `curl http://localhost:8001/api/daily/info -o /dev/null -w "HTTP %{http_code}\n"` → harus 401.

---

## 3️⃣ SSH Hardening — Key-Only Auth (HATI-HATI!)

### 3a. Di LAPTOP Bapak (BUKAN VPS) generate SSH key

```bash
# Mac/Linux:
ssh-keygen -t ed25519 -C "admin-bais-tni" -f ~/.ssh/bais_vps_key

# Windows PowerShell:
ssh-keygen -t ed25519 -C "admin-bais-tni" -f $env:USERPROFILE\.ssh\bais_vps_key
```

Tekan Enter 3x (password opsional, tapi disarankan).

### 3b. Copy public key ke VPS

```bash
# Mac/Linux di laptop Bapak:
ssh-copy-id -i ~/.ssh/bais_vps_key.pub root@187.77.115.220

# Atau manual: copy isi file ~/.ssh/bais_vps_key.pub
# Lalu di VPS:
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_DISINI" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3c. Test login dengan key DULU (di terminal BARU)

```bash
# Di laptop, terminal BARU:
ssh -i ~/.ssh/bais_vps_key root@187.77.115.220
# Harus masuk tanpa minta password
```

⚠️ **JANGAN LANJUT SEBELUM TEST INI BERHASIL!**

### 3d. Setelah key-login berhasil, disable password auth

```bash
# Di VPS:
sudo nano /etc/ssh/sshd_config
```

Ubah/tambahkan:
```
PasswordAuthentication no
PermitRootLogin prohibit-password   # boleh root tapi hanya pakai key
PubkeyAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

```bash
sudo sshd -t       # cek syntax — kalau error, JANGAN restart
sudo systemctl reload ssh
```

✅ Verifikasi dari laptop baru: `ssh -i ~/.ssh/bais_vps_key root@187.77.115.220` masih bisa.
❌ Verifikasi password ditolak: `ssh root@187.77.115.220` (tanpa -i) → harus `Permission denied (publickey)`.

### 🚨 Kalau Lock Out

Bapak punya 2 opsi:
1. **VNC Console** dari panel provider VPS → login langsung, edit `/etc/ssh/sshd_config` revert
2. **Rescue mode** dari panel provider

Itulah kenapa setiap provider VPS punya web console — bukan untuk dipakai harian tapi **safety net**.

---

## 4️⃣ Fail2ban — Auto Ban IP Brute Force

```bash
sudo apt install -y fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

Di bagian `[DEFAULT]`, set:
```ini
bantime  = 1h
findtime = 10m
maxretry = 3
backend  = systemd
```

Aktifkan jail SSH:
```ini
[sshd]
enabled = true
port    = ssh
filter  = sshd
logpath = /var/log/auth.log
maxretry = 3
```

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
```

---

## 5️⃣ Setup Ollama (LLM Lokal — 100% On-Server)

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Service auto-start
sudo systemctl enable ollama
sudo systemctl start ollama
sudo systemctl status ollama | head -5

# Bind ke localhost only (security!)
sudo systemctl edit ollama --full
```

Tambah/ubah di section `[Service]`:
```
Environment="OLLAMA_HOST=127.0.0.1:11434"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama

# Pull model (pilih sesuai RAM VPS)
ollama pull llama3.2:3b      # ~2GB RAM (cepat, ringkasan OK)
# ATAU
ollama pull llama3.2:1b      # ~1GB RAM (kalau VPS Bapak < 4GB)
# ATAU
ollama pull qwen2.5:7b       # ~5GB RAM (kualitas lebih baik untuk B.Indonesia)

# Test
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Sebutkan 3 langkah analisis intelijen militer dalam 2 kalimat.",
  "stream": false
}' | python3 -m json.tool
```

### Hubungkan ke aplikasi
```bash
sudo nano /var/www/LaporanKapuas/backend/.env
```

Tambah:
```
AI_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

```bash
sudo supervisorctl restart bais-backend
```

Test generate PDF dari aplikasi — AI summary sekarang dari Ollama lokal. **Zero data leaves the VPS.**

---

## 6️⃣ Nginx Reverse Proxy — Tambahan Security

Edit nginx site config Bapak (`/etc/nginx/sites-enabled/laporan-kapuas` atau sejenis):

```nginx
server {
    listen 80;
    server_name _;  # ganti dengan domain bila ada

    # Sembunyikan versi nginx
    server_tokens off;

    # Body size limit (cegah upload monster)
    client_max_body_size 25M;

    # Timeout
    client_body_timeout 30s;
    client_header_timeout 10s;
    keepalive_timeout 60s;
    send_timeout 30s;

    # Connection limit per IP (anti-DDoS)
    limit_conn perip 20;
    limit_req zone=mylimit burst=50 nodelay;

    # Frontend static
    location / {
        root /var/www/LaporanKapuas/frontend/build;
        try_files $uri /index.html;
    }

    # API proxy ke backend
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # Block common scanners
    location ~* \.(env|git|sql|bak|swp)$ { deny all; }
}
```

Di `/etc/nginx/nginx.conf` (block `http`), tambah:
```nginx
limit_req_zone $binary_remote_addr zone=mylimit:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=perip:10m;
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 7️⃣ Automatic Security Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Pilih "Yes"
```

---

## 8️⃣ Setup HTTPS (Bila Sudah Punya Domain)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d domain.bapak.com
# Ikuti prompt: email, agree TOS
# Otomatis: update nginx config + sertifikat + auto-renewal cron
```

Setelah HTTPS aktif, edit `backend/.env`:
```
ALLOWED_ORIGINS=https://domain.bapak.com
```

Edit `frontend/.env` di build pipeline:
```
REACT_APP_BACKEND_URL=https://domain.bapak.com
```

```bash
cd /var/www/LaporanKapuas/frontend && yarn build && sudo systemctl reload nginx
sudo supervisorctl restart bais-backend
```

---

## 9️⃣ Manual Backup MongoDB (Kapan Saja Sebelum Deploy)

```bash
TS=$(date +%Y%m%d_%H%M%S)
sudo mkdir -p /backup
sudo mongodump --uri="mongodb://baisapp:PASSWORD@127.0.0.1:27017/bais_summary_db?authSource=bais_summary_db" \
  --out=/backup/mongo_$TS
sudo tar -czf /backup/bais_$TS.tar.gz -C /backup mongo_$TS
sudo rm -rf /backup/mongo_$TS
echo "✅ Backup: /backup/bais_$TS.tar.gz"
```

### Restore
```bash
sudo tar -xzf /backup/bais_20260603_120000.tar.gz -C /tmp
sudo mongorestore --uri="mongodb://..." --drop /tmp/mongo_20260603_120000
```

---

## 🔟 Audit Log (Sudah Built-In)

Login sebagai admin → menu Admin Users (kalau ada UI Audit) atau cek via API:

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@bais.tni.mil.id","password":"Bais2026!"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 50 audit entries terakhir
curl -s http://localhost:8001/api/audit?limit=50 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Audit tercatat untuk: `login_success`, `login_failed`, dst.

---

## ✅ Final Checklist

- [ ] UFW aktif, hanya port 22/80/443 yang dibuka
- [ ] MongoDB bind 127.0.0.1, auth enabled
- [ ] SSH key-only, password disabled
- [ ] Fail2ban aktif untuk SSH
- [ ] Ollama install + AI_PROVIDER=ollama di .env
- [ ] Nginx rate-limit + security headers
- [ ] HTTPS via Let's Encrypt (kalau ada domain)
- [ ] Test login admin masih bisa
- [ ] Test brute-force lock setelah 3x salah
- [ ] Test generate PDF — AI summary dari Ollama, bukan Claude

Selamat — VPS Bapak sudah jauh lebih aman! 🛡️
