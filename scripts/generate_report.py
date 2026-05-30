#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py  -  Market Daily Report
Versjon: 2026-05-30-northstar-v4

Ny i v4:
- RSI daily, weekly og monthly (alle tre timeframes)
- MACD standard 12/26/9 + MACD14 (14/28/9)
- 3yr MA avstand (SMA156 weekly): nær = bra, langt over = dårlig, under = potensiale
- 36WMA avstand som kortsiktig MA-filter
- Northstar score 0-100 av alle datapunkter
- Sektorscore (snitt): Aksjer, Tech, Edelmetaller, Rawarer, Valuta, Crypto, Renter
- Instrumenter sortert etter score, alle datapunkter vist
- 9 ratio-charts
- 4-panel mørke charts: pris+MA, RSI, MACD, MACD14
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

VERSION = "2026-05-30-northstar-v4"
TZ  = ZoneInfo("Europe/Oslo")
NOW = datetime.now(tz=TZ)

DOCS     = Path("docs")
CHARTS   = DOCS / "charts"
NEWS_DIR = DOCS / "news"
DOCS.mkdir(exist_ok=True)
CHARTS.mkdir(exist_ok=True)
NEWS_DIR.mkdir(exist_ok=True)

FORCE_INPUT       = os.environ.get("FORCE_RUN", "false").lower() == "true"
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
FORCE = FORCE_INPUT or IN_GITHUB_ACTIONS

print(f"Full run: {FORCE} at {NOW.isoformat()} (version {VERSION})")
with open(DOCS / "run_mode.json", "w", encoding="utf-8") as f:
    json.dump({"force": FORCE, "now": NOW.isoformat(), "version": VERSION}, f, indent=2)

if not FORCE and not ((NOW.hour == 19 and NOW.minute >= 45) or (NOW.hour == 20 and NOW.minute <= 10)):
    with open(DOCS / "heartbeat.json", "w", encoding="utf-8") as f:
        json.dump({"last_run_local": NOW.isoformat(), "version": VERSION}, f, indent=2)
    with open(DOCS / "index.html", "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset='utf-8'><title>Market Daily Report</title>"
                f"<h1>Market Daily Report</h1><p>{NOW.isoformat()}</p>"
                f"<p>Full rapport genereres kl. 20:00 Europe/Oslo.</p>")
    raise SystemExit(0)

LOG = []
def log(msg):
    print(msg)
    LOG.append(f"{datetime.now().isoformat()}  {msg}")

def flush_log():
    with open(DOCS / "run_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")

YF_SESSION = requests.Session()
YF_SESSION.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "*/*",
                            "Accept-Language": "en-US,en;q=0.9"})

FRED_KEY  = os.environ.get("FRED_API_KEY", "").strip()
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# ─── INSTRUMENTS ───────────────────────────────────────────────
INSTRUMENT_GROUPS = [
    {
        "key": "renter_spreads", "title": "0. Renter & Spreads", "sector": "Renter",
        "description": "10yr yield, yieldkurve, realrente, kredittstress. Forteller makroregime.",
        "instruments": [
            {"id": "UTEN",  "label": "10yr UST",       "symbol_label": "UTEN",  "source": "yf",          "candidates": ["UTEN"]},
            {"id": "2S10S", "label": "2s10s kurve",     "symbol_label": "FRED",  "source": "fred_spread"},
            {"id": "SCHP",  "label": "10yr realrente",  "symbol_label": "SCHP",  "source": "yf",          "candidates": ["SCHP"]},
            {"id": "TLT",   "label": "20yr UST",        "symbol_label": "TLT",   "source": "yf",          "candidates": ["TLT"]},
            {"id": "HYG",   "label": "High Yield",      "symbol_label": "HYG",   "source": "yf",          "candidates": ["HYG", "JNK"]},
            {"id": "LQD",   "label": "IG Kreditt",      "symbol_label": "LQD",   "source": "yf",          "candidates": ["LQD"]},
        ],
    },
    {
        "key": "aksjer", "title": "1. Aksjer", "sector": "Aksjer",
        "description": "Bred aksjeeksponering, vekstsyklus og regional styrke.",
        "instruments": [
            {"id": "SPY",  "label": "S&P 500",          "symbol_label": "SPY",   "source": "yf", "candidates": ["SPY"]},
            {"id": "QQQ",  "label": "Nasdaq-100",        "symbol_label": "QQQ",   "source": "yf", "candidates": ["QQQ"]},
            {"id": "IWM",  "label": "Russell 2000",      "symbol_label": "IWM",   "source": "yf", "candidates": ["IWM"]},
            {"id": "ACWI", "label": "ACWI Global",       "symbol_label": "ACWI",  "source": "yf", "candidates": ["ACWI"]},
            {"id": "EXSA", "label": "STOXX Europe 600",  "symbol_label": "EXSA",  "source": "yf", "candidates": ["EXSA.DE","EXSA","MEUD"]},
            {"id": "EEM",  "label": "MSCI EM",           "symbol_label": "EEM",   "source": "yf", "candidates": ["EEM","VWO"]},
            {"id": "VNQ",  "label": "Housing US",        "symbol_label": "VNQ",   "source": "yf", "candidates": ["VNQ"]},
            {"id": "IAI",  "label": "Broker/Dealers",    "symbol_label": "IAI",   "source": "yf", "candidates": ["IAI"]},
        ],
    },
    {
        "key": "tech", "title": "2. Tech & Halvledere", "sector": "Tech",
        "description": "Teknologilederskap og AI-infrastruktur.",
        "instruments": [
            {"id": "SOXQ", "label": "Semiconductors",   "symbol_label": "SOXQ",  "source": "yf", "candidates": ["SOXQ","SOXX"]},
            {"id": "HACK", "label": "Cybersecurity",    "symbol_label": "HACK",  "source": "yf", "candidates": ["HACK","CIBR"]},
            {"id": "SKYY", "label": "Cloud",            "symbol_label": "SKYY",  "source": "yf", "candidates": ["SKYY","CLOU"]},
            {"id": "BOTZ", "label": "Robotics/AI",      "symbol_label": "BOTZ",  "source": "yf", "candidates": ["BOTZ","IRBO"]},
        ],
    },
    {
        "key": "rawarer", "title": "3. Rawarer", "sector": "Rawarer",
        "description": "Inflasjonspress, reflasjon og rawvaresyklus.",
        "instruments": [
            {"id": "BCOM",  "label": "Commodity bred",  "symbol_label": "BCOM",  "source": "yf", "candidates": ["BCOM","PDBC","DBC"]},
            {"id": "USO",   "label": "Olje (WTI)",      "symbol_label": "USO",   "source": "yf", "candidates": ["USO","BNO"]},
            {"id": "UNG",   "label": "Naturgass",       "symbol_label": "UNG",   "source": "yf", "candidates": ["UNG"]},
            {"id": "COPX",  "label": "Kobber miners",   "symbol_label": "COPX",  "source": "yf", "candidates": ["COPX","JJC"]},
            {"id": "XME",   "label": "Metals/Mining",   "symbol_label": "XME",   "source": "yf", "candidates": ["XME"]},
            {"id": "XLE",   "label": "Energy",          "symbol_label": "XLE",   "source": "yf", "candidates": ["XLE"]},
            {"id": "DBA",   "label": "Agri/mat",        "symbol_label": "DBA",   "source": "yf", "candidates": ["DBA"]},
        ],
    },
    {
        "key": "edelmetaller", "title": "4. Edelmetaller", "sector": "Edelmetaller",
        "description": "Gull, solv, gruvere. Northstar sin kjernesektor.",
        "instruments": [
            {"id": "GLD",  "label": "Gull",             "symbol_label": "GLD",   "source": "yf", "candidates": ["GLD","IAU"]},
            {"id": "SLV",  "label": "Solv",             "symbol_label": "SLV",   "source": "yf", "candidates": ["SLV","SIVR"]},
            {"id": "GDX",  "label": "Gull miners",      "symbol_label": "GDX",   "source": "yf", "candidates": ["GDX"]},
            {"id": "GDXJ", "label": "Junior gull",      "symbol_label": "GDXJ",  "source": "yf", "candidates": ["GDXJ"]},
            {"id": "SIL",  "label": "Solv miners",      "symbol_label": "SIL",   "source": "yf", "candidates": ["SIL"]},
            {"id": "SILJ", "label": "Junior solv",      "symbol_label": "SILJ",  "source": "yf", "candidates": ["SILJ"]},
            {"id": "PPLT", "label": "Platina",          "symbol_label": "PPLT",  "source": "yf", "candidates": ["PPLT","PLTM"]},
            {"id": "PALL", "label": "Palladium",        "symbol_label": "PALL",  "source": "yf", "candidates": ["PALL"]},
        ],
    },
    {
        "key": "uranium", "title": "5. Uranium & Energiomstilling", "sector": "Rawarer",
        "description": "Northstar bullish roadmap. Venter pa $100 breakout.",
        "instruments": [
            {"id": "URA",  "label": "Uranium ETF",      "symbol_label": "URA",   "source": "yf", "candidates": ["URA"]},
            {"id": "URNM", "label": "Uranium miners",   "symbol_label": "URNM",  "source": "yf", "candidates": ["URNM"]},
            {"id": "NLR",  "label": "Nuclear energy",   "symbol_label": "NLR",   "source": "yf", "candidates": ["NLR"]},
            {"id": "ICLN", "label": "Clean energy",     "symbol_label": "ICLN",  "source": "yf", "candidates": ["ICLN"]},
        ],
    },
    {
        "key": "valuta", "title": "6. Valuta & Dollar", "sector": "Valuta",
        "description": "Dollar-regimet. Northstar Milkshake Arc: bearish USD langsiktig.",
        "instruments": [
            {"id": "UUP", "label": "DXY",               "symbol_label": "UUP",   "source": "yf", "candidates": ["UUP","USDU"]},
            {"id": "FXE", "label": "EUR/USD",            "symbol_label": "FXE",   "source": "yf", "candidates": ["FXE"]},
            {"id": "FXY", "label": "JPY",                "symbol_label": "FXY",   "source": "yf", "candidates": ["FXY"]},
            {"id": "CEW", "label": "EM Currencies",      "symbol_label": "CEW",   "source": "yf", "candidates": ["CEW"]},
            {"id": "FXA", "label": "AUD",                "symbol_label": "FXA",   "source": "yf", "candidates": ["FXA"]},
        ],
    },
    {
        "key": "crypto", "title": "7. Crypto & Volatilitet", "sector": "Crypto",
        "description": "Risiko-on spekulasjon og likviditetsindikator.",
        "instruments": [
            {"id": "BTC",  "label": "Bitcoin",           "symbol_label": "BITO",  "source": "yf", "candidates": ["BITO","IBIT","BTC-USD"]},
            {"id": "ETHA", "label": "Ethereum",          "symbol_label": "ETHA",  "source": "yf", "candidates": ["ETHA","ETH-USD"]},
            {"id": "VIXY", "label": "VIX",               "symbol_label": "VIXY",  "source": "yf", "candidates": ["VIXY"]},
        ],
    },
]

RATIO_PAIRS = [
    ("GLD",  "SPY",  "GLD/SPY"),
    ("GDX",  "GLD",  "GDX/GLD"),
    ("SLV",  "GLD",  "SLV/GLD"),
    ("URA",  "SPY",  "URA/SPY"),
    ("XLE",  "SPY",  "XLE/SPY"),
    ("EEM",  "SPY",  "EEM/SPY"),
    ("IWM",  "SPY",  "IWM/SPY"),
    ("COPX", "SPY",  "COPX/SPY"),
    ("GDX",  "SPY",  "GDX/SPY"),
]

ALL_IDS = [i["id"] for g in INSTRUMENT_GROUPS for i in g["instruments"]]

# ─── MATH ──────────────────────────────────────────────────────
def SMA(s, n):
    return s.rolling(n).mean()

def RSI(s, n=14):
    d  = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1/n, adjust=False).mean() / dn.ewm(alpha=1/n, adjust=False).mean()
    return 100 - (100 / (1 + rs))

def MACD_calc(s, fast=12, slow=26, sig=9):
    ef = s.ewm(span=fast, adjust=False).mean()
    es = s.ewm(span=slow, adjust=False).mean()
    m  = ef - es
    sl = m.ewm(span=sig, adjust=False).mean()
    return m, sl, m - sl

def pct_dist(a, b):
    try:
        return (a - b) / b if b and not np.isnan(b) else np.nan
    except Exception:
        return np.nan

def safe_id(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)

# ─── DATA ──────────────────────────────────────────────────────
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
    df = df.sort_index()[~df.index.duplicated(keep="last")].dropna(subset=["close_use"])
    return df if len(df) >= 50 else None

def yf_series_from_candidates(candidates):
    for sym in candidates:
        for attempt in range(3):
            try:
                data = yf.download(sym, period="max", interval="1d",
                                   auto_adjust=True, progress=False,
                                   session=YF_SESSION, threads=False)
                df = normalize_yf_df(data)
                if df is not None:
                    log(f"  yf ok: {sym}")
                    return df, sym
            except Exception as e:
                log(f"  yf error {sym} try{attempt+1}: {e}")
            time.sleep(1 + attempt)
    return None, None

def fred_series(series_id):
    if not FRED_KEY:
        return None
    try:
        r = requests.get(
            f"{FRED_BASE}?series_id={series_id}&api_key={FRED_KEY}&file_type=json&observation_start=1990-01-01",
            timeout=60)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        if not obs:
            return None
        df = pd.DataFrame(obs)[["date","value"]]
        df["date"]  = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.set_index("date").sort_index().dropna().asfreq("B").ffill()
        df["close_use"] = df["value"]
        df["volume"]    = np.nan
        log(f"  fred ok: {series_id}")
        return df[["close_use","volume"]]
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
    df["volume"]    = np.nan
    return df[["close_use","volume"]], "FRED:DGS10-DGS2"

def get_instrument_series(inst):
    if inst["source"] == "yf":
        return yf_series_from_candidates(inst["candidates"])
    if inst["source"] == "fred_spread":
        return fred_2s10s_series()
    raise ValueError(f"Unknown source: {inst['source']}")

def with_indicators(df):
    out = df.copy()
    out["sma36"]  = SMA(out["close_use"], 36)
    out["sma156"] = SMA(out["close_use"], 156)
    out["rsi14"]  = RSI(out["close_use"], 14)
    m,  sl,  h   = MACD_calc(out["close_use"], 12, 26, 9)
    out["macd"] = m;  out["macd_signal"] = sl;  out["macd_hist"] = h
    m14, sl14, h14 = MACD_calc(out["close_use"], 14, 28, 9)
    out["macd14"] = m14; out["macd14_signal"] = sl14; out["macd14_hist"] = h14
    return out

def resample_frames(base_df):
    daily   = with_indicators(base_df)
    weekly  = with_indicators(base_df.resample("W-FRI").last().dropna(how="all"))
    monthly = with_indicators(base_df.resample("ME").last().dropna(how="all"))
    return daily, weekly, monthly

def frame_summary(df, is_weekly=False):
    if df is None or df.empty:
        return {}
    last   = float(df["close_use"].iloc[-1])
    sma36  = df["sma36"].iloc[-1]  if "sma36"  in df.columns else np.nan
    sma156 = df["sma156"].iloc[-1] if "sma156" in df.columns else np.nan

    def fv(col):
        v = df[col].iloc[-1] if col in df.columns else np.nan
        return float(v) if pd.notna(v) else None

    macd_cross = macd14_cross = None
    if len(df) >= 2:
        ld  = df["macd"].iloc[-1]   - df["macd_signal"].iloc[-1]
        pd_ = df["macd"].iloc[-2]   - df["macd_signal"].iloc[-2]
        macd_cross = bool(ld > 0 and pd_ <= 0)
        ld14  = df["macd14"].iloc[-1]   - df["macd14_signal"].iloc[-1]
        pd14  = df["macd14"].iloc[-2]   - df["macd14_signal"].iloc[-2]
        macd14_cross = bool(ld14 > 0 and pd14 <= 0)

    return {
        "last":               last,
        "sma36":              float(sma36)  if pd.notna(sma36)  else None,
        "sma156":             float(sma156) if pd.notna(sma156) else None,
        "close_above_sma36":  bool(last > float(sma36))  if pd.notna(sma36)  else None,
        "close_above_sma156": bool(last > float(sma156)) if pd.notna(sma156) else None,
        "dist_to_36MA":       float(pct_dist(last, float(sma36)))  if pd.notna(sma36)  else None,
        "dist_to_3yr_MA":     float(pct_dist(last, float(sma156))) if (pd.notna(sma156) and is_weekly) else None,
        "rsi14":              fv("rsi14"),
        "macd":               fv("macd"),      "macd_signal":  fv("macd_signal"),
        "macd_hist":          fv("macd_hist"), "macd_cross":   macd_cross,
        "macd14":             fv("macd14"),    "macd14_signal":fv("macd14_signal"),
        "macd14_hist":        fv("macd14_hist"),"macd14_cross":macd14_cross,
    }

# ─── NORTHSTAR SCORE ───────────────────────────────────────────
def northstar_score(entry):
    """
    Score 0-100. Hoeyere = lavrisiko entry.

    Grunnprinsipp: lav RSI, nær/under MA, MACD nær null eller snur opp = bra.
    Hoey RSI, langt over MA, MACD hoyt og fallende = darlig entry.

    Max points:
      3yr MA avstand  (25) — under/naer = bra, langt over = 0
      36WMA avstand   (15) — under eller naer = bra, langt over = 0
      RSI daily       (10) — lav = bra, hoey = darlig
      RSI weekly      (20) — lav = bra, hoey = darlig
      RSI monthly     (20) — lav = bra, hoey = darlig
      MACD weekly     ( 5) — nær null eller snur = bra, hoyt = darlig
      MACD14 weekly   ( 5) — samme logikk
    Total max: 100
    """
    score  = 0
    points = []   # (label, pts, max_pts, note)

    d = entry.get("frames",{}).get("daily")   or {}
    w = entry.get("frames",{}).get("weekly")  or {}
    m = entry.get("frames",{}).get("monthly") or {}

    # ── 3yr MA avstand (weekly SMA156) ──────────────────────────
    # Under = potensiale (10p), naer = ideal (25p), langt over = 0p
    dist3yr = w.get("dist_to_3yr_MA")
    if dist3yr is not None:
        p3 = dist3yr * 100
        if p3 < -15:
            pts = 8;  note = f"Langt under 3yr MA ({p3:.1f}%) — konsoliderer"
        elif p3 < 0:
            pts = 18; note = f"Under 3yr MA ({p3:.1f}%) — potensiale"
        elif p3 < 5:
            pts = 25; note = f"Ideal — naer 3yr MA ({p3:.1f}%)"
        elif p3 < 15:
            pts = 16; note = f"Moderat over 3yr MA ({p3:.1f}%)"
        elif p3 < 30:
            pts = 7;  note = f"Stretched ({p3:.1f}%) — forsiktig"
        elif p3 < 50:
            pts = 2;  note = f"Klart stretched ({p3:.1f}%) — unnga entry"
        else:
            pts = 0;  note = f"Ekstremt stretched ({p3:.1f}%) — ikke entry"
        score += pts
        points.append(("3yr MA", pts, 25, note))
    else:
        points.append(("3yr MA", 0, 25, "ingen data"))

    # ── 36WMA avstand ────────────────────────────────────────────
    # Under eller naer = bra. Langt over = darlig entry.
    dist36 = w.get("dist_to_36MA")
    if dist36 is not None:
        p36 = dist36 * 100
        if p36 < -10:
            pts = 10; note = f"Under 36WMA ({p36:.1f}%) — potensiale"
        elif p36 < 0:
            pts = 13; note = f"Rett under 36WMA ({p36:.1f}%)"
        elif p36 < 3:
            pts = 15; note = f"Naer 36WMA ({p36:.1f}%) — god entry"
        elif p36 < 10:
            pts = 10; note = f"Litt over 36WMA ({p36:.1f}%)"
        elif p36 < 20:
            pts = 5;  note = f"Over 36WMA ({p36:.1f}%) — ok"
        elif p36 < 35:
            pts = 2;  note = f"Klart over 36WMA ({p36:.1f}%) — forsiktig"
        else:
            pts = 0;  note = f"Langt over 36WMA ({p36:.1f}%) — ikke entry"
        score += pts
        points.append(("36WMA", pts, 15, note))
    else:
        points.append(("36WMA", 0, 15, "ingen data"))

    # ── RSI daily (10p) ──────────────────────────────────────────
    # < 30 = oversold (8p), 30-45 = lav/bra (10p), 45-60 = ok (7p),
    # 60-70 = hoey (3p), > 70 = overbought (0p)
    drsi = d.get("rsi14")
    if drsi is not None:
        if drsi < 30:          pts = 8;  note = f"Oversold ({drsi:.1f}) — bounce-fare"
        elif drsi < 45:        pts = 10; note = f"Lav/bra ({drsi:.1f})"
        elif drsi < 60:        pts = 7;  note = f"Noeytral ({drsi:.1f})"
        elif drsi < 70:        pts = 3;  note = f"Hoey ({drsi:.1f})"
        else:                  pts = 0;  note = f"Overbought ({drsi:.1f})"
        score += pts
        points.append(("RSI daily", pts, 10, note))
    else:
        points.append(("RSI daily", 0, 10, "ingen data"))

    # ── RSI weekly (20p) ─────────────────────────────────────────
    wrsi = w.get("rsi14")
    if wrsi is not None:
        if wrsi < 30:          pts = 14; note = f"Oversold ({wrsi:.1f})"
        elif wrsi < 45:        pts = 20; note = f"Lav/bra ({wrsi:.1f})"
        elif wrsi < 60:        pts = 14; note = f"Noeytral ({wrsi:.1f})"
        elif wrsi < 70:        pts = 5;  note = f"Hoey ({wrsi:.1f})"
        else:                  pts = 0;  note = f"Overbought ({wrsi:.1f})"
        score += pts
        points.append(("RSI weekly", pts, 20, note))
    else:
        points.append(("RSI weekly", 0, 20, "ingen data"))

    # ── RSI monthly (20p) ────────────────────────────────────────
    mrsi = m.get("rsi14")
    if mrsi is not None:
        if mrsi < 35:          pts = 16; note = f"Lav/bra ({mrsi:.1f})"
        elif mrsi < 50:        pts = 20; note = f"God ({mrsi:.1f})"
        elif mrsi < 60:        pts = 14; note = f"Moderat ({mrsi:.1f})"
        elif mrsi < 70:        pts = 6;  note = f"Hoey ({mrsi:.1f})"
        elif mrsi < 78:        pts = 2;  note = f"Klart hoey ({mrsi:.1f})"
        else:                  pts = 0;  note = f"Overbought ({mrsi:.1f})"
        score += pts
        points.append(("RSI monthly", pts, 20, note))
    else:
        points.append(("RSI monthly", 0, 20, "ingen data"))

    # ── MACD weekly (5p) ─────────────────────────────────────────
    # Nær null og snur opp = bra. Hoyt positivt og faller = darlig.
    wh = w.get("macd_hist")
    wm = w.get("macd")
    if wh is not None and wm is not None and wm != 0:
        normalized = abs(wh / wm) if wm else 0   # hist relativt til MACD-linjen
        cross = w.get("macd_cross")
        if cross:
            pts = 5; note = f"Bullish cross ({wh:.4f}) — momentum snur"
        elif wh < 0 and wh > -abs(wm)*0.3:
            pts = 4; note = f"Nær null neg ({wh:.4f}) — mulig snu"
        elif wh > 0 and normalized < 0.3:
            pts = 3; note = f"Svakt pos ({wh:.4f}) — tidlig"
        elif wh < 0:
            pts = 2; note = f"Neg ({wh:.4f})"
        else:
            pts = 1; note = f"Pos men hoyt ({wh:.4f}) — allerede loept"
        score += pts
        points.append(("MACD W", pts, 5, note))
    elif wh is not None:
        pts = 3 if wh < 0 else 1
        note = f"{'Neg' if wh < 0 else 'Pos'} ({wh:.4f})"
        score += pts
        points.append(("MACD W", pts, 5, note))
    else:
        points.append(("MACD W", 0, 5, "ingen data"))

    # ── MACD14 weekly (5p) ───────────────────────────────────────
    wh14 = w.get("macd14_hist")
    wm14 = w.get("macd14")
    if wh14 is not None and wm14 is not None and wm14 != 0:
        cross14 = w.get("macd14_cross")
        if cross14:
            pts = 5; note = f"Bullish cross ({wh14:.4f})"
        elif wh14 < 0 and wh14 > -abs(wm14)*0.3:
            pts = 4; note = f"Nær null neg ({wh14:.4f})"
        elif wh14 > 0 and abs(wh14/wm14) < 0.3:
            pts = 3; note = f"Svakt pos ({wh14:.4f})"
        elif wh14 < 0:
            pts = 2; note = f"Neg ({wh14:.4f})"
        else:
            pts = 1; note = f"Pos men hoyt ({wh14:.4f})"
        score += pts
        points.append(("MACD14 W", pts, 5, note))
    elif wh14 is not None:
        pts = 3 if wh14 < 0 else 1
        score += pts
        points.append(("MACD14 W", pts, 5, f"{'Neg' if wh14 < 0 else 'Pos'} ({wh14:.4f})"))
    else:
        points.append(("MACD14 W", 0, 5, "ingen data"))

    return min(score, 100), points

def score_label(s):
    if s >= 75: return ("groen",  "Lavrisiko entry")
    if s >= 55: return ("gul",    "Noytral")
    if s >= 35: return ("oransje","Avvent")
    return           ("rod",     "Unnga/trim")

def score_color(s):
    if s is None: return "#9aa7b5"
    if s >= 75:   return "#50c878"
    if s >= 55:   return "#f0a500"
    if s >= 35:   return "#e08030"
    return              "#e05050"

# ─── PLOTTING ──────────────────────────────────────────────────
BG="#0b0d10"; FG="#e7edf3"; GRID="#27313d"
C_PRICE="#4a9eff"; C_SMA36="#f0a500"; C_SMA156="#e05050"
C_RSI="#7ec8e3"; C_SIG="#f0a500"; C_MACD="#4a9eff"; C_MACD14="#c084fc"

def _style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    for sp in ax.spines.values(): sp.set_color(GRID)
    ax.yaxis.label.set_color(FG)
    ax.grid(True, color=GRID, linewidth=0.4, linestyle=":")

def plot_compact(df, title, out_path):
    try:
        fig, axes = plt.subplots(4, 1, sharex=True, figsize=(11,10),
                                 facecolor=BG, gridspec_kw={"height_ratios":[3,1,1,1]})
        for ax in axes: _style_ax(ax)

        s = df["close_use"]
        axes[0].plot(df.index, s, color=C_PRICE, lw=1.2, label="Close")
        axes[0].plot(df.index, SMA(s,36),  color=C_SMA36,  lw=1.0, label="SMA36")
        sma156 = SMA(s,156)
        if sma156.notna().any():
            axes[0].plot(df.index, sma156, color=C_SMA156, lw=0.9, ls="--", label="SMA156 (3yr)")
        axes[0].set_title(title, fontsize=10, color=FG)
        axes[0].legend(loc="upper left", fontsize=7, facecolor=BG, labelcolor=FG, framealpha=0.7)

        rsi = RSI(s)
        axes[1].plot(df.index, rsi, color=C_RSI, lw=1.0, label="RSI(14)")
        axes[1].axhline(70, color="#e05050", ls="--", lw=0.7)
        axes[1].axhline(50, color=GRID,      ls=":",  lw=0.5)
        axes[1].axhline(30, color="#50c878", ls="--", lw=0.7)
        axes[1].set_ylim(0, 100)
        axes[1].set_ylabel("RSI", color=FG, fontsize=8)
        axes[1].legend(loc="upper left", fontsize=7, facecolor=BG, labelcolor=FG, framealpha=0.7)

        m, sig, hist = MACD_calc(s, 12, 26, 9)
        colors2 = ["#50c878" if v >= 0 else "#e05050" for v in hist.fillna(0)]
        axes[2].bar(df.index, hist, color=colors2, alpha=0.55, width=5)
        axes[2].plot(df.index, m,   color=C_MACD, lw=0.9, label="MACD")
        axes[2].plot(df.index, sig, color=C_SIG,  lw=0.9, label="Signal")
        axes[2].axhline(0, color=GRID, lw=0.5)
        axes[2].set_ylabel("MACD", color=FG, fontsize=8)
        axes[2].legend(loc="upper left", fontsize=7, facecolor=BG, labelcolor=FG, framealpha=0.7)

        m14, sig14, hist14 = MACD_calc(s, 14, 28, 9)
        colors3 = ["#50c878" if v >= 0 else "#e05050" for v in hist14.fillna(0)]
        axes[3].bar(df.index, hist14, color=colors3, alpha=0.55, width=5)
        axes[3].plot(df.index, m14,   color=C_MACD14, lw=0.9, label="MACD14")
        axes[3].plot(df.index, sig14, color=C_SIG,    lw=0.9, label="Signal")
        axes[3].axhline(0, color=GRID, lw=0.5)
        axes[3].set_ylabel("MACD14", color=FG, fontsize=8)
        locator = mdates.AutoDateLocator()
        axes[3].xaxis.set_major_locator(locator)
        axes[3].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        axes[3].legend(loc="upper left", fontsize=7, facecolor=BG, labelcolor=FG, framealpha=0.7)

        plt.tight_layout(pad=0.7)
        plt.savefig(out_path, dpi=120, facecolor=BG)
        plt.close(fig)
    except Exception as e:
        log(f"plot error {title}: {e}")

def plot_ratio(df_num, df_den, label, out_path):
    try:
        combined = pd.DataFrame({"num": df_num["close_use"], "den": df_den["close_use"]}).dropna()
        if len(combined) < 50: return
        combined["ratio"] = combined["num"] / combined["den"]
        weekly = combined["ratio"].resample("W-FRI").last().dropna()
        if len(weekly) < 36: return
        ws = pd.Series(weekly.values, index=weekly.index)

        fig, axes = plt.subplots(2,1, sharex=True, figsize=(11,6), facecolor=BG)
        for ax in axes: _style_ax(ax)
        axes[0].plot(weekly.index, weekly.values, color=C_SMA36, lw=1.2, label=label)
        sma36 = SMA(ws, 36)
        if sma36.notna().any():
            axes[0].plot(weekly.index, sma36.values, color=C_PRICE, lw=0.9, ls="--", label="SMA36")
        axes[0].set_title(f"Ratio: {label}", fontsize=10, color=FG)
        axes[0].legend(fontsize=7, facecolor=BG, labelcolor=FG, framealpha=0.7)
        rsi = RSI(ws)
        axes[1].plot(weekly.index, rsi.values, color=C_RSI, lw=1.0)
        axes[1].axhline(70, color="#e05050", ls="--", lw=0.7)
        axes[1].axhline(30, color="#50c878", ls="--", lw=0.7)
        axes[1].set_ylim(0,100)
        axes[1].set_ylabel("RSI(14)", color=FG, fontsize=8)
        locator = mdates.AutoDateLocator()
        axes[1].xaxis.set_major_locator(locator)
        axes[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        plt.tight_layout(pad=0.7)
        plt.savefig(out_path, dpi=120, facecolor=BG)
        plt.close(fig)
        log(f"  ratio: {label}")
    except Exception as e:
        log(f"  ratio error {label}: {e}")

# ─── NEWS ──────────────────────────────────────────────────────
def last_n_days_posts(url, days=4):
    from bs4 import BeautifulSoup
    out = []
    try:
        r = requests.get(url, timeout=30); r.raise_for_status()
        soup  = BeautifulSoup(r.text, "lxml")
        items = soup.find_all("item")
        cutoff = pd.Timestamp(NOW.date()) - pd.Timedelta(days=days)
        for it in items[:20]:
            tn = it.find("title"); ln = it.find("link")
            if not tn or not ln: continue
            title = tn.get_text(strip=True); link = ln.get_text(strip=True)
            pub = it.find("pubdate")
            ts  = pd.to_datetime(pub.get_text(strip=True)) if pub else None
            if ts is not None:
                if ts.tzinfo is None: ts = ts.tz_localize("UTC")
                if ts.tz_convert(TZ) < pd.Timestamp(cutoff, tz=TZ): continue
            out.append({"title": title, "link": link,
                        "published": ts.tz_convert(TZ).isoformat() if ts else ""})
    except Exception as e:
        log(f"rss error {url}: {e}")
    return out

# ─── MAIN LOOP ─────────────────────────────────────────────────
log(f"Starting - {len(ALL_IDS)} instruments")
raw_cache = {}

summary = {
    "generated_local": NOW.isoformat(),
    "assets": {},
    "categories": [
        {"key": g["key"], "title": g["title"], "description": g["description"],
         "sector": g.get("sector",""), "instrument_ids": [i["id"] for i in g["instruments"]]}
        for g in INSTRUMENT_GROUPS
    ],
}

for group in INSTRUMENT_GROUPS:
    for inst in group["instruments"]:
        iid = inst["id"]
        log(f"Fetching {iid}...")
        df, resolved = get_instrument_series(inst)

        entry = {
            "id": iid, "display_name": inst["label"], "symbol_label": inst["symbol_label"],
            "resolved_symbol": resolved, "source": inst["source"],
            "category_key": group["key"], "category_title": group["title"],
            "sector": group.get("sector",""),
            "frames": {"daily":{}, "weekly":{}, "monthly":{}},
            "missing_data": df is None or getattr(df,"empty",True),
        }
        if entry["missing_data"]:
            summary["assets"][iid] = entry; log(f"  MISSING: {iid}"); continue

        raw_cache[iid] = df
        daily, weekly, monthly = resample_frames(df)
        entry["frames"]["daily"]   = frame_summary(daily,   is_weekly=False)
        entry["frames"]["weekly"]  = frame_summary(weekly,  is_weekly=True)
        entry["frames"]["monthly"] = frame_summary(monthly, is_weekly=False)

        last_252 = daily.tail(252)
        entry["52w_high"] = float(last_252["close_use"].max()) if not last_252.empty else None
        entry["52w_low"]  = float(last_252["close_use"].min()) if not last_252.empty else None

        score, score_points = northstar_score(entry)
        emoji, slabel = score_label(score)
        entry["northstar_score"]        = score
        entry["northstar_score_label"]  = slabel
        entry["northstar_score_points"] = score_points

        if not weekly.empty:
            plot_compact(weekly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - weekly",
                         CHARTS / f"{iid}_weekly_compact.png")
        if not monthly.empty:
            plot_compact(monthly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - monthly",
                         CHARTS / f"{iid}_monthly_compact.png")

        summary["assets"][iid] = entry
        log(f"  OK: {iid} score={score}")

# Sector scores
sector_scores = {}
for iid, a in summary["assets"].items():
    if a.get("missing_data") or a.get("northstar_score") is None: continue
    sec = a.get("sector","Annet")
    sector_scores.setdefault(sec, []).append(a["northstar_score"])

sector_summary = {}
for sec, scores in sector_scores.items():
    avg = round(sum(scores)/len(scores), 1)
    emoji, label = score_label(avg)
    sector_summary[sec] = {"avg_score": avg, "label": label, "n": len(scores)}

# Ratio charts
log("Ratio charts...")
ratio_results = {}
for (num_id, den_id, label) in RATIO_PAIRS:
    if num_id in raw_cache and den_id in raw_cache:
        rid = f"RATIO_{num_id}_{den_id}"
        out_path = CHARTS / f"{rid}_weekly_compact.png"
        plot_ratio(raw_cache[num_id], raw_cache[den_id], label, out_path)
        ratio_results[rid] = {"label": label, "numerator": num_id, "denominator": den_id,
                              "chart_weekly": f"charts/{rid}_weekly_compact.png"}

# News
log("News...")
news = {"nftrh": last_n_days_posts("https://nftrh.com/blog/feed/"),
        "northstar": last_n_days_posts("https://northstarbadcharts.com/feed/")}
with open(NEWS_DIR/"news.json","w",encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=2)

# Portfolio brief
def build_portfolio_brief(assets_dict, sector_sum):
    buckets = {"lavrisiko":[], "noytral":[], "avvent":[], "unnga":[]}
    for iid, a in assets_dict.items():
        if a.get("missing_data") or a.get("northstar_score") is None: continue
        s  = a["northstar_score"]
        w_ = a.get("frames",{}).get("weekly")  or {}
        d_ = a.get("frames",{}).get("daily")   or {}
        m_ = a.get("frames",{}).get("monthly") or {}
        it = {"id":iid,"name":a.get("display_name",iid),"score":s,
              "label":a.get("northstar_score_label",""),"w":w_,"d":d_,"m":m_}
        if s>=75:   buckets["lavrisiko"].append(it)
        elif s>=55: buckets["noytral"].append(it)
        elif s>=35: buckets["avvent"].append(it)
        else:       buckets["unnga"].append(it)
    for k in buckets: buckets[k].sort(key=lambda x:-x["score"])

    def fr(v): return f"{v:.1f}" if isinstance(v,float) else "-"
    def fp(v): return f"{v*100:.1f}%" if isinstance(v,float) else "-"

    lines = [f"## Ukentlig Portfolio-Brief - {NOW.strftime('%d. %B %Y')}","",
             "### Sektorscore","","| Sektor | Score | Signal | n |","|---|---:|---|---:|"]
    for sec in sorted([s for s in ["Aksjer","Tech","Edelmetaller","Rawarer","Valuta","Crypto","Renter"] if s in sector_sum], key=lambda s:-sector_sum[s]["avg_score"]):
        ss = sector_sum[sec]
        lines.append(f"| {sec} | {ss['avg_score']} | {ss['label']} | {ss['n']} |")
    lines.append("")

    for key, title, desc in [
        ("lavrisiko","Lavrisiko entry","Near 3yr MA, RSI ok, momentum positivt."),
        ("noytral",  "Noytral - hold","Trend OK men ikke ideal entry."),
        ("avvent",   "Avvent",         "Stretched eller svak momentum."),
        ("unnga",    "Unnga/trim",     "Overbought, under MA, eller ingen bekreftelse."),
    ]:
        lines += [f"### {title}",f"_{desc}_","",
                  "| Instrument | Score | D-RSI | W-RSI | M-RSI | Dist 3yr | Dist 36W |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for it in buckets[key]:
            lines.append(
                f"| {it['name']} | **{it['score']}** | "
                f"{fr(it['d'].get('rsi14'))} | {fr(it['w'].get('rsi14'))} | {fr(it['m'].get('rsi14'))} | "
                f"{fp(it['w'].get('dist_to_3yr_MA'))} | {fp(it['w'].get('dist_to_36MA'))} |")
        if not buckets[key]: lines.append("_Ingen instrumenter._")
        lines.append("")
    return "\n".join(lines)

brief_md = build_portfolio_brief(summary["assets"], sector_summary)
with open(DOCS/"portfolio_brief.md","w",encoding="utf-8") as f: f.write(brief_md)

# Index.json
index = {"generated_local": NOW.isoformat(), "version": VERSION, "summary": summary,
         "sector_summary": sector_summary, "ratio_charts": ratio_results,
         "notes": {"instrument_count": len(ALL_IDS)}}
with open(DOCS/"index.json","w",encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

files = sorted([f"charts/{fn.name}" for fn in CHARTS.glob("*.png")])
with open(DOCS/"filelist.json","w",encoding="utf-8") as f:
    json.dump({"charts":files}, f, ensure_ascii=False, indent=2)

# ─── HTML ──────────────────────────────────────────────────────
def fmt(v, d=1): return f"{v:.{d}f}" if isinstance(v,float) and not math.isnan(v) else "-"
def fmt_pct(v):  return f"{v*100:.1f}%" if isinstance(v,float) and not math.isnan(v) else "-"

def macd_html(v):
    if v is None: return "-"
    c = "#50c878" if v>0 else "#e05050"
    arr = "&#9650;" if v>0 else "&#9660;"
    return f'<span style="color:{c}">{arr} {abs(v):.4f}</span>'

def build_homepage(index_data, filelist, brief_md_text):
    assets     = index_data.get("summary",{}).get("assets",{})
    categories = index_data.get("summary",{}).get("categories",[])
    sec_sum    = index_data.get("sector_summary",{})
    ratios     = index_data.get("ratio_charts",{})
    generated  = index_data.get("generated_local") or NOW.isoformat()
    file_set   = set(filelist)

    CSS = """:root{--bg:#0b0d10;--panel:#12161c;--panel2:#171c23;--text:#e7edf3;--muted:#9aa7b5;--border:#27313d}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.45}
.wrap{max-width:1600px;margin:0 auto;padding:20px 16px 40px}
h1{margin:0 0 4px;font-size:24px}h2{margin:0 0 6px;font-size:18px}
.topnote{color:var(--muted);margin:0 0 18px;font-size:13px}
.section{margin:0 0 22px;padding:14px 16px;border:1px solid var(--border);border-radius:14px;background:var(--panel)}
.sector-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-top:10px}
.sc{padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--panel2);text-align:center}
.sc-name{font-size:11px;color:var(--muted)}.sc-score{font-size:22px;font-weight:700;margin:2px 0}
.sc-label{font-size:10px}.sc-n{font-size:10px;color:var(--muted)}
.inst-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
.inst-table th{background:var(--panel2);padding:5px 7px;text-align:left;border-bottom:1px solid var(--border);color:var(--muted);font-weight:600;white-space:nowrap}
.inst-table td{padding:4px 7px;border-bottom:1px solid #1e2530;vertical-align:top}
.inst-table tr:last-child td{border-bottom:none}.inst-table tr:hover td{background:#161b22}
.pill{display:inline-block;padding:2px 6px;border-radius:6px;font-size:11px;font-weight:700}
.pts-bar{display:flex;gap:2px;flex-wrap:wrap;margin-top:3px}
.pt{font-size:10px;padding:1px 4px;border-radius:3px;background:#1e2530;color:var(--muted)}
.pt.ok{background:#0d2a1a;color:#50c878}.pt.mid{background:#2a2000;color:#f0a500}.pt.bad{background:#2a0d0d;color:#e05050}
.charts-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:10px;margin-top:10px}
figure{margin:0;border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#0f141a}
img{display:block;width:100%;height:auto}figcaption{padding:5px 10px;border-top:1px solid var(--border);color:var(--muted);font-size:12px}
.missing{padding:12px;border:1px dashed var(--border);border-radius:8px;color:var(--muted);font-size:12px}
details>summary{cursor:pointer;color:var(--muted);font-size:13px;padding:4px 0}
.brief-pre{white-space:pre-wrap;font-size:11px;color:var(--muted);font-family:monospace;margin-top:8px;background:var(--panel2);padding:10px;border-radius:8px;max-height:350px;overflow-y:auto}
footer{margin-top:18px;color:var(--muted);font-size:12px}"""

    parts = [f"""<!doctype html><html lang="no"><head>
<meta charset="utf-8"><title>Market Daily Report</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style></head><body><div class="wrap">
<h1>Market Daily Report</h1>
<p class="topnote">Generert: {html.escape(str(generated))} &nbsp;&bull;&nbsp; {VERSION}</p>"""]

    # Sector overview
    parts.append('<section class="section"><h2>&#128202; Sektorscore</h2>'
                 '<p style="color:var(--muted);font-size:12px">Snitt Northstar-score. Hoeyere = lavrisiko entry.</p>'
                 '<div class="sector-grid">')
    for sec in sorted([s for s in ["Aksjer","Tech","Edelmetaller","Rawarer","Valuta","Crypto","Renter"] if s in sec_sum], key=lambda s:-sec_sum[s]["avg_score"]):
        ss = sec_sum[sec]; avg = ss["avg_score"]; c = score_color(avg)
        parts.append(
            f'<div class="sc" style="border-color:{c}50">'
            f'<div class="sc-name">{html.escape(sec)}</div>'
            f'<div class="sc-score" style="color:{c}">{avg}</div>'
            f'<div class="sc-label" style="color:{c}">{html.escape(ss["label"])}</div>'
            f'<div class="sc-n">{ss["n"]} instr.</div></div>')
    parts.append('</div></section>')

    # Portfolio brief
    parts.append('<section class="section"><h2>&#128203; Ukentlig Portfolio-Brief</h2>'
                 '<details><summary>Vis full analyse (klikk)</summary>'
                 f'<div class="brief-pre">{html.escape(brief_md_text)}</div>'
                 '</details></section>')

    # Instrument categories
    for category in categories:
        items = []
        for iid in category.get("instrument_ids",[]):
            a = assets.get(iid,{})
            score = a.get("northstar_score",-1) if not a.get("missing_data") else -1
            items.append((score, a.get("display_name") or iid, iid, a))
        items.sort(key=lambda x:-x[0])

        parts.append(f'<section class="section"><h2>{html.escape(category.get("title",""))}</h2>'
                     f'<p style="color:var(--muted);font-size:12px">{html.escape(category.get("description",""))}</p>')

        parts.append('<table class="inst-table"><thead><tr>'
                     '<th>Instrument</th><th>Score</th>'
                     '<th>D-RSI</th><th>W-RSI</th><th>M-RSI</th>'
                     '<th>Dist 3yr MA</th><th>Dist 36WMA</th>'
                     '<th>MACD W</th><th>MACD14 W</th>'
                     '<th>52w</th></tr></thead><tbody>')

        chart_items = []
        for _, _, iid, a in items:
            if a.get("missing_data"):
                parts.append(f'<tr><td colspan="10" style="color:var(--muted)">'
                              f'{html.escape(a.get("display_name") or iid)} - ingen data</td></tr>')
                continue
            d_ = (a.get("frames") or {}).get("daily")   or {}
            w_ = (a.get("frames") or {}).get("weekly")  or {}
            m_ = (a.get("frames") or {}).get("monthly") or {}
            sc = a.get("northstar_score", 0)
            slabel = a.get("northstar_score_label","")
            spoints = a.get("northstar_score_points",[])
            c = score_color(sc)

            # score point pills
            pills = '<div class="pts-bar">'
            for (plabel, pts, maxpts, pnote) in spoints:
                r = pts/maxpts if maxpts>0 else 0
                cls = "ok" if r>=0.8 else ("mid" if r>=0.4 else "bad")
                pills += f'<span class="pt {cls}" title="{html.escape(pnote)}">{html.escape(plabel)}: {pts}/{maxpts}</span>'
            pills += '</div>'

            high52 = ""
            if a.get("52w_high") and d_.get("last") and d_["last"] >= a["52w_high"]*0.999:
                high52 = '<span style="color:#f0a500">52H</span>'

            parts.append(
                f'<tr>'
                f'<td><strong style="font-size:12px">{html.escape(a.get("display_name") or iid)}</strong>'
                f'<br><span style="color:var(--muted);font-size:10px">{html.escape(a.get("symbol_label") or iid)}</span></td>'
                f'<td><span class="pill" style="background:{c}20;color:{c};border:1px solid {c}40">{sc}</span>'
                f'<br><span style="font-size:10px;color:{c}">{html.escape(slabel)}</span>{pills}</td>'
                f'<td>{fmt(d_.get("rsi14"))}</td>'
                f'<td>{fmt(w_.get("rsi14"))}</td>'
                f'<td>{fmt(m_.get("rsi14"))}</td>'
                f'<td>{fmt_pct(w_.get("dist_to_3yr_MA"))}</td>'
                f'<td>{fmt_pct(w_.get("dist_to_36MA"))}</td>'
                f'<td>{macd_html(w_.get("macd_hist"))}</td>'
                f'<td>{macd_html(w_.get("macd14_hist"))}</td>'
                f'<td>{high52}</td></tr>')
            chart_items.append((iid, a))

        parts.append('</tbody></table>')

        parts.append('<div class="charts-grid">')
        for iid, a in chart_items:
            dname = a.get("display_name") or iid
            for suffix, cap in [("weekly_compact","weekly"),("monthly_compact","monthly")]:
                path = f"charts/{iid}_{suffix}.png"
                if path in file_set:
                    parts.append(f'<figure><img src="{html.escape(path)}" alt="{html.escape(dname)} {cap}" loading="lazy">'
                                  f'<figcaption>{html.escape(dname)} - {cap}</figcaption></figure>')
        parts.append('</div></section>')

    # Ratio charts
    ratio_files = [(rid,r) for rid,r in ratios.items() if r.get("chart_weekly") in file_set]
    if ratio_files:
        parts.append('<section class="section"><h2>&#128200; Ratio Charts</h2>'
                     '<p style="color:var(--muted);font-size:12px">Over SMA36 = outperformer. Northstar sektor-screening.</p>'
                     '<div class="charts-grid">')
        for rid, r in ratio_files:
            parts.append(f'<figure><img src="{html.escape(r["chart_weekly"])}" alt="{html.escape(r["label"])}" loading="lazy">'
                          f'<figcaption>{html.escape(r["label"])}</figcaption></figure>')
        parts.append('</div></section>')

    parts.append('<footer>Data: <a href="index.json" style="color:var(--muted)">index.json</a> &bull; '
                 '<a href="portfolio_brief.md" style="color:var(--muted)">portfolio_brief.md</a> &bull; '
                 '<a href="report.json" style="color:var(--muted)">report.json</a></footer>'
                 '</div></body></html>')
    return "".join(parts)

html_doc = build_homepage(index, files, brief_md)
with open(DOCS/"index.html","w",encoding="utf-8") as f: f.write(html_doc)

log(f"DONE - {len(summary['assets'])} instruments, {len(files)} charts, version={VERSION}")
flush_log()
print("Done.")
