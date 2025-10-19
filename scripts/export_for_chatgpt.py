#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Produserer docs/chatgpt_feed.json i format:
{
  "spec": "chatgpt-feed-v1",
  "generated_utc": "...",
  "mirrors": { "raw": "...", "jsdelivr": "...", "pages": "..." },
  "tickers": [
     { "symbol": "...",
       "metrics": { ... },
       "charts": { "best": "https://...", "daily": "...", "weekly": "...", "monthly": "...", "hourly": "..." }
     }, ...
  ],
  "news": [
     {"title": "...", "source": "...", "url": "...", "timestamp_iso": "...", "summary": "...", "image": "..."}, ...
  ],
  "missing": [ "beskrivelser ..." ]
}
"""
import os, sys, json, re, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from lib_net import build_session, fetch_first_ok, choose_first_available_png, normalize_title, normalize_url, dedup_news

PAGES = Path("docs")
INDEX = PAGES / "index.json"
NEWS  = PAGES / "news" / "news.json"
FILELIST = PAGES / "filelist.json"
INDEX_HTML = PAGES / "index.html"
OUT_FEED = PAGES / "chatgpt_feed.json"

RAW_BASE = "https://raw.githubusercontent.com/regg92s-hub/market-daily-report/gh-pages"
JSD_BASE = "https://cdn.jsdelivr.net/gh/regg92s-hub/market-daily-report@gh-pages"
PAG_BASE = "https://regg92s-hub.github.io/market-daily-report"

TS = os.environ.get("RUN_ID") or dt.datetime.utcnow().isoformat(timespec="seconds")+"Z"

OSLO = ZoneInfo("Europe/Oslo")

# ----------------- util -----------------

def _log(msg: str):
    print(f"[export] {msg}", flush=True)

def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _is_html_head(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8")[:300].strip().lower()
        return head.startswith("<!doctype") or head.startswith("<html")
    except Exception:
        return False

def _safe_get(d, *path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur: return default
        cur = cur[k]
    return cur

def _ensure_list(x):
    return x if isinstance(x, list) else []

def _is_compact(name: str) -> bool:
    return name.endswith("_compact.png")

def _candidate_pngs(symbol: str, timeframe: str) -> list[str]:
    base = f"charts/{symbol}_{timeframe}"
    return [f"{base}_compact.png", f"{base}_price.png", f"{base}_rsi.png", f"{base}_macd.png"]

# ----------------- load local base files -----------------

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

# ----------------- build charts map from filelist/index.html -----------------

def build_charts_from_filelist(filelist, symbols: list[str]) -> dict[str, dict]:
    """
    Returnerer per symbol: { 'daily': url, 'weekly': url, 'monthly': url, 'hourly': url, 'best': url }
    Velger kun *_compact.png hvis mulig.
    """
    charts = {s: {} for s in symbols}
    files = _ensure_list(filelist) if isinstance(filelist, list) else _ensure_list(filelist.get("files"))
    pngs = [f for f in files if isinstance(f, str) and f.endswith(".png")]
    # Velg compact først
    per_sym_tf = {}
    for s in symbols:
        per_sym_tf[s] = {tf: None for tf in ("daily","weekly","monthly","hourly")}
    # parse navn
    for f in pngs:
        m = re.search(r"charts/([A-Za-z0-9\-]+)_(hourly|daily|weekly|monthly)_(?:compact|price|rsi|macd)\.png$", f)
        if not m: continue
        sym, tf = m.group(1), m.group(2)
        if sym not in per_sym_tf: continue
        if f.endswith("_compact.png"):
            if per_sym_tf[sym][tf] is None:
                per_sym_tf[sym][tf] = f

    # hvis compact mangler, prøv price/rsi/macd
    if isinstance(filelist, list):
        allfiles = set(filelist)
    else:
        allfiles = set(_ensure_list(filelist.get("files")))
    for s in symbols:
        for tf in ("daily","weekly","monthly","hourly"):
            if per_sym_tf[s][tf] is None:
                for alt in _candidate_pngs(s, tf):
                    if alt in allfiles:
                        per_sym_tf[s][tf] = alt
                        break

    # best = daily→weekly→monthly→hourly
    for s in symbols:
        c = {}
        for tf in ("daily","weekly","monthly","hourly"):
            if per_sym_tf[s][tf]:
                c[tf] = per_sym_tf[s][tf]
        best = c.get("daily") or c.get("weekly") or c.get("monthly") or c.get("hourly")
        if best: c["best"] = best
        charts[s] = c
    return charts

# ----------------- build feed -----------------

def main():
    session = build_session()
    idx, nws, fl, miss = load_base_files()

    # symbols vi bryr oss om (fra ønsket univers)
    symbols = [
        "GLD","SLV","USO","ETH-USD","BTC-USD","URNM","GDX","GDXJ","SIL","SILJ",
        "ACWI","SPY","DTWEXM","VIXCLS","HYG","LQD","DGS10","DGS3MO","DGS2","2s10s"
    ]

    tickers = []
    # metrics fra index.json: idx["summary"]["assets"][symbol]
    assets = (idx or {}).get("summary", {}).get("assets", {}) if isinstance(idx, dict) else {}

    # lag chart map
    charts_map = build_charts_from_filelist(fl or {}, symbols)

    # speil for PNG (vi genererer absolutte URLer)
    def to_abs_urls(rel: str) -> dict:
        if not rel: return {}
        raw = f"{RAW_BASE}/{rel}"
        jsd = f"{JSD_BASE}/{rel}"
        pag = f"{PAG_BASE}/{rel}"
        return {"raw": raw, "jsdelivr": jsd, "pages": pag}

    # for hvert symbol: metrics + charts + best (med speilprøving)
    for s in symbols:
        a = assets.get(s, {}) if isinstance(assets, dict) else {}
        metrics = {}
        # plukk ut kjente felter hvis finnes
        for k in ("52w_high","52w_low","dist_to_36WMA","dist_to_36MMA","weekly_close_count_above_36WMA",
                  "gdx_gld_ratio_vs_50dma","sil_slv_ratio_vs_50dma","vol20_up_ok"):
            if k in a: metrics[k]=a[k]
        # frames->daily for RSI/MACD/last etc.
        daily = a.get("frames", {}).get("daily", {}) if isinstance(a, dict) else {}
        if isinstance(daily, dict):
            for k in ("last","sma36","close_above_sma36","rsi14","macd","macd_signal","macd_hist","macd_cross"):
                if k in daily: metrics[k]=daily[k]

        # charts: bygg absolutte URLer og velg "best" ved å teste speil rekkefølge
        cm = charts_map.get(s, {})
        chart_urls = {}
        chosen_best = None
        for tf in ("daily","weekly","monthly","hourly"):
            rel = cm.get(tf)
            if not rel: continue
            absu = to_abs_urls(rel)
            # forsøk HEAD i rekkefølge:
            best_url = choose_first_available_png(session, [absu["raw"], absu["jsdelivr"], absu["pages"]])
            if best_url:
                chart_urls[tf] = best_url
        # best
        for pref in ("daily","weekly","monthly","hourly"):
            if chart_urls.get(pref):
                chosen_best = chart_urls[pref]
                break
        if chosen_best: chart_urls["best"] = chosen_best

        tickers.append({
            "symbol": s,
            "metrics": metrics,
            "charts": chart_urls
        })

    # news normalisering + dedup
    news_items = []
    if isinstance(nws, dict) and isinstance(nws.get("items"), list):
        its = nws["items"]
    elif isinstance(nws, list):
        its = nws
    else:
        its = []

    for it in its:
        title = (it.get("title") or "").strip()
        url = (it.get("url") or it.get("link") or "").strip()
        source = (it.get("source") or it.get("site") or "").strip()
        ts = (it.get("timestamp") or it.get("published") or it.get("date") or "").strip()
        summary = (it.get("summary") or it.get("desc") or it.get("description") or "").strip()
        image = (it.get("image") or it.get("img") or "").strip()
        if not (title and url and ts): 
            continue
        news_items.append({
            "title": title,
            "source": source,
            "url": normalize_url(url),
            "timestamp_iso": ts,
            "summary": summary,
            "image": image
        })
    news_items = dedup_news(news_items)

    feed = {
        "spec": "chatgpt-feed-v1",
        "generated_utc": dt.datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "mirrors": {
            "raw": RAW_BASE,
            "jsdelivr": JSD_BASE,
            "pages": PAG_BASE,
        },
        "tickers": tickers,
        "news": news_items,
        "missing": miss,
    }

    OUT_FEED.parent.mkdir(parents=True, exist_ok=True)
    OUT_FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"wrote {OUT_FEED}")

if __name__ == "__main__":
    main()
