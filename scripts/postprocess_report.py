#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
postprocess_report.py (robust + speil-fallback)
- Leser docs/index.json (eller henter korrekt fra raw/jsDelivr/github.io hvis lokal er HTML/ugyldig)
- Leser docs/news/news.json (best effort)
- Normaliserer pr-ticker felter (tåler variasjoner)
- Skriver atomisk:
    docs/report.json
    docs/report.md
    docs/report_table.html
- Setter inn/erstatter merket blokk i docs/index.html:
    <!-- REPORT_TABLE_START --> ... <!-- REPORT_TABLE_END -->
- Miljøvariabler:
    POSTPROC_SOFT_FAIL=true|false  (default false)
    PAGES_BRANCH=gh-pages          (valgfritt; default gh-pages)
"""

from __future__ import annotations
import json, os, re, sys, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

# ---------- Paths / Config ----------
PAGES      = Path("docs")
INDEX      = PAGES / "index.json"
NEWS       = PAGES / "news" / "news.json"
OUT_JSON   = PAGES / "report.json"
OUT_MD     = PAGES / "report.md"
OUT_TABLE  = PAGES / "report_table.html"
INDEX_HTML = PAGES / "index.html"

TABLE_START = "<!-- REPORT_TABLE_START -->"
TABLE_END   = "<!-- REPORT_TABLE_END -->"

SOFT_FAIL   = os.environ.get("POSTPROC_SOFT_FAIL", "false").lower() == "true"
PAGES_BRANCH= os.environ.get("PAGES_BRANCH", "gh-pages")

# ---------- I/O helpers ----------
def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def write_json_atomic(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def looks_like_html(s: str) -> bool:
    head = s.lstrip()[:80].lower()
    return head.startswith("<!doctype") or head.startswith("<html") or "<html" in head

def load_local_json_or_html(path: Path) -> tuple[Optional[dict], Optional[str]]:
    """Returner (json_obj, raw_text). Hvis JSON feiler, returner (None, raw_text)."""
    if not path.exists():
        return None, None
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return None, raw
    # Hvis det ser ut som HTML, ikke prøv å parse som JSON
    if looks_like_html(raw):
        return None, raw
    try:
        return json.loads(raw), raw
    except json.JSONDecodeError:
        return None, raw

def fetch_text(url: str) -> Optional[str]:
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = r.read()
        # anta UTF-8
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None

def try_fetch_index_from_mirrors() -> Optional[dict]:
    """
    Forsøk å hente korrekt index.json fra speil hvis lokal er HTML/ugyldig.
    Speilrekkefølge: raw -> jsDelivr -> github.io
    """
    repo = os.environ.get("GITHUB_REPOSITORY")  # "owner/repo"
    if not repo or "/" not in repo:
        return None
    owner, name = repo.split("/", 1)

    mirrors = [
        f"https://raw.githubusercontent.com/{owner}/{name}/{PAGES_BRANCH}/index.json",
        f"https://cdn.jsdelivr.net/gh/{owner}/{name}@{PAGES_BRANCH}/index.json",
        f"https://{owner}.github.io/{name}/index.json",
    ]
    for url in mirrors:
        txt = fetch_text(url + f"?t={int(datetime.utcnow().timestamp())}")
        if not txt:
            continue
        if looks_like_html(txt):
            # feil ressurs (HTML) – prøv neste
            continue
        try:
            return json.loads(txt)
        except Exception:
            continue
    return None

def _exit_or_raise(message: str):
    if SOFT_FAIL:
        print(f"{message}  (SOFT_FAIL=true ⇒ fortsetter uten output)")
        _write_placeholders()
        sys.exit(0)
    raise SystemExit(message)

def _write_placeholders():
    now = datetime.utcnow().isoformat() + "Z"
    out_obj = {"generated_local": now, "spec_version": "v1", "assets": [], "news": {}}
    try:
        write_json_atomic(OUT_JSON, out_obj)
        write_text_atomic(OUT_MD, f"# Daglig rapport – {now}\n\n(Data manglet eller var ugyldig.)\n")
        placeholder = f"{TABLE_START}\n<p>Ingen data tilgjengelig (index.json manglet/var tom/HTML) – {now}</p>\n{TABLE_END}"
        write_text_atomic(OUT_TABLE, placeholder)
        if INDEX_HTML.exists():
            html = INDEX_HTML.read_text(encoding="utf-8")
            if TABLE_START in html and TABLE_END in html:
                html = re.sub(rf"{re.escape(TABLE_START)}.*?{re.escape(TABLE_END)}",
                              placeholder, html, flags=re.DOTALL)
            else:
                if "</body>" in html:
                    html = html.replace("</body>", placeholder + "\n</body>")
                else:
                    html += "\n" + placeholder
            write_text_atomic(INDEX_HTML, html)
    except Exception as e:
        print(f"[postprocess] WARN writing placeholders: {e}")

# ---------- Normalisering ----------
def as_float(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        try:
            if (x != x) or (x == float("inf")) or (x == float("-inf")):
                return None
            return float(x)
        except Exception:
            return None
    if isinstance(x, str):
        try:
            x = x.strip().replace(",", "")
            return float(x)
        except Exception:
            return None
    return None

def _get(d: Dict, *ks, default=None):
    cur = d
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def _bool_to_ja_nei(v):
    return "Ja" if v is True else ("Nei" if v is False else "")

def _tf(frame: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(frame, dict):
        frame = {}
    last = as_float(frame.get("last"))
    sma36 = as_float(frame.get("sma36"))
    dist = None
    if last is not None and sma36 not in (None, 0.0):
        dist = (last - sma36) / sma36
    return {
        "last": last,
        "sma36": sma36,
        "close_above_sma36": frame.get("close_above_sma36"),
        "dist_to_36MA": dist,
        "rsi14": as_float(frame.get("rsi14")),
        "macd": as_float(frame.get("macd")),
        "macd_signal": as_float(frame.get("macd_signal")),
        "macd_hist": as_float(frame.get("macd_hist")),
        "macd_cross": frame.get("macd_cross"),
    }

def _maybe_frame(a: Dict[str, Any], key: str) -> Dict[str, Any] | None:
    prefix = key[:1]  # h/d/w/m
    cand_last = a.get(f"{prefix}_last") or a.get(f"{key}_last")
    cand_sma  = a.get(f"{prefix}_sma36") or a.get(f"{key}_sma36")
    cand_rsi  = a.get(f"{prefix}_rsi14") or a.get(f"{key}_rsi14")
    if any(x is not None for x in (cand_last, cand_sma, cand_rsi)):
        return {"last": as_float(cand_last), "sma36": as_float(cand_sma), "rsi14": as_float(cand_rsi)}
    return None

# ---------- Bygg pr-ticker ----------
def build_assets(idx: Dict[str, Any]) -> list[Dict[str, Any]]:
    assets_in = _get(idx, "summary", "assets") or _get(idx, "assets") or {}
    if not isinstance(assets_in, dict):
        assets_in = {}

    out = []
    for ticker, a in sorted(assets_in.items()):
        if not isinstance(a, dict):
            a = {}

        frames_in = a.get("frames") if isinstance(a.get("frames"), dict) else {}
        frames = {
            "hourly":  _tf(_get(frames_in, "hourly",  default=_maybe_frame(a, "hourly"))),
            "daily":   _tf(_get(frames_in, "daily",   default=_maybe_frame(a, "daily"))),
            "weekly":  _tf(_get(frames_in, "weekly",  default=_maybe_frame(a, "weekly"))),
            "monthly": _tf(_get(frames_in, "monthly", default=_maybe_frame(a, "monthly"))),
        }

        last = frames["daily"]["last"]
        if last is None:
            last = as_float(a.get("last"))

        hi52 = as_float(a.get("52w_high"))
        lo52 = as_float(a.get("52w_low"))

        is_52w_high = is_52w_low = None
        if last is not None:
            if hi52 is not None:
                is_52w_high = (last >= hi52 * 0.999)
            if lo52 is not None:
                is_52w_low  = (last <= lo52 * 1.001)

        out.append({
            "ticker": ticker,
            "is_52w_high": is_52w_high,
            "is_52w_low":  is_52w_low,
            "52w_high": hi52,
            "52w_low":  lo52,
            "dist_to_36WMA": as_float(a.get("dist_to_36WMA")),
            "dist_to_36MMA": as_float(a.get("dist_to_36MMA")),
            "weekly_close_count_above_36WMA": a.get("weekly_close_count_above_36WMA"),
            "gdx_gld_ratio_vs_50dma": a.get("gdx_gld_ratio_vs_50dma"),
            "sil_slv_ratio_vs_50dma": a.get("sil_slv_ratio_vs_50dma"),
            "vol20_up_ok": a.get("vol20_up_ok"),
            "frames": frames
        })
    return out

# ---------- HTML-tabell ----------
def _round(x, n=2):
    return round(x, n) if isinstance(x, (int, float)) else ""

def build_table_html(assets: list[Dict[str, Any]], gen: str) -> str:
    css = """
<style>
#report-table {border-collapse: collapse; width: 100%; font: 14px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Arial;}
#report-table th, #report-table td { border:1px solid #ddd; padding:6px 8px; text-align:center;}
#report-table th { background:#f5f5f7; position:sticky; top:0;}
#report-table tbody tr:nth-child(even) { background:#fafafa;}
#report-wrap h2 { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;}
#genstamp { color:#555; font-size:12px; margin-top:8px;}
</style>
"""
    header = f"""
{TABLE_START}
<div id="report-wrap">
<h2>Daglig tabell (numerisk)</h2>
{css}
<table id="report-table">
<thead>
<tr>
<th>Ticker</th>
<th>52w</th>
<th>Uker ≥36WMA</th>
<th>Dist 36WMA</th>
<th>Dist 36MMA</th>
<th>H ≥36</th><th>D ≥36</th><th>W ≥36</th><th>M ≥36</th>
<th>RSI14 (D)</th><th>MACD (D)</th><th>MACD cross (D)</th>
<th>GDX/GLD&gt;50DMA</th><th>SIL/SLV&gt;50DMA</th><th>Vol20 up OK</th>
</tr>
</thead>
<tbody>
"""
    rows = []
    for a in assets:
        f = a["frames"]
        h, d, w, m = f["hourly"], f["daily"], f["weekly"], f["monthly"]
        rows.append(
            "<tr>"
            f"<td>{a['ticker']}</td>"
            f"<td>{('H' if a.get('is_52w_high') else '')}{('L' if a.get('is_52w_low') else '')}</td>"
            f"<td>{a.get('weekly_close_count_above_36WMA') or ''}</td>"
            f"<td>{(_round((a.get('dist_to_36WMA') or 0)*100,2) if isinstance(a.get('dist_to_36WMA'),(int,float)) else '')}%</td>"
            f"<td>{(_round((a.get('dist_to_36MMA') or 0)*100,2) if isinstance(a.get('dist_to_36MMA'),(int,float)) else '')}%</td>"
            f"<td>{_bool_to_ja_nei(h.get('close_above_sma36'))}</td>"
            f"<td>{_bool_to_ja_nei(d.get('close_above_sma36'))}</td>"
            f"<td>{_bool_to_ja_nei(w.get('close_above_sma36'))}</td>"
            f"<td>{_bool_to_ja_nei(m.get('close_above_sma36'))}</td>"
            f"<td>{_round(d.get('rsi14'),2)}</td>"
            f"<td>{_round(d.get('macd'),3)}</td>"
            f"<td>{_bool_to_ja_nei(d.get('macd_cross'))}</td>"
            f"<td>{_bool_to_ja_nei(a.get('gdx_gld_ratio_vs_50dma'))}</td>"
            f"<td>{_bool_to_ja_nei(a.get('sil_slv_ratio_vs_50dma'))}</td>"
            f"<td>{_bool_to_ja_nei(a.get('vol20_up_ok'))}</td>"
            "</tr>"
        )

    footer = f"""
</tbody>
</table>
<div id="genstamp">Generert: {gen}</div>
</div>
{TABLE_END}
"""
    return header + "\n".join(rows) + footer

# ---------- Main ----------
def main():
    # 1) Les lokal index.json. Hvis HTML/ugyldig, hent fra speil.
    idx_obj, raw = load_local_json_or_html(INDEX)
    if idx_obj is None:
        if raw is None:
            msg = f"[postprocess] MISSING or EMPTY: {INDEX}"
            # prøv speil uansett
        elif looks_like_html(raw):
            msg = f"[postprocess] HTML detected in {INDEX} (feil innhold). Forsøker speil..."
        else:
            msg = f"[postprocess] INVALID JSON in {INDEX}. Forsøker speil..."
        print(msg)
        idx_obj = try_fetch_index_from_mirrors()
        if idx_obj is None:
            _exit_or_raise(msg + " Speil ga ingen gyldig JSON.")

        # Lagre reparert index.json lokalt for sporbarhet
        try:
            write_json_atomic(INDEX, idx_obj)
            print("[postprocess] Reparerte docs/index.json fra speil.")
        except Exception as e:
            print(f"[postprocess] WARN: kunne ikke skrive reparert index.json: {e}")

    idx = idx_obj
    gen = idx.get("generated_local") or datetime.utcnow().isoformat() + "Z"

    # 2) Bygg assets
    assets = build_assets(idx)

    # 3) Les news (best effort)
    news = {}
    if NEWS.exists():
        news_obj, news_raw = load_local_json_or_html(NEWS)
        if news_obj is not None:
            news = news_obj
        else:
            if news_raw and looks_like_html(news_raw):
                print(f"[postprocess] HTML detected in {NEWS} (hopper over).")
            elif news_raw is None:
                print(f"[postprocess] MISSING: {NEWS}")
            else:
                print(f"[postprocess] INVALID JSON in {NEWS} (hopper over).")

    # 4) Skriv utdata atomisk
    out_obj = {"generated_local": gen, "spec_version": "v1", "assets": assets, "news": news}
    write_json_atomic(OUT_JSON, out_obj)

    md_lines = [
        f"# Daglig rapport – {gen}",
        "",
        "| Ticker | 52w | Uker≥36WMA | Dist36WMA | Dist36MMA | H≥36 | D≥36 | W≥36 | M≥36 | RSI14(D) | MACD(D) | MACDcross(D) | GDX/GLD>50 | SIL/SLV>50 | Vol20 |",
        "|---|---|---:|---:|---:|---|---|---|---|---:|---:|---|---|---|---|"
    ]
    for a in assets:
        f = a["frames"]; h, d, w, m = f["hourly"], f["daily"], f["weekly"], f["monthly"]
        md_lines.append(
            f"| {a['ticker']} | "
            f"{('H' if a.get('is_52w_high') else '')}{('L' if a.get('is_52w_low') else '')} | "
            f"{a.get('weekly_close_count_above_36WMA') or ''} | "
            f"{(_round((a.get('dist_to_36WMA') or 0)*100,2) if isinstance(a.get('dist_to_36WMA'),(int,float)) else '')}% | "
            f"{(_round((a.get('dist_to_36MMA') or 0)*100,2) if isinstance(a.get('dist_to_36MMA'),(int,float)) else '')}% | "
            f"{_bool_to_ja_nei(h.get('close_above_sma36'))} | "
            f"{_bool_to_ja_nei(d.get('close_above_sma36'))} | "
            f"{_bool_to_ja_nei(w.get('close_above_sma36'))} | "
            f"{_bool_to_ja_nei(m.get('close_above_sma36'))} | "
            f"{_round(d.get('rsi14'),2)} | "
            f"{_round(d.get('macd'),3)} | "
            f"{_bool_to_ja_nei(d.get('macd_cross'))} | "
            f"{_bool_to_ja_nei(a.get('gdx_gld_ratio_vs_50dma'))} | "
            f"{_bool_to_ja_nei(a.get('sil_slv_ratio_vs_50dma'))} | "
            f"{_bool_to_ja_nei(a.get('vol20_up_ok'))} |"
        )
    write_text_atomic(OUT_MD, "\n".join(md_lines))

    table_html = build_table_html(assets, gen)
    write_text_atomic(OUT_TABLE, table_html)

    # 5) Oppdater index.html idempotent
    if INDEX_HTML.exists():
        html = INDEX_HTML.read_text(encoding="utf-8")
        if TABLE_START in html and TABLE_END in html:
            html = re.sub(rf"{re.escape(TABLE_START)}.*?{re.escape(TABLE_END)}",
                          table_html, html, flags=re.DOTALL)
        else:
            html = re.sub(r'<h2>Daglig tabell.*?</table>\s*(<div id="genstamp">.*?</div>)?',
                          "", html, flags=re.DOTALL)
            if "</body>" in html:
                html = html.replace("</body>", table_html + "\n</body>")
            else:
                html += "\n" + table_html
        write_text_atomic(INDEX_HTML, html)
    else:
        minimal = f"""<!doctype html><meta charset="utf-8">
<title>Daglig rapport</title>
<body>
<h1>Daglig rapport</h1>
{table_html}
</body>
"""
        write_text_atomic(INDEX_HTML, minimal)

    print("[postprocess] OK")

if __name__ == "__main__":
    main()
