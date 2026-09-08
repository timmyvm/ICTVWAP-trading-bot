#!/usr/bin/env bash
# One-shot VPS setup for the v0.10c EMA-bracket paper trader.
#
# On a fresh Ubuntu 22.04/24.04 server, as root:
#   git clone https://github.com/timmyvm/ICTVWAP-trading-bot.git
#   bash ICTVWAP-trading-bot/deploy/vps_setup.sh
#
# Installs python, creates the venv, writes a paper-only .env (no API
# keys — the bot cannot touch real funds), installs a systemd service,
# and starts it. Safe to re-run; an existing .env is left untouched.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"
echo "==> setting up in $REPO_DIR"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-venv python3-pip git

if [ ! -d venv ]; then
    python3 -m venv venv
fi
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cat > .env <<'ENV'
PAPER_TRADE=true
BYBIT_TESTNET=false
STRATEGY=ema_bracket
ENV
    echo "==> wrote .env (paper mode, mainnet market data, ema_bracket strategy)"
else
    echo "==> .env already exists — leaving it untouched"
fi

cat > /etc/systemd/system/powelltrades.service <<UNIT
[Unit]
Description=Powell Trades EMA-bracket paper trader
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$REPO_DIR
ExecStart=$REPO_DIR/venv/bin/python main.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now powelltrades
sleep 3
systemctl --no-pager --full status powelltrades | head -12 || true

echo
echo "==> done. Useful commands:"
echo "    systemctl status powelltrades"
echo "    tail -f $REPO_DIR/logs/bot.log"
echo "    $REPO_DIR/venv/bin/python $REPO_DIR/scripts/paper_stats.py"
