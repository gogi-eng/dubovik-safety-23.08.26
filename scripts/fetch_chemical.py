#!/usr/bin/env python3
"""Download chemical.mp4 from Pexels CDN."""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "videos" / "chemical.mp4"
PAGE = "https://www.pexels.com/video/a-drone-shot-over-the-refinery-by-the-river-4404095/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Known Pexels CDN fallback (refinery / industrial plant)
FALLBACK = "https://videos.pexels.com/video-files/4404095/4404095-uhd_2560_1440_25fps.mp4"


def main() -> None:
    urls: list[str] = []
    try:
        req = urllib.request.Request(PAGE, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
        urls = re.findall(r"https://videos\.pexels\.com/video-files/\d+/\d+[^\"'\\s>]+\.mp4", html)
    except Exception as exc:
        print(f"page fetch failed: {exc}")

    if not urls:
        urls = [FALLBACK]

    for url in urls:
        print(f"try {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if len(data) < 100_000:
                continue
            DEST.write_bytes(data)
            print(f"saved {DEST.name}: {len(data) // 1024} KB")
            return
        except Exception as exc:
            print(f"failed: {exc}")

    raise SystemExit("could not download chemical.mp4")


if __name__ == "__main__":
    main()
