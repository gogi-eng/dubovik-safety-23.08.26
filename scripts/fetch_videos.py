#!/usr/bin/env python3
"""Fetch Pixabay CDN URLs from video pages and download clips."""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

VIDEOS = {
    "construction": "https://pixabay.com/videos/buildings-cranes-office-building-151668/",
    "chemical": "https://pixabay.com/videos/factory-industry-industrial-plant-209/",
    "kitchen": "https://pixabay.com/videos/kitchen-restaurant-cooking-416/",
    "store": "https://pixabay.com/videos/supermarket-grocery-store-shopping-40130/",
}

OUT_DIR = Path(__file__).resolve().parent.parent / "videos"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_page(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "ignore")


def find_mp4_urls(html: str) -> list[str]:
    urls = re.findall(r"https://cdn\.pixabay\.com/video/[^\"'\\s>]+\.mp4", html)
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"  saved {dest.name}: {len(data) // 1024} KB")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, page in VIDEOS.items():
        dest = OUT_DIR / f"{name}.mp4"
        if dest.exists() and dest.stat().st_size > 100_000:
            print(f"{name}: already exists ({dest.stat().st_size // 1024} KB)")
            continue
        print(f"{name}: fetching {page}")
        html = fetch_page(page)
        urls = find_mp4_urls(html)
        if not urls:
            print(f"  no CDN URLs found", file=sys.stderr)
            continue
        for candidate in urls:
            print(f"  try {candidate}")
            try:
                download(candidate, dest)
                break
            except Exception as exc:
                print(f"  failed: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
