#!/usr/bin/env bash
# =============================================================================
#  SCRIPT INSTALL OLLAMA + QWEN2.5:7B - BAIS TNI SUMMARY GEOSPASIKA
#  Target  : Ubuntu 22.04 / 24.04 LTS
#  Purpose : AI Summary 100% on-server (data tidak keluar ke API publik)
#  RAM     : Minimum 8 GB (model qwen2.5:7b butuh ±5-6 GB saat inference)
# =============================================================================
#
#  CARA PAKAI:
#    sudo ./vps-ollama-setup.sh
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
  err "Jalankan dengan sudo: sudo ./vps-ollama-setup.sh"
  exit 1
fi

echo ""
echo "============================================================"
echo "  INSTALL OLLAMA + QWEN2.5:7B"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------------
# 1. CEK SPESIFIKASI VPS
# -----------------------------------------------------------------------------
log "Step 1/6: Cek spesifikasi VPS..."

TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
TOTAL_DISK_GB=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}')
CPU_CORES=$(nproc)

echo "  RAM     : ${TOTAL_RAM_GB} GB"
echo "  CPU     : ${CPU_CORES} cores"
echo "  Disk free: ${TOTAL_DISK_GB} GB"

if [ "$TOTAL_RAM_GB" -lt 6 ]; then
  warn "RAM kurang dari 6 GB. Model qwen2.5:7b kemungkinan akan lambat/OOM."
  warn "Disarankan pakai model lebih kecil: llama3.2:3b (butuh ±3 GB RAM)"
  read -p "Lanjut tetap pakai qwen2.5:7b? (y/N): " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    MODEL="llama3.2:3b"
    log "Akan pakai model: $MODEL"
  else
    MODEL="qwen2.5:7b"
  fi
else
  MODEL="qwen2.5:7b"
fi

if [ "$TOTAL_DISK_GB" -lt 10 ]; then
  err "Disk free < 10 GB. Model butuh ±5 GB. Bersihkan disk dulu."
  exit 1
fi

# -----------------------------------------------------------------------------
# 2. INSTALL OLLAMA (official script)
# -----------------------------------------------------------------------------
log "Step 2/6: Install Ollama..."

if command -v ollama >/dev/null 2>&1; then
  log "Ollama sudah ter-install: $(ollama --version 2>&1 | head -n1)"
else
  curl -fsSL https://ollama.com/install.sh | sh
  log "Ollama ter-install."
fi

# -----------------------------------------------------------------------------
# 3. KONFIGURASI OLLAMA - BIND 127.0.0.1 SAJA (security)
# -----------------------------------------------------------------------------
log "Step 3/6: Konfigurasi Ollama bind ke localhost saja..."

# Pastikan service file ada
SERVICE_FILE="/etc/systemd/system/ollama.service"
if [ ! -f "$SERVICE_FILE" ]; then
  err "File $SERVICE_FILE tidak ditemukan. Install Ollama gagal?"
  exit 1
fi

# Tambahkan Environment OLLAMA_HOST=127.0.0.1:11434 (anti-akses publik)
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_KEEP_ALIVE=10m"
Environment="OLLAMA_NUM_PARALLEL=2"
EOF

systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama

sleep 5
if systemctl is-active --quiet ollama; then
  log "Ollama service aktif di 127.0.0.1:11434"
else
  err "Ollama gagal start. Cek: journalctl -u ollama -n 50"
  exit 1
fi

# -----------------------------------------------------------------------------
# 4. PULL MODEL
# -----------------------------------------------------------------------------
log "Step 4/6: Download model $MODEL (ini bisa 5-15 menit, sabar ya)..."
echo ""
ollama pull "$MODEL"
echo ""
log "Model $MODEL berhasil di-download."

# Tampilkan list model
echo ""
echo "Model tersedia di VPS:"
ollama list
echo ""

# -----------------------------------------------------------------------------
# 5. TEST MODEL
# -----------------------------------------------------------------------------
log "Step 5/6: Test model dengan prompt sederhana..."
echo ""
TEST_OUTPUT=$(curl -s http://127.0.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"Jawab dalam 1 kalimat: apa itu intelijen geospasial?\",\"stream\":false}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','NO RESPONSE')[:300])" 2>/dev/null || echo "TEST FAILED")

echo "Output Ollama:"
echo "  $TEST_OUTPUT"
echo ""

# -----------------------------------------------------------------------------
# 6. UPDATE BACKEND .env
# -----------------------------------------------------------------------------
log "Step 6/6: Update backend .env..."

# Cari folder backend
BACKEND_ENV=""
for candidate in /root/SUMMARY_GEOSPASIKA_BAIS_TNI/backend/.env \
                 /root/bais/backend/.env \
                 /opt/bais/backend/.env \
                 /home/*/SUMMARY_GEOSPASIKA_BAIS_TNI/backend/.env \
                 /app/backend/.env; do
  if [ -f "$candidate" ]; then
    BACKEND_ENV="$candidate"
    break
  fi
done

if [ -z "$BACKEND_ENV" ]; then
  warn "Backend .env tidak ditemukan otomatis."
  warn "Tambahkan manual ke backend/.env Anda:"
  echo ""
  echo "    AI_PROVIDER=ollama"
  echo "    OLLAMA_HOST=http://127.0.0.1:11434"
  echo "    OLLAMA_MODEL=$MODEL"
  echo ""
else
  log "Backend .env ditemukan: $BACKEND_ENV"
  
  # Backup
  cp "$BACKEND_ENV" "${BACKEND_ENV}.bak.$(date +%Y%m%d-%H%M%S)"
  
  # Update / tambah variable
  for KEY_VAL in "AI_PROVIDER=ollama" "OLLAMA_HOST=http://127.0.0.1:11434" "OLLAMA_MODEL=$MODEL"; do
    KEY="${KEY_VAL%%=*}"
    if grep -q "^${KEY}=" "$BACKEND_ENV"; then
      sed -i "s|^${KEY}=.*|${KEY_VAL}|" "$BACKEND_ENV"
    else
      echo "$KEY_VAL" >> "$BACKEND_ENV"
    fi
  done
  
  log "Backend .env updated. Restart backend untuk apply:"
  echo "    sudo supervisorctl restart bais-backend"
fi

# -----------------------------------------------------------------------------
# RINGKASAN
# -----------------------------------------------------------------------------
echo ""
echo "============================================================"
echo -e "${GREEN}  OLLAMA SIAP DIGUNAKAN${NC}"
echo "============================================================"
echo ""
echo " Service     : ollama.service (enabled, auto-start saat boot)"
echo " Listen      : 127.0.0.1:11434 (localhost only, tidak ekspos publik)"
echo " Model       : $MODEL"
echo " Backend     : AI_PROVIDER=ollama"
echo ""
echo " PERINTAH BERGUNA:"
echo "   ollama list                          # lihat model tersedia"
echo "   ollama ps                            # lihat model yang loaded"
echo "   ollama pull <model>                  # download model baru"
echo "   systemctl status ollama              # cek service"
echo "   journalctl -u ollama -f              # tail log"
echo ""
echo " LANGKAH SELANJUTNYA:"
echo "   1. sudo supervisorctl restart bais-backend"
echo "   2. Coba generate PDF dari aplikasi - AI summary sekarang lokal"
echo "   3. Cek log backend untuk konfirmasi:"
echo "      sudo tail -f /var/log/supervisor/bais-backend*.log"
echo ""
echo "============================================================"
