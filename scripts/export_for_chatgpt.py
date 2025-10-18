#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, re, time
from pathlib import Path
from datetime import datetime, timezone

PAGES = Path("docs")
INDEX = PAGES / "index.json"
FILELIST = PAGES / "filelist.json"
NEWS = PAGES / "news" / "news.json"
OUT = PAGES / "chatgpt_feed.json"

OWNER = "regg92s-hub"
REPO  = "market-daily-report"
BRANCH = os.getenv("PAGES_BRANCH", "gh-pages")

def load_json(p: Path):
    if not p.exists(): return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def ensure_filelist_from_dir():
    """Hvis filelist.json mangler: bygg den ved å liste docs/charts/*."""
    if FILELIST.exists(): 
        return load_json(FILELIST) or {}
    charts_dir = PAGES / "charts"
    items = []
    if charts_dir.exists():
        for p in sorted(charts_dir.glob("*.png")):
            items.append({"path": f"charts/{p.name}"})
    data = {"files": items}
    FILELIST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data

def pick_compact_per_ticker(filelist):
    """
    Returnerer dict: {ticker: {"charts": {best:'path', 'daily':..., 'weekly':..., 'monthly':..., 'hourly':...}}}
    velger kun *_compact.png. Prioritet: daily > weekly > monthly > hourly
    """
    files = (filelist or {}).get("files", [])
    compacts = [f["path"] for f in files if isinstance(f, dict) and isinstance(f.get("path"), str) and f["path"].endswith("_compact.png")]
    # Mønster: <ticker>_<tf>_compact.png, fx: GLD_daily_compact.png
    rx = re.compile(r"^charts/([A-Za-z0-9\-\._]+)_(hourly|daily|weekly|monthly)_compact\.png$")
    by_ticker = {}
    for path in compacts:
        m = rx.match(path)
        if not m: 
            continue
        ticker, tf = m.group(1), m.group(2)
        info = by_ticker.setdefault(ticker, {"charts": {}})
        info["charts"][tf] = path

    # finn "best" i prioritert rekkefølge
    for t, info in by_ticker.items():
        charts = info["charts"]
        for tf in ("daily","weekly","monthly","hourly"):
            if tf in charts:
                info["charts"]["best"] = charts[tf]
                break
    return by_ticker

def build_urls(path, ts):
    raw = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{path}?t={ts}"
    jsd = f"https://cdn.jsdelivr.net/gh/{OWNER}/{REPO}@{BRANCH}/{path}?t={ts}"
    ghp = f"https://{OWNER}.github.io/{REPO}/{path}?t={ts}"
    return {"raw": raw, "jsdelivr": jsd, "pages": ghp}

def main():
    ts = os.getenv("GITHUB_RUN_ID") or str(int(time.time()))
    idx = load_json(INDEX) or {}
    fl = ensure_filelist_from_dir()
    nw = load_json(NEWS) or {"items": []}

    # bygg kompakter per ticker
    comp = pick_compact_per_ticker(fl)

    # hent tall vi bryr oss om per ticker fra index.json (om tilgjengelig)
    # forventet struktur: idx["summary"]["assets"][ticker] -> metrics
    assets = ((idx.get("summary") or {}).get("assets") or {}) if isinstance(idx, dict) else {}
    out_tickers = {}
    for ticker, charts in comp.items():
        a = assets.get(ticker, {})
        frames = (a.get("frames") or {}) if isinstance(a, dict) else {}
        d = {
            "ticker": ticker,
            "metrics": {
                "52w_high": a.get("52w_high"),
                "52w_low": a.get("52w_low"),
                "dist_to_36WMA": a.get("dist_to_36WMA"),
                "dist_to_36MMA": a.get("dist_to_36MMA"),
                "weekly_close_count_above_36WMA": a.get("weekly_close_count_above_36WMA"),
                "gdx_gld_ratio_vs_50dma": a.get("gdx_gld_ratio_vs_50dma"),
                "sil_slv_ratio_vs_50dma": a.get("sil_slv_ratio_vs_50dma"),
                "vol20_up_ok": a.get("vol20_up_ok"),
                "frames": {
                    "hourly":  frames.get("hourly"),
                    "daily":   frames.get("daily"),
                    "weekly":  frames.get("weekly"),
                    "monthly": frames.get("monthly"),
                }
            },
            "charts": {}
        }
        # legg på URLer for valgt graf + alle tidsrammer som finnes
        for key in ("best","daily","weekly","monthly","hourly"):
            p = charts["charts"].get(key)
            if not p: 
                continue
            d["charts"][key] = build_urls(p, ts)
        out_tickers[ticker] = d

    # nyheter (lett dedup ved URL+title+ts hvis finnes)
    news_items = []
    seen = set()
    for it in nw.get("items", []):
        if not isinstance(it, dict): 
            continue
        title = it.get("title") or ""
        url = it.get("url") or it.get("link") or ""
        tstamp = it.get("published") or it.get("date") or ""
        dedup_key = (title.strip(), url.strip(), tstamp.strip())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        news_items.append({
            "title": title,
            "url": url,
            "timestamp": tstamp,
            "summary": it.get("summary") or it.get("description") or "",
            "image": it.get("image") or it.get("img") or ""
        })

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "cache_bust": ts,
        "mirrors": {
            "primary": f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}",
            "fallback": f"https://cdn.jsdelivr.net/gh/{OWNER}/{REPO}@{BRANCH}",
            "pages": f"https://{OWNER}.github.io/{REPO}",
        },
        "tickers": out_tickers,
        "news": news_items,
        "sources": {
            "index_json_ok": bool(idx),
            "filelist_ok": bool(fl),
            "news_ok": bool(news_items),
        }
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(Path.cwd())}")

if __name__ == "__main__":
    main()
