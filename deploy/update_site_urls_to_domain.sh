#!/usr/bin/env bash
# Заменяет http://207.154.238.178/ на https://ot-pb.by/ в файлах сайта на сервере.
# Запускается автоматически после успешного certbot из setup_ot_pb_domain.sh
#
#   bash deploy/update_site_urls_to_domain.sh          # только показать что изменится
#   bash deploy/update_site_urls_to_domain.sh --apply # применить
#
set -euo pipefail

OLD_URL="http://207.154.238.178/"
NEW_URL="https://ot-pb.by/"
SITE_ROOT="${1:-/var/www/dubovik}"

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
  SITE_ROOT="/var/www/dubovik"
elif [[ "${2:-}" == "--apply" ]]; then
  APPLY=1
fi

FILES=(
  "$SITE_ROOT/index.html"
  "$SITE_ROOT/promo/vizitka-rassylka.html"
  "$SITE_ROOT/promo/rassylka-kontakty-rabota-by.html"
)

echo "Замена: $OLD_URL → $NEW_URL"
echo "Каталог: $SITE_ROOT"
echo ""

CHANGED=0
for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "  пропуск (нет файла): $f"
    continue
  fi
  if grep -q "$OLD_URL" "$f"; then
    CHANGED=1
    echo "  найдено в: $f"
    if [[ $APPLY -eq 1 ]]; then
      sed -i "s|${OLD_URL}|${NEW_URL}|g" "$f"
      echo "    → обновлено"
    fi
  else
    echo "  уже без IP: $f"
  fi
done

if [[ $APPLY -eq 0 ]]; then
  echo ""
  echo "Это пробный прогон. Для применения: bash $0 --apply"
elif [[ $CHANGED -eq 0 ]]; then
  echo "Нечего менять — ссылки уже на домен."
else
  echo ""
  echo "Ссылки обновлены. Перезагрузка nginx не нужна (статические файлы)."
fi
