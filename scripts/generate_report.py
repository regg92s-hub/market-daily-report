import os, json, time, math
from datetime import datetime
from dateutil import tz
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

# ---------- KONFIG ----------
API_KEY = os.environ["ALPHA_VANTAGE_KEY"]
TZ = tz.gettz("Europe/Oslo")
NOW = datetime.now(tz=TZ)

# --- Force/fullrun-styring ---
FORCE = os.environ.get("FORCE_RUN", "false").lower() == "true"
os.makedirs("docs", exist_ok=True)

# Kjør bare full jobb rundt 20:00 lokal tid, med mindre FORCE=true
from dateutil import tz
if not FORCE:
    if not (NOW.hour == 20 and NOW.minute <= 10):
        # skriv heartbeat + minimal index for å unngå 404
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


# Kjør kun full jobb nær kl. 20:00 lokal tid (±10 min). Ellers skriv heartbeat og avslutt uten feil.
os.makedirs("docs", exist_ok=True)
if not (NOW.hour == 20 and NOW.minute <= 10):
    with open("docs/heartbeat.json", "w") as f:
        json.dump({"last_run_local": NOW.isoformat()}, f, indent=2)
    raise SystemExit(0)

# For enkel gratisbruker: hold deg til symboler som fungerer på AV gratis
TICKERS = {
    "GLD":"ETF", "SLV":"ETF", "USO":"ETF",
    "GDX":"ETF","GDXJ":"ETF","SIL":"ETF","SILJ":"ETF",
    "URNM":"ETF","ACWI":"ETF","SPY":"ETF",
    "HYG":"ETF","LQD":"ETF",
    "BTC-USD":"CRYPTO","ETH-USD":"CRYPTO",
    # DXY, VIX og renteserier er ikke på AV gratis i en form som er stabil.
    # De utelates i denne gratis-varianten for robusthet.
}

AV_MAP = {
    "GLD":"GLD","SLV":"SLV","USO":"USO","GDX":"GDX","GDXJ":"GDXJ","SIL":"SIL","SILJ":"SILJ",
    "URNM":"URNM","ACWI":"ACWI","SPY":"SPY","HYG":"HYG","LQD":"LQD",
    "BTC-USD":"BTC","ETH-USD":"ETH",
}

# ---------- ENKEL THROTTLING ----------
# Alpha Vantage (free): ~5 kall/min og ~500/dag. Vi sover 13 sek pr. kall.
def av_get(url):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    time.sleep(13)
    return r

# ---------- HJELPERE ----------
def av_series(symbol, interval):
    base = "https://www.alphavantage.co/query?"
    if interval == "DAILY":
        fn = "TIME_SERIES_DAILY_ADJUSTED"; key = "Time Series (Daily)"
        url = f"{base}function={fn}&symbol={symbol}&outputsize=full&apikey={API_KEY}"
    elif interval == "WEEKLY":
        fn = "TIME_SERIES_WEEKLY_ADJUSTED"; key = "Weekly Adjusted Time Series"
        url = f"{base}function={fn}&symbol={symbol}&apikey={API_KEY}"
    elif interval == "MONTHLY":
        fn = "TIME_SERIES_MONTHLY_ADJUSTED"; key = "Monthly Adjusted Time Series"
        url = f"{base}function={fn}&symbol={symbol}&apikey={API_KEY}"
    elif interval == "INTRADAY_60":
        fn = "TIME_SERIES_INTRADAY"; key = "Time Series (60min)"
        url = f"{base}function={fn}&symbol={symbol}&interval=60min&outputsize=full&apikey={API_KEY}"
    else:
        raise ValueError("bad interval")

    js = av_get(url).json()
    if key not in js:
        return None

    df = (pd.DataFrame(js[key]).T
          .rename(columns={
              "1. open":"open","2. high":"high","3. low":"low","4. close":"close",
              "5. adjusted close":"adj_close","6. volume":"volume"
          })
          .apply(pd.to_numeric, errors="ignore"))
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    df["close_use"] = df["adj_close"] if "adj_close" in df.columns and not df["adj_close"].isna().all() else df["close"]
    return df

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
    except Exception:
        return []

# ---------- KJØRING ----------
os.makedirs("docs/charts", exist_ok=True)
os.makedirs("docs/news", exist_ok=True)
summary = {"generated_local": NOW.isoformat(), "assets": {}}

def safe_get(symbol, label):
    try:
        return av_series(symbol, label)
    except Exception:
        return None

# Hent serier og lag grafer/indikatorer
for sym in AV_MAP.keys():
    av_sym = AV_MAP[sym]
    daily = safe_get(av_sym, "DAILY")
    weekly = safe_get(av_sym, "WEEKLY")
    monthly = safe_get(av_sym, "MONTHLY")
    hourly = safe_get(av_sym, "INTRADAY_60")

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
        if weekly is not None and "sma36" in weekly.columns:
            dist_36w = pct(weekly["close_use"].iloc[-1], weekly["sma36"].iloc[-1])
        dist_36m = np.nan
        if monthly is not None and "sma36" in monthly.columns:
            dist_36m = pct(monthly["close_use"].iloc[-1], monthly["sma36"].iloc[-1])

        summary["assets"][sym] = {
            "last": float(daily["close_use"].iloc[-1]),
            "52w_high": float(hi52), "52w_low": float(lo52),
            "dist_to_36WMA": None if math.isnan(dist_36w) else float(dist_36w),
            "dist_to_36MMA": None if math.isnan(dist_36m) else float(dist_36m),
        }

def ratio_series(num_sym, den_sym):
    num = safe_get(AV_MAP[num_sym], "DAILY")
    den = safe_get(AV_MAP[den_sym], "DAILY")
    if num is None or den is None: return None
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

gdx_gld = ratio_series("GDX","GLD")
sil_slv = ratio_series("SIL","SLV")

def volume_filter(sym):
    df = safe_get(AV_MAP[sym], "DAILY")
    if df is None or df.empty: return None
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["up_day"] = (df["close_use"] > df["close_use"].shift(1)).astype(int)
    df["up20"] = df["up_day"].rolling(20).sum()
    return df.tail(60)[["volume","vol_ma20","up20"]]

vol_filters = {s: volume_filter(s) for s in ["GDX","GDXJ","SIL","SILJ"]}

hyg_lqd = ratio_series("HYG","LQD")
spx_acwi = ratio_series("SPY","ACWI")

news = {
    "nftrh": last_n_days_posts("https://nftrh.com/blog/feed/"),
    "northstar": last_n_days_posts("https://northstarbadcharts.com/feed/")
}
with open("docs/news/news.json","w") as f: json.dump(news, f, indent=2)

index = {
  "generated_local": NOW.isoformat(),
  "summary": summary,
  "notes": {
    "ratios": {"GDX/GLD": bool(gdx_gld is not None), "SIL/SLV": bool(sil_slv is not None)},
    "vol_filters": {k: bool(v is not None) for k,v in vol_filters.items()},
    "market_temp": {"HYG/LQD": bool(hyg_lqd is not None), "SPX/ACWI": bool(spx_acwi is not None)},
    "omitted_free_tickers": ["DXY","VIX","^TNX","^IRX","^UST2Y"]
  }
}
with open("docs/index.json","w") as f: json.dump(index, f, indent=2)

html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Daglig rapport {NOW.strftime('%Y-%m-%d')}</title></head><body>
<h1>Daglig rapport {NOW.strftime('%Y-%m-%d')}</h1>
<p>Generert (Europe/Oslo): {NOW}</p>
<p>Se <a href="index.json">index.json</a> for tall og <code>charts/</code> for grafer.</p>
<h2>Nyhetsutdrag (siste 2–3 dager)</h2>
<pre>{json.dumps(news, indent=2)}</pre>
</body></html>"""
with open("docs/index.html","w") as f: f.write(html)

print("Done.")
