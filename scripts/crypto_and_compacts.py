#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill missing instruments/charts after generate_report.py.

Denne jobben:
- fyller inn manglende data for weekly/monthly compact-grafer
- bruker mer robuste fallback-kandidater for Yahoo Finance
- oppdaterer kategorier på forsiden
- bytter Platina fra PLTM til PPLT
"""
import os
import json
import math
import re
import time
import html
from pathlib import Path

import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHARTS = DOCS / "charts"
INDEX = DOCS / "index.json"
FILELIST = DOCS / "filelist.json"

DOCS.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

HTTP = requests.Session()
HTTP.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
})

FRED_KEY = os.environ.get("FRED_API_KEY", "").strip()
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

INSTRUMENT_GROUPS = [
    {
        "key": "vekstsyklusen",
        "title": "1. Vekstsyklusen",
        "description": "Dette er instrumenter som sier mest om bred økonomisk aktivitet, syklisk styrke og regional risikovilje.",
        "instruments": [
            {"id": "SPY", "label": "S&P 500", "symbol_label": "SPY", "source": "yf", "candidates": ["SPY", "VOO"]},
            {"id": "IWM", "label": "Russell 2000", "symbol_label": "IWM", "source": "yf", "candidates": ["IWM", "VTWO"]},
            {"id": "EXSA", "label": "STOXX Europe 600", "symbol_label": "EXSA", "source": "yf", "candidates": ["EXSA.DE", "EXSA", "MEUD"]},
            {"id": "EEM", "label": "MSCI EM", "symbol_label": "EEM", "source": "yf", "candidates": ["EEM", "VWO"]},
            {"id": "VNQ", "label": "Housing US", "symbol_label": "VNQ", "source": "yf", "candidates": ["VNQ", "IYR", "SCHH"]},
            {"id": "TRET", "label": "Housing global", "symbol_label": "TRET", "source": "yf", "candidates": ["TRET", "REET", "VNQI"]},
        ],
    },
    {
        "key": "renter_og_finansielle_forhold",
        "title": "2. Renter, kurve og finansielle forhold",
        "description": "Dette er instrumenter som sier mest om pengepolitikk, rentekurve og finansielle forhold.",
        "instruments": [
            {"id": "UTWO", "label": "2-årig UST", "symbol_label": "UTWO", "source": "yf", "candidates": ["UTWO", "SHY", "VGSH", "USTB"]},
            {"id": "UTEN", "label": "10-årig UST", "symbol_label": "UTEN", "source": "yf", "candidates": ["UTEN", "IEF", "GOVT", "TLH"]},
            {"id": "2S10S", "label": "2s10s", "symbol_label": "STPU / UCT2", "source": "fred_spread"},
            {"id": "SCHP", "label": "10-årig realrente", "symbol_label": "SCHP", "source": "yf", "candidates": ["SCHP", "TIP"]},
        ],
    },
    {
        "key": "inflasjonssyklusen",
        "title": "3. Inflasjonssyklusen",
        "description": "Dette er instrumenter som typisk reagerer tidlig på inflasjonspress og råvaredrevet reflasjon.",
        "instruments": [
            {"id": "BCOM", "label": "Commodity", "symbol_label": "BCOM", "source": "yf", "candidates": ["BCOM", "PDBC", "DBC"]},
            {"id": "USO", "label": "Olje", "symbol_label": "USO", "source": "yf", "candidates": ["USO", "BNO"]},
            {"id": "UNG", "label": "Naturgass", "symbol_label": "UNG", "source": "yf", "candidates": ["UNG", "UNL"]},
            {"id": "COPX", "label": "Kobber", "symbol_label": "COPX", "source": "yf", "candidates": ["COPX", "CPER", "JJC"]},
        ],
    },
    {
        "key": "kredittsyklusen",
        "title": "4. Kredittsyklusen",
        "description": "Her følger du hvor mye stress eller lettelse det er i kredittmarkedet.",
        "instruments": [
            {"id": "HYG", "label": "US High Yield OAS", "symbol_label": "HYG", "source": "yf", "candidates": ["HYG", "JNK"]},
        ],
    },
    {
        "key": "valuta_og_dollar",
        "title": "5. Valuta- og dollar-syklusen",
        "description": "Dette er hovedinstrumentet for dollarregimet og globalt finansielt press.",
        "instruments": [
            {"id": "UUP", "label": "DXY", "symbol_label": "UUP", "source": "yf", "candidates": ["UUP", "USDU", "DX-Y.NYB"]},
        ],
    },
    {
        "key": "lederskap_i_aksjemarkedet",
        "title": "6. Lederskap innad i aksjemarkedet",
        "description": "Dette er instrumenter som sier noe om hvilke deler av aksjemarkedet som leder an.",
        "instruments": [
            {"id": "QQQ", "label": "Nasdaq-100", "symbol_label": "QQQ", "source": "yf", "candidates": ["QQQ", "QQQM"]},
            {"id": "SOXQ", "label": "SOX / semiconductors", "symbol_label": "SOXQ", "source": "yf", "candidates": ["SOXQ", "SMH", "SOXX"]},
        ],
    },
    {
        "key": "volatilitet_og_risikovilje",
        "title": "7. Volatilitet og risikovilje",
        "description": "Dette er instrumenter som sier mest om risikopåslag, spekulasjon og stress i markedet.",
        "instruments": [
            {"id": "VIXY", "label": "VIX", "symbol_label": "VIXY", "source": "yf", "candidates": ["VIXY", "^VIX"]},
            {"id": "BTC", "label": "BTC", "symbol_label": "BITO / IBIT", "source": "yf", "candidates": ["BITO", "IBIT", "BTC-USD"]},
            {"id": "ETHA", "label": "ETH", "symbol_label": "ETHA", "source": "yf", "candidates": ["ETHA", "ETH-USD"]},
        ],
    },
    {
        "key": "edelmetaller_og_nisjeravarer",
        "title": "8. Edelmetaller og nisjeråvarer",
        "description": "Dette er instrumenter som ofte fanger opp realrente, safe haven, industribruk og spesialsykluser.",
        "instruments": [
            {"id": "GLD", "label": "Gull", "symbol_label": "GLD", "source": "yf", "candidates": ["GLD", "IAU"]},
            {"id": "SLV", "label": "Sølv", "symbol_label": "SLV", "source": "yf", "candidates": ["SLV", "SIVR"]},
            {"id": "URA", "label": "Uranium", "symbol_label": "URA", "source": "yf", "candidates": ["URA", "URNM"]},
            {"id": "PPLT", "label": "Platina", "symbol_label": "PPLT", "source": "yf", "candidates": ["PPLT", "PLTM", "PL=F"]},
            {"id": "PALL", "label": "Palladium", "symbol_label": "PALL", "source": "yf", "candidates": ["PALL", "PA=F"]},
        ],
    },
]


def load_json(path: Path, default):
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return default
        return json.loads(raw)
    except Exception:
        return default


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s or "")


def sma(s, n):
    return s.rolling(n).mean()


def rsi(s, n=14):
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / n, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / n, adjust=False).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))


def macd(s, fast=12, slow=26, signal=9):
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def pct(a, b):
    return (a - b) / b if (b is not None and b != 0) else np.nan


def normalize_yf_df(df):
    if df is None or getattr(df, "empty", True):
        return None
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.get_level_values(0)
    out = out.rename(columns=str.lower)
    if "close" not in out.columns:
        return None
    out["close_use"] = pd.to_numeric(out["close"], errors="coerce")
    if "volume" not in out.columns:
        out["volume"] = np.nan
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out.dropna(subset=["close_use"])
    if len(out) < 80:
        return None
    return out


def try_yf_download(sym: str):
    attempts = [
        lambda: yf.download(sym, period="15y", interval="1d", auto_adjust=True, progress=False, threads=False),
        lambda: yf.download(sym, period="10y", interval="1d", auto_adjust=True, progress=False, threads=False),
        lambda: yf.Ticker(sym).history(period="15y", interval="1d", auto_adjust=True),
        lambda: yf.Ticker(sym).history(period="10y", interval="1d", auto_adjust=True),
    ]
    for fn in attempts:
        try:
            df = normalize_yf_df(fn())
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
    return None


def yf_series_from_candidates(candidates):
    for sym in candidates:
        df = try_yf_download(sym)
        if df is not None and not df.empty:
            print(f"[OK] {sym}")
            return df, sym
        time.sleep(0.5)
    return None, None


def fred_series(series_id):
    if not FRED_KEY:
        return None
    url = (
        f"{FRED_BASE}?series_id={series_id}"
        f"&api_key={FRED_KEY}&file_type=json&observation_start=1990-01-01"
    )
    try:
        r = HTTP.get(url, timeout=60)
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
        return df[["close_use", "volume"]]
    except Exception:
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
    out[f"sma{ma_len}"] = sma(out["close_use"], ma_len)
    out["rsi14"] = rsi(out["close_use"])
    m, sig, hist = macd(out["close_use"])
    out["macd"] = m
    out["macd_signal"] = sig
    out["macd_hist"] = hist
    return out


def resample_frames(df):
    daily = with_indicators(df)
    weekly = with_indicators(df.resample("W-FRI").last().dropna(how="all"))
    monthly = with_indicators(df.resample("ME").last().dropna(how="all"))
    return daily, weekly, monthly


def frame_summary(df, ma_len=36):
    if df is None or df.empty:
        return {}
    last = float(df["close_use"].iloc[-1])
    ma = df[f"sma{ma_len}"].iloc[-1] if f"sma{ma_len}" in df.columns else np.nan
    macd_cross = None
    if len(df) >= 2:
        last_delta = df["macd"].iloc[-1] - df["macd_signal"].iloc[-1]
        prev_delta = df["macd"].iloc[-2] - df["macd_signal"].iloc[-2]
        macd_cross = bool(last_delta > 0 and prev_delta <= 0)
    return {
        "last": last,
        "sma36": float(ma) if pd.notna(ma) else None,
        "close_above_sma36": bool(last > ma) if pd.notna(ma) else None,
        "rsi14": float(df["rsi14"].iloc[-1]) if pd.notna(df["rsi14"].iloc[-1]) else None,
        "macd": float(df["macd"].iloc[-1]) if pd.notna(df["macd"].iloc[-1]) else None,
        "macd_signal": float(df["macd_signal"].iloc[-1]) if pd.notna(df["macd_signal"].iloc[-1]) else None,
        "macd_hist": float(df["macd_hist"].iloc[-1]) if pd.notna(df["macd_hist"].iloc[-1]) else None,
        "macd_cross": macd_cross,
    }


def plot_compact(df, title, out_compact, ma_len=36):
    import matplotlib.dates as mdates
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
    axes[0].plot(df.index, df["close_use"], label="Close")
    axes[0].plot(df.index, sma(df["close_use"], ma_len), label=f"SMA{ma_len}")
    axes[0].set_title(title)
    axes[0].legend(loc="upper left")

    rr = rsi(df["close_use"])
    axes[1].plot(df.index, rr, label="RSI(14)")
    axes[1].axhline(70, linestyle="--", linewidth=0.8)
    axes[1].axhline(30, linestyle="--", linewidth=0.8)
    axes[1].legend(loc="upper left")

    mm, sig, hist = macd(df["close_use"])
    axes[2].plot(df.index, mm, label="MACD")
    axes[2].plot(df.index, sig, label="Signal")
    axes[2].bar(df.index, hist, alpha=0.5, label="Hist")
    locator = mdates.AutoDateLocator()
    axes[2].xaxis.set_major_locator(locator)
    axes[2].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    axes[2].legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(out_compact, dpi=120)
    plt.close(fig)


def build_homepage(index_data, filelist):
    assets = index_data.get("summary", {}).get("assets", {})
    categories = index_data.get("summary", {}).get("categories", [])
    generated = index_data.get("generated_local", "")
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
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.45; }}
    .wrap {{ max-width: 1500px; margin: 0 auto; padding: 24px 18px 40px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    .topnote {{ color: var(--muted); margin: 0 0 28px; }}
    .category {{ margin: 0 0 28px; padding: 18px; border: 1px solid var(--border); border-radius: 16px; background: var(--panel); }}
    .category h2 {{ margin: 0 0 6px; font-size: 24px; }}
    .category p {{ margin: 0 0 18px; color: var(--muted); }}
    .instrument {{ margin: 0 0 20px; padding: 16px; border: 1px solid var(--border); border-radius: 14px; background: var(--panel-2); }}
    .instrument:last-child {{ margin-bottom: 0; }}
    .instrument-head {{ display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: baseline; margin-bottom: 12px; }}
    .instrument-head h3 {{ margin: 0; font-size: 20px; }}
    .ticker {{ color: var(--muted); font-weight: 600; }}
    .meta {{ color: var(--muted); font-size: 14px; }}
    .charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 14px; }}
    figure {{ margin: 0; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: #0f141a; }}
    img {{ display: block; width: 100%; height: auto; background: #0f141a; }}
    figcaption {{ padding: 8px 10px; border-top: 1px solid var(--border); color: var(--muted); font-size: 13px; }}
    .missing {{ padding: 18px; border: 1px dashed var(--border); border-radius: 12px; color: var(--muted); background: #0f141a; }}
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
            monthly_rsi = (((asset.get("frames") or {}).get("monthly") or {}).get("rsi14"))
            meta_bits = [f"RSI(14) monthly: {fmt_rsi(monthly_rsi)}"]
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
            parts.append("</div></article>")
        parts.append("</section>")
    parts.append("</div></body></html>")
    return "".join(parts)


def main():
    idx = load_json(INDEX, default={})
    current_assets = ((idx.get("summary") or {}).get("assets") or {}) if isinstance(idx, dict) else {}

    for old_name in ("PLTM_weekly_compact.png", "PLTM_monthly_compact.png"):
        old_path = CHARTS / old_name
        if old_path.exists():
            try:
                old_path.unlink()
            except Exception:
                pass

    summary = {
        "generated_local": idx.get("generated_local") or pd.Timestamp.utcnow().isoformat(),
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
            asset_existing = current_assets.get(instrument_id) or {}
            if instrument_id == "PPLT" and not asset_existing:
                asset_existing = current_assets.get("PLTM") or {}

            if inst["source"] == "fred_spread":
                df, resolved_symbol = fred_2s10s_series()
            else:
                df, resolved_symbol = yf_series_from_candidates(inst["candidates"])

            entry = {
                "id": instrument_id,
                "display_name": inst["label"],
                "symbol_label": inst["symbol_label"],
                "resolved_symbol": resolved_symbol or asset_existing.get("resolved_symbol"),
                "source": inst["source"],
                "category_key": group["key"],
                "category_title": group["title"],
                "frames": {"daily": {}, "weekly": {}, "monthly": {}},
                "missing_data": False,
            }

            if df is None or df.empty:
                frames = asset_existing.get("frames") or {}
                entry["frames"]["daily"] = frames.get("daily") or {}
                entry["frames"]["weekly"] = frames.get("weekly") or {}
                entry["frames"]["monthly"] = frames.get("monthly") or {}
                entry["52w_high"] = asset_existing.get("52w_high")
                entry["52w_low"] = asset_existing.get("52w_low")
                entry["dist_to_36WMA"] = asset_existing.get("dist_to_36WMA")
                entry["dist_to_36MMA"] = asset_existing.get("dist_to_36MMA")
                entry["missing_data"] = True
                print(f"[MISS] {instrument_id}")
                summary["assets"][instrument_id] = entry
                continue

            daily, weekly, monthly = resample_frames(df)
            entry["frames"]["daily"] = frame_summary(daily)
            entry["frames"]["weekly"] = frame_summary(weekly)
            entry["frames"]["monthly"] = frame_summary(monthly)

            last_252 = daily.tail(252)
            entry["52w_high"] = float(last_252["close_use"].max()) if not last_252.empty else None
            entry["52w_low"] = float(last_252["close_use"].min()) if not last_252.empty else None
            weekly_sma = weekly["sma36"].iloc[-1] if not weekly.empty else np.nan
            monthly_sma = monthly["sma36"].iloc[-1] if not monthly.empty else np.nan
            entry["dist_to_36WMA"] = float(pct(weekly["close_use"].iloc[-1], weekly_sma)) if pd.notna(weekly_sma) else None
            entry["dist_to_36MMA"] = float(pct(monthly["close_use"].iloc[-1], monthly_sma)) if pd.notna(monthly_sma) else None

            if not weekly.empty:
                plot_compact(weekly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - weekly", CHARTS / f"{instrument_id}_weekly_compact.png")
            if not monthly.empty:
                plot_compact(monthly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - monthly", CHARTS / f"{instrument_id}_monthly_compact.png")

            summary["assets"][instrument_id] = entry

    idx["summary"] = summary
    idx["generated_local"] = pd.Timestamp.utcnow().isoformat()
    idx.setdefault("notes", {})
    idx["notes"]["homepage"] = "Forsiden viser kun weekly_compact.png og monthly_compact.png gruppert etter kategori og sortert på RSI(14) monthly."
    idx["notes"]["instrument_count"] = sum(len(g["instruments"]) for g in INSTRUMENT_GROUPS)
    save_json(INDEX, idx)

    files = sorted([f"charts/{fn.name}" for fn in CHARTS.glob("*.png")])
    save_json(FILELIST, {"charts": files})

    (DOCS / "index.html").write_text(build_homepage(idx, files), encoding="utf-8")
    print("crypto_and_compacts.py: backfill complete")


if __name__ == "__main__":
    main()
