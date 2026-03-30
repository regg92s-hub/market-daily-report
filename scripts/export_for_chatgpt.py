#!/usr/bin/env python3
# scripts/export_for_chatgpt.py
import json, re, html, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

def load_json(p, default=None):
    fallback = {} if default is None else default
    try:
        raw = Path(p).read_text(encoding="utf-8")
    except Exception:
        return fallback
    if not raw.strip():
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback

def norm(s):
    return re.sub(r"\\s+", " ", s or "").strip()

def absolute_url(u):
    if not u:
        return u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return f"https://regg92s-hub.github.io/market-daily-report/{u.lstrip('/')}"

def charts_from_filelist(filelist):
    out = {}
    for p in filelist:
        fp = str(p)
        if not fp.endswith(".png"):
            continue
        m = re.search(r"(?:^|/)charts/([A-Za-z0-9\-_]+)_(weekly|monthly)_compact\\.png$", fp)
        if not m:
            continue
        ticker, tf = m.group(1), m.group(2)
        out.setdefault(ticker, {})
        out[ticker][tf] = absolute_url(fp)
    return out

def build_feed(index_data, filelist, news):
    charts_map = charts_from_filelist(filelist)
    assets = ((index_data or {}).get("summary") or {}).get("assets") or {}
    categories = ((index_data or {}).get("summary") or {}).get("categories") or []

    category_map = {}
    for cat in categories:
        for instrument_id in cat.get("instrument_ids", []):
            category_map[instrument_id] = {
                "key": cat.get("key"),
                "title": cat.get("title"),
                "description": cat.get("description"),
            }

    tickers = []
    for instrument_id, asset in assets.items():
        monthly = (asset.get("frames") or {}).get("monthly") or {}
        weekly = (asset.get("frames") or {}).get("weekly") or {}
        tickers.append({
            "ticker": instrument_id,
            "display_name": asset.get("display_name"),
            "symbol_label": asset.get("symbol_label"),
            "resolved_symbol": asset.get("resolved_symbol"),
            "category": category_map.get(instrument_id, {}),
            "metrics": {
                "dist_36wma": asset.get("dist_to_36WMA"),
                "dist_36mma": asset.get("dist_to_36MMA"),
                "weekly_rsi14": weekly.get("rsi14"),
                "monthly_rsi14": monthly.get("rsi14"),
                "weekly_macd": weekly.get("macd"),
                "monthly_macd": monthly.get("macd"),
            },
            "charts": {
                "weekly": charts_map.get(instrument_id, {}).get("weekly"),
                "monthly": charts_map.get(instrument_id, {}).get("monthly"),
            },
        })

    news_out = []
    raw_items = []
    if isinstance(news, dict):
        for source, items in news.items():
            if isinstance(items, list):
                for item in items:
                    raw_items.append({**item, "source": item.get("source") or source})
    elif isinstance(news, list):
        raw_items = news

    for item in raw_items:
        title = norm(item.get("title") or item.get("headline"))
        summary = norm(item.get("summary") or item.get("desc") or item.get("description"))
        url = item.get("url") or item.get("link")
        image = item.get("image") or item.get("image_url")
        ts = item.get("ts") or item.get("timestamp") or item.get("published_at") or item.get("published")
        source = item.get("source") or item.get("site") or "news"
        if not title and not url:
            continue
        news_out.append({
            "title": title,
            "summary": summary,
            "url": url,
            "image": image,
            "timestamp": ts,
            "source": source,
        })

    feed = {
        "spec": "chatgpt-feed-v2",
        "generated_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "mirrors": {
            "primary":  "https://raw.githubusercontent.com/regg92s-hub/market-daily-report/gh-pages/chatgpt_feed.json",
            "jsdelivr": "https://cdn.jsdelivr.net/gh/regg92s-hub/market-daily-report@gh-pages/chatgpt_feed.json",
            "pages":    "https://regg92s-hub.github.io/market-daily-report/chatgpt_feed.json",
            "txt":      "https://regg92s-hub.github.io/market-daily-report/chatgpt_feed.txt",
            "html":     "https://regg92s-hub.github.io/market-daily-report/chatgpt_feed.html",
        },
        "tickers": tickers,
        "news": news_out,
    }
    return feed

def write_all(feed):
    DOCS.mkdir(parents=True, exist_ok=True)
    with open(DOCS / "chatgpt_feed.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    with open(DOCS / "chatgpt_feed.txt", "w", encoding="utf-8") as f:
        f.write(json.dumps(feed, ensure_ascii=False))
    pretty = html.escape(json.dumps(feed, ensure_ascii=False, indent=2))
    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>chatgpt_feed</title></head>
<body>
<h1>chatgpt_feed</h1>
<pre id="feed">{pretty}</pre>
</body></html>"""
    with open(DOCS / "chatgpt_feed.html", "w", encoding="utf-8") as f:
        f.write(html_doc)

def main():
    idx = load_json(DOCS / "index.json", default={}) if (DOCS / "index.json").exists() else {}
    fl_path = DOCS / "filelist.json"
    if fl_path.exists():
        fl_raw = load_json(fl_path, default={})
        if isinstance(fl_raw, list):
            filelist = fl_raw
        else:
            filelist = fl_raw.get("charts", fl_raw.get("files", []))
    else:
        filelist = []

    news = {}
    npath = DOCS / "news" / "news.json"
    if npath.exists():
        raw = load_json(npath, default={})
        news = raw

    feed = build_feed(idx, filelist, news)
    write_all(feed)
    print("OK: wrote chatgpt_feed.{json,txt,html}")

if __name__ == "__main__":
    main()
