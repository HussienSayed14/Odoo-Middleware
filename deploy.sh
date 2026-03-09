#!/bin/bash
# deploy.sh — run this on your Ubuntu server
# Assumes code is already cloned at /root/Odoo-Middleware
# Usage: bash deploy.sh

set -e

APP_DIR="/root/Odoo-Middleware"
SERVICE_NAME="odoo-middleware"

echo "==> Moving to app directory"
cd $APP_DIR

echo "==> Setting up Python virtual environment"
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Creating systemd service"
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Odoo Middleware FastAPI App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME
EnvironmentFile=$APP_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

echo "==> Reloading systemd and enabling service"
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo ""
echo "✅ Done! Service is running."
echo ""
echo "Useful commands:"
echo "  systemctl status $SERVICE_NAME        # check if running"
echo "  systemctl restart $SERVICE_NAME       # restart after code changes"
echo "  systemctl stop $SERVICE_NAME          # stop"
echo "  journalctl -u $SERVICE_NAME -f        # live logs"
echo "  journalctl -u $SERVICE_NAME -n 100    # last 100 lines"