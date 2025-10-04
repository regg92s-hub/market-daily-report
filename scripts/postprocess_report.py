#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
postprocess_report.py
- Leser docs/index.json og docs/news/news.json
- Bygger:
    docs/report.json
    docs/report.md
    docs/report_table.html
- Setter inn HTML-tabellen i docs/index.html (idempotent; ingen duplikat)
- Krever kun index.json (ingen index_lite.json)
"""

from __future__ import annotations
import json, os, re, sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

# ---------- Paths ----------
PAGES      = Path("docs")
INDEX      = PAGES / "index.json"
NEWS       = PAGES / "news" / "news.json"
OUT_JSON   = PAGES / "report.json"
OUT_MD     = PAGES / "report.md"
OUT_TABLE  = PAGES / "report_table.html"
INDEX_HTML = PAGES / "index.html"

TABLE_START = "<!-- REPORT_TABLE_START -->"
TABLE_END   = "<!-- REPORT_TABLE_END -->"

# ---------- Utils ----------
def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def write_json_atomic(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"[postprocess] MISSING: {path}")
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise SystemExit(f"[postprocess] EMPTY: {path} (size=0). Generator skrev ikke gyldig JSON.)")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Skriv litt av innholdet for feilsøk
        snip = raw[:400]
        print(f"[postprocess] FIRST 400 CHARS OF {path}:\n{snip}")
        raise SystemExit(f"[postprocess] INVALID JSON in {path}: {e}")

def _get(d: Dict, *ks, default=None):
    cur = d
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def _round(x, n=2):
    return round(x, n) if isinstance(x, (int, float)) else ""

def _bool_to_ja_nei(v):
    return "Ja" if v is True else ("Nei" if v is False else "")

def _tf(frame: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normaliser per-timeframe felt."""
    if not isinstance(frame, dict):
        frame = {}
    last = frame.get("last")
    sma36 = frame.get("sma36")
    dist = None
    if isinstance(last, (int, float)) and isinstance(sma36, (int, float)) and sma36:
        dist = (last - sma36) / sma36
    return {
        "last": last if isinstance(last, (int, float)) else None,
        "sma36": sma36 if isinstance(sma36, (int, float)) else None,
        "close_above_sma36": frame.get("close_above_sma36"),
        "dist_to_36MA": dist,
        "rsi14": frame.get("rsi14"),
        "macd": frame.get("macd"),
        "macd_signal": frame.get("macd_signal"),
        "macd_hist": frame.get("macd_hist"),
        "macd_cross": frame.get("macd_cross"),
    }

# ---------- Builders ----------
def build_assets(idx: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Trekk ut pr-ticker tall fra index.json på en robust måte."""
    assets_in = _get(idx, "summary", "assets", default={}) or {}
    out = []

    for ticker, a in sorted(assets_in.items()):
        # Tolerer variasjon i index.json-struktur
        frames = {
            "hourly":  _tf(_get(a, "frames", "hourly",  default={})),
            "daily":   _tf(_get(a, "frames", "daily",   default={})),
            "weekly":  _tf(_get(a, "frames", "weekly",  default={})),
            "monthly": _tf(_get(a, "frames", "monthly", default={})),
        }

        # Finn "last" (foretrekk daily.last, ellers top-nivå last)
        last_daily = frames["daily"].get("last")
        last_any   = a.get("last")
        last = last_daily if isinstance(last_daily, (int, float)) else (last_any if isinstance(last_any, (int, float)) else None)

        hi52 = a.get("52w_high")
        lo52 = a.get("52w_low")

        is_52w_high = None
        is_52w_low  = None
        if isinstance(last, (int, float)):
            if isinstance(hi52, (int, float)):
                is_52w_high = (last >= hi52 * 0.999)
            if isinstance(lo52, (int, float)):
                is_52w_low  = (last <= lo52 * 1.001)

        out.append({
            "ticker": ticker,
            "is_52w_high": is_52w_high,
            "is_52w_low":  is_52w_low,
            "52w_high": hi52,
            "52w_low":  lo52,
            "dist_to_36WMA": a.get("dist_to_36WMA"),
            "dist_to_36MMA": a.get("dist_to_36MMA"),
            "weekly_close_count_above_36WMA": a.get("weekly_close_count_above_36WMA"),
            "gdx_gld_ratio_vs_50dma": a.get("gdx_gld_ratio_vs_50dma"),
            "sil_slv_ratio_vs_50dma": a.get("sil_slv_ratio_vs_50dma"),
            "vol20_up_ok": a.get("vol20_up_ok"),
            "frames": frames
        })

    return out

def build_table_html(assets: list[Dict[str, Any]], gen: str) -> str:
    css = """
<style>
#report-table {border-collapse: collapse; width: 100%; font: 14px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Arial; }
#report-table th, #report-table td { border:1px solid #ddd; padding:6px 8px; text-align:center; }
#report-table th { background:#f5f5f7; position:sticky; top:0; }
#report-table tbody tr:nth-child(even) { background:#fafafa; }
#report-wrap h2 { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; }
#genstamp { color:#555; font-size:12px; margin-top:8px; }
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
            f"<td>{(_round((a.get('dist_to_36WMA') or 0)*100,2) if isinstance(a.get('dist_to_36WMA'), (int,float)) else '')}%</td>"
            f"<td>{(_round((a.get('dist_to_36MMA') or 0)*100,2) if isinstance(a.get('dist_to_36MMA'), (int,float)) else '')}%</td>"
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
    # 1) Les index.json (robust)
    idx = load_json_file(INDEX)
    gen = idx.get("generated_local") or datetime.utcnow().isoformat() + "Z"

    # 2) Bygg asset-liste
    assets = build_assets(idx)

    # 3) Les news (valgfritt)
    news = {}
    if NEWS.exists():
        try:
            news = load_json_file(NEWS)
        except SystemExit as e:
            # Ikke fall; bare rapporter videre uten nyheter
            print(str(e))
            news = {}
        except Exception as e:
            print(f"[postprocess] WARN: kunne ikke lese {NEWS}: {e}")
            news = {}

    # 4) Skriv outputs (atomisk)
    out_obj = {
        "generated_local": gen,
        "spec_version": "v1",
        "assets": assets,
        "news": news
    }
    write_json_atomic(OUT_JSON, out_obj)

    md_lines = [
        f"# Daglig rapport – {gen}",
        "",
        "| Ticker | 52w | Uker≥36WMA | Dist36WMA | Dist36MMA | H≥36 | D≥36 | W≥36 | M≥36 | RSI14(D) | MACD(D) | MACDcross(D) | GDX/GLD>50 | SIL/SLV>50 | Vol20 |",
        "|---|---|---:|---:|---:|---|---|---|---|---:|---:|---|---|---|---|"
    ]
    for a in assets:
        f = a["frames"]; d = f["daily"]; h=f["hourly"]; w=f["weekly"]; m=f["monthly"]
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

    # 5) Oppdater index.html idempotent (ingen duplikater)
    if INDEX_HTML.exists():
        html = INDEX_HTML.read_text(encoding="utf-8")

        # Fjern tidligere blokk mellom markører hvis den finnes
        if TABLE_START in html and TABLE_END in html:
            html = re.sub(
                rf"{re.escape(TABLE_START)}.*?{re.escape(TABLE_END)}",
                table_html,
                html,
                flags=re.DOTALL
            )
        else:
            # Backward-compat: fjern evt. gammel tabell-seksjon basert på overskrift
            html = re.sub(
                r'<h2>Daglig tabell.*?</table>\s*(<div id="genstamp">.*?</div>)?',
                "",
                html,
                flags=re.DOTALL
            )
            # Sett inn før </body> om mulig, ellers append
            if "</body>" in html:
                html = html.replace("</body>", table_html + "\n</body>")
            else:
                html = html + "\n" + table_html

        write_text_atomic(INDEX_HTML, html)
    else:
        # Hvis index.html ikke finnes, lag en minimal side
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
