#!/usr/bin/env bash
# Настройка домена ot-pb.by для сайта Дубовик (не трогает PRD-BOT / trading_bot)
#
# Использование:
#   bash deploy/setup_ot_pb_domain.sh --nginx-only     # до пропагации DNS (certbot пропускаем)
#   bash deploy/setup_ot_pb_domain.sh --https          # когда DNS уже указывает на сервер
#   bash deploy/setup_ot_pb_domain.sh                  # то же что --https
#
# DNS у регистратора (hoster.by / active.by):
#   A  @   → 207.154.238.178
#   A  www → 207.154.238.178
#
set -euo pipefail

DOMAIN="ot-pb.by"
WWW="www.${DOMAIN}"
SERVER_IP="207.154.238.178"
SITE_ROOT="/var/www/dubovik"
EMAIL="${CERTBOT_EMAIL:-admin@${DOMAIN}}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-}"

if [[ "$MODE" != "--nginx-only" && "$MODE" != "--https" && "$MODE" != "" ]]; then
  echo "Неизвестный аргумент: $MODE"
  echo "Использование: $0 [--nginx-only | --https]"
  exit 1
fi

if [[ "$MODE" == "" ]]; then
  MODE="--https"
fi

echo "=== ot-pb.by setup (mode: $MODE) ==="
echo "Сайт: $SITE_ROOT"
echo "Не трогаем: trading_bot, telegram_signal_agent, PRD-BOT-ALL, AGENT-WORLD"

export DEBIAN_FRONTEND=noninteractive

echo "[1/5] Пакеты nginx + certbot..."
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx

if [[ ! -d "$SITE_ROOT" ]]; then
  echo "ОШИБКА: каталог $SITE_ROOT не найден. Сначала: bash scripts/deploy_dubovik_site.sh"
  exit 1
fi

echo "[2/5] Копируем nginx config ot-pb-by..."
cp "$SCRIPT_DIR/nginx-ot-pb-by.conf" /etc/nginx/sites-available/ot-pb-by
ln -sf /etc/nginx/sites-available/ot-pb-by /etc/nginx/sites-enabled/ot-pb-by

echo "[3/5] Проверка nginx..."
nginx -t
systemctl enable nginx
systemctl reload nginx

echo "[4/5] Проверка DNS (необязательно)..."
RESOLVED="$(getent ahosts "$DOMAIN" 2>/dev/null | awk '/STREAM/ {print $1; exit}' || true)"
if [[ -n "$RESOLVED" ]]; then
  echo "  $DOMAIN → $RESOLVED"
  if [[ "$RESOLVED" != "$SERVER_IP" ]]; then
    echo "  ВНИМАНИЕ: DNS пока не на $SERVER_IP — certbot может не сработать."
  fi
else
  echo "  $DOMAIN пока не резолвится — это нормально до настройки DNS у регистратора."
fi

if [[ "$MODE" == "--nginx-only" ]]; then
  echo "[5/5] Режим --nginx-only: certbot пропущен."
  echo ""
  echo "Готово (HTTP по IP как раньше + nginx ждёт домен)."
  echo "Когда DNS заработает, запустите:"
  echo "  bash $SCRIPT_DIR/setup_ot_pb_domain.sh --https"
  exit 0
fi

echo "[5/5] Certbot HTTPS для $DOMAIN и $WWW..."
set +e
certbot --nginx \
  -d "$DOMAIN" \
  -d "$WWW" \
  --non-interactive \
  --agree-tos \
  -m "$EMAIL" \
  --redirect
CERTBOT_RC=$?
set -e

nginx -t
systemctl reload nginx

if [[ $CERTBOT_RC -ne 0 ]]; then
  echo ""
  echo "Certbot не смог выпустить сертификат (обычно DNS ещё не обновился)."
  echo "Проверьте A-записи @ и www → $SERVER_IP, подождите 15–60 мин и снова:"
  echo "  bash $SCRIPT_DIR/setup_ot_pb_domain.sh --https"
  exit 1
fi

echo ""
echo "HTTPS готов. Обновляем ссылки на сайте..."
bash "$SCRIPT_DIR/update_site_urls_to_domain.sh" --apply

echo ""
echo "=== Готово ==="
echo "  https://${DOMAIN}/"
echo "  https://${WWW}/"
echo "Проверка: curl -sI https://${DOMAIN}/ | head -5"
