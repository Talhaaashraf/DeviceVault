#!/usr/bin/env bash
# DeviceVault - one-shot production installer for Debian/Ubuntu.
#
# Usage (from the repository root):
#   sudo bash deploy/install.sh
#
# What it does:
#   1. Installs nginx, Python and Node.js (if missing)
#   2. Copies the app to /opt/devicevault and creates a "devicevault" system user
#   3. Creates the backend virtualenv and a .env with a random SECRET_KEY
#   4. Builds the frontend into /opt/devicevault/frontend/dist
#   5. Installs the systemd service and the nginx site, then starts both
set -euo pipefail

APP_DIR=/opt/devicevault
APP_USER=devicevault
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo bash deploy/install.sh" >&2
  exit 1
fi

echo "==> Installing system packages"
apt-get update -y
apt-get install -y nginx python3 python3-venv python3-pip rsync curl
NODE_MAJOR=$(node -p "process.versions.node.split('.')[0]" 2>/dev/null || echo 0)
if (( NODE_MAJOR < 22 )); then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

echo "==> Creating service user and copying files to $APP_DIR"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.git' --exclude 'node_modules' --exclude '.venv' --exclude 'dist' \
  --exclude '*.db' --exclude '.env' \
  "$SRC_DIR"/ "$APP_DIR"/

echo "==> Setting up backend"
cd "$APP_DIR/backend"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt
if [[ ! -f .env ]]; then
  SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
  sed "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" .env.example > .env
  chmod 600 .env
  echo "    Generated backend/.env with a random SECRET_KEY"
fi

echo "==> Building frontend"
cd "$APP_DIR/frontend"
npm ci --no-audit --no-fund
npm run build

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Installing systemd service"
cp "$APP_DIR/deploy/systemd/devicevault.service" /etc/systemd/system/devicevault.service
systemctl daemon-reload
systemctl enable --now devicevault
systemctl restart devicevault

echo "==> Configuring nginx"
cp "$APP_DIR/deploy/nginx/devicevault.conf" /etc/nginx/sites-available/devicevault
ln -sf /etc/nginx/sites-available/devicevault /etc/nginx/sites-enabled/devicevault
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo
echo "DeviceVault is running at http://$(hostname -I | awk '{print $1}')/"
echo "Default login: admin@company.com / Admin123!  (change it after first sign-in)"
