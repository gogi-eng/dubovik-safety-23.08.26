#!/usr/bin/env bash
# Деплой сайта Dubovik на DigitalOcean (не трогает PRD-BOT)
set -euo pipefail

SITE_ROOT="${1:-/var/www/dubovik}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[1/6] nginx..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx

echo "[2/6] каталог $SITE_ROOT..."
mkdir -p "$SITE_ROOT"
cp "$SRC_DIR/index.html" "$SRC_DIR/styles.css" "$SRC_DIR/i18n.js" "$SRC_DIR/app.js" "$SRC_DIR/contact_api.py" "$SITE_ROOT/"
mkdir -p "$SITE_ROOT/images" "$SITE_ROOT/videos" "$SITE_ROOT/promo"
cp -r "$SRC_DIR/images/"* "$SITE_ROOT/images/"
cp -r "$SRC_DIR/videos/"*.mp4 "$SITE_ROOT/videos/" 2>/dev/null || true
if [[ -d "$SRC_DIR/promo" ]]; then
  cp -r "$SRC_DIR/promo/"* "$SITE_ROOT/promo/"
fi
chmod 644 "$SITE_ROOT"/*.html "$SITE_ROOT"/*.css "$SITE_ROOT"/*.js "$SITE_ROOT"/*.py
chmod 644 "$SITE_ROOT/images/"* 2>/dev/null || true
chmod 644 "$SITE_ROOT/videos/"*.mp4 2>/dev/null || true
chmod 644 "$SITE_ROOT/promo/"* 2>/dev/null || true

if [[ ! -f "$SITE_ROOT/.env" ]]; then
  cp "$SRC_DIR/deploy/.env.example" "$SITE_ROOT/.env"
  echo "Создан $SITE_ROOT/.env — заполните TELEGRAM_* и SMTP_*"
fi
chown root:www-data "$SITE_ROOT/.env"
chmod 640 "$SITE_ROOT/.env"

echo "[3/6] systemd dubovik-contact..."
cp "$SRC_DIR/deploy/dubovik-contact.service" /etc/systemd/system/dubovik-contact.service
systemctl daemon-reload
systemctl enable dubovik-contact
systemctl restart dubovik-contact

echo "[4/6] nginx config..."
cp "$SRC_DIR/deploy/nginx-dubovik.conf" /etc/nginx/sites-available/dubovik
ln -sf /etc/nginx/sites-available/dubovik /etc/nginx/sites-enabled/dubovik
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

echo "[5/6] проверка..."
sleep 1
curl -sf "http://127.0.0.1/" | head -c 80 || true
echo
curl -sf "http://127.0.0.1/api/health" || true
echo

echo "[6/6] готово. Сайт: http://$(curl -sf ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')/"
echo "Форма заработает после заполнения /var/www/dubovik/.env"
