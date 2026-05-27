#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py  –  Market Daily Report
Versjon: 2026-05-27-northstar-v3

Forbedringer fra v2:
- Flere instrumenter: GDX, GDXJ, SIL, SILJ, URNM, SOXQ, XLE, XME, ACWI, LQD, TLT, IAI
- Ratio-charts: GLD/SPY, GDX/GLD, SLV/GLD, URA/SPY, XLE/SPY, EEM/SPY
- 3yr MA avstand (Northstar lower-risk entry filter)
- Northstar-kompatibel portfolio score per instrument
- NFTRH macro-indikatorer: Gold-Silver Ratio (GSR), 10yr yield via FRED
- Ukentlig portfolio-brief injiseres i index.html
"""
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
import matplotlib.dates as mdates

VERSION = "2026-05-27-northstar-v3"
TZ = ZoneInfo("Europe/Oslo")
NOW = datetime.now(tz=TZ)

DOCS   = Path("docs")
CHARTS = DOCS / "charts"
NEWS_DIR = DOCS / "news"

DOCS.mkdir(exist_ok=True)
CHARTS.mkdir(exist_ok=True)
NEWS_DIR.mkdir(exist_ok=True)

FORCE_INPUT = os.environ.get("FORCE_RUN", "false").lower() == "true"
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
FORCE = FORCE_INPUT or IN_GITHUB_ACTIONS

print(f"Full run: {FORCE} at {NOW.isoformat()} (version {VERSION})")

with open(DOCS / "run_mode.json", "w", encoding="utf-8") as f:
    json.dump({"force": FORCE, "now": NOW.isoformat(), "version": VERSION}, f, indent=2)

if not FORCE and not ((NOW.hour == 19 and NOW.minute >= 45) or (NOW.hour == 20 and NOW.minute <= 10)):
    with open(DOCS / "heartbeat.json", "w", encoding="utf-8") as f:
        json.dump({"last_run_local": NOW.isoformat(), "version": VERSION}, f, indent=2)
    with open(DOCS / "index.html", "w", encoding="utf-8") as f:
        f.write(
            "<!doctype html><meta charset='utf-8'><title>Market Daily Report</title>"
            f"<h1>Market Daily Report</h1><p>Generert: {NOW.isoformat()}</p>"
            "<p>Full rapport genereres kl. 20:00 Europe/Oslo.</p>"
        )
    raise SystemExit(0)

LOG = []
def log(msg):
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

FRED_KEY  = os.environ.get("FRED_API_KEY", "").strip()
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# ─────────────────────────────────────────────
#  INSTRUMENT UNIVERSE
# ─────────────────────────────────────────────
INSTRUMENT_GROUPS = [
    {
        "key": "makro_renter",
        "title": "0. Makro & Renter",
        "description": "10yr yield, yield-kurve, realrente og kredittstress. Forteller deg hvilket makroregime vi er i.",
        "instruments": [
            {"id": "UTEN",  "label": "10-årig UST",     "symbol_label": "UTEN",   "source": "yf",          "candidates": ["UTEN"]},
            {"id": "2S10S", "label": "2s10s kurve",      "symbol_label": "FRED",   "source": "fred_spread"},
            {"id": "SCHP",  "label": "10yr realrente",   "symbol_label": "SCHP",   "source": "yf",          "candidates": ["SCHP"]},
            {"id": "TLT",   "label": "20yr UST",         "symbol_label": "TLT",    "source": "yf",          "candidates": ["TLT"]},
            {"id": "HYG",   "label": "High Yield OAS",   "symbol_label": "HYG",    "source": "yf",          "candidates": ["HYG", "JNK"]},
            {"id": "LQD",   "label": "IG Kreditt",       "symbol_label": "LQD",    "source": "yf",          "candidates": ["LQD"]},
        ],
    },
    {
        "key": "vekstsyklusen",
        "title": "1. Vekstsyklusen",
        "description": "Bred økonomisk aktivitet, syklisk styrke og regional risikovilje.",
        "instruments": [
            {"id": "SPY",   "label": "S&P 500",          "symbol_label": "SPY",    "source": "yf", "candidates": ["SPY"]},
            {"id": "QQQ",   "label": "Nasdaq-100",        "symbol_label": "QQQ",    "source": "yf", "candidates": ["QQQ"]},
            {"id": "IWM",   "label": "Russell 2000",      "symbol_label": "IWM",    "source": "yf", "candidates": ["IWM"]},
            {"id": "ACWI",  "label": "ACWI Global",       "symbol_label": "ACWI",   "source": "yf", "candidates": ["ACWI"]},
            {"id": "EXSA",  "label": "STOXX Europe 600",  "symbol_label": "EXSA",   "source": "yf", "candidates": ["EXSA.DE", "EXSA", "MEUD"]},
            {"id": "EEM",   "label": "MSCI EM",           "symbol_label": "EEM",    "source": "yf", "candidates": ["EEM", "VWO"]},
            {"id": "SOXQ",  "label": "Semiconductors",    "symbol_label": "SOXQ",   "source": "yf", "candidates": ["SOXQ", "SOXX"]},
            {"id": "IAI",   "label": "Broker/Dealers",    "symbol_label": "IAI",    "source": "yf", "candidates": ["IAI"]},
            {"id": "VNQ",   "label": "Housing US",        "symbol_label": "VNQ",    "source": "yf", "candidates": ["VNQ"]},
        ],
    },
    {
        "key": "inflasjon_commodities",
        "title": "2. Inflasjon & Råvarer",
        "description": "Reagerer tidlig på inflasjonspress og råvaredrevet reflasjon.",
        "instruments": [
            {"id": "BCOM",  "label": "Commodity bred",   "symbol_label": "BCOM",   "source": "yf", "candidates": ["BCOM", "PDBC", "DBC"]},
            {"id": "USO",   "label": "Olje (WTI)",       "symbol_label": "USO",    "source": "yf", "candidates": ["USO", "BNO"]},
            {"id": "UNG",   "label": "Naturgass",        "symbol_label": "UNG",    "source": "yf", "candidates": ["UNG"]},
            {"id": "COPX",  "label": "Kobber miners",    "symbol_label": "COPX",   "source": "yf", "candidates": ["COPX", "JJC"]},
            {"id": "XME",   "label": "Metals & Mining",  "symbol_label": "XME",    "source": "yf", "candidates": ["XME"]},
            {"id": "XLE",   "label": "Energy sektor",    "symbol_label": "XLE",    "source": "yf", "candidates": ["XLE"]},
            {"id": "DBA",   "label": "Agri / mat",       "symbol_label": "DBA",    "source": "yf", "candidates": ["DBA"]},
        ],
    },
    {
        "key": "edelmetaller",
        "title": "3. Edelmetaller",
        "description": "Gull, sølv, gruvere og ratio-signaler. Northstar-sektoren.",
        "instruments": [
            {"id": "GLD",   "label": "Gull",             "symbol_label": "GLD",    "source": "yf", "candidates": ["GLD", "IAU"]},
            {"id": "SLV",   "label": "Sølv",             "symbol_label": "SLV",    "source": "yf", "candidates": ["SLV", "SIVR"]},
            {"id": "GDX",   "label": "Gull miners",      "symbol_label": "GDX",    "source": "yf", "candidates": ["GDX"]},
            {"id": "GDXJ",  "label": "Junior gull",      "symbol_label": "GDXJ",   "source": "yf", "candidates": ["GDXJ"]},
            {"id": "SIL",   "label": "Sølv miners",      "symbol_label": "SIL",    "source": "yf", "candidates": ["SIL"]},
            {"id": "SILJ",  "label": "Junior sølv",      "symbol_label": "SILJ",   "source": "yf", "candidates": ["SILJ"]},
            {"id": "PPLT",  "label": "Platina",          "symbol_label": "PPLT",   "source": "yf", "candidates": ["PPLT", "PLTM"]},
            {"id": "PALL",  "label": "Palladium",        "symbol_label": "PALL",   "source": "yf", "candidates": ["PALL"]},
        ],
    },
    {
        "key": "uranium_energy_transition",
        "title": "4. Uranium & Energiomstilling",
        "description": "Uranium, kjernekraft og ren energi. Northstar bullish roadmap.",
        "instruments": [
            {"id": "URA",   "label": "Uranium ETF",      "symbol_label": "URA",    "source": "yf", "candidates": ["URA"]},
            {"id": "URNM",  "label": "Uranium miners",   "symbol_label": "URNM",   "source": "yf", "candidates": ["URNM"]},
            {"id": "NLR",   "label": "Nuclear energy",   "symbol_label": "NLR",    "source": "yf", "candidates": ["NLR"]},
            {"id": "ICLN",  "label": "Clean energy",     "symbol_label": "ICLN",   "source": "yf", "candidates": ["ICLN"]},
        ],
    },
    {
        "key": "valuta_dollar",
        "title": "5. Valuta & Dollar",
        "description": "Dollar-regimet og globalt finansielt press. Northstar Milkshake Arc roadmap: bearish USD langsiktig.",
        "instruments": [
            {"id": "UUP",   "label": "DXY",              "symbol_label": "UUP",    "source": "yf", "candidates": ["UUP", "USDU"]},
            {"id": "FXE",   "label": "EUR/USD",          "symbol_label": "FXE",    "source": "yf", "candidates": ["FXE"]},
            {"id": "FXY",   "label": "JPY",              "symbol_label": "FXY",    "source": "yf", "candidates": ["FXY"]},
            {"id": "CEW",   "label": "EM Currencies",    "symbol_label": "CEW",    "source": "yf", "candidates": ["CEW"]},
        ],
    },
    {
        "key": "volatilitet_risiko",
        "title": "6. Volatilitet & Risiko",
        "description": "Risikopåslag, spekulasjon og stress. VIX-complacency er advarselssignal.",
        "instruments": [
            {"id": "VIXY",  "label": "VIX",              "symbol_label": "VIXY",   "source": "yf", "candidates": ["VIXY"]},
            {"id": "BTC",   "label": "Bitcoin",          "symbol_label": "BITO",   "source": "yf", "candidates": ["BITO", "IBIT", "BTC-USD"]},
            {"id": "ETHA",  "label": "Ethereum",         "symbol_label": "ETHA",   "source": "yf", "candidates": ["ETHA", "ETH-USD"]},
        ],
    },
]

# Ratio pairs: (teller_id, nevner_id, label)
RATIO_PAIRS = [
    ("GLD",  "SPY",  "GLD/SPY"),
    ("GDX",  "GLD",  "GDX/GLD"),
    ("SLV",  "GLD",  "SLV/GLD"),
    ("URA",  "SPY",  "URA/SPY"),
    ("XLE",  "SPY",  "XLE/SPY"),
    ("EEM",  "SPY",  "EEM/SPY"),
    ("IWM",  "SPY",  "IWM/SPY"),
    ("COPX", "SPY",  "COPX/SPY"),
]

ALL_IDS = [inst["id"] for group in INSTRUMENT_GROUPS for inst in group["instruments"]]

# ─────────────────────────────────────────────
#  DATA HELPERS
# ─────────────────────────────────────────────
def SMA(s, n):
    return s.rolling(n).mean()

def RSI(s, n=14):
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1/n, adjust=False).mean() / dn.ewm(alpha=1/n, adjust=False).mean()
    return 100 - (100 / (1 + rs))

def MACD(s, fast=12, slow=26, sig=9):
    ef = s.ewm(span=fast, adjust=False).mean()
    es = s.ewm(span=slow, adjust=False).mean()
    m  = ef - es
    sl = m.ewm(span=sig, adjust=False).mean()
    return m, sl, m - sl

def pct(a, b):
    return (a - b) / b if (b is not None and b != 0) else np.nan

def safe_id(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)

def normalize_yf_df(data):
    if data is None or getattr(data, "empty", True):
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
    if len(df) < 50:
        return None
    return df

def yf_series_from_candidates(candidates):
    for sym in candidates:
        for attempt in range(3):
            try:
                data = yf.download(sym, period="max", interval="1d",
                                   auto_adjust=True, progress=False,
                                   session=YF_SESSION, threads=False)
                df = normalize_yf_df(data)
                if df is not None and not df.empty:
                    log(f"  yf ok: {sym}")
                    return df, sym
            except Exception as e:
                log(f"  yf error {sym} try{attempt+1}: {e}")
            time.sleep(1 + attempt)
    return None, None

def fred_series(series_id):
    if not FRED_KEY:
        return None
    url = (f"{FRED_BASE}?series_id={series_id}"
           f"&api_key={FRED_KEY}&file_type=json&observation_start=1990-01-01")
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
        log(f"  fred ok: {series_id}")
        return df[["close_use", "volume"]]
    except Exception as e:
        log(f"  fred error {series_id}: {e}")
        return None

def fred_2s10s_series():
    y2  = fred_series("DGS2")
    y10 = fred_series("DGS10")
    if y2 is None or y10 is None:
        return None, None
    df = pd.DataFrame(index=y10.index.union(y2.index))
    df["y2"]  = y2["close_use"]
    df["y10"] = y10["close_use"]
    df = df.sort_index().ffill().dropna()
    df["close_use"] = df["y10"] - df["y2"]
    df["volume"] = np.nan
    return df[["close_use", "volume"]], "FRED:DGS10-DGS2"

def get_instrument_series(inst):
    if inst["source"] == "yf":
        return yf_series_from_candidates(inst["candidates"])
    if inst["source"] == "fred_spread":
        return fred_2s10s_series()
    raise ValueError(f"Unknown source: {inst['source']}")

def with_indicators(df, ma_len=36):
    out = df.copy()
    out[f"sma{ma_len}"]  = SMA(out["close_use"], ma_len)
    out["sma156"]        = SMA(out["close_use"], 156)   # 3yr MA (weekly)
    out["rsi14"]         = RSI(out["close_use"])
    m, sl, hist          = MACD(out["close_use"])
    out["macd"]          = m
    out["macd_signal"]   = sl
    out["macd_hist"]     = hist
    return out

def resample_frames(base_df):
    daily   = with_indicators(base_df)
    weekly  = with_indicators(base_df.resample("W-FRI").last().dropna(how="all"))
    monthly = with_indicators(base_df.resample("ME").last().dropna(how="all"))
    return daily, weekly, monthly

def frame_summary(df, ma_len=36):
    if df is None or df.empty:
        return {}
    last = float(df["close_use"].iloc[-1])
    sma  = df[f"sma{ma_len}"].iloc[-1] if f"sma{ma_len}" in df.columns else np.nan
    sma3yr = df["sma156"].iloc[-1] if "sma156" in df.columns else np.nan
    dist_3yr = pct(last, float(sma3yr)) if pd.notna(sma3yr) else None
    macd_cross = None
    if len(df) >= 2:
        ld = df["macd"].iloc[-1] - df["macd_signal"].iloc[-1]
        pd_ = df["macd"].iloc[-2] - df["macd_signal"].iloc[-2]
        macd_cross = bool(ld > 0 and pd_ <= 0)
    return {
        "last":              last,
        "sma36":             float(sma) if pd.notna(sma) else None,
        "sma156_3yr":        float(sma3yr) if pd.notna(sma3yr) else None,
        "close_above_sma36": bool(last > sma) if pd.notna(sma) else None,
        "dist_to_3yr_MA":    float(dist_3yr) if dist_3yr is not None else None,
        "rsi14":             float(df["rsi14"].iloc[-1]) if pd.notna(df["rsi14"].iloc[-1]) else None,
        "macd":              float(df["macd"].iloc[-1]) if pd.notna(df["macd"].iloc[-1]) else None,
        "macd_signal":       float(df["macd_signal"].iloc[-1]) if pd.notna(df["macd_signal"].iloc[-1]) else None,
        "macd_hist":         float(df["macd_hist"].iloc[-1]) if pd.notna(df["macd_hist"].iloc[-1]) else None,
        "macd_cross":        macd_cross,
    }

# ─────────────────────────────────────────────
#  PLOTTING
# ─────────────────────────────────────────────
def plot_compact(df, title, out_path, ma_len=36, dark=True):
    try:
        style_bg   = "#0b0d10" if dark else "white"
        style_fg   = "#e7edf3" if dark else "black"
        style_grid = "#27313d" if dark else "#eeeeee"
        style_ma   = "#f0a500"
        style_3yr  = "#e05050"
        style_price= "#4a9eff"

        fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 8),
                                 facecolor=style_bg)
        for ax in axes:
            ax.set_facecolor(style_bg)
            ax.tick_params(colors=style_fg)
            ax.spines[:].set_color(style_grid)
            ax.yaxis.label.set_color(style_fg)
            ax.xaxis.label.set_color(style_fg)
            ax.title.set_color(style_fg)
            ax.grid(True, color=style_grid, linewidth=0.5)

        # Price + MAs
        axes[0].plot(df.index, df["close_use"], color=style_price, label="Close", linewidth=1.2)
        axes[0].plot(df.index, SMA(df["close_use"], ma_len), color=style_ma,
                     label=f"SMA{ma_len}", linewidth=1.0)
        sma3 = SMA(df["close_use"], 156)
        if sma3.notna().any():
            axes[0].plot(df.index, sma3, color=style_3yr, linestyle="--",
                         label="SMA156 (3yr)", linewidth=0.9)
        axes[0].set_title(title, fontsize=11)
        axes[0].legend(loc="upper left", fontsize=8, facecolor=style_bg,
                       labelcolor=style_fg, framealpha=0.7)

        # RSI
        r = RSI(df["close_use"])
        axes[1].plot(df.index, r, color="#7ec8e3", label="RSI(14)", linewidth=1.0)
        axes[1].axhline(70, color="#e05050", linestyle="--", linewidth=0.8)
        axes[1].axhline(50, color=style_grid, linestyle=":", linewidth=0.6)
        axes[1].axhline(30, color="#50c878", linestyle="--", linewidth=0.8)
        axes[1].set_ylim(0, 100)
        axes[1].legend(loc="upper left", fontsize=8, facecolor=style_bg,
                       labelcolor=style_fg, framealpha=0.7)

        # MACD
        m, sig, hist = MACD(df["close_use"])
        colors = ["#50c878" if v >= 0 else "#e05050" for v in hist]
        axes[2].bar(df.index, hist, color=colors, alpha=0.6, label="Hist", width=5)
        axes[2].plot(df.index, m,   color="#4a9eff", label="MACD",   linewidth=1.0)
        axes[2].plot(df.index, sig, color=style_ma,  label="Signal", linewidth=1.0)
        locator = mdates.AutoDateLocator()
        axes[2].xaxis.set_major_locator(locator)
        axes[2].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        axes[2].legend(loc="upper left", fontsize=8, facecolor=style_bg,
                       labelcolor=style_fg, framealpha=0.7)

        plt.tight_layout(pad=0.8)
        plt.savefig(out_path, dpi=120, facecolor=style_bg)
        plt.close(fig)
    except Exception as e:
        log(f"plot error {title}: {e}")

def plot_ratio(df_num, df_den, label, out_path, dark=True):
    """Plot ratio chart between two series."""
    try:
        combined = pd.DataFrame({
            "num": df_num["close_use"],
            "den": df_den["close_use"],
        }).dropna()
        if len(combined) < 50:
            return
        combined["ratio"] = combined["num"] / combined["den"]
        weekly = combined["ratio"].resample("W-FRI").last().dropna()
        if len(weekly) < 36:
            return

        style_bg   = "#0b0d10" if dark else "white"
        style_fg   = "#e7edf3" if dark else "black"
        style_grid = "#27313d" if dark else "#eeeeee"

        fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10, 6),
                                 facecolor=style_bg)
        for ax in axes:
            ax.set_facecolor(style_bg)
            ax.tick_params(colors=style_fg)
            ax.spines[:].set_color(style_grid)
            ax.grid(True, color=style_grid, linewidth=0.5)

        axes[0].plot(weekly.index, weekly.values, color="#f0a500", linewidth=1.2)
        axes[0].plot(weekly.index, SMA(pd.Series(weekly.values, index=weekly.index), 36).values,
                     color="#4a9eff", linewidth=0.9, linestyle="--", label="SMA36")
        axes[0].set_title(f"Ratio: {label}", fontsize=11, color=style_fg)
        axes[0].legend(fontsize=8, facecolor=style_bg, labelcolor=style_fg, framealpha=0.7)

        rr = RSI(pd.Series(weekly.values, index=weekly.index))
        axes[1].plot(weekly.index, rr.values, color="#7ec8e3", linewidth=1.0)
        axes[1].axhline(70, color="#e05050", linestyle="--", linewidth=0.8)
        axes[1].axhline(30, color="#50c878", linestyle="--", linewidth=0.8)
        axes[1].set_ylim(0, 100)
        axes[1].set_ylabel("RSI(14)", color=style_fg, fontsize=9)

        locator = mdates.AutoDateLocator()
        axes[1].xaxis.set_major_locator(locator)
        axes[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        plt.tight_layout(pad=0.8)
        plt.savefig(out_path, dpi=120, facecolor=style_bg)
        plt.close(fig)
        log(f"  ratio chart ok: {label}")
    except Exception as e:
        log(f"  ratio chart error {label}: {e}")

# ─────────────────────────────────────────────
#  NORTHSTAR PORTFOLIO SCORE
# ─────────────────────────────────────────────
def northstar_score(entry):
    """
    Beregn Northstar-inspirert score 0-100 for hvert instrument.
    Høy score = bullish + lower-risk entry.
    Logikk:
      - Above 3yr MA weekly: +20 (trend bekreftet)
      - Dist til 3yr MA < 15%: +20 (ikke stretched)
      - Weekly RSI < 60: +15 (ikke overbought)
      - Monthly RSI < 65: +15 (ikke stretched på monthly)
      - MACD weekly positiv: +10
      - Weekly RSI > 40: +10 (ikke oversold crash)
      - Above SMA36 weekly: +10
    """
    score = 0
    notes = []
    w = entry.get("frames", {}).get("weekly") or {}
    m = entry.get("frames", {}).get("monthly") or {}

    dist3yr = w.get("dist_to_3yr_MA")
    above36 = w.get("close_above_sma36")
    wrsi    = w.get("rsi14")
    mrsi    = m.get("rsi14")
    macd_h  = w.get("macd_hist")

    if above36 is True:
        score += 20
        notes.append("✓ Over 3yr MA")
    elif above36 is False:
        notes.append("✗ Under 3yr MA")

    if dist3yr is not None:
        pct_dist = dist3yr * 100
        if pct_dist < 5:
            score += 20
            notes.append(f"✓ Nær 3yr MA ({pct_dist:.1f}%)")
        elif pct_dist < 15:
            score += 12
            notes.append(f"~ Moderat stretched ({pct_dist:.1f}%)")
        else:
            notes.append(f"✗ Stretched fra 3yr MA ({pct_dist:.1f}%)")

    if wrsi is not None:
        if 40 <= wrsi <= 60:
            score += 25
            notes.append(f"✓ RSI weekly ideell ({wrsi:.1f})")
        elif wrsi < 40:
            score += 10
            notes.append(f"~ RSI weekly lav ({wrsi:.1f})")
        elif wrsi <= 70:
            score += 8
            notes.append(f"~ RSI weekly høy ({wrsi:.1f})")
        else:
            notes.append(f"✗ RSI weekly overbought ({wrsi:.1f})")

    if mrsi is not None:
        if mrsi < 60:
            score += 15
            notes.append(f"✓ RSI monthly ok ({mrsi:.1f})")
        elif mrsi < 70:
            score += 7
            notes.append(f"~ RSI monthly høy ({mrsi:.1f})")
        else:
            notes.append(f"✗ RSI monthly overbought ({mrsi:.1f})")

    if macd_h is not None and macd_h > 0:
        score += 10
        notes.append("✓ MACD hist positiv")

    return min(score, 100), notes

def score_label(score):
    if score >= 75: return "🟢 Lavrisiko entry"
    if score >= 50: return "🟡 Nøytral"
    if score >= 30: return "🟠 Avvent"
    return "🔴 Unngå/trim"

# ─────────────────────────────────────────────
#  NEWS
# ─────────────────────────────────────────────
def fetch_first_image_from_page(url):
    try:
        rr = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        soup = __import__("bs4").BeautifulSoup(rr.text, "lxml")
        meta = (soup.find("meta", property="og:image") or
                soup.find("meta", attrs={"name": "twitter:image"}))
        if meta and meta.get("content"):
            return meta["content"]
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception:
        pass
    return None

def last_n_days_posts(url, days=4):
    out = []
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = __import__("bs4").BeautifulSoup(r.text, "lxml")
        items = soup.find_all("item")
        cutoff = pd.Timestamp(NOW.date()) - pd.Timedelta(days=days)
        for it in items[:20]:
            tn = it.find("title")
            ln = it.find("link")
            if not tn or not ln:
                continue
            title = tn.get_text(strip=True)
            link  = ln.get_text(strip=True)
            pub   = it.find("pubdate")
            ts    = pd.to_datetime(pub.get_text(strip=True)) if pub else None
            if ts is not None:
                if ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                if ts.tz_convert(TZ) < pd.Timestamp(cutoff, tz=TZ):
                    continue
            rec = {"title": title, "link": link,
                   "published": ts.tz_convert(TZ).isoformat() if ts else ""}
            img_url = fetch_first_image_from_page(link)
            if img_url:
                try:
                    ir = requests.get(img_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                    ir.raise_for_status()
                    ext = os.path.splitext(urlparse(img_url).path)[1].lower() or ".jpg"
                    fname = f"news_{safe_id(title)}{ext if ext in ['.jpg','.jpeg','.png'] else '.jpg'}"
                    with open(NEWS_DIR / fname, "wb") as f:
                        f.write(ir.content)
                    rec["image"] = f"news/{fname}"
                except Exception:
                    pass
            out.append(rec)
    except Exception as e:
        log(f"rss error {url}: {e}")
    return out

# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────
log(f"Starting data collection – {len(ALL_IDS)} instruments")

# Cache raw series for ratio charts
raw_series_cache = {}

summary = {
    "generated_local": NOW.isoformat(),
    "assets": {},
    "categories": [
        {
            "key": g["key"],
            "title": g["title"],
            "description": g["description"],
            "instrument_ids": [inst["id"] for inst in g["instruments"]],
        }
        for g in INSTRUMENT_GROUPS
    ],
}

for group in INSTRUMENT_GROUPS:
    for inst in group["instruments"]:
        iid = inst["id"]
        log(f"Fetching {iid}...")
        df, resolved = get_instrument_series(inst)

        entry = {
            "id": iid,
            "display_name": inst["label"],
            "symbol_label": inst["symbol_label"],
            "resolved_symbol": resolved,
            "source": inst["source"],
            "category_key": group["key"],
            "category_title": group["title"],
            "frames": {"daily": {}, "weekly": {}, "monthly": {}},
            "missing_data": False,
        }

        if df is None or df.empty:
            entry["missing_data"] = True
            summary["assets"][iid] = entry
            log(f"  MISSING: {iid}")
            continue

        raw_series_cache[iid] = df
        daily, weekly, monthly = resample_frames(df)

        entry["frames"]["daily"]   = frame_summary(daily)
        entry["frames"]["weekly"]  = frame_summary(weekly)
        entry["frames"]["monthly"] = frame_summary(monthly)

        last_252 = daily.tail(252)
        entry["52w_high"] = float(last_252["close_use"].max()) if not last_252.empty else None
        entry["52w_low"]  = float(last_252["close_use"].min()) if not last_252.empty else None

        wsma = weekly["sma36"].iloc[-1]  if not weekly.empty  else np.nan
        msma = monthly["sma36"].iloc[-1] if not monthly.empty else np.nan
        entry["dist_to_36WMA"] = float(pct(weekly["close_use"].iloc[-1],  wsma)) if pd.notna(wsma) else None
        entry["dist_to_36MMA"] = float(pct(monthly["close_use"].iloc[-1], msma)) if pd.notna(msma) else None

        # Northstar score
        score, score_notes = northstar_score(entry)
        entry["northstar_score"]       = score
        entry["northstar_score_label"] = score_label(score)
        entry["northstar_notes"]       = score_notes

        # Charts
        if not weekly.empty:
            plot_compact(weekly.tail(400),
                         f"{inst['label']} ({inst['symbol_label']}) – weekly",
                         CHARTS / f"{iid}_weekly_compact.png")
        if not monthly.empty:
            plot_compact(monthly.tail(400),
                         f"{inst['label']} ({inst['symbol_label']}) – monthly",
                         CHARTS / f"{iid}_monthly_compact.png")

        summary["assets"][iid] = entry
        log(f"  OK: {iid} score={score}")

# ─────────────────────────────────────────────
#  RATIO CHARTS
# ─────────────────────────────────────────────
log("Building ratio charts...")
ratio_results = {}
for (num_id, den_id, label) in RATIO_PAIRS:
    if num_id in raw_series_cache and den_id in raw_series_cache:
        ratio_id = f"RATIO_{num_id}_{den_id}"
        out_path = CHARTS / f"{ratio_id}_weekly_compact.png"
        plot_ratio(raw_series_cache[num_id], raw_series_cache[den_id], label, out_path)
        ratio_results[ratio_id] = {
            "label": label, "numerator": num_id, "denominator": den_id,
            "chart_weekly": f"charts/{ratio_id}_weekly_compact.png"
        }

# ─────────────────────────────────────────────
#  NEWS
# ─────────────────────────────────────────────
log("Fetching news...")
news = {
    "nftrh":     last_n_days_posts("https://nftrh.com/blog/feed/"),
    "northstar": last_n_days_posts("https://northstarbadcharts.com/feed/"),
}
with open(NEWS_DIR / "news.json", "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
#  PORTFOLIO BRIEF
# ─────────────────────────────────────────────
def build_portfolio_brief(assets_dict):
    """
    Genererer ukentlig portfolio-brief basert på Northstar-logikk.
    Kategoriserer hvert instrument og gir handlingsanbefaling.
    """
    categories = {
        "lavrisiko":  [],   # score >= 75
        "nøytral":    [],   # score 50-74
        "avvent":     [],   # score 30-49
        "unngå":      [],   # score < 30
    }
    for iid, a in assets_dict.items():
        if a.get("missing_data"):
            continue
        score = a.get("northstar_score", 0)
        label = a.get("northstar_score_label", "")
        w     = a.get("frames", {}).get("weekly") or {}
        m     = a.get("frames", {}).get("monthly") or {}
        item  = {
            "id":      iid,
            "name":    a.get("display_name", iid),
            "score":   score,
            "label":   label,
            "wrsi":    w.get("rsi14"),
            "mrsi":    m.get("rsi14"),
            "dist3yr": w.get("dist_to_3yr_MA"),
            "notes":   a.get("northstar_notes", []),
        }
        if score >= 75:
            categories["lavrisiko"].append(item)
        elif score >= 50:
            categories["nøytral"].append(item)
        elif score >= 30:
            categories["avvent"].append(item)
        else:
            categories["unngå"].append(item)

    for k in categories:
        categories[k].sort(key=lambda x: -x["score"])

    lines = [
        f"## 📊 Ukentlig Portfolio-Brief – {NOW.strftime('%d. %B %Y')}",
        "",
        "_Basert på Northstar-metodikk: 3yr MA avstand, RSI timeframes, MACD momentum._",
        "",
    ]

    emoji_map = {
        "lavrisiko": "🟢 Lavrisiko entry",
        "nøytral":   "🟡 Nøytral – hold",
        "avvent":    "🟠 Avvent – ikke legg til",
        "unngå":     "🔴 Unngå / trim",
    }
    desc_map = {
        "lavrisiko": "Pris nær 3yr MA, RSI ikke overbought, trend intakt. Beste entry-sone.",
        "nøytral":   "Trend OK men ikke perfekt entry. Hold eksisterende, vent på bedre punkt.",
        "avvent":    "Stretched eller svak momentum. Ikke legg til. Overvåk.",
        "unngå":     "Overbought, under MA, eller mangler bekreftelse. Trim eller stå unna.",
    }

    for key in ["lavrisiko", "nøytral", "avvent", "unngå"]:
        items = categories[key]
        lines.append(f"### {emoji_map[key]}")
        lines.append(f"_{desc_map[key]}_")
        lines.append("")
        if not items:
            lines.append("_Ingen instrumenter i denne kategorien._")
        else:
            lines.append("| Instrument | Score | W-RSI | M-RSI | Dist 3yr MA | Northstar-signal |")
            lines.append("|---|---:|---:|---:|---:|---|")
            for it in items:
                dist_str = f"{it['dist3yr']*100:.1f}%" if it["dist3yr"] is not None else "–"
                wrsi_str = f"{it['wrsi']:.1f}" if it["wrsi"] is not None else "–"
                mrsi_str = f"{it['mrsi']:.1f}" if it["mrsi"] is not None else "–"
                top_note = it["notes"][0] if it["notes"] else "–"
                lines.append(f"| {it['name']} | {it['score']} | {wrsi_str} | {mrsi_str} | {dist_str} | {top_note} |")
        lines.append("")

    return "\n".join(lines)

brief_md = build_portfolio_brief(summary["assets"])
with open(DOCS / "portfolio_brief.md", "w", encoding="utf-8") as f:
    f.write(brief_md)
log("Portfolio brief written.")

# ─────────────────────────────────────────────
#  INDEX.JSON
# ─────────────────────────────────────────────
index = {
    "generated_local": NOW.isoformat(),
    "version": VERSION,
    "summary": summary,
    "ratio_charts": ratio_results,
    "notes": {
        "homepage": "Sortert etter RSI(14) weekly. Grønn/rød Northstar-score per instrument.",
        "instrument_count": len(ALL_IDS),
    },
}
with open(DOCS / "index.json", "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

files = sorted([f"charts/{fn.name}" for fn in CHARTS.glob("*.png")])
with open(DOCS / "filelist.json", "w", encoding="utf-8") as f:
    json.dump({"charts": files}, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
#  HOMEPAGE
# ─────────────────────────────────────────────
def build_homepage(index_data, filelist, brief_markdown):
    assets     = index_data.get("summary", {}).get("assets", {})
    categories = index_data.get("summary", {}).get("categories", [])
    ratios     = index_data.get("ratio_charts", {})
    generated  = index_data.get("generated_local") or NOW.isoformat()
    file_set   = set(filelist)

    def fmt_rsi(v):
        return "–" if not isinstance(v, (int, float)) or math.isnan(v) else f"{v:.1f}"

    def score_color(s):
        if s is None: return "#9aa7b5"
        if s >= 75: return "#50c878"
        if s >= 50: return "#f0a500"
        if s >= 30: return "#e08030"
        return "#e05050"

    # Convert markdown brief to simple HTML
    brief_html = brief_markdown.replace("&", "&amp;").replace("<", "&lt;")
    brief_html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", brief_html, flags=re.M)
    brief_html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", brief_html, flags=re.M)
    brief_html = re.sub(r"^_(.+)_$",  r"<em>\1</em>", brief_html, flags=re.M)
    brief_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", brief_html)
    # Table rows
    lines_out = []
    in_table = False
    for line in brief_html.split("\n"):
        if line.startswith("|") and "---" in line:
            in_table = True
            continue
        if line.startswith("|") and in_table:
            cells = [c.strip() for c in line.strip("|").split("|")]
            lines_out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            lines_out.append('<table class="brief-table"><thead><tr>' +
                             "".join(f"<th>{c}</th>" for c in cells) + "</tr></thead><tbody>")
            in_table = False
        else:
            if in_table:
                lines_out.append("</tbody></table>")
                in_table = False
            lines_out.append(line)
    brief_html = "\n".join(lines_out)

    parts = [f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <title>Market Daily Report</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {{
      --bg:#0b0d10; --panel:#12161c; --panel2:#171c23;
      --text:#e7edf3; --muted:#9aa7b5; --border:#27313d;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
          background:var(--bg);color:var(--text);line-height:1.45}}
    .wrap{{max-width:1500px;margin:0 auto;padding:24px 18px 40px}}
    h1{{margin:0 0 6px;font-size:28px}}
    h2{{margin:24px 0 6px;font-size:22px}}
    h3{{margin:18px 0 4px;font-size:18px}}
    .topnote{{color:var(--muted);margin:0 0 24px;font-size:14px}}
    .brief-section{{padding:20px;border:1px solid var(--border);border-radius:16px;
                    background:var(--panel);margin-bottom:28px}}
    .brief-table{{border-collapse:collapse;width:100%;margin:10px 0}}
    .brief-table th,.brief-table td{{border:1px solid var(--border);padding:5px 8px;font-size:13px}}
    .brief-table th{{background:var(--panel2)}}
    .category{{margin:0 0 28px;padding:18px;border:1px solid var(--border);
               border-radius:16px;background:var(--panel)}}
    .category h2{{margin:0 0 6px;font-size:22px}}
    .category p{{margin:0 0 18px;color:var(--muted)}}
    .instrument{{margin:0 0 20px;padding:16px;border:1px solid var(--border);
                 border-radius:14px;background:var(--panel2)}}
    .instrument:last-child{{margin-bottom:0}}
    .instrument-head{{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:baseline;margin-bottom:12px}}
    .instrument-head h3{{margin:0;font-size:18px}}
    .ticker{{color:var(--muted);font-weight:600}}
    .meta{{color:var(--muted);font-size:13px}}
    .score-badge{{padding:2px 8px;border-radius:8px;font-size:12px;font-weight:700}}
    .charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}}
    .ratio-section{{margin-bottom:28px;padding:18px;border:1px solid var(--border);
                    border-radius:16px;background:var(--panel)}}
    figure{{margin:0;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:#0f141a}}
    img{{display:block;width:100%;height:auto;background:#0f141a}}
    figcaption{{padding:8px 10px;border-top:1px solid var(--border);color:var(--muted);font-size:13px}}
    .missing{{padding:18px;border:1px dashed var(--border);border-radius:12px;
              color:var(--muted);background:#0f141a}}
    footer{{margin-top:24px;color:var(--muted);font-size:13px}}
    em{{color:var(--muted)}}
  </style>
</head>
<body>
<div class="wrap">
  <h1>Market Daily Report</h1>
  <p class="topnote">Generert: {html.escape(str(generated))} • Sortert etter RSI(14) weekly • Northstar-score per instrument</p>

  <section class="brief-section">
    {brief_html}
  </section>
"""]

    # Instrument sections
    for category in categories:
        items = []
        for iid in category.get("instrument_ids", []):
            asset = assets.get(iid, {})
            w_rsi = ((asset.get("frames") or {}).get("weekly") or {}).get("rsi14")
            sort_key = w_rsi if isinstance(w_rsi, (int, float)) and not math.isnan(w_rsi) else float("inf")
            items.append((sort_key, asset.get("display_name") or iid, iid, asset))
        items.sort(key=lambda x: (x[0], x[1]))

        parts.append(
            f'<section class="category"><h2>{html.escape(category.get("title",""))}</h2>'
            f'<p>{html.escape(category.get("description",""))}</p>'
        )
        for _, _, iid, asset in items:
            dname  = asset.get("display_name") or iid
            slabel = asset.get("symbol_label") or iid
            resolved = asset.get("resolved_symbol")
            w = (asset.get("frames") or {}).get("weekly") or {}
            m = (asset.get("frames") or {}).get("monthly") or {}
            score = asset.get("northstar_score")
            slabel_score = asset.get("northstar_score_label", "")
            dist3yr = w.get("dist_to_3yr_MA")
            dist3yr_str = f"{dist3yr*100:.1f}%" if dist3yr is not None else "–"

            meta_bits = [
                f"W-RSI: {fmt_rsi(w.get('rsi14'))}",
                f"M-RSI: {fmt_rsi(m.get('rsi14'))}",
                f"Dist 3yr MA: {dist3yr_str}",
            ]
            if resolved and resolved != slabel:
                meta_bits.append(f"data: {resolved}")

            sc_color = score_color(score)
            score_badge = (f'<span class="score-badge" style="background:{sc_color}20;'
                           f'color:{sc_color};border:1px solid {sc_color}40">'
                           f'{slabel_score} ({score})</span>') if score is not None else ""

            weekly_path  = f"charts/{iid}_weekly_compact.png"
            monthly_path = f"charts/{iid}_monthly_compact.png"

            parts.append(
                f'<article class="instrument">'
                f'<div class="instrument-head">'
                f'<h3>{html.escape(dname)}</h3>'
                f'<span class="ticker">{html.escape(slabel)}</span>'
                f'{score_badge}'
                f'<span class="meta">{" • ".join(html.escape(b) for b in meta_bits)}</span>'
                f'</div><div class="charts">'
            )
            for path, cap in [(weekly_path, "weekly"), (monthly_path, "monthly")]:
                if path in file_set:
                    parts.append(
                        f'<figure><img src="{html.escape(path)}" alt="{html.escape(dname)} {cap}">'
                        f'<figcaption>{cap}_compact.png</figcaption></figure>'
                    )
                else:
                    parts.append(f'<div class="missing">{cap}_compact.png mangler</div>')
            parts.append("</div></article>")
        parts.append("</section>")

    # Ratio charts section
    ratio_files = [(rid, r) for rid, r in ratios.items() if r.get("chart_weekly") in file_set]
    if ratio_files:
        parts.append('<section class="ratio-section"><h2>📈 Ratio Charts (Sektor vs SPY / internt)</h2>')
        parts.append('<p style="color:var(--muted)">Ratio over SMA36 = sektoren outperformer. Brukes til sektor-screening etter Northstar-metodikk.</p>')
        parts.append('<div class="charts">')
        for rid, r in ratio_files:
            parts.append(
                f'<figure><img src="{html.escape(r["chart_weekly"])}" alt="{html.escape(r["label"])}">'
                f'<figcaption>{html.escape(r["label"])}</figcaption></figure>'
            )
        parts.append("</div></section>")

    parts.append(
        "<footer>Datafiler: <a href='index.json' style='color:var(--muted)'>index.json</a> • "
        "<a href='portfolio_brief.md' style='color:var(--muted)'>portfolio_brief.md</a> • "
        "<a href='report.json' style='color:var(--muted)'>report.json</a>"
        "</footer></div></body></html>"
    )
    return "".join(parts)

html_doc = build_homepage(index, files, brief_md)
with open(DOCS / "index.html", "w", encoding="utf-8") as f:
    f.write(html_doc)

log(f"DONE – instruments={len(summary['assets'])} charts={len(files)} version={VERSION}")
flush_log()
print("Done.")
