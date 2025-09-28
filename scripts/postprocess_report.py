#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, re
from pathlib import Path
from datetime import datetime

PAGES_DIR = Path(os.getenv("PAGES_DIR", "docs")).resolve()
INDEX_PATH = PAGES_DIR / "index.json"
NEWS_PATH = PAGES_DIR / "news" / "news.json"
OUT_JSON = PAGES_DIR / "report.json"
OUT_MD = PAGES_DIR / "report.md"
OUT_TABLE = PAGES_DIR / "report_table.html"
INDEX_HTML = PAGES_DIR / "index.html"

def _get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def _frame_summary(fr):
    if not isinstance(fr, dict):
        return None
    last  = fr.get("last")
    sma36 = fr.get("sma36")
    dist = None
    if isinstance(last,(int,float)) and isinstance(sma36,(int,float)) and sma36:
        dist = (last - sma36) / sma36
    return {
        "close_above_sma36": fr.get("close_above_sma36"),
        "dist_to_36MA": dist,
        "rsi14": fr.get("rsi14"),
        "macd": fr.get("macd"),
        "macd_signal": fr.get("macd_signal"),
        "macd_hist": fr.get("macd_hist"),
        "macd_cross": fr.get("macd_cross"),
    }

def _asset_summary(ticker, a):
    out = {
        "ticker": ticker,
        "52w_high": a.get("52w_high"),
        "52w_low": a.get("52w_low"),
        "dist_to_36WMA": a.get("dist_to_36WMA"),
        "dist_to_36MMA": a.get("dist_to_36MMA"),
        "weekly_close_count_above_36WMA": a.get("weekly_close_count_above_36WMA"),
        "gdx_gld_ratio_vs_50dma": a.get("gdx_gld_ratio_vs_50dma"),
        "sil_slv_ratio_vs_50dma": a.get("sil_slv_ratio_vs_50dma"),
        "vol20_up_ok": a.get("vol20_up_ok"),
        "frames": {
            "hourly":  _frame_summary(_get(a, "frames", "hourly")),
            "daily":   _frame_summary(_get(a, "frames", "daily")),
            "weekly":  _frame_summary(_get(a, "frames", "weekly")),
            "monthly": _frame_summary(_get(a, "frames", "monthly")),
        },
    }
    # 52w flagg (basert på daily last om tilgjengelig):
    last = _get(a, "frames", "daily", "last")
    if isinstance(last,(int,float)):
        if isinstance(out["52w_high"],(int,float)):
            out["is_52w_high"] = last >= out["52w_high"] * 0.999
        if isinstance(out["52w_low"],(int,float)):
            out["is_52w_low"] = last <= out["52w_low"] * 1.001
    return out

def _round(x, n=2):
    return round(x, n) if isinstance(x, (int,float)) else ""

def build_table_html(assets, generated_local):
    rows = []
    for a in assets:
        d = a["frames"].get("daily") or {}
        rows.append(f"""
    <tr>
      <td>{a['ticker']}</td>
      <td>{'H' if a.get('is_52w_high') else ''}{'L' if a.get('is_52w_low') else ''}</td>
      <td>{a.get('weekly_close_count_above_36WMA') if a.get('weekly_close_count_above_36WMA') is not None else ''}</td>
      <td>{_round((a.get('dist_to_36WMA') or 0)*100,2) if isinstance(a.get('dist_to_36WMA'),(int,float)) else ''}%</td>
      <td>{'Ja' if d.get('close_above_sma36') is True else ('Nei' if d.get('close_above_sma36') is False else '')}</td>
      <td>{_round(d.get('rsi14'),2)}</td>
      <td>{_round(d.get('macd'),3)}</td>
    </tr>""")
    return f"""<h2>Daglig tabell (fallback)</h2>
<table>
  <thead>
    <tr>
      <th>Ticker</th>
      <th>52w</th>
      <th>Uker ≥36WMA</th>
      <th>Dist 36WMA</th>
      <th>Daily ≥36MA</th>
      <th>RSI14</th>
      <th>MACD</th>
    </tr>
  </thead>
  <tbody>
{''.join(rows)}
  </tbody>
</table>
<p>Generert: {generated_local}</p>"""

def main():
    if not INDEX_PATH.exists():
        raise SystemExit("Mangler docs/index.json")
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        idx = json.load(f)

    generated_local = idx.get("generated_local") or datetime.utcnow().isoformat()+"Z"
    assets_src = _get(idx, "summary", "assets") or {}
    assets_out = [_asset_summary(t, a) for t, a in assets_src.items()]

    # Nyheter (valgfritt)
    news = {}
    if NEWS_PATH.exists():
        try:
            with open(NEWS_PATH, "r", encoding="utf-8") as f:
                news = json.load(f)
        except Exception:
            news = {}

    # report.json
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "generated_local": generated_local,
            "spec_version": "v1",
            "assets": assets_out,
            "news": news
        }, f, ensure_ascii=False, indent=2)

    # report.md (kompakt)
    lines = [
        f"# Daglig rapport – {generated_local}",
        "",
        "| Ticker | 52w | Uker ≥36WMA | Dist 36WMA | Daily ≥36MA | RSI14 | MACD |",
        "|---|---|---:|---:|---|---:|---:|",
    ]
    for a in assets_out:
        d = a["frames"].get("daily") or {}
        lines.append(
            f"| {a['ticker']} | "
            f"{'H' if a.get('is_52w_high') else ''}{'L' if a.get('is_52w_low') else ''} | "
            f"{a.get('weekly_close_count_above_36WMA') if a.get('weekly_close_count_above_36WMA') is not None else ''} | "
            f"{_round((a.get('dist_to_36WMA') or 0)*100,2) if isinstance(a.get('dist_to_36WMA'),(int,float)) else ''}% | "
            f"{'Ja' if d.get('close_above_sma36') is True else ('Nei' if d.get('close_above_sma36') is False else '')} | "
            f"{_round(d.get('rsi14'),2)} | "
            f"{_round(d.get('macd'),3)} |"
        )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    # report_table.html
    table_html = build_table_html(assets_out, generated_local)
    OUT_TABLE.write_text(table_html, encoding="utf-8")

    # injiser tabell nederst i index.html hvis finnes
    if INDEX_HTML.exists():
        html = INDEX_HTML.read_text(encoding="utf-8")
        # fjern ev. gammel tabell
        html = re.sub(r'<h2>Daglig tabell \(fallback\)</h2>.*?</table>\s*<p>Generert:.*?</p>', "", html, flags=re.DOTALL)
        if "</body>" in html:
            html = html.replace("</body>", table_html + "\n</body>")
        else:
            html = html + "\n" + table_html
        INDEX_HTML.write_text(html, encoding="utf-8")

if __name__ == "__main__":
    main()
