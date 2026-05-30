#!/bin/bash
# =========================================================================
# BAIS GEOSPASIKA - DEPLOY SCRIPT (Step 9 → 16)
# Run on fresh VPS after: Step 0-8 done (Python 3.11, Node 20, MongoDB,
# Nginx, Supervisor installed; repo cloned to /var/www/LaporanKapuas;
# venv already created at backend/venv)
# =========================================================================
set -e

APP_DIR="/var/www/LaporanKapuas"
VPS_IP="187.77.115.220"
LLM_KEY="${EMERGENT_LLM_KEY:-sk-emergent-266Fc0dDb2eFeE63a4}"

echo "🔧 [9/16] Fix requirements.txt litellm URL..."
cd "$APP_DIR/backend"
source venv/bin/activate
sed -i 's|^litellm @ https://customer-assets\.emergentagent\.com.*|litellm==1.80.0|' requirements.txt
echo "  litellm: $(grep litellm requirements.txt)"

echo "🐍 [9/16] Install Python dependencies..."
pip install --upgrade pip wheel
pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
deactivate

echo "🔐 [10/16] Write backend .env..."
cat > "$APP_DIR/backend/.env" <<EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=bais_geospasika
EMERGENT_LLM_KEY=$LLM_KEY
EOF
chmod 600 "$APP_DIR/backend/.env"

echo "🎨 [11/16] Build frontend..."
cd "$APP_DIR/frontend"
cat > .env <<EOF
REACT_APP_BACKEND_URL=http://$VPS_IP
EOF
yarn install
yarn build

echo "⚙️  [12/16] Setup supervisor for backend..."
cat > /etc/supervisor/conf.d/bais-backend.conf <<'EOF'
[program:bais-backend]
command=/var/www/LaporanKapuas/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001 --workers 2
directory=/var/www/LaporanKapuas/backend
user=root
autostart=true
autorestart=true
stdout_logfile=/var/log/bais-backend.out.log
stderr_logfile=/var/log/bais-backend.err.log
environment=PATH="/var/www/LaporanKapuas/backend/venv/bin:/usr/bin:/bin"
EOF
supervisorctl reread
supervisorctl update
sleep 3

echo "🧪 [13/16] Test backend (local)..."
curl -fsS http://localhost:8001/api/ || { echo "❌ Backend failed!"; tail -50 /var/log/bais-backend.err.log; exit 1; }
echo ""

echo "🌐 [14/16] Setup Nginx reverse proxy..."
cat > /etc/nginx/sites-available/bais <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 50M;

    root /var/www/LaporanKapuas/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2?|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
ln -sf /etc/nginx/sites-available/bais /etc/nginx/sites-enabled/bais
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "✅ [15/16] Final verification..."
echo "  MongoDB: $(systemctl is-active mongod)"
echo "  Nginx:   $(systemctl is-active nginx)"
echo "  Backend: $(supervisorctl status bais-backend | awk '{print $2}')"
echo ""
echo "  Curl via Nginx:"
curl -fsS http://$VPS_IP/api/ && echo ""

echo ""
echo "=========================================================================="
echo "🎉 DEPLOY SUCCESS! Open browser: http://$VPS_IP"
echo "=========================================================================="
echo ""
echo "Default login accounts:"
echo "  Admin     : admin@bais.tni.mil.id / Bais2026!"
echo "  Piket     : piket@bais.tni.mil.id / Piket2026!"
echo "  Tim LID   : lid@bais.tni.mil.id / Lid2026!"
echo "  Tim KONTRA: kontra@bais.tni.mil.id / Kontra2026!"
echo "  Tim GAL   : gal@bais.tni.mil.id / Gal2026!"
echo "  Tim MEDMON: medmon@bais.tni.mil.id / Medmon2026!"
echo "  Tim GEOINT: geoint@bais.tni.mil.id / Geoint2026!"
echo ""
echo "⚠️  IMPORTANT POST-DEPLOY:"
echo "  1. Change VPS root password (passwd)"
echo "  2. Regenerate Emergent LLM Key in dashboard"
echo "  3. Update: $APP_DIR/backend/.env (line EMERGENT_LLM_KEY)"
echo "  4. Restart backend: supervisorctl restart bais-backend"
echo "=========================================================================="
