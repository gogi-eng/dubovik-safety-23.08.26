#!/usr/bin/env python3
import json
import urllib.parse
import urllib.request

queries = [
    ("chemical", "collection:prelinger AND (title:chem* OR title:industr*)"),
    ("kitchen", "collection:prelinger AND title:kitchen"),
]

for label, q in queries:
    print(f"\n=== {label} ===")
    url = (
        "https://archive.org/advancedsearch.php?"
        f"q={urllib.parse.quote(q)}&fl[]=identifier,title&rows=12&output=json"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        docs = json.load(resp)["response"]["docs"]
    for item in docs:
        ident = item["identifier"]
        try:
            with urllib.request.urlopen(
                f"https://archive.org/metadata/{ident}", timeout=20
            ) as resp:
                meta = json.load(resp)
            mp4 = [
                f
                for f in meta.get("files", [])
                if f.get("name", "").lower().endswith(".mp4")
            ]
            mp4.sort(key=lambda f: int(f.get("size", 0)))
            if not mp4:
                continue
            f = mp4[0]
            size_mb = int(f["size"]) / 1024 / 1024
            print(
                ident,
                round(size_mb, 1),
                "MB",
                f.get("length", "?"),
                "s",
                "|",
                item.get("title", "")[:55],
            )
        except Exception as exc:
            print(ident, "ERR", exc)
