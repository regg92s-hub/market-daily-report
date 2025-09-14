import os, json, time, math
from datetime import datetime
from dateutil import tz
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

# ---------- KONFIG ----------
TZ = tz.gettz("Europe/Oslo")
NOW = datetime.now(tz=TZ)

# Kataloger
os.makedirs("docs", exist_ok=True)
os.makedirs("docs/charts", exist_ok=True)
os.makedirs("docs/news", exist_ok=True)

# --- Force/fullrun-styring ---
FORCE = os.environ.get("FORCE_RUN", "false").lower() == "true"
print(f"Full run mode: {FORCE} at {NOW.isoformat()}")

with open("docs/run_mode.json","w") as f:
    json.dump({"force": FORCE, "now": NOW.isoformat()}, f, indent=2)

if not FORCE and not (NOW.hour == 20 and NOW.minute <= 10):
    with open("docs/heartbeat.json", "w") as f:
        json.dump({"last_run_local": NOW.isoformat()}, f, indent=2)
    with open("docs/index.html", "w") as f:
        f.write(
            f"<!doctype html><meta charset='utf-8'><title>Market Daily Report</title>"
            f"<h1>Market Daily Report</h1>"
            f"<p>Generert: {NOW.isoformat()}</p>"
            f"<p>Full rapport genereres kl. 20:00 Europe/Oslo.</p>"
        )
    raise SystemExit(0)

# ---------- LOGGING ----------
LOG = []
def log(msg):
    print(msg)
    LOG.append(f"{datetime.now().isoformat()}  {msg}")
def flush_log():
    with open("docs/run_log.txt","w") as f:
        f.write("\n".join(LOG) + "\n")

# ---------- TICKERS (yfinance) ----------
TICKERS = {
    "GLD":"ETF", "SLV":"ETF", "USO":"ETF",
    "GDX":"ETF","GDXJ":"ETF","SIL":"ETF","SILJ":"ETF",
    "URNM":"ETF","ACWI":"ETF","SPY":"ETF",
    "HYG":"ETF","LQD":"ETF",
    "BTC-USD":"CRYPTO","ETH-USD":"CRYPTO",
}
ALL = list(TICKERS.keys())

# Tillat å begrense antall tickere via env for test / fart
allow = os.environ.get("ALLOWED_TICKERS", "").upper().strip()
if allow:
    keep = {s.strip() for s in allow.split(",") if s.strip()}
    ALL = [t for t in ALL if t.upper() in keep]
    log(f"ALLOWED_TICKERS filter aktiv: {ALL}")

DISABLE_INTRADAY = os.environ.get("DISABLE_INTRADAY","false").lower() == "true"

# ---------- HJELPERE (indikatorer/plot) ----------
def SMA(s, n): return s.rolling(n).mean()

def RSI(s, n=14):
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    rs = up.rolling(n).mean() / down.rolling(n).mean()
    return 100 - (100/(1+rs))

def MACD(s, fast=12, slow=26, sig=9):
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=sig, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist

def pct(a,b):
    return (a-b)/b if (b is not None and b!=0) else np.nan

def plot_price_ind(df, title, outpath, ma_len):
    plt.figure()
    ax = plt.gca()
    df["close_use"].plot(ax=ax, label="Close")
    SMA(df["close_use"], ma_len).plot(ax=ax, label=f"SMA{ma_len}")
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outpath, dpi=120)
    plt.close()

def plot_rsi_macd(df, title, out_rsi, out_macd):
    rsi = RSI(df["close_use"])
    plt.figure()
    rsi.plot()
    plt.title(f"{title} - RSI(14)")
    plt.tight_layout()
    plt.savefig(out_rsi, dpi=120)
    plt.close()

    macd, signal, hist = MACD(df["close_use"])
    plt.figure()
    macd.plot(label="MACD")
    signal.plot(label="Signal")
    hist.plot(label="Hist")
    plt.legend()
    plt.title(f"{title} - MACD(12,26,9)")
    plt.tight_layout()
    plt.savefig(out_macd, dpi=120)
    plt.close()

# ---------- yfinance henter ----------
def yf_series(sym: str, kind: str):
    """
    kind: 'DAILY','WEEKLY','MONTHLY','INTRADAY_60'
    Vi resampler selv til uke/måned.
    """
    try:
        if kind == "DAILY":
            data = yf.download(sym, period="max", interval="1d", auto_adjust=True, progress=False)
        elif kind == "WEEKLY":
            d = yf.download(sym, period="max", interval="1d", auto_adjust=True, progress=False)
            data = d.resample("W-FRI").last()
        elif kind == "MONTHLY":
            d = yf.download(sym, period="max", interval="1d", auto_adjust=True, progress=False)
            data = d.resample("M").last()
        elif kind == "INTRADAY_60":
            if DISABLE_INTRADAY:
                return None
            data = yf.download(sym, period="730d", interval="1h", auto_adjust=True, progress=False)
        else:
            return None
    except Exception as e:
        log(f"yfinance error {sym} {kind}: {e}")
        return None

    if data is None or data.empty or ("Close" not in data.columns and "close" not in data.columns):
        log(f"no data {sym} {kind}")
        return None

    df = data.rename(columns=str.lower).copy()
    if "close" not in df.columns:
        return None
    df["close_use"] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = np.nan
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    return df

# ---------- RSS ----------
def last_n_days_posts(url, days=3):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        items = soup.find_all("item")
        out = []
        cutoff = pd.Timestamp(NOW.date()) - pd.Timedelta(days=days)
        for it in items[:20]:
            t = it.find("title").get_text(strip=True)
            lnk = it.find("link").get_text(strip=True)
            pub = it.find("pubdate")
            ts = pd.to_datetime(pub.get_text(strip=True)) if pub else None
            if ts is not None and ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            if ts is not None and ts.tz_convert(TZ) >= pd.Timestamp(cutoff, tz=TZ):
                out.append({"title": t, "link": lnk, "published": ts.tz_convert(TZ).isoformat()})
        return out
    except Exception as e:
        log(f"rss error: {e}")
        return []

# ---------- FRED ----------
FRED_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

def fred_series(series_id):
    if not FRED_KEY:
        return None
    url = (f"{FRED_BASE}?series_id={series_id}"
           f"&api_key={FRED_KEY}&file_type=json&observation_start=1990-01-01")
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        js = r.json()
        obs = js.get("observations", [])
        if not obs:
            return None
        df = pd.DataFrame(obs)[["date","value"]]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.set_index("date").sort_index().dropna()
        df = df.asfreq("B").ffill()  # handelsdager
        df.rename(columns={"value":"close_use"}, inplace=True)
        return df
    except Exception as e:
        log(f"fred error {series_id}: {e}")
        return None

# ---------- KJØRING ----------
summary = {"generated_local": NOW.isoformat(), "assets": {}}

def ratio_series(num_sym, den_sym):
    num = yf_series(num_sym, "DAILY")
    den = yf_series(den_sym, "DAILY")
    if num is None or den is None or num.empty or den.empty:
        return None
    df = pd.DataFrame(index=num.index.union(den.index))
    df["n"] = num["close_use"]; df["d"] = den["close_use"]
    df.dropna(inplace=True)
    df["ratio"] = df["n"]/df["d"]
    df["ma50"] = df["ratio"].rolling(50).mean()
    out = f"docs/charts/{num_sym}_{den_sym}_ratio.png"
    plt.figure()
    df["ratio"].plot(label=f"{num_sym}/{den_sym}")
    df["ma50"].plot(label="MA50")
    plt.legend(); plt.tight_layout(); plt.title(f"{num_sym}/{den_sym} ratio vs MA50")
    plt.savefig(out, dpi=120); plt.close()
    return df.tail(400)

def volume_filter(sym):
    df = yf_series(sym, "DAILY")
    if df is None or df.empty: return None
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["up_day"] = (df["close_use"] > df["close_use"].shift(1)).astype(int)
    df["up20"] = df["up_day"].rolling(20).sum()
    return df.tail(60)[["volume","vol_ma20","up20"]]

# Hent serier og lag grafer/indikatorer (yfinance)
for sym in ALL:
    daily   = yf_series(sym, "DAILY")
    weekly  = yf_series(sym, "WEEKLY")
    monthly = yf_series(sym, "MONTHLY")
    hourly  = yf_series(sym, "INTRADAY_60")

    series_map = [("hourly", hourly), ("daily", daily), ("weekly", weekly), ("monthly", monthly)]
    for name, df in series_map:
        if df is None or df.empty:
            continue
        n = 36
        df[f"sma{n}"] = SMA(df["close_use"], n)
        df["rsi14"] = RSI(df["close_use"])
        macd, signal, hist = MACD(df["close_use"])
        df["macd"], df["macd_signal"], df["macd_hist"] = macd, signal, hist

        base = f"docs/charts/{sym}_{name}"
        plot_price_ind(df.tail(400), f"{sym} - {name} price vs SMA{n}", base+"_price.png", n)
        plot_rsi_macd(df.tail(400), f"{sym} - {name}", base+"_rsi.png", base+"_macd.png")

    if daily is not None and not daily.empty:
        last_252 = daily.tail(252)
        hi52, lo52 = last_252["close_use"].max(), last_252["close_use"].min()
        dist_36w = np.nan
        if weekly is not None and "sma36" in weekly.columns and pd.notna(weekly["sma36"].iloc[-1]):
            dist_36w = pct(weekly["close_use"].iloc[-1], weekly["sma36"].iloc[-1])
        dist_36m = np.nan
        if monthly is not None and "sma36" in monthly.columns and pd.notna(monthly["sma36"].iloc[-1]):
            dist_36m = pct(monthly["close_use"].iloc[-1], monthly["sma36"].iloc[-1])

        summary["assets"][sym] = {
            "last": float(daily["close_use"].iloc[-1]),
            "52w_high": float(hi52), "52w_low": float(lo52),
            "dist_to_36WMA": None if (isinstance(dist_36w, float) and math.isnan(dist_36w)) else float(dist_36w),
            "dist_to_36MMA": None if (isinstance(dist_36m, float) and math.isnan(dist_36m)) else float(dist_36m),
        }

# Ratioer / volumfilter / markedstemp-ratioer
gdx_gld = ratio_series("GDX","GLD")
sil_slv = ratio_series("SIL","SLV")
vol_filters = {s: volume_filter(s) for s in ["GDX","GDXJ","SIL","SILJ"]}
hyg_lqd = ratio_series("HYG","LQD")
spx_acwi = ratio_series("SPY","ACWI")

# ---------- FRED: DXY proxy, VIX, renter, 2s10s ----------
fred_assets = {}

# DXY proxy: Trade Weighted U.S. Dollar Index (major) – DTWEXM
dxy = fred_series("DTWEXM")
if dxy is not None and not dxy.empty:
    sma200 = dxy["close_use"].rolling(200).mean()
    plot_price_ind(dxy.tail(800), "DXY proxy (DTWEXM) - price vs SMA200", "docs/charts/DXY_price.png", 200)
    plot_rsi_macd(dxy.tail(800), "DXY proxy (DTWEXM)", "docs/charts/DXY_rsi.png", "docs/charts/DXY_macd.png")
    fred_assets["DXY"] = {
        "last": float(dxy["close_use"].iloc[-1]),
        "dist_to_200DMA": float((dxy["close_use"].iloc[-1] - sma200.iloc[-1]) / sma200.iloc[-1]) if pd.notna(sma200.iloc[-1]) else None
    }

# VIX: VIXCLS
vix = fred_series("VIXCLS")
if vix is not None and not vix.empty:
    plot_price_ind(vix.tail(800), "VIX (VIXCLS)", "docs/charts/VIX_price.png", 200)
    plot_rsi_macd(vix.tail(800), "VIX (VIXCLS)", "docs/charts/VIX_rsi.png", "docs/charts/VIX_macd.png")
    fred_assets["VIX"] = {"last": float(vix["close_use"].iloc[-1])}

# Renter: 3M, 2Y, 10Y + 2s10s
y3m = fred_series("DGS3MO")
y2y = fred_series("DGS2")
y10 = fred_series("DGS10")
if (y10 is not None and not y10.empty) and (y2y is not None and not y2y.empty):
    spread = pd.DataFrame(index=y10.index.union(y2y.index))
    spread["y10"] = y10["close_use"]; spread["y2"] = y2y["close_use"]
    spread = spread.ffill().dropna()
    spread["s210"] = spread["y10"] - spread["y2"]
    plt.figure(); spread["s210"].plot()
    plt.title("2Y/10Y spread (DGS10 - DGS2)")
    plt.tight_layout(); plt.savefig("docs/charts/2Y10Y_spread.png", dpi=120); plt.close()
    fred_assets["yields"] = {
        "DGS3MO": float(y3m["close_use"].iloc[-1]) if (y3m is not None and not y3m.empty) else None,
        "DGS2": float(y2y["close_use"].iloc[-1]),
        "DGS10": float(y10["close_use"].iloc[-1]),
        "2s10s": float(spread["s210"].iloc[-1])
    }

# ---------- RSS ----------
news = {
    "nftrh": last_n_days_posts("https://nftrh.com/blog/feed/"),
    "northstar": last_n_days_posts("https://northstarbadcharts.com/feed/")
}
with open("docs/news/news.json","w") as f: json.dump(news, f, indent=2)

# ---------- INDEX JSON ----------
index = {
  "generated_local": NOW.isoformat(),
  "summary": summary,
  "fred": fred_assets,
  "notes": {
    "ratios": {"GDX/GLD": bool(gdx_gld is not None), "SIL/SLV": bool(sil_slv is not None)},
    "vol_filters": {k: bool(v is not None) for k,v in vol_filters.items()},
    "market_temp": {
        "HYG/LQD": bool(hyg_lqd is not None),
        "SPX/ACWI": bool(spx_acwi is not None),
        "DXY_vs_200DMA": "DXY" in fred_assets,
        "VIX": "VIX" in fred_assets,
        "yields_and_2s10s": "yields" in fred_assets
    }
  }
}
with open("docs/index.json","w") as f: json.dump(index, f, indent=2)

# ---------- HTML (liste grafer) ----------
files = sorted([f for f in os.listdir("docs/charts") if f.endswith(".png")])
links = "\n".join([f'<li><a href="charts/{fn}">{fn}</a></li>' for fn in files])
html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Daglig rapport {NOW.strftime('%Y-%m-%d')}</title></head><body>
<h1>Daglig rapport {NOW.strftime('%Y-%m-%d')}</h1>
<p>Generert (Europe/Oslo): {NOW}</p>
<p>Data: <a href="index.json">index.json</a> • Nyheter: <a href="news/news.json">news.json</a></p>
<h2>Grafer</h2>
<ul>{links}</ul>
</body></html>"""
with open("docs/index.html","w") as f: f.write(html)

# ---------- LOGG ----------
ok_assets = list(summary.get("assets", {}).keys())
log(f"SUMMARY assets_count={len(ok_assets)} charts={len(files)} intraday_disabled={DISABLE_INTRADAY} fred_keys={list(fred_assets.keys())}")
flush_log()

print("Done.")
