#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eksporterer docs/chatgpt_feed.json i et robust format selv om index.json kun har 'summary'
(fred/yields/notes/market_temp) og ikke 'summary.assets'.
"""
import os, sys, json, re, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from lib_net import (
    build_session, fetch_first_ok, choose_first_available_png,
    normalize_title, normalize_url, dedup_news
)

PAGES = Path("docs")
INDEX = PAGES / "index.json"
NEWS  = PAGES / "news" / "news.json"
FILELIST = PAGES / "filelist.json"
INDEX_HTML = PAGES / "index.html"
OUT_FEED = PAGES / "chatgpt_feed.json"

RAW_BASE = "https://raw.githubusercontent.com/regg92s-hub/market-daily-report/gh-pages"
JSD_BASE = "https://cdn.jsdelivr.net/gh/regg92s-hub/market-daily-report@gh-pages"
PAG_BASE = "https://regg92s-hub.github.io/market-daily-report"

RUN_TAG = os.environ.get("RUN_ID") or dt.datetime.utcnow().isoformat(timespec="seconds")+"Z"
OSLO = ZoneInfo("Europe/Oslo")

# ---------- helpers ----------
def _log(msg: str): print(f"[export] {msg}", flush=True)

def _read_json(path: Path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def _is_html_head(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8")[:300].strip().lower()
        return head.startswith("<!doctype") or head.startswith("<html")
    except Exception:
        return False

def _ensure_list(x): return x if isinstance(x, list) else []

def _candidate_pngs(symbol: str, timeframe: str) -> list[str]:
    base = f"charts/{symbol}_{timeframe}"
    return [f"{base}_compact.png", f"{base}_price.png", f"{base}_rsi.png", f"{base}_macd.png"]

def load_base_files():
    idx, nws, fl, miss = None, None, None, []
    if INDEX.exists() and not _is_html_head(INDEX):
        idx = _read_json(INDEX)
        if idx is None: miss.append("docs/index.json: invalid JSON")
    else:
        miss.append("docs/index.json: missing or HTML")

    if NEWS.exists():
        nws = _read_json(NEWS)
        if nws is None: miss.append("docs/news/news.json: invalid JSON")
    else:
        miss.append("docs/news/news.json: missing")

    if FILELIST.exists():
        fl = _read_json(FILELIST)
        if fl is None: miss.append("docs/filelist.json: invalid JSON")
    else:
        miss.append("docs/filelist.json: missing")

    return idx, nws, fl, miss

def build_charts_from_filelist(filelist, symbols: list[str]) -> dict[str, dict]:
    charts = {s: {} for s in symbols}
    files = _ensure_list(filelist) if isinstance(filelist, list) else _ensure_list((filelist or {}).get("files"))
    allfiles = set(files)
    # plukk *_compact først
    per = {s: {tf: None for tf in ("daily","weekly","monthly","hourly")} for s in symbols}
    for f in files:
        m = re.search(r"charts/([A-Za-z0-9\-]+)_(hourly|daily|weekly|monthly)_(?:compact|price|rsi|macd)\.png$", f or "")
        if not m: continue
        sym, tf = m.group(1), m.group(2)
        if sym in per and f.endswith("_compact.png") and per[sym][tf] is None:
            per[sym][tf] = f
    # fallback til price/rsi/macd
    for s in symbols:
        for tf in ("daily","weekly","monthly","hourly"):
            if per[s][tf] is None:
                for alt in _candidate_pngs(s, tf):
                    if alt in allfiles:
                        per[s][tf] = alt
                        break
    # bygg result + best
    for s in symbols:
        c = {}
        for tf in ("daily","weekly","monthly","hourly"):
            if per[s][tf]: c[tf] = per[s][tf]
        best = c.get("daily") or c.get("weekly") or c.get("monthly") or c.get("hourly")
        if best: c["best"] = best
        charts[s] = c
    return charts

def to_abs_urls(rel: str) -> dict:
    return {
        "raw": f"{RAW_BASE}/{rel}",
        "jsdelivr": f"{JSD_BASE}/{rel}",
        "pages": f"{PAG_BASE}/{rel}",
    }

# ---------- main ----------
def main():
    session = build_session()
    idx, nws, fl, miss = load_base_files()

    summary = (idx or {}).get("summary") if isinstance(idx, dict) else {}
    assets  = (summary or {}).get("assets") if isinstance(summary, dict) else None  # kan være None/{} i lean

    # univers som vises i rapporten
    universe = [
        "GLD","SLV","USO","ETH-USD","BTC-USD","URNM","GDX","GDXJ","SIL","SILJ",
        "ACWI","SPY","DTWEXM","VIXCLS","HYG","LQD","DGS10","DGS3MO","DGS2","2s10s"
    ]

    # bygg charts fra filelist som vanlig
    charts_map_rel = build_charts_from_filelist(fl or {}, universe)

    # metrics builder – støtter både full assets og lean summary
    tickers = []
    for sym in universe:
        metrics = {}
        # 1) full assets (dersom finnes)
        if isinstance(assets, dict) and sym in assets:
            a = assets.get(sym, {})
            # kopier “ramme”-nøkler som finnes
            frames = (a.get("frames") or {}) if isinstance(a, dict) else {}
            daily  = frames.get("daily") or {}
            for k in ("last","sma36","close_above_sma36","rsi14","macd","macd_signal","macd_hist","macd_cross"):
                if k in daily: metrics[k] = daily[k]
            for k in ("52w_high","52w_low","dist_to_36WMA","dist_to_36MMA","weekly_close_count_above_36WMA",
                      "gdx_gld_ratio_vs_50dma","sil_slv_ratio_vs_50dma","vol20_up_ok"):
                if k in a: metrics[k] = a[k]

        # 2) lean summary (fred/yields/…)
        # map til symbols vi bruker
        fred = (summary or {}).get("fred") or {}
        yields = (summary or {}).get("yields") or {}
        if sym == "DTWEXM" and "DXY" in fred:
            metrics["last"] = fred["DXY"].get("last")
            if "dist_to_200DMA" in fred["DXY"]:
                metrics["dist_to_200DMA"] = fred["DXY"]["dist_to_200DMA"]
        if sym == "VIXCLS" and "VIX" in fred:
            metrics["last"] = fred["VIX"].get("last")
        if sym == "DGS3MO" and "DGS3MO" in yields:
            metrics["last"] = yields["DGS3MO"]
        if sym == "DGS2" and "DGS2" in yields:
            metrics["last"] = yields["DGS2"]
        if sym == "DGS10" and "DGS10" in yields:
            metrics["last"] = yields["DGS10"]
        if sym == "2s10s" and "2s10s" in yields:
            metrics["last"] = yields["2s10s"]

        # charts: lag absolutte URL-er med speiltest
        chart_urls = {}
        rels = charts_map_rel.get(sym, {})
        for tf in ("daily","weekly","monthly","hourly"):
            rel = rels.get(tf)
            if not rel: continue
            absu = to_abs_urls(rel)
            chosen = choose_first_available_png(session, [absu["raw"], absu["jsdelivr"], absu["pages"]])
            if chosen:
                chart_urls[tf] = chosen
        for pref in ("daily","weekly","monthly","hourly"):
            if chart_urls.get(pref):
                chart_urls["best"] = chart_urls[pref]; break

        tickers.append({"symbol": sym, "metrics": metrics, "charts": chart_urls})

    # news: støtt både liste og {items:[…]}
    news_raw = []
    if isinstance(nws, dict) and isinstance(nws.get("items"), list):
        news_raw = nws["items"]
    elif isinstance(nws, list):
        news_raw = nws
    news_items = []
    for it in news_raw:
        title = (it.get("title") or "").strip()
        url = (it.get("url") or it.get("link") or "").strip()
        source = (it.get("source") or it.get("site") or "").strip()
        ts = (it.get("timestamp") or it.get("published") or it.get("date") or "").strip()
        summary_txt = (it.get("summary") or it.get("desc") or it.get("description") or "").strip()
        image = (it.get("image") or it.get("img") or "").strip()
        if not (title and url and ts): 
            continue
        news_items.append({
            "title": title,
            "source": source,
            "url": normalize_url(url),
            "timestamp_iso": ts,
            "summary": summary_txt,
            "image": image
        })
    news_items = dedup_news(news_items)

    # trekk med notes/market_temp så rapportmotor kan bruke det direkte
    notes_block = (summary or {}).get("notes") or {}
    market_temp = (summary or {}).get("market_temp") or {}

    feed = {
        "spec": "chatgpt-feed-v1",
        "generated_utc": dt.datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "mirrors": {"raw": RAW_BASE, "jsdelivr": JSD_BASE, "pages": PAG_BASE},
        "tickers": tickers,
        "news": news_items,
        "notes": notes_block,          # <-- NYTT
        "market_temp": market_temp,    # <-- NYTT
        "missing": miss,
    }

    OUT_FEED.parent.mkdir(parents=True, exist_ok=True)
    OUT_FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"wrote {OUT_FEED}")

if __name__ == "__main__":
    main()
