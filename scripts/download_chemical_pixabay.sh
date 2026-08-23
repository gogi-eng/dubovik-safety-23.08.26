#!/usr/bin/env bash
set -euo pipefail
PAGE="https://pixabay.com/videos/factory-industry-industrial-plant-209/"
HTML=$(curl -fsSL -A "Mozilla/5.0" "$PAGE" || true)
echo "$HTML" | grep -oE 'https://cdn\.pixabay\.com/video/[^"'\'' ]+\.mp4' | sort -u | head -5
for u in $(echo "$HTML" | grep -oE 'https://cdn\.pixabay\.com/video/[^"'\'' ]+\.mp4' | sort -u); do
  echo "try $u"
  if curl -fsSL -A "Mozilla/5.0" -o /var/www/dubovik/videos/chemical.mp4 "$u"; then
    chmod 644 /var/www/dubovik/videos/chemical.mp4
    ls -la /var/www/dubovik/videos/chemical.mp4
    exit 0
  fi
done
exit 1
