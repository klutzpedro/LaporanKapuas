#!/bin/bash
# SSH Key-Only Authentication Setup (SAFE — won't lock you out)
# Run AS ROOT on VPS
set -e
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

[ "$EUID" -ne 0 ] && { echo "Jalankan dengan sudo"; exit 1; }

cat <<EOF
${BLUE}╔══════════════════════════════════════════════════════════╗
║  SSH Key-Only Setup — SAFE Workflow                      ║
╚══════════════════════════════════════════════════════════╝${NC}

Workflow:
  1. Bapak generate SSH key di LAPTOP/PC Bapak.
  2. Copy isi file PUBLIC KEY (.pub) ke prompt di bawah.
  3. Script test login key dulu sebelum disable password.

${YELLOW}STEP 1 — Di laptop/PC Bapak, jalankan:${NC}
  Mac/Linux:  ssh-keygen -t ed25519 -C "admin-bais" -f ~/.ssh/bais_vps_key
  Windows:    ssh-keygen -t ed25519 -C "admin-bais" -f \$env:USERPROFILE\.ssh\bais_vps_key

  Tekan Enter beberapa kali (password opsional tapi disarankan).

${YELLOW}STEP 2 — Tampilkan public key di laptop Bapak:${NC}
  Mac/Linux:  cat ~/.ssh/bais_vps_key.pub
  Windows:    type \$env:USERPROFILE\.ssh\bais_vps_key.pub

  Copy SEMUA isi (mulai dari "ssh-ed25519 AAAA...").

EOF

read -p "Paste public key di sini, lalu tekan Enter: " PUBKEY
[ -z "$PUBKEY" ] && { echo "Public key kosong. Batal."; exit 1; }
[[ ! "$PUBKEY" =~ ^ssh- ]] && { echo "Format public key tidak valid (harus mulai dengan 'ssh-')"; exit 1; }

# Install key
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Avoid duplicate
if grep -qF "$PUBKEY" ~/.ssh/authorized_keys; then
    echo -e "${YELLOW}Public key sudah ada di authorized_keys.${NC}"
else
    echo "$PUBKEY" >> ~/.ssh/authorized_keys
    echo -e "${GREEN}✅ Public key terinstall.${NC}"
fi

cat <<EOF

${YELLOW}STEP 3 — TEST LOGIN DENGAN KEY (di terminal BARU di laptop):${NC}
  ssh -i ~/.ssh/bais_vps_key root@$(hostname -I | awk '{print $1}')

${RED}WAJIB: berhasil login tanpa minta password dulu sebelum lanjut!${NC}

EOF

read -p "Sudah berhasil login dengan key di terminal baru? [y/N] " REPLY
if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
    echo "Batal — silakan test login dengan key dulu, lalu jalankan script ini lagi."
    exit 0
fi

# Disable password auth
echo "Backup sshd_config → /root/hardening-backup/sshd_config.before_keyonly"
cp /etc/ssh/sshd_config /root/hardening-backup/sshd_config.before_keyonly

# Set safe defaults
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config

# Append safety settings if missing
grep -q "^ClientAliveInterval" /etc/ssh/sshd_config || echo "ClientAliveInterval 300" >> /etc/ssh/sshd_config
grep -q "^ClientAliveCountMax" /etc/ssh/sshd_config || echo "ClientAliveCountMax 2" >> /etc/ssh/sshd_config

# Validate
if sshd -t 2>&1; then
    systemctl reload ssh
    echo -e "${GREEN}✅ SSH key-only AKTIF.${NC}"
    echo ""
    echo "Verifikasi:"
    echo "  ssh -i ~/.ssh/bais_vps_key root@$(hostname -I | awk '{print $1}')   → harus berhasil"
    echo "  ssh root@$(hostname -I | awk '{print $1}')                            → harus DITOLAK"
    echo ""
    echo -e "${YELLOW}⚠️  JANGAN logout dari session ini sampai test verifikasi di atas berhasil.${NC}"
    echo "Kalau lock-out, gunakan VNC console dari panel VPS, edit /etc/ssh/sshd_config:"
    echo "  PasswordAuthentication yes → lalu systemctl reload ssh"
else
    echo -e "${RED}❌ sshd config error! Revert:${NC}"
    cp /root/hardening-backup/sshd_config.before_keyonly /etc/ssh/sshd_config
    systemctl reload ssh
fi
