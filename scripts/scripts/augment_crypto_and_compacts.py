#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, math
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

PAGES = Path("docs")
INDEX = PAGES/"index.json"
CHARTS = PAGES/"charts"
CHARTS.mkdir(parents=True, exist_ok=True)

CRYPTOS = ["BTC-USD", "ETH-USD"]

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / roll_down
    return 100 - (100/(1+rs))

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def sma(s, n): return s.rolling(n).mean()

def get_tf_data(ticker):
    # daily / weekly / monthly
    d = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
    if d.empty: return None
    d = d.dropna()
    d["RSI14"] = rsi(d["Close"])
    d["MACD"], d["MACD_SIGNAL"], d["MACD_HIST"] = macd(d["Close"])
    d["SMA36"] = sma(d["Close"], 36)

    w = d.resample("W-FRI").last()
    w["SMA36"] = sma(w["Close"], 36)
    w["RSI14"] = rsi(w["Close"])
    w["MACD"], w["MACD_SIGNAL"], w["MACD_HIST"] = macd(w["Close"])

    m = d.resample("M").last()
    m["SMA36"] = sma(m["Close"], 36)
    m["RSI14"] = rsi(m["Close"])
    m["MACD"], m["MACD_SIGNAL"], m["MACD_HIST"] = macd(m["Close"])

    return d, w, m

def weekly_close_count_above_36WMA(w):
    # teller sammenhengende uker til slutt over 36WMA bakover
    above = (w["Close"] > w["SMA36"]).fillna(False)
    cnt = 0
    for val in reversed(above.tolist()):
        if val: cnt += 1
        else: break
    return cnt

def make_compact_png(ticker, d):
    # kompakt: pris vs SMA36 + RSI + MACD
    close = d["Close"].tail(220)
    sma36 = d["SMA36"].tail(220)
    rsi14 = d["RSI14"].tail(220)
    macd_line = d["MACD"].tail(220)
    macd_sig = d["MACD_SIGNAL"].tail(220)
    hist = d["MACD_HIST"].tail(220)

    fig = plt.figure(figsize=(9,6))
    ax1 = plt.subplot2grid((3,1),(0,0))
    ax2 = plt.subplot2grid((3,1),(1,0))
    ax3 = plt.subplot2grid((3,1),(2,0))

    ax1.plot(close.index, close.values, label="Close")
    ax1.plot(sma36.index, sma36.values, label="SMA36")
    ax1.legend(loc="upper left"); ax1.set_title(f"{ticker} – Price vs 36MA")

    ax2.plot(rsi14.index, rsi14.values, label="RSI14")
    ax2.axhline(70, linestyle="--"); ax2.axhline(30, linestyle="--")
    ax2.legend(loc="upper left"); ax2.set_title("RSI(14)")

    ax3.plot(macd_line.index, macd_line.values, label="MACD")
    ax3.plot(macd_sig.index, macd_sig.values, label="Signal")
    ax3.bar(hist.index, hist.values)  # histogram
    ax3.legend(loc="upper left"); ax3.set_title("MACD(12,26,9)")

    fig.tight_layout()
    out = CHARTS/f"{ticker.replace('/','-')}_daily_compact.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out.name

def upsert_index_for(ticker, d, w, m):
    # last/52w/36WMA/MMA, RSI/MACD, uketeller
    last = float(d["Close"].iloc[-1])
    high_52 = float(d["Close"].rolling(252).max().iloc[-1])
    low_52 = float(d["Close"].rolling(252).min().iloc[-1])
    dist_36w = None
    dist_36m = None
    if not math.isnan(w["SMA36"].iloc[-1]) and w["SMA36"].iloc[-1] != 0:
        dist_36w = (w["Close"].iloc[-1]-w["SMA36"].iloc[-1])/w["SMA36"].iloc[-1]
    if not math.isnan(m["SMA36"].iloc[-1]) and m["SMA36"].iloc[-1] != 0:
        dist_36m = (m["Close"].iloc[-1]-m["SMA36"].iloc[-1])/m["SMA36"].iloc[-1]

    entry = {
        "52w_high": high_52, "52w_low": low_52,
        "dist_to_36WMA": dist_36w, "dist_to_36MMA": dist_36m,
        "weekly_close_count_above_36WMA": weekly_close_count_above_36WMA(w),
        "frames": {
            "daily": {
                "last": last,
                "sma36": float(d["SMA36"].iloc[-1]),
                "close_above_sma36": bool(d["Close"].iloc[-1] > d["SMA36"].iloc[-1]),
                "rsi14": float(d["RSI14"].iloc[-1]),
                "macd": float(d["MACD"].iloc[-1]),
                "macd_signal": float(d["MACD_SIGNAL"].iloc[-1]),
                "macd_hist": float(d["MACD_HIST"].iloc[-1]),
                "macd_cross": bool(d["MACD"].iloc[-2] < d["MACD_SIGNAL"].iloc[-2] and d["MACD"].iloc[-1] > d["MACD_SIGNAL"].iloc[-1]) if len(d)>2 else None
            },
            "weekly": {
                "last": float(w["Close"].iloc[-1]),
                "sma36": float(w["SMA36"].iloc[-1]),
                "close_above_sma36": bool(w["Close"].iloc[-1] > w["SMA36"].iloc[-1]),
                "rsi14": float(w["RSI14"].iloc[-1]),
                "macd": float(w["MACD"].iloc[-1]),
                "macd_signal": float(w["MACD_SIGNAL"].iloc[-1]),
                "macd_hist": float(w["MACD_HIST"].iloc[-1]),
                "macd_cross": bool(w["MACD"].iloc[-2] < w["MACD_SIGNAL"].iloc[-2] and w["MACD"].iloc[-1] > w["MACD_SIGNAL"].iloc[-1]) if len(w)>2 else None
            },
            "monthly": {
                "last": float(m["Close"].iloc[-1]),
                "sma36": float(m["SMA36"].iloc[-1]),
                "close_above_sma36": bool(m["Close"].iloc[-1] > m["SMA36"].iloc[-1]),
                "rsi14": float(m["RSI14"].iloc[-1]),
                "macd": float(m["MACD"].iloc[-1]),
                "macd_signal": float(m["MACD_SIGNAL"].iloc[-1]),
                "macd_hist": float(m["MACD_HIST"].iloc[-1]),
                "macd_cross": bool(m["MACD"].iloc[-2] < m["MACD_SIGNAL"].iloc[-2] and m["MACD"].iloc[-1] > m["MACD_SIGNAL"].iloc[-1]) if len(m)>2 else None
            }
        }
    }
    return entry

def main():
    if not INDEX.exists():
        raise SystemExit("Fant ikke docs/index.json – kjør generate_report.py først.")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    assets = idx.get("summary", {}).get("assets", {})
    changed = False

    for t in CRYPTOS:
        got = get_tf_data(t)
        if not got: 
            print(f"Advarsel: ingen data for {t}")
            continue
        d, w, m = got
        entry = upsert_index_for(t, d, w, m)
        img = make_compact_png(t, d)
        # oppdater filelist.json?
        assets[t] = {**assets.get(t, {}), **entry}
        changed = True

    if changed:
        # bump metadata
        idx.setdefault("summary", {}).setdefault("assets", {})
        idx["summary"]["assets"] = assets
        idx["generated_local"] = datetime.now(timezone.utc).astimezone().isoformat()
        INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
