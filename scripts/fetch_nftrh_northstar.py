#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import feedparser

OUTDIR = Path("docs/news")
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTJSON = OUTDIR/"news.json"

FEEDS = [
    ("NFTRH", "https://nftrh.com/blog/feed/"),
    ("Northstar", "https://northstarbadcharts.com/feed/"),
]
LOOKBACK_DAYS = 3

UA = {"User-Agent": "Mozilla/5.0 (compatible; MDReportBot/1.0; +https://example.com)"}

def clean_filename(s):
    s = re.sub(r"[^a-zA-Z0-9_.-]+", "_", s.strip())[:80]
    return s or f"img_{int(time.time())}"

def fetch_first_image(url):
    try:
        html = requests.get(url, timeout=20, headers=UA).text
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception:
        return None
    return None

def download(url, dest):
    try:
        r = requests.get(url, timeout=30, headers=UA)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception:
        return False

def load_existing():
    if not OUTJSON.exists():
        return []
    try:
        data = json.loads(OUTJSON.read_text(encoding="utf-8"))
        # Aksepter både list og dict; normaliser til list
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # vanlige nøkler: {"posts":[...]} eller et enkelt-objekt -> putt i list
            if "posts" in data and isinstance(data["posts"], list):
                return data["posts"]
            return [data]
        return []
    except Exception:
        return []

def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    posts=[]
    for source, feed in FEEDS:
        d = feedparser.parse(feed)
        for e in d.entries:
            try:
                published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                published = datetime.now(timezone.utc)
            if published < cutoff:
                continue
            title = e.title
            link  = e.link
            img_url = fetch_first_image(link)
            img_file = None
            if img_url:
                ext = (img_url.split("?")[0].split(".")[-1] or "jpg")
                ext = "jpg" if len(ext) > 5 else ext  # defensivt
                name = clean_filename(f"{source}_{title}") + "." + ext
                dest = OUTDIR/name
                if download(img_url, dest):
                    img_file = f"news/{name}"
            posts.append({
                "source": source,
                "title": title,
                "url": link,
                "published": published.isoformat(),
                "image": img_file
            })

    existing = load_existing()
    merged = posts + existing
    merged.sort(key=lambda x: x.get("published",""), reverse=True)
    merged = merged[:20]
    OUTJSON.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(merged)} posts to {OUTJSON}")

if __name__ == "__main__":
    main()
