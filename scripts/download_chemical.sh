#!/usr/bin/env bash
set -euo pipefail
DEST="/tmp/chemical.mp4"
URLS=(
  "https://cdn.pixabay.com/video/2016/03/09/209-158912000_1280x720_30fps.mp4"
  "https://cdn.pixabay.com/video/2016/03/09/209-158912000_640x360_30fps.mp4"
  "https://videos.pexels.com/video-files/4404095/4404095-hd_1920_1080_25fps.mp4"
)
for u in "${URLS[@]}"; do
  echo "try $u"
  if curl -fsSL -A "Mozilla/5.0" -o "$DEST" "$u" && [[ $(stat -c%s "$DEST") -gt 100000 ]]; then
    echo "ok $(stat -c%s "$DEST")"
    cp "$DEST" /var/www/dubovik/videos/chemical.mp4
    chmod 644 /var/www/dubovik/videos/chemical.mp4
    exit 0
  fi
done
exit 1
