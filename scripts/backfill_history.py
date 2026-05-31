#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_history.py  –  Engangs-script (kan kjoeres flere ganger, idempotent)

Rekonstruerer score-historikk for de siste ~8 ukene ved aa:
  1. Hente full prishistorikk for alle instrumenter (samme univers som generate_report)
  2. For hver fredag bakover: kutte data ved den datoen og beregne Northstar-score
  3. Skrive docs/history/{YYYY-MM-DD}.json + manifest.json

Slik faar sparkline-grafene paa sektorscore og rotasjon ekte datapunkter umiddelbart,
i stedet for aa vente 6 uker paa at historikk samler seg.

Kjoer: python scripts/backfill_history.py
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import numpy as np

# Importer alt fra generate_report saa vi bruker EKSAKT samme logikk
import importlib.util
import os
os.environ.setdefault("FORCE_RUN", "true")   # unngaa tidsvindu-gate i generate_report
SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("genreport", SCRIPT_DIR / "generate_report.py")

# generate_report kjoerer main() ved import. For aa unngaa det setter vi en guard:
# vi leser fila og fjerner alt etter "MAIN DATA LOOP"-markoeren, exec'er bare toppen.
src = (SCRIPT_DIR / "generate_report.py").read_text(encoding="utf-8")
marker = "# ─── MAIN LOOP ─"
if marker not in src:
    marker = "log(f\"Starting"
head = src.split(marker)[0]

# Bygg et modul-namespace med kun definisjonene (ingen kjoering av loop).
# Fjern tidsvindu-gate-blokken som ellers kan kalle raise SystemExit foer
# funksjonsdefinisjonene lenger nede i fila rekker aa lastes.
import re as _re
head = _re.sub(
    r"if not FORCE and not \(\(NOW\.hour.*?raise SystemExit\(0\)",
    "pass",
    head, flags=_re.DOTALL)

mod = {}
try:
    exec(compile(head, "genreport_head", "exec"), mod)
except SystemExit:
    pass

INSTRUMENT_GROUPS   = mod["INSTRUMENT_GROUPS"]
get_instrument_series = mod["get_instrument_series"]
resample_frames     = mod["resample_frames"]
frame_summary       = mod["frame_summary"]
northstar_score     = mod["northstar_score"]
score_label         = mod["score_label"]
with_indicators     = mod["with_indicators"]

TZ  = ZoneInfo("Europe/Oslo")
NOW = datetime.now(tz=TZ)

DOCS = Path("docs")
HIST_DIR = DOCS / "history"
HIST_DIR.mkdir(parents=True, exist_ok=True)

WEEKS_BACK = 8

def score_at_cutoff(full_df, cutoff_ts):
    """Beregn Northstar-score som om 'i dag' var cutoff_ts."""
    df = full_df[full_df.index <= cutoff_ts]
    if df is None or len(df) < 200:
        return None
    daily, weekly, monthly = resample_frames(df)
    entry = {"frames": {
        "daily":   frame_summary(daily,   is_weekly=False),
        "weekly":  frame_summary(weekly,  is_weekly=True),
        "monthly": frame_summary(monthly, is_weekly=False),
    }}
    score, _ = northstar_score(entry)
    return score

def main():
    print(f"Backfill starter – {WEEKS_BACK} uker bakover")

    # 0. Hent eksisterende historikk fra live gh-pages slik at vi ikke
    #    overskriver ekte (ikke-backfilled) snapshots som har samlet seg.
    import requests
    PAGES_HIST = "https://regg92s-hub.github.io/market-daily-report/history"
    if not list(HIST_DIR.glob("*.json")):
        try:
            r = requests.get(f"{PAGES_HIST}/manifest.json", timeout=20)
            if r.status_code == 200:
                for d in r.json().get("dates", [])[-60:]:
                    rr = requests.get(f"{PAGES_HIST}/{d}.json", timeout=15)
                    if rr.status_code == 200:
                        (HIST_DIR / f"{d}.json").write_bytes(rr.content)
                print(f"  hentet eksisterende historikk fra gh-pages")
        except Exception as e:
            print(f"  bootstrap hoppet over: {e}")

    # 1. Hent all prisdata en gang
    series_cache = {}
    sector_of = {}
    for group in INSTRUMENT_GROUPS:
        for inst in group["instruments"]:
            iid = inst["id"]
            sector_of[iid] = group.get("sector", "")
            df, resolved = get_instrument_series(inst)
            if df is not None and not df.empty:
                series_cache[iid] = df
                print(f"  hentet {iid} ({resolved})")
            else:
                print(f"  MANGLER {iid}")

    # 2. Finn de siste N fredagene
    fridays = []
    d = NOW.date()
    # gaa til forrige fredag
    while d.weekday() != 4:  # 4 = fredag
        d -= timedelta(days=1)
    for _ in range(WEEKS_BACK):
        fridays.append(d)
        d -= timedelta(days=7)
    fridays.reverse()

    # 3. For hver fredag: beregn score per instrument + sektor-snitt
    written = 0
    for friday in fridays:
        cutoff = pd.Timestamp(friday)
        scores = {}
        for iid, df in series_cache.items():
            try:
                s = score_at_cutoff(df, cutoff)
                if s is not None:
                    scores[iid] = s
            except Exception as e:
                print(f"    {iid} @ {friday}: {e}")

        if not scores:
            continue

        # sektor-snitt
        sector_scores = {}
        for iid, s in scores.items():
            sec = sector_of.get(iid, "Annet")
            sector_scores.setdefault(sec, []).append(s)
        sector_avg = {sec: round(sum(v)/len(v), 1) for sec, v in sector_scores.items()}

        snapshot = {
            "date": friday.strftime("%Y-%m-%d"),
            "generated": f"{friday.isoformat()}T20:00:00+02:00",
            "scores": scores,
            "sector_scores": sector_avg,
            "backfilled": True,
        }
        out = HIST_DIR / f"{friday.strftime('%Y-%m-%d')}.json"
        # ikke overskriv ekte (ikke-backfilled) snapshots
        if out.exists():
            try:
                existing = json.loads(out.read_text(encoding="utf-8"))
                if not existing.get("backfilled"):
                    print(f"  hopper over {friday} (ekte data finnes)")
                    continue
            except Exception:
                pass
        out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1
        print(f"  skrev {friday} ({len(scores)} instrumenter)")

    # 4. Oppdater manifest
    all_dates = sorted([p.stem for p in HIST_DIR.glob("*.json") if p.stem != "manifest"])
    (HIST_DIR / "manifest.json").write_text(
        json.dumps({"dates": all_dates}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Ferdig – skrev {written} snapshots, manifest har {len(all_dates)} datoer")

if __name__ == "__main__":
    main()
