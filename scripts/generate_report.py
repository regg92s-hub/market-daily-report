#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, time, math, re, html
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse

import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

VERSION = "2026-03-30-cycles-homepage-2"
TZ = ZoneInfo("Europe/Oslo")
NOW = datetime.now(tz=TZ)

DOCS = Path("docs")
CHARTS = DOCS / "charts"
NEWS_DIR = DOCS / "news"

DOCS.mkdir(exist_ok=True)
CHARTS.mkdir(exist_ok=True)
NEWS_DIR.mkdir(exist_ok=True)

FORCE_INPUT = os.environ.get("FORCE_RUN", "false").lower() == "true"
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
FORCE = FORCE_INPUT or IN_GITHUB_ACTIONS
print(
    f"Full run mode: {FORCE} "
    f"(force_input={FORCE_INPUT}, github_actions={IN_GITHUB_ACTIONS}) "
    f"at {NOW.isoformat()} (version {VERSION})"
)

with open(DOCS / "run_mode.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "force": FORCE,
            "force_input": FORCE_INPUT,
            "github_actions": IN_GITHUB_ACTIONS,
            "now": NOW.isoformat(),
            "version": VERSION,
        },
        f,
        indent=2,
    )

if not FORCE and not ((NOW.hour == 19 and NOW.minute >= 45) or (NOW.hour == 20 and NOW.minute <= 10)):
    with open(DOCS / "heartbeat.json", "w", encoding="utf-8") as f:
        json.dump({"last_run_local": NOW.isoformat(), "version": VERSION}, f, indent=2)
    with open(DOCS / "index.html", "w", encoding="utf-8") as f:
        f.write(
            "<!doctype html><meta charset='utf-8'><title>Market Daily Report</title>"
            f"<h1>Market Daily Report</h1>"
            f"<p>Generert: {NOW.isoformat()}</p>"
            "<p>Full rapport genereres kl. 20:00 Europe/Oslo.</p>"
        )
    raise SystemExit(0)

LOG = []

def log(msg: str):
    print(msg)
    LOG.append(f"{datetime.now().isoformat()}  {msg}")

def flush_log():
    with open(DOCS / "run_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")

YF_SESSION = requests.Session()
YF_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
})

INSTRUMENT_GROUPS = [
    {
        "key": "vekstsyklusen",
        "title": "1. Vekstsyklusen",
        "description": "Dette er instrumenter som sier mest om bred økonomisk aktivitet, syklisk styrke og regional risikovilje.",
        "instruments": [
            {"id": "SPY", "label": "S&P 500", "symbol_label": "SPY", "source": "yf", "candidates": ["SPY"]},
            {"id": "IWM", "label": "Russell 2000", "symbol_label": "IWM", "source": "yf", "candidates": ["IWM"]},
            {"id": "EXSA", "label": "STOXX Europe 600", "symbol_label": "EXSA", "source": "yf", "candidates": ["EXSA", "EXSA.DE"]},
            {"id": "EEM", "label": "MSCI EM", "symbol_label": "EEM", "source": "yf", "candidates": ["EEM"]},
            {"id": "VNQ", "label": "Housing US", "symbol_label": "VNQ", "source": "yf", "candidates": ["VNQ"]},
            {"id": "TRET", "label": "Housing global", "symbol_label": "TRET", "source": "yf", "candidates": ["TRET"]},
        ],
    },
    {
        "key": "renter_og_finansielle_forhold",
        "title": "2. Renter, kurve og finansielle forhold",
        "description": "Dette er instrumenter som sier mest om pengepolitikk, rentekurve og finansielle forhold.",
        "instruments": [
            {"id": "UTWO", "label": "2-årig UST", "symbol_label": "UTWO", "source": "yf", "candidates": ["UTWO"]},
            {"id": "UTEN", "label": "10-årig UST", "symbol_label": "UTEN", "source": "yf", "candidates": ["UTEN"]},
            {"id": "2S10S", "label": "2s10s", "symbol_label": "STPU / UCT2", "source": "fred_spread"},
            {"id": "SCHP", "label": "10-årig realrente", "symbol_label": "SCHP", "source": "yf", "candidates": ["SCHP"]},
        ],
    },
    {
        "key": "inflasjonssyklusen",
        "title": "3. Inflasjonssyklusen",
        "description": "Dette er instrumenter som typisk reagerer tidlig på inflasjonspress og råvaredrevet reflasjon.",
        "instruments": [
            {"id": "BCOM", "label": "Commodity", "symbol_label": "BCOM", "source": "yf", "candidates": ["BCOM", "PDBC"]},
            {"id": "USO", "label": "Olje", "symbol_label": "USO", "source": "yf", "candidates": ["USO"]},
            {"id": "UNG", "label": "Naturgass", "symbol_label": "UNG", "source": "yf", "candidates": ["UNG"]},
            {"id": "COPX", "label": "Kobber", "symbol_label": "COPX", "source": "yf", "candidates": ["COPX"]},
        ],
    },
    {
        "key": "kredittsyklusen",
        "title": "4. Kredittsyklusen",
        "description": "Her følger du hvor mye stress eller lettelse det er i kredittmarkedet.",
        "instruments": [
            {"id": "HYG", "label": "US High Yield OAS", "symbol_label": "HYG", "source": "yf", "candidates": ["HYG"]},
        ],
    },
    {
        "key": "valuta_og_dollar",
        "title": "5. Valuta- og dollar-syklusen",
        "description": "Dette er hovedinstrumentet for dollarregimet og globalt finansielt press.",
        "instruments": [
            {"id": "UUP", "label": "DXY", "symbol_label": "UUP", "source": "yf", "candidates": ["UUP"]},
        ],
    },
    {
        "key": "lederskap_i_aksjemarkedet",
        "title": "6. Lederskap innad i aksjemarkedet",
        "description": "Dette er instrumenter som sier noe om hvilke deler av aksjemarkedet som leder an.",
        "instruments": [
            {"id": "QQQ", "label": "Nasdaq-100", "symbol_label": "QQQ", "source": "yf", "candidates": ["QQQ"]},
            {"id": "SOXQ", "label": "SOX / semiconductors", "symbol_label": "SOXQ", "source": "yf", "candidates": ["SOXQ"]},
        ],
    },
    {
        "key": "volatilitet_og_risikovilje",
        "title": "7. Volatilitet og risikovilje",
        "description": "Dette er instrumenter som sier mest om risikopåslag, spekulasjon og stress i markedet.",
        "instruments": [
            {"id": "VIXY", "label": "VIX", "symbol_label": "VIXY", "source": "yf", "candidates": ["VIXY"]},
            {"id": "BTC", "label": "BTC", "symbol_label": "BITO / IBIT", "source": "yf", "candidates": ["BITO", "IBIT"]},
            {"id": "ETHA", "label": "ETH", "symbol_label": "ETHA", "source": "yf", "candidates": ["ETHA"]},
        ],
    },
    {
        "key": "edelmetaller_og_nisjeravarer",
        "title": "8. Edelmetaller og nisjeråvarer",
        "description": "Dette er instrumenter som ofte fanger opp realrente, safe haven, industribruk og spesialsykluser.",
        "instruments": [
            {"id": "GLD", "label": "Gull", "symbol_label": "GLD", "source": "yf", "candidates": ["GLD"]},
            {"id": "SLV", "label": "Sølv", "symbol_label": "SLV", "source": "yf", "candidates": ["SLV"]},
            {"id": "URA", "label": "Uranium", "symbol_label": "URA", "source": "yf", "candidates": ["URA"]},
            {"id": "PLTM", "label": "Platina", "symbol_label": "PLTM", "source": "yf", "candidates": ["PLTM"]},
            {"id": "PALL", "label": "Palladium", "symbol_label": "PALL", "source": "yf", "candidates": ["PALL"]},
        ],
    },
]

ALL_IDS = [inst["id"] for group in INSTRUMENT_GROUPS for inst in group["instruments"]]

FRED_KEY = os.environ.get("FRED_API_KEY", "").strip()
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

def SMA(s, n):
    return s.rolling(n).mean()

def RSI(s, n=14):
    d = s.diff()
    up = d.clip(lower=0)
    down = -d.clip(upper=0)
    rs = up.rolling(n).mean() / down.rolling(n).mean()
    return 100 - (100 / (1 + rs))

def MACD(s, fast=12, slow=26, sig=9):
    e_fast = s.ewm(span=fast, adjust=False).mean()
    e_slow = s.ewm(span=slow, adjust=False).mean()
    m = e_fast - e_slow
    sigl = m.ewm(span=sig, adjust=False).mean()
    return m, sigl, m - sigl

def pct(a, b):
    return (a - b) / b if (b is not None and b != 0) else np.nan

def safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)

def normalize_yf_df(data):
    if data is None or data.empty:
        return None
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    if "close" not in df.columns:
        return None
    df["close_use"] = pd.to_numeric(df["close"], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = np.nan
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df.dropna(subset=["close_use"])
    return df

def yf_series_from_candidates(candidates):
    for sym in candidates:
        for i in range(3):
            try:
                data = yf.download(
                    sym,
                    period="max",
                    interval="1d",
                    auto_adjust=True,
                    progress=False,
                    session=YF_SESSION,
                    threads=False,
                )
                df = normalize_yf_df(data)
                if df is not None and not df.empty:
                    log(f"using yfinance for {sym}")
                    return df, sym
            except Exception as e:
                log(f"yfinance error {sym} try{i+1}: {e}")
            time.sleep(1 + i)
    return None, None

def fred_series(series_id):
    if not FRED_KEY:
        return None
    url = (
        f"{FRED_BASE}?series_id={series_id}"
        f"&api_key={FRED_KEY}&file_type=json&observation_start=1990-01-01"
    )
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        if not obs:
            return None
        df = pd.DataFrame(obs)[["date", "value"]]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.set_index("date").sort_index().dropna()
        df = df.asfreq("B").ffill()
        df["close_use"] = df["value"]
        df["volume"] = np.nan
        log(f"fred ok {series_id}")
        return df[["close_use", "volume"]]
    except Exception as e:
        log(f"fred error {series_id}: {e}")
        return None

def fred_2s10s_series():
    y2 = fred_series("DGS2")
    y10 = fred_series("DGS10")
    if y2 is None or y10 is None or y2.empty or y10.empty:
        return None, None
    df = pd.DataFrame(index=y10.index.union(y2.index))
    df["y2"] = y2["close_use"]
    df["y10"] = y10["close_use"]
    df = df.sort_index().ffill().dropna()
    df["close_use"] = df["y10"] - df["y2"]
    df["volume"] = np.nan
    return df[["close_use", "volume"]], "FRED:DGS10-DGS2"

def with_indicators(df, ma_len=36):
    out = df.copy()
    out[f"sma{ma_len}"] = SMA(out["close_use"], ma_len)
    out["rsi14"] = RSI(out["close_use"])
    macd, signal, hist = MACD(out["close_use"])
    out["macd"] = macd
    out["macd_signal"] = signal
    out["macd_hist"] = hist
    return out

def resample_frames(base_df):
    daily = with_indicators(base_df)
    weekly = with_indicators(base_df.resample("W-FRI").last().dropna(how="all"))
    monthly = with_indicators(base_df.resample("ME").last().dropna(how="all"))
    return daily, weekly, monthly

def plot_compact(df, title, out_compact, ma_len=36):
    try:
        import matplotlib.dates as mdates
        fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
        axes[0].plot(df.index, df["close_use"], label="Close")
        axes[0].plot(df.index, SMA(df["close_use"], ma_len), label=f"SMA{ma_len}")
        axes[0].set_title(title)
        axes[0].legend(loc="upper left")

        r = RSI(df["close_use"])
        axes[1].plot(df.index, r, label="RSI(14)")
        axes[1].axhline(70, linestyle="--", linewidth=0.8)
        axes[1].axhline(30, linestyle="--", linewidth=0.8)
        axes[1].legend(loc="upper left")

        macd, sig, hist = MACD(df["close_use"])
        axes[2].plot(df.index, macd, label="MACD")
        axes[2].plot(df.index, sig, label="Signal")
        axes[2].bar(df.index, hist, alpha=0.5, label="Hist")
        locator = mdates.AutoDateLocator()
        axes[2].xaxis.set_major_locator(locator)
        axes[2].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        axes[2].legend(loc="upper left")

        plt.tight_layout()
        plt.savefig(out_compact, dpi=120)
        plt.close(fig)
    except Exception as e:
        log(f"compact plot error {title}: {e}")

def frame_summary(df, ma_len=36):
    if df is None or df.empty:
        return {}
    last = float(df["close_use"].iloc[-1])
    sma = df[f"sma{ma_len}"].iloc[-1] if f"sma{ma_len}" in df.columns else np.nan
    macd_cross = None
    if len(df) >= 2:
        last_delta = df["macd"].iloc[-1] - df["macd_signal"].iloc[-1]
        prev_delta = df["macd"].iloc[-2] - df["macd_signal"].iloc[-2]
        macd_cross = bool(last_delta > 0 and prev_delta <= 0)
    return {
        "last": last,
        "sma36": float(sma) if pd.notna(sma) else None,
        "close_above_sma36": bool(last > sma) if pd.notna(sma) else None,
        "rsi14": float(df["rsi14"].iloc[-1]) if pd.notna(df["rsi14"].iloc[-1]) else None,
        "macd": float(df["macd"].iloc[-1]) if pd.notna(df["macd"].iloc[-1]) else None,
        "macd_signal": float(df["macd_signal"].iloc[-1]) if pd.notna(df["macd_signal"].iloc[-1]) else None,
        "macd_hist": float(df["macd_hist"].iloc[-1]) if pd.notna(df["macd_hist"].iloc[-1]) else None,
        "macd_cross": macd_cross,
    }

def fetch_first_image_from_page(url):
    try:
        rr = requests.get(url, timeout=30, headers={"User-Agent": YF_SESSION.headers["User-Agent"]})
        rr.raise_for_status()
        soup = BeautifulSoup(rr.text, "lxml")
        meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if meta and meta.get("content"):
            return meta["content"]
        link = soup.find("link", rel="image_src")
        if link and link.get("href"):
            return link["href"]
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception:
        return None
    return None

def last_n_days_posts(url, days=3):
    out = []
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        items = soup.find_all("item")
        cutoff = pd.Timestamp(NOW.date()) - pd.Timedelta(days=days)
        for it in items[:20]:
            title_node = it.find("title")
            link_node = it.find("link")
            if not title_node or not link_node:
                continue
            title = title_node.get_text(strip=True)
            link = link_node.get_text(strip=True)
            pub = it.find("pubdate")
            ts = pd.to_datetime(pub.get_text(strip=True)) if pub else None
            if ts is not None and ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            if ts is not None and ts.tz_convert(TZ) >= pd.Timestamp(cutoff, tz=TZ):
                rec = {"title": title, "link": link, "published": ts.tz_convert(TZ).isoformat()}
                img_url = fetch_first_image_from_page(link)
                if img_url:
                    try:
                        ir = requests.get(img_url, timeout=30, headers={"User-Agent": YF_SESSION.headers["User-Agent"]})
                        ir.raise_for_status()
                        ext = os.path.splitext(urlparse(img_url).path)[1].lower() or ".jpg"
                        fname = f"news_{safe_id(title)}{ext if ext in ['.jpg', '.jpeg', '.png'] else '.jpg'}"
                        with open(NEWS_DIR / fname, "wb") as f:
                            f.write(ir.content)
                        rec["image"] = f"news/{fname}"
                    except Exception:
                        pass
                out.append(rec)
    except Exception as e:
        log(f"rss error {url}: {e}")
    return out

def get_instrument_series(inst):
    source = inst["source"]
    if source == "yf":
        return yf_series_from_candidates(inst["candidates"])
    if source == "fred_spread":
        return fred_2s10s_series()
    raise ValueError(f"Unknown source: {source}")

def build_homepage(index_data, filelist):
    assets = index_data.get("summary", {}).get("assets", {})
    categories = index_data.get("summary", {}).get("categories", [])
    generated = index_data.get("generated_local") or NOW.isoformat()

    file_set = set(filelist)

    def fmt_rsi(v):
        return "mangler" if not isinstance(v, (int, float)) or math.isnan(v) else f"{v:.1f}"

    parts = [f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <title>Market Daily Report</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {{
      --bg: #0b0d10;
      --panel: #12161c;
      --panel-2: #171c23;
      --text: #e7edf3;
      --muted: #9aa7b5;
      --border: #27313d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    .wrap {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 24px 18px 40px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
    }}
    .topnote {{
      color: var(--muted);
      margin: 0 0 28px;
    }}
    .category {{
      margin: 0 0 28px;
      padding: 18px;
      border: 1px solid var(--border);
      border-radius: 16px;
      background: var(--panel);
    }}
    .category h2 {{
      margin: 0 0 6px;
      font-size: 24px;
    }}
    .category p {{
      margin: 0 0 18px;
      color: var(--muted);
    }}
    .instrument {{
      margin: 0 0 20px;
      padding: 16px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--panel-2);
    }}
    .instrument:last-child {{
      margin-bottom: 0;
    }}
    .instrument-head {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      align-items: baseline;
      margin-bottom: 12px;
    }}
    .instrument-head h3 {{
      margin: 0;
      font-size: 20px;
    }}
    .ticker {{
      color: var(--muted);
      font-weight: 600;
    }}
    .meta {{
      color: var(--muted);
      font-size: 14px;
    }}
    .charts {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 14px;
    }}
    figure {{
      margin: 0;
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      background: #0f141a;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      background: #0f141a;
    }}
    figcaption {{
      padding: 8px 10px;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 13px;
    }}
    .missing {{
      padding: 18px;
      border: 1px dashed var(--border);
      border-radius: 12px;
      color: var(--muted);
      background: #0f141a;
    }}
    footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Market Daily Report</h1>
    <p class="topnote">Forsiden viser kun weekly_compact.png og monthly_compact.png. Instrumentene er sortert innen hver kategori etter RSI(14) monthly fra lavest til høyest. Generert: {html.escape(str(generated))}</p>
"""]

    for category in categories:
        items = []
        for instrument_id in category.get("instrument_ids", []):
            asset = assets.get(instrument_id, {})
            monthly_rsi = (((asset.get("frames") or {}).get("monthly") or {}).get("rsi14"))
            sort_key = monthly_rsi if isinstance(monthly_rsi, (int, float)) and not math.isnan(monthly_rsi) else float("inf")
            items.append((sort_key, asset.get("display_name") or instrument_id, instrument_id, asset))
        items.sort(key=lambda x: (x[0], x[1]))

        parts.append(
            f'<section class="category"><h2>{html.escape(category.get("title", ""))}</h2>'
            f'<p>{html.escape(category.get("description", ""))}</p>'
        )

        for _, _, instrument_id, asset in items:
            display_name = asset.get("display_name") or instrument_id
            symbol_label = asset.get("symbol_label") or asset.get("resolved_symbol") or instrument_id
            resolved = asset.get("resolved_symbol")
            meta_bits = [f"RSI(14) monthly: {fmt_rsi((((asset.get('frames') or {}).get('monthly') or {}).get('rsi14')))}"]
            if resolved and resolved != symbol_label:
                meta_bits.append(f"data: {resolved}")

            weekly_path = f"charts/{instrument_id}_weekly_compact.png"
            monthly_path = f"charts/{instrument_id}_monthly_compact.png"

            parts.append(
                f'<article class="instrument">'
                f'<div class="instrument-head"><h3>{html.escape(display_name)}</h3>'
                f'<span class="ticker">{html.escape(symbol_label)}</span>'
                f'<span class="meta">{" • ".join(html.escape(bit) for bit in meta_bits)}</span></div>'
                f'<div class="charts">'
            )

            if weekly_path in file_set:
                parts.append(
                    f'<figure><img src="{html.escape(weekly_path)}" alt="{html.escape(display_name)} weekly compact">'
                    f'<figcaption>weekly_compact.png</figcaption></figure>'
                )
            else:
                parts.append('<div class="missing">weekly_compact.png mangler</div>')

            if monthly_path in file_set:
                parts.append(
                    f'<figure><img src="{html.escape(monthly_path)}" alt="{html.escape(display_name)} monthly compact">'
                    f'<figcaption>monthly_compact.png</figcaption></figure>'
                )
            else:
                parts.append('<div class="missing">monthly_compact.png mangler</div>')

            parts.append('</div></article>')

        parts.append('</section>')

    parts.append(
        "<footer>Datafiler finnes fortsatt i repoet, men forsiden er begrenset til disse grafene.</footer>"
        "</div></body></html>"
    )
    return "".join(parts)

summary = {
    "generated_local": NOW.isoformat(),
    "assets": {},
    "categories": [
        {
            "key": group["key"],
            "title": group["title"],
            "description": group["description"],
            "instrument_ids": [inst["id"] for inst in group["instruments"]],
        }
        for group in INSTRUMENT_GROUPS
    ],
}

for group in INSTRUMENT_GROUPS:
    for inst in group["instruments"]:
        instrument_id = inst["id"]
        df, resolved_symbol = get_instrument_series(inst)

        entry = {
            "id": instrument_id,
            "display_name": inst["label"],
            "symbol_label": inst["symbol_label"],
            "resolved_symbol": resolved_symbol,
            "source": inst["source"],
            "category_key": group["key"],
            "category_title": group["title"],
            "frames": {"daily": {}, "weekly": {}, "monthly": {}},
            "missing_data": False,
        }

        if df is None or df.empty:
            entry["missing_data"] = True
            summary["assets"][instrument_id] = entry
            log(f"missing data for {instrument_id}")
            continue

        daily, weekly, monthly = resample_frames(df)
        entry["frames"]["daily"] = frame_summary(daily)
        entry["frames"]["weekly"] = frame_summary(weekly)
        entry["frames"]["monthly"] = frame_summary(monthly)

        last_252 = daily.tail(252)
        if not last_252.empty:
            entry["52w_high"] = float(last_252["close_use"].max())
            entry["52w_low"] = float(last_252["close_use"].min())
        else:
            entry["52w_high"] = None
            entry["52w_low"] = None

        weekly_sma = weekly["sma36"].iloc[-1] if not weekly.empty else np.nan
        monthly_sma = monthly["sma36"].iloc[-1] if not monthly.empty else np.nan
        entry["dist_to_36WMA"] = float(pct(weekly["close_use"].iloc[-1], weekly_sma)) if pd.notna(weekly_sma) else None
        entry["dist_to_36MMA"] = float(pct(monthly["close_use"].iloc[-1], monthly_sma)) if pd.notna(monthly_sma) else None

        weekly_out = CHARTS / f"{instrument_id}_weekly_compact.png"
        monthly_out = CHARTS / f"{instrument_id}_monthly_compact.png"
        if not weekly.empty:
            plot_compact(weekly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - weekly", weekly_out)
        if not monthly.empty:
            plot_compact(monthly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - monthly", monthly_out)

        summary["assets"][instrument_id] = entry

news = {
    "nftrh": last_n_days_posts("https://nftrh.com/blog/feed/"),
    "northstar": last_n_days_posts("https://northstarbadcharts.com/feed/"),
}
with open(NEWS_DIR / "news.json", "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=2)

index = {
    "generated_local": NOW.isoformat(),
    "version": VERSION,
    "summary": summary,
    "notes": {
        "homepage": "Forsiden viser kun weekly_compact.png og monthly_compact.png gruppert etter kategori og sortert på RSI(14) monthly.",
        "instrument_count": len(ALL_IDS),
    },
}
with open(DOCS / "index.json", "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

files = sorted([f"charts/{fn.name}" for fn in CHARTS.glob("*.png")])
with open(DOCS / "filelist.json", "w", encoding="utf-8") as f:
    json.dump({"charts": files}, f, ensure_ascii=False, indent=2)

html_doc = build_homepage(index, files)
with open(DOCS / "index.html", "w", encoding="utf-8") as f:
    f.write(html_doc)

log(f"SUMMARY instruments={len(summary['assets'])} charts={len(files)} version={VERSION}")
flush_log()
print("Done.")
