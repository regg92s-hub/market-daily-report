#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export a single, robust feed for the ChatGPT report runner.

Input (under docs/):
- index.json
- filelist.json
- news/news.json

Output:
- chatgpt_feed.json  (in docs/)
"""

from __future__ import annotations
import json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

# ---------- Paths ----------
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "index.json"
FILELIST = DOCS / "filelist.json"
NEWS = DOCS / "news" / "news.json"
OUT = DOCS / "chatgpt_feed.json"

# ---------- Mirrors ----------
REPO = "regg92s-hub/market-daily-report"
BRANCH = "gh-pages"
PAGES_BASE = f"https://{REPO.split('/')[0]}.github.io/{REPO.split('/')[1]}"
RAW_BASE   = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
JS_BASE    = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}"

MIRRORS = {
    "raw": RAW_BASE,
    "jsdelivr": JS_BASE,
    "pages": PAGES_BASE,
}

# ---------- Helpers ----------
def _safe_read_json(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _get(d, *ks, default=None):
    cur = d
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def _num(x):
    return x if isinstance(x, (int, float)) else None

def _now_utc_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _normalize_news_container(nw):
    """
    Accept:
      - {"items": [...]} or {"news":[...]} or [...]
    Return list.
    """
    if nw is None:
        return []
    if isinstance(nw, dict):
        if "items" in nw and isinstance(nw["items"], list):
            return nw["items"]
        if "news" in nw and isinstance(nw["news"], list):
            return nw["news"]
        # Sometimes producers put directly under "data"
        if "data" in nw and isinstance(nw["data"], list):
            return nw["data"]
        return []
    if isinstance(nw, list):
        return nw
    return []

def _abspath_for(rel: str) -> dict:
    """
    Build absolute URLs for a file under docs/ (e.g. charts/GLD_daily_compact.png)
    """
    rel = rel.lstrip("/")
    return {
        "raw":     f"{RAW_BASE}/{rel}",
        "jsdelivr":f"{JS_BASE}/{rel}",
        "pages":   f"{PAGES_BASE}/{rel}",
    }

def _choose_best_compact(files_for_ticker: list[str]) -> dict:
    """
    Prioritize *_daily_compact.png → *_weekly_compact.png → *_monthly_compact.png → *_hourly_compact.png
    Return dict with keys best, daily, weekly, monthly, hourly where present (as absolute mirror dicts).
    """
    frames = ["daily", "weekly", "monthly", "hourly"]
    out = {}
    def find_for(frame):
        pat = re.compile(rf"_{frame}_compact\.png$", re.IGNORECASE)
        for f in files_for_ticker:
            if pat.search(f):
                return f
        return None

    for fr in frames:
        hit = find_for(fr)
        if hit:
            out[fr] = _abspath_for(hit)

    # pick best = first available in priority
    for fr in frames:
        if fr in out:
            out["best"] = out[fr]
            break
    return out

def _collect_compacts_by_ticker(filelist) -> dict[str, list[str]]:
    """
    filelist is expected as list of paths or dict with "files": [...]
    Filter on *_compact.png then bucket by ticker inferred from prefix before first "_".
    """
    files = []
    if isinstance(filelist, list):
        files = filelist
    elif isinstance(filelist, dict):
        if isinstance(filelist.get("files"), list):
            files = filelist["files"]
        # Some producers store under "all" or "charts"
        elif isinstance(filelist.get("all"), list):
            files = filelist["all"]
        elif isinstance(filelist.get("charts"), list):
            files = filelist["charts"]

    # Keep only PNGs that end with _compact.png
    files = [f for f in files if isinstance(f, str) and f.lower().endswith("_compact.png")]
    # Try to ensure "charts/" prefix if missing
    normalized = []
    for f in files:
        if not f.startswith("charts/") and "charts/" not in f:
            if f.startswith("/"):
                normalized.append("charts" + f)
            else:
                normalized.append("charts/" + f)
        else:
            normalized.append(f.lstrip("/"))
    files = normalized

    buckets = {}
    for f in files:
        # Infer ticker as the prefix before first "_"
        base = Path(f).name
        m = re.match(r"^([A-Za-z0-9\-\._]+)_", base)
        if not m:
            continue
        ticker = m.group(1)
        buckets.setdefault(ticker, []).append(f)
    return buckets

def _metrics_from_index(idx, ticker: str) -> dict:
    """
    Defensive extraction aligned with your index.json produced by generate_report.
    """
    a = _get(idx, "summary", "assets", ticker, default={}) or {}
    frames = _get(a, "frames", default={}) or {}
    d = frames.get("daily") or {}
    w = frames.get("weekly") or {}
    m = frames.get("monthly") or {}
    h = frames.get("hourly") or {}

    out = {
        "last": _num(d.get("last")),
        "is_52w_high": a.get("is_52w_high"),
        "is_52w_low":  a.get("is_52w_low"),
        "52w_high": _num(a.get("52w_high")),
        "52w_low":  _num(a.get("52w_low")),
        "dist_to_36WMA": _num(a.get("dist_to_36WMA")),
        "dist_to_36MMA": _num(a.get("dist_to_36MMA")),
        "weekly_close_count_above_36WMA": _num(a.get("weekly_close_count_above_36WMA")),
        "gdx_gld_ratio_vs_50dma": a.get("gdx_gld_ratio_vs_50dma"),
        "sil_slv_ratio_vs_50dma": a.get("sil_slv_ratio_vs_50dma"),
        "vol20_up_ok": a.get("vol20_up_ok"),
        "frames": {
            "hourly": {
                "close_above_sma36": h.get("close_above_sma36"),
                "dist_to_36MA": _num(h.get("dist_to_36MA")),
                "rsi14": _num(h.get("rsi14")),
                "macd": _num(h.get("macd")),
                "macd_signal": _num(h.get("macd_signal")),
                "macd_hist": _num(h.get("macd_hist")),
                "macd_cross": h.get("macd_cross"),
            },
            "daily": {
                "close_above_sma36": d.get("close_above_sma36"),
                "dist_to_36MA": _num(d.get("dist_to_36MA")),
                "rsi14": _num(d.get("rsi14")),
                "macd": _num(d.get("macd")),
                "macd_signal": _num(d.get("macd_signal")),
                "macd_hist": _num(d.get("macd_hist")),
                "macd_cross": d.get("macd_cross"),
            },
            "weekly": {
                "close_above_sma36": w.get("close_above_sma36"),
                "dist_to_36MA": _num(w.get("dist_to_36MA")),
                "rsi14": _num(w.get("rsi14")),
                "macd": _num(w.get("macd")),
                "macd_signal": _num(w.get("macd_signal")),
                "macd_hist": _num(w.get("macd_hist")),
                "macd_cross": w.get("macd_cross"),
            },
            "monthly": {
                "close_above_sma36": m.get("close_above_sma36"),
                "dist_to_36MA": _num(m.get("dist_to_36MA")),
                "rsi14": _num(m.get("rsi14")),
                "macd": _num(m.get("macd")),
                "macd_signal": _num(m.get("macd_signal")),
                "macd_hist": _num(m.get("macd_hist")),
                "macd_cross": m.get("macd_cross"),
            },
        }
    }
    return out

def main():
    idx = _safe_read_json(INDEX) or {}
    fl = _safe_read_json(FILELIST) or []
    nw = _safe_read_json(NEWS)

    # Build compacts per ticker
    compacts = _collect_compacts_by_ticker(fl)

    # Determine ticker universe from either index.json summary assets keys or from compacts
    tickers_from_index = list((_get(idx, "summary", "assets", default={}) or {}).keys())
    tickers_from_files = list(compacts.keys())
    tickers = sorted(set(tickers_from_index) | set(tickers_from_files))

    # Build tickers payload
    tickers_payload = []
    for t in tickers:
        metrics = _metrics_from_index(idx, t) if idx else {}
        chart_files = compacts.get(t, [])
        charts = _choose_best_compact(chart_files) if chart_files else {}
        tickers_payload.append({
            "symbol": t,
            "metrics": metrics,
            "charts": charts,
        })

    # Build news payload
    news_items_src = _normalize_news_container(nw)
    news_payload = []
    for it in news_items_src:
        if not isinstance(it, dict):
            continue
        title = it.get("title") or it.get("headline") or ""
        url   = it.get("url") or it.get("link") or ""
        ts    = it.get("timestamp") or it.get("published_at") or it.get("pubDate") or it.get("date") or ""
        summary = it.get("summary") or it.get("description") or ""
        image = it.get("image") or it.get("image_url") or it.get("thumb") or None
        source = it.get("source") or it.get("site") or ""
        if not title and not url:
            continue
        news_payload.append({
            "title": title,
            "url": url,
            "timestamp": ts,
            "summary": summary,
            "image": image,
            "source": source,
        })

    out = {
        "spec": "chatgpt-feed-v1",
        "generated_utc": _now_utc_iso(),
        "mirrors": MIRRORS,
        "tickers": tickers_payload,
        "news": news_payload,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[export_for_chatgpt] wrote {OUT}")

if __name__ == "__main__":
    main()
