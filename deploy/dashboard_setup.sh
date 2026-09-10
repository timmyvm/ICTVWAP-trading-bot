#!/usr/bin/env bash
# One-shot setup for the web dashboard (scripts/dashboard.py).
#   bash ICTVWAP-trading-bot/deploy/dashboard_setup.sh
# Generates DASHBOARD_TOKEN if missing, installs a systemd service,
# opens the firewall port if ufw is active, and prints your URL.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"
PORT="${DASHBOARD_PORT:-8080}"

touch .env
if ! grep -q "^DASHBOARD_TOKEN=" .env; then
    TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
    echo "DASHBOARD_TOKEN=$TOKEN" >> .env
    echo "==> generated DASHBOARD_TOKEN"
else
    TOKEN="$(grep "^DASHBOARD_TOKEN=" .env | cut -d= -f2)"
    echo "==> using existing DASHBOARD_TOKEN"
fi

cat > /etc/systemd/system/powelltrades-dash.service <<UNIT
[Unit]
Description=Powell Trades paper-trading dashboard
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$REPO_DIR
ExecStart=$REPO_DIR/venv/bin/python scripts/dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now powelltrades-dash

if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow "$PORT"/tcp
    echo "==> opened port $PORT in ufw"
fi

IP="$(curl -s --max-time 10 https://api.ipify.org || hostname -I | awk '{print $1}')"
sleep 2
systemctl --no-pager status powelltrades-dash | head -5 || true
echo
echo "==> your dashboard:"
echo "    http://$IP:$PORT/?token=$TOKEN"
echo "    (bookmark it — the token is the password)"
