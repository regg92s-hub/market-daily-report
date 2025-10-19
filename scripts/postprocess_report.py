#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, re, datetime as dt
from pathlib import Path
from lib_net import build_session, fetch_first_ok

PAGES = Path("docs")
INDEX = PAGES/"index.json"
NEWS  = PAGES/"news"/"news.json"
OUT_JSON  = PAGES/"report.json"
OUT_MD    = PAGES/"report.md"
OUT_TABLE = PAGES/"report_table.html"
INDEX_HTML= PAGES/"index.html"

RAW_BASE = "https://raw.githubusercontent.com/regg92s-hub/market-daily-report/gh-pages"
JSD_BASE = "https://cdn.jsdelivr.net/gh/regg92s-hub/market-daily-report@gh-pages"
PAG_BASE = "https://regg92s-hub.github.io/market-daily-report"

def _get(d,*ks,default=None):
    cur=d
    for k in ks:
        if not isinstance(cur,dict) or k not in cur: return default
        cur=cur[k]
    return cur

def _tf(fr):
    if not isinstance(fr,dict): return {}
    last=fr.get("last"); sma36=fr.get("sma36")
    dist=None
    if isinstance(last,(int,float)) and isinstance(sma36,(int,float)) and sma36:
        dist=(last-sma36)/sma36
    return {
        "close_above_sma36": fr.get("close_above_sma36"),
        "dist_to_36MA": dist,
        "rsi14": fr.get("rsi14"),
        "macd": fr.get("macd"),
        "macd_signal": fr.get("macd_signal"),
        "macd_hist": fr.get("macd_hist"),
        "macd_cross": fr.get("macd_cross"),
    }

def _round(x,n=2): return round(x,n) if isinstance(x,(int,float)) else ""

def build_assets(idx):
    assets = _get(idx,"summary","assets",default={}) or {}
    out=[]
    for t,a in assets.items():
        o={
            "ticker": t,
            "is_52w_high": None,
            "is_52w_low": None,
            "52w_high": a.get("52w_high"),
            "52w_low": a.get("52w_low"),
            "dist_to_36WMA": a.get("dist_to_36WMA"),
            "dist_to_36MMA": a.get("dist_to_36MMA"),
            "weekly_close_count_above_36WMA": a.get("weekly_close_count_above_36WMA"),
            "gdx_gld_ratio_vs_50dma": a.get("gdx_gld_ratio_vs_50dma"),
            "sil_slv_ratio_vs_50dma": a.get("sil_slv_ratio_vs_50dma"),
            "vol20_up_ok": a.get("vol20_up_ok"),
            "frames": {
                "hourly":  _tf(_get(a,"frames","hourly",default={})),
                "daily":   _tf(_get(a,"frames","daily",default={})),
                "weekly":  _tf(_get(a,"frames","weekly",default={})),
                "monthly": _tf(_get(a,"frames","monthly",default={})),
            }
        }
        last = _get(a,"frames","daily","last")
        if isinstance(last,(int,float)):
            if isinstance(o["52w_high"],(int,float)): o["is_52w_high"] = last >= o["52w_high"]*0.999
            if isinstance(o["52w_low"], (int,float)): o["is_52w_low"]  = last <= o["52w_low"]*1.001
        out.append(o)
    return out

def build_table_html(assets, gen):
    header = """
<h2>Daglig tabell (numerisk)</h2>
<table>
<thead>
<tr>
<th>Ticker</th>
<th>52w</th>
<th>Uker ≥36WMA</th>
<th>Dist 36WMA</th>
<th>Dist 36MMA</th>
<th>H ≥36</th><th>D ≥36</th><th>W ≥36</th><th>M ≥36</th>
<th>RSI14 (D)</th><th>MACD (D)</th><th>MACD cross (D)</th>
<th>GDX/GLD>50DMA</th><th>SIL/SLV>50DMA</th><th>Vol20 up OK</th>
</tr>
</thead>
<tbody>
"""
    rows=[]
    for a in assets:
        f=a["frames"]; d=f["daily"]; w=f["weekly"]; m=f["monthly"]; h=f["hourly"]
        rows.append(f"<tr>"
            f"<td>{a['ticker']}</td>"
            f"<td>{'H' if a.get('is_52w_high') else ''}{'L' if a.get('is_52w_low') else ''}</td>"
            f"<td>{a.get('weekly_close_count_above_36WMA') or ''}</td>"
            f"<td>{_round((a.get('dist_to_36WMA') or 0)*100,2) if isinstance(a.get('dist_to_36WMA'),(int,float)) else ''}%</td>"
            f"<td>{_round((a.get('dist_to_36MMA') or 0)*100,2) if isinstance(a.get('dist_to_36MMA'),(int,float)) else ''}%</td>"
            f"<td>{'Ja' if h.get('close_above_sma36') else ('Nei' if h.get('close_above_sma36') is False else '')}</td>"
            f"<td>{'Ja' if d.get('close_above_sma36') else ('Nei' if d.get('close_above_sma36') is False else '')}</td>"
            f"<td>{'Ja' if w.get('close_above_sma36') else ('Nei' if w.get('close_above_sma36') is False else '')}</td>"
            f"<td>{'Ja' if m.get('close_above_sma36') else ('Nei' if m.get('close_above_sma36') is False else '')}</td>"
            f"<td>{_round(d.get('rsi14'),2)}</td>"
            f"<td>{_round(d.get('macd'),3)}</td>"
            f"<td>{'Ja' if d.get('macd_cross') else ('Nei' if d.get('macd_cross') is False else '')}</td>"
            f"<td>{'Ja' if a.get('gdx_gld_ratio_vs_50dma') else ('Nei' if a.get('gdx_gld_ratio_vs_50dma') is False else '')}</td>"
            f"<td>{'Ja' if a.get('sil_slv_ratio_vs_50dma') else ('Nei' if a.get('sil_slv_ratio_vs_50dma') is False else '')}</td>"
            f"<td>{'Ja' if a.get('vol20_up_ok') else ('Nei' if a.get('vol20_up_ok') is False else '')}</td>"
            f"</tr>")
    footer = f"""
</tbody>
</table>
<p>Generert: {gen}</p>
"""
    return header + "\n".join(rows) + footer

def main():
    # Prøv lokal index.json; hvis HTML/mangler – prøv speil i postprocess (fail-soft)
    gen = dt.datetime.utcnow().isoformat(timespec="seconds")+"Z"
    idx = None
    missing_notes = []

    def is_html_text(path: Path) -> bool:
        try:
            head = path.read_text(encoding="utf-8")[:200].lower()
            return head.startswith("<!doctype") or head.startswith("<html")
        except Exception:
            return False

    if INDEX.exists() and not is_html_text(INDEX):
        try:
            idx = json.loads(INDEX.read_text(encoding="utf-8"))
            gen = idx.get("generated_local") or gen
        except Exception as e:
            missing_notes.append(f"docs/index.json invalid JSON: {e}")

    if idx is None:
        # forsøk å hente index.json fra speil
        session = build_session()
        urls = [
            f"{RAW_BASE}/index.json?t={os.environ.get('GITHUB_RUN_ID','postproc')}",
            f"{JSD_BASE}/index.json?t={os.environ.get('GITHUB_RUN_ID','postproc')}",
            f"{PAG_BASE}/index.json?t={os.environ.get('GITHUB_RUN_ID','postproc')}",
        ]
        try:
            body, used, hdrs = fetch_first_ok(session, urls)
            if body:
                idx = json.loads(body.decode("utf-8", errors="replace"))
                gen = idx.get("generated_local") or gen
                missing_notes.append(f"postprocess: brukte speil for index.json ({used})")
            else:
                missing_notes.append("postprocess: index.json 304 Not Modified – beholder lokal hvis fantes")
        except Exception as e:
            missing_notes.append(f"postprocess: klarte ikke hente index.json fra speil: {e}")

    assets = build_assets(idx or {"summary": {"assets": {}}})

    news = {}
    if NEWS.exists():
        try: news = json.loads(NEWS.read_text(encoding="utf-8"))
        except Exception as e:
            news = {}
            missing_notes.append(f"news/news.json invalid JSON: {e}")

    OUT_JSON.write_text(json.dumps({
        "generated_local": gen,
        "spec_version": "v1",
        "assets": assets,
        "news": news,
        "missing": missing_notes
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        f"# Daglig rapport – {gen}",
        "",
        "## Manglet/feilet",
    ] + [f"- {m}" for m in missing_notes] + [
        "",
        "## Oversikt",
        "",
        "| Ticker | 52w | Uker≥36WMA | Dist36WMA | Dist36MMA | D≥36 | RSI14 | MACD | MACDcross | GDX/GLD>50 | SIL/SLV>50 | Vol20 |",
        "|---|---|---:|---:|---:|---|---:|---:|---|---|---|---|",
    ]
    for a in assets:
        d=a["frames"]["daily"]
        md.append(
            f"| {a['ticker']} | "
            f"{'H' if a.get('is_52w_high') else ''}{'L' if a.get('is_52w_low') else ''} | "
            f"{a.get('weekly_close_count_above_36WMA') or ''} | "
            f"{_round((a.get('dist_to_36WMA') or 0)*100,2) if isinstance(a.get('dist_to_36WMA'),(int,float)) else ''}% | "
            f"{_round((a.get('dist_to_36MMA') or 0)*100,2) if isinstance(a.get('dist_to_36MMA'),(int,float)) else ''}% | "
            f"{'Ja' if d.get('close_above_sma36') else ('Nei' if d.get('close_above_sma36') is False else '')} | "
            f"{_round(d.get('rsi14'),2)} | "
            f"{_round(d.get('macd'),3)} | "
            f"{'Ja' if d.get('macd_cross') else ('Nei' if d.get('macd_cross') is False else '')} | "
            f"{'Ja' if a.get('gdx_gld_ratio_vs_50dma') else ('Nei' if a.get('gdx_gld_ratio_vs_50dma') is False else '')} | "
            f"{'Ja' if a.get('sil_slv_ratio_vs_50dma') else ('Nei' if a.get('sil_slv_ratio_vs_50dma') is False else '')} | "
            f"{'Ja' if a.get('vol20_up_ok') else ('Nei' if a.get('vol20_up_ok') is False else '')} |"
        )
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    table_html = build_table_html(assets, gen)
    OUT_TABLE.write_text(table_html, encoding="utf-8")

    # injiser tabell i index.html hvis finnes
    if INDEX_HTML.exists():
        try:
            html = INDEX_HTML.read_text(encoding="utf-8")
            html = re.sub(r'<h2>Daglig tabell.*?</table>\s*<p>Generert:.*?</p>', "", html, flags=re.DOTALL|re.IGNORECASE)
            html = html.replace("</body>", table_html + "\n</body>") if "</body>" in html else (html + "\n" + table_html)
            INDEX_HTML.write_text(html, encoding="utf-8")
        except Exception:
            pass

if __name__ == "__main__":
    main()
