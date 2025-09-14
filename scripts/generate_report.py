# scripts/generate_report.py
import os, json, time, math, re
from datetime import datetime
from dateutil import tz
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from urllib.parse import urlparse

VERSION = "2025-09-14d"

# Optional: Stooq via pandas-datareader (fallback for ETF/aksjer)
try:
    from pandas_datareader import data as pdr
    HAS_PDR = True
except Exception:
    HAS_PDR = False

# ---------- KONFIG ----------
TZ = tz.gettz("Europe/Oslo")
NOW = datetime.now(tz=TZ)

# Kataloger
os.makedirs("docs", exist_ok=True)
os.makedirs("docs/charts", exist_ok=True)
os.makedirs("docs/news", exist_ok=True)

# --- Force/fullrun-styring ---
FORCE = os.environ.get("FORCE_RUN", "false").lower() == "true"
print(f"Full run mode: {FORCE} at {NOW.isoformat()} (version {VERSION})")

with open("docs/run_mode.json","w") as f:
    json.dump({"force": FORCE, "now": NOW.isoformat(), "version": VERSION}, f, indent=2)

# Ikke blokker manuell kjøring; kun planlagt begrenses av vindu:
if not FORCE and not (
    (NOW.hour == 19 and NOW.minute >= 45) or
    (NOW.hour == 20 and NOW.minute <= 10)
):
    # heartbeat + minimal index for å unngå tom side
    with open("docs/heartbeat.json", "w") as f:
        json.dump({"last_run_local": NOW.isoformat(), "version": VERSION}, f, indent=2)
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

# ---------- YF session ----------
YF_SESSION = requests.Session()
YF_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
})

# ---------- TICKERS ----------
TICKERS = {
    "GLD":"ETF", "SLV":"ETF", "USO":"ETF",
    "GDX":"ETF","GDXJ":"ETF","SIL":"ETF","SILJ":"ETF",
    "URNM":"ETF","ACWI":"ETF","SPY":"ETF",
    "HYG":"ETF","LQD":"ETF",
    "BTC-USD":"CRYPTO","ETH-USD":"CRYPTO",
}
ALL = list(TICKERS.keys())

# Valgfritt filter for test
allow = os.environ.get("ALLOWED_TICKERS", "").upper().strip()
if allow:
    keep = {s.strip() for s in allow.split(",") if s.strip()}
    ALL = [t for t in ALL if t.upper() in keep]
    log(f"ALLOWED_TICKERS filter aktiv: {ALL}")

DISABLE_INTRADAY = os.environ.get("DISABLE_INTRADAY","false").lower() == "true"

# ---------- Indikatorer / plot ----------
def SMA(s, n): return s.rolling(n).mean()
def RSI(s, n=14):
    d = s.diff(); up = d.clip(lower=0); down = -d.clip(upper=0)
    rs = up.rolling(n).mean() / down.rolling(n).mean()
    return 100 - (100/(1+rs))
def MACD(s, fast=12, slow=26, sig=9):
    e_fast = s.ewm(span=fast, adjust=False).mean()
    e_slow = s.ewm(span=slow, adjust=False).mean()
    m = e_fast - e_slow; sigl = m.ewm(span=sig, adjust=False).mean()
    return m, sigl, m - sigl
def pct(a,b): return (a-b)/b if (b is not None and b!=0) else np.nan

def plot_price_ind(df, title, outpath, ma_len):
    plt.figure(); ax = plt.gca()
    df["close_use"].plot(ax=ax, label="Close")
    SMA(df["close_use"], ma_len).plot(ax=ax, label=f"SMA{ma_len}")
    ax.set_title(title); ax.legend(); plt.tight_layout()
    plt.savefig(outpath, dpi=120); plt.close()

def plot_rsi_macd(df, title, out_rsi, out_macd):
    rsi = RSI(df["close_use"]); plt.figure(); rsi.plot()
    plt.title(f"{title} - RSI(14)"); plt.tight_layout()
    plt.savefig(out_rsi, dpi=120); plt.close()
    macd, signal, hist = MACD(df["close_use"])
    plt.figure(); macd.plot(label="MACD"); signal.plot(label="Signal"); hist.plot(label="Hist")
    plt.legend(); plt.title(f"{title} - MACD(12,26,9)"); plt.tight_layout()
    plt.savefig(out_macd, dpi=120); plt.close()

def plot_volume(df, sym):
    last = df.tail(60).copy()
    if last.empty: return
    plt.figure()
    last["volume"].plot(label="Volume")
    if "vol_ma20" in last.columns:
        last["vol_ma20"].plot(label="Vol MA20")
    plt.legend(); plt.title(f"{sym} - Volume (20D snitt)")
    plt.tight_layout(); plt.savefig(f"docs/charts/{sym}_volume.png", dpi=120); plt.close()

# ---------- Fallback-kilder ----------
def stooq_series(sym: str):
    """Daglig fra Stooq (ETF/aksjer), prøver også .US-suffiks."""
    if not HAS_PDR:
        return None
    tried = [sym]
    if not sym.endswith(".US"):
        tried.append(f"{sym}.US")
    for s in tried:
        try:
            df = pdr.DataReader(s, "stooq")  # Open High Low Close Volume
            if df is None or df.empty:
                continue
            df = df.sort_index().rename(columns=str.lower)
            df["close_use"] = df["close"]
            if "volume" not in df.columns: df["volume"] = np.nan
            log(f"stooq ok {s}")
            return df
        except Exception as e:
            log(f"stooq error {s}: {e}")
    return None

CG_MAP = {"BTC-USD":"bitcoin", "ETH-USD":"ethereum"}
def cg_series(sym: str):
    """CoinGecko fallback for krypto (daglig)."""
    coin = CG_MAP.get(sym)
    if not coin: return None
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=max"
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": YF_SESSION.headers["User-Agent"]})
        r.raise_for_status()
        js = r.json(); prices = js.get("prices", [])
        if not prices: return None
        df = pd.DataFrame(prices, columns=["ts","price"])
        df["date"] = pd.to_datetime(df["ts"], unit="ms")
        df = df.set_index("date").sort_index()
        out = pd.DataFrame(index=df.index)
        out["close_use"] = df["price"].astype(float)
        out["volume"] = np.nan
        log(f"coingecko ok {sym}")
        return out
    except Exception as e:
        log(f"coingecko error {sym}: {e}")
        return None

# ---------- yfinance henter (med retry + fallbacks) ----------
def yf_series(sym: str, kind: str):
    """
    kind: 'DAILY','WEEKLY','MONTHLY','INTRADAY_60'
    """
    def _dl(interval, period):
        for i in range(3):
            try:
                data = yf.download(
                    sym, period=period, interval=interval,
                    auto_adjust=True, progress=False, session=YF_SESSION
                )
                if data is not None and not data.empty:
                    return data
            except Exception as e:
                log(f"yfinance error {sym} {interval} try{i+1}: {e}")
            time.sleep(2 + i)
        return None

    if kind == "DAILY":
        data = _dl("1d", "max")
    elif kind == "WEEKLY":
        d = _dl("1d", "max"); data = d.resample("W-FRI").last() if d is not None else None
    elif kind == "MONTHLY":
        d = _dl("1d", "max"); data = d.resample("ME").last() if d is not None else None
    elif kind == "INTRADAY_60":
        data = None if DISABLE_INTRADAY else _dl("1h", "730d")
    else:
        return None

    if data is None or data.empty:
        df = cg_series(sym) if sym.endswith("-USD") else stooq_series(sym)
        if df is None or df.empty:
            log(f"no data {sym} {kind} (yf + fallbacks)")
            return None
        log(f"using fallback for {sym} {kind}")
        return df

    df = data.rename(columns=str.lower).copy()
    if "close" not in df.columns:
        log(f"no close {sym} {kind}")
        return None
    df["close_use"] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = np.nan
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    log(f"using yfinance for {sym} {kind}")
    return df

# ---------- RSS + bildehenting ----------
def safe_slug(s):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s)[:80]

def fetch_first_image_from_page(url):
    try:
        rr = requests.get(url, timeout=30, headers={"User-Agent": YF_SESSION.headers["User-Agent"]})
        rr.raise_for_status()
        soup = BeautifulSoup(rr.text, "lxml")
        meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name":"twitter:image"})
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
            t = it.find("title").get_text(strip=True)
            lnk = it.find("link").get_text(strip=True)
            pub = it.find("pubdate")
            ts = pd.to_datetime(pub.get_text(strip=True)) if pub else None
            if ts is not None and ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            if ts is not None and ts.tz_convert(TZ) >= pd.Timestamp(cutoff, tz=TZ):
                rec = {"title": t, "link": lnk, "published": ts.tz_convert(TZ).isoformat()}
                img_url = fetch_first_image_from_page(lnk)
                if img_url:
                    try:
                        ir = requests.get(img_url, timeout=30, headers={"User-Agent": YF_SESSION.headers["User-Agent"]})
                        ir.raise_for_status()
                        ext = os.path.splitext(urlparse(img_url).path)[1].lower() or ".jpg"
                        fname = f"news_{safe_slug(t)}{ext if ext in ['.jpg','.jpeg','.png'] else '.jpg'}"
                        with open(os.path.join("docs","news",fname), "wb") as f:
                            f.write(ir.content)
                        rec["image"] = f"news/{fname}"
                    except Exception:
                        pass
                out.append(rec)
    except Exception as e:
        log(f"rss error: {e}")
    return out

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
    plt.figure(); df["ratio"].plot(label=f"{num_sym}/{den_sym}"); df["ma50"].plot(label="MA50")
    plt.legend(); plt.tight_layout(); plt.title(f"{num_sym}/{den_sym} ratio vs MA50")
    plt.savefig(out, dpi=120); plt.close()
    return df.tail(400)

def volume_filter(sym):
    df = yf_series(sym, "DAILY")
    if df is None or df.empty: return None
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["up_day"] = (df["close_use"] > df["close_use"].shift(1)).astype(int)
    df["up20"] = df["up_day"].rolling(20).sum()
    plot_volume(df, sym)
    return df.tail(60)[["volume","vol_ma20","up20"]]

# Hovedløp: yfinance/crypto/ETF serier + grafer (+ beriket index.json)
for sym in ALL:
    daily   = yf_series(sym, "DAILY")
    weekly  = yf_series(sym, "WEEKLY")
    monthly = yf_series(sym, "MONTHLY")
    hourly  = yf_series(sym, "INTRADAY_60")

    rsi14_last = None
    macd_cross = None

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

        if name == "daily":
            rsi14_last = float(df["rsi14"].iloc[-1]) if pd.notna(df["rsi14"].iloc[-1]) else None
            if len(df) >= 2:
                last = df["macd"].iloc[-1] - df["macd_signal"].iloc[-1]
                prev = df["macd"].iloc[-2] - df["macd_signal"].iloc[-2]
                macd_cross = bool((last > 0) and (prev <= 0))

        # SPY 200DMA (temperatur-figur)
        if sym == "SPY" and name == "daily":
            plt.figure()
            df["close_use"].plot(label="SPY")
            df["close_use"].rolling(200).mean().plot(label="200DMA")
            plt.legend(); plt.title("SPY vs 200DMA"); plt.tight_layout()
            plt.savefig("docs/charts/SPY_200dma.png", dpi=120); plt.close()

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
            "rsi14_last": rsi14_last,
            "macd_cross": macd_cross
        }

# Ratioer / volumfilter / market-temp ratioer
gdx_gld = ratio_series("GDX","GLD")
sil_slv = ratio_series("SIL","SLV")
hyg_lqd = ratio_series("HYG","LQD")
spx_acwi = ratio_series("SPY","ACWI")
gld_spy = ratio_series("GLD","SPY")  # NY!

# Volumfilter (PNG + JSON-sammendrag)
vol_filters = {s: volume_filter(s) for s in ["GDX","GDXJ","SIL","SILJ"]}
vol_summary = {}
for s, df in vol_filters.items():
    if df is not None and not df.empty:
        last = df.iloc[-1]
        vol_summary[s] = {
            "last_volume": float(last["volume"]) if pd.notna(last["volume"]) else None,
            "last_vol_ma20": float(last["vol_ma20"]) if pd.notna(last["vol_ma20"]) else None,
            "up20": float(last["up20"]) if pd.notna(last["up20"]) else None
        }
with open("docs/volminers.json","w") as f:
    json.dump(vol_summary, f, indent=2)

# ---------- FRED: DXY proxy, VIX, renter, 2s10s ----------
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
        df = df.asfreq("B").ffill()
        df.rename(columns={"value":"close_use"}, inplace=True)
        log(f"fred ok {series_id}")
        return df
    except Exception as e:
        log(f"fred error {series_id}: {e}")
        return None

fred_assets = {}
dxy = fred_series("DTWEXM")
if dxy is not None and not dxy.empty:
    sma200 = dxy["close_use"].rolling(200).mean()
    plot_price_ind(dxy.tail(800), "DXY proxy (DTWEXM) - price vs SMA200", "docs/charts/DXY_price.png", 200)
    plot_rsi_macd(dxy.tail(800), "DXY proxy (DTWEXM)", "docs/charts/DXY_rsi.png", "docs/charts/DXY_macd.png")
    fred_assets["DXY"] = {
        "last": float(dxy["close_use"].iloc[-1]),
        "dist_to_200DMA": float((dxy["close_use"].iloc[-1] - sma200.iloc[-1]) / sma200.iloc[-1]) if pd.notna(sma200.iloc[-1]) else None
    }

vix = fred_series("VIXCLS")
if vix is not None and not vix.empty:
    plot_price_ind(vix.tail(800), "VIX (VIXCLS)", "docs/charts/VIX_price.png", 200)
    plot_rsi_macd(vix.tail(800), "VIX (VIXCLS)", "docs/charts/VIX_rsi.png", "docs/charts/VIX_macd.png")
    fred_assets["VIX"] = {"last": float(vix["close_use"].iloc[-1])}

y3m = fred_series("DGS3MO")
y2y = fred_series("DGS2")
y10 = fred_series("DGS10")
if (y10 is not None and not y10.empty) and (y2y is not None and not y2y.empty):
    spread = pd.DataFrame(index=y10.index.union(y2y.index))
    spread["y10"] = y10["close_use"]; spread["y2"] = y2y["close_use"]
    spread = spread.ffill().dropna()
    spread["s210"] = spread["y10"] - spread["y2"]
    plt.figure(); spread["s210"].plot(); plt.title("2Y/10Y spread (DGS10 - DGS2)")
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
temps = {
    "HYG_LQD_ratio": bool(hyg_lqd is not None),
    "SPY_ACWI_ratio": bool(spx_acwi is not None),
    "DXY_vs_200DMA": "DXY" in fred_assets,
    "VIX": "VIX" in fred_assets,
    "yields_and_2s10s": "yields" in fred_assets
}
try:
    spy = yf_series("SPY", "DAILY")
    acwi = yf_series("ACWI", "DAILY")
    if spy is not None and not spy.empty:
        temps["SPY_above_200DMA"] = bool(spy["close_use"].iloc[-1] > spy["close_use"].rolling(200).mean().iloc[-1])
    if acwi is not None and not acwi.empty:
        temps["ACWI_above_200DMA"] = bool(acwi["close_use"].iloc[-1] > acwi["close_use"].rolling(200).mean().iloc[-1])
except Exception as e:
    log(f"temp calc error: {e}")

index = {
  "generated_local": NOW.isoformat(),
  "version": VERSION,
  "summary": summary,
  "fred": fred_assets,
  "notes": {
    "ratios": {"GDX/GLD": bool(gdx_gld is not None), "SIL/SLV": bool(sil_slv is not None), "GLD/SPY": bool(gld_spy is not None)},
    "vol_filters": {k: bool(v is not None) for k,v in vol_filters.items()},
    "market_temp": temps
  }
}
with open("docs/index.json","w") as f: json.dump(index, f, indent=2)

# ---------- FILLISTE ----------
files = sorted([f"charts/{fn}" for fn in os.listdir("docs/charts") if fn.endswith(".png")])
with open("docs/filelist.json","w") as f:
    json.dump({"charts": files}, f, indent=2)

# ---------- HTML ----------
links = "\n".join([f'<li><a href="{fn}">{os.path.basename(fn)}</a></li>' for fn in files])
html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Daglig rapport {NOW.strftime('%Y-%m-%d')}</title></head><body>
<h1>Daglig rapport {NOW.strftime('%Y-%m-%d')}</h1>
<p>Generert (Europe/Oslo): {NOW}</p>
<p>Data: <a href="index.json">index.json</a> • Nyheter: <a href="news/news.json">news.json</a> • Filer: <a href="filelist.json">filelist.json</a></p>
<h2>Grafer</h2>
<ul>{links}</ul>
</body></html>"""
with open("docs/index.html","w") as f: f.write(html)

# ---------- LOGG ----------
ok_assets = list(summary.get("assets", {}).keys())
log(f"SUMMARY assets_count={len(ok_assets)} charts={len(files)} "
    f"intraday_disabled={DISABLE_INTRADAY} version={VERSION}")
flush_log()
print("Done.")
