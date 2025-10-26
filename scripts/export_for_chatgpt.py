#!/usr/bin/env python3
# scripts/export_for_chatgpt.py
import json, os, sys, re, html, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHARTS = DOCS / "charts"

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

def pick_best_chart(chart_dict):
    # chart_dict kan ha keys: best, daily, weekly, monthly, hourly
    if not isinstance(chart_dict, dict):
        return None
    for key in ("best","daily","weekly","monthly","hourly"):
        if chart_dict.get(key):
            return chart_dict[key]
    return None

def absolute_url(u):
    # Hvis filsti er relativ i filelist/index – gjør den absolutt under Pages-roten
    if not u: return u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    # standard base = GitHub Pages-rot
    return f"https://regg92s-hub.github.io/market-daily-report/{u.lstrip('/')}"
    
def charts_from_filelist(filelist):
    # Returner {ticker: {"daily":url, "weekly":url, "monthly":url, "hourly":url, "best":url}}
    out = {}
    for p in filelist:
        fp = str(p)
        if not fp.endswith(".png"):
            continue
        # matcher <TICKER>_<tf>_compact.png
        m = re.search(r"/charts/([A-Za-z0-9\-\_]+)_(hourly|daily|weekly|monthly)_compact\.png$", fp)
        if not m:
            continue
        ticker, tf = m.group(1), m.group(2)
        out.setdefault(ticker, {})
        out[ticker][tf] = absolute_url(fp)
    # velg best etter prioritetsrekkefølge
    for t, d in out.items():
        for k in ("daily","weekly","monthly","hourly"):
            if d.get(k):
                d["best"] = d.get("best") or d[k]
    return out

def coalesce_metric(d, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def build_feed(index_data, filelist, news):
    charts_map = charts_from_filelist(filelist if isinstance(filelist, list) else filelist.get("files", []))
    tickers = []

    wanted = [
        "GLD","SLV","USO","ETH-USD","BTC-USD","URNM","GDX","GDXJ","SIL","SILJ",
        "ACWI","SPY","DTWEXM","VIXCLS","HYG","LQD","DGS10","DGS3MO","DGS2","2s10s"
    ]
    # index.json antas å ha per-ticker metadata
    for tkr in wanted:
        md = (index_data.get("tickers", {}).get(tkr) 
              if isinstance(index_data, dict) else None) or {}
        ch = charts_map.get(tkr, {})
        metrics = {
            "last":            coalesce_metric(md, "last","close","price"),
            "h52":             coalesce_metric(md, "h52","high52","high_52w"),
            "l52":             coalesce_metric(md, "l52","low52","low_52w"),
            "dist_36wma":      coalesce_metric(md, "dist_36wma","dist_to_36wma","dist_to_36WMA"),
            "dist_36mma":      coalesce_metric(md, "dist_36mma","dist_to_36mma","dist_to_36MMA"),
            "rsi14":           coalesce_metric(md, "rsi14","RSI14","rsi"),
            "macd_line":       coalesce_metric(md, "macd_line","macd"),
            "macd_signal":     coalesce_metric(md, "macd_signal","macdSig","macd_signal_line"),
            "macd_hist":       coalesce_metric(md, "macd_hist","macdHist","macd_histogram"),
            "weekly_above_36w":coalesce_metric(md, "weekly_above_36w","weekly_close_above_36wma_weeks"),
        }
        charts = {
            "best":   ch.get("best"),
            "daily":  ch.get("daily"),
            "weekly": ch.get("weekly"),
            "monthly":ch.get("monthly"),
            "hourly": ch.get("hourly"),
        }
        tickers.append({"ticker": tkr, "metrics": metrics, "charts": charts})

    # normaliser nyheter til en flat liste med (title, summary, url, image, ts, source)
    news_out = []
    items = news.get("items", news if isinstance(news, list) else [])
    for item in items:
        title = norm(item.get("title") or item.get("headline"))
        summary = norm(item.get("summary") or item.get("desc") or item.get("description"))
        url = item.get("url") or item.get("link")
        image = item.get("image") or item.get("image_url")
        ts = item.get("ts") or item.get("timestamp") or item.get("published_at")
        source = item.get("source") or item.get("site") or "news"
        if not title and not url:
            continue
        news_out.append({
            "title": title, "summary": summary, "url": url, "image": image, 
            "timestamp": ts, "source": source
        })

    feed = {
        "spec": "chatgpt-feed-v1",
        "generated_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
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
    # JSON
    with open(DOCS/"chatgpt_feed.json","w",encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    # TXT (ren JSON som tekst, lett å lese via nettleser)
    with open(DOCS/"chatgpt_feed.txt","w",encoding="utf-8") as f:
        f.write(json.dumps(feed, ensure_ascii=False))
    # HTML med <pre> – veldig stabilt å hente
    pretty = html.escape(json.dumps(feed, ensure_ascii=False, indent=2))
    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>chatgpt_feed</title></head>
<body>
<h1>chatgpt_feed (v1)</h1>
<pre id="feed">{pretty}</pre>
</body></html>"""
    with open(DOCS/"chatgpt_feed.html","w",encoding="utf-8") as f:
        f.write(html_doc)

def main():
    idx = load_json(DOCS/"index.json") if (DOCS/"index.json").exists() else {}
    # filelist kan være enten en liste av stier eller {"files":[...]}
    fl_path = (DOCS/"filelist.json")
    if fl_path.exists():
        fl_raw = load_json(fl_path)
        filelist = fl_raw.get("files", fl_raw)  # støtt begge format
    else:
        filelist = []
    # nyheter kan komme som liste eller {"items":[...]}
    news = {}
    npath = DOCS/"news"/"news.json"
    if npath.exists():
        raw = load_json(npath)
        news = raw if isinstance(raw, dict) else {"items": raw}
    feed = build_feed(idx, filelist, news)
    write_all(feed)
    print("OK: wrote chatgpt_feed.{json,txt,html}")

if __name__ == "__main__":
    main()
