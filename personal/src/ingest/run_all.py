"""
Orchestrator — fetch every M1 frame, cache to data/raw/, and emit a combined
proof-of-ingestion (first 5 rows of each) that mirrors the M1 submission.

Usage (from project root):
    python -m src.ingest.run_all --start 2019-01-01 [--refresh]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow `python src/ingest/run_all.py` as well as `-m src.ingest.run_all`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.ingest import common, market, macro, physical, risk
else:
    from . import common, market, macro, physical, risk

from src.ingest.common import START_DEFAULT, INTERIM_DIR, log  # noqa: E402

# (title, callable, expected M1 columns) — ordered as in the M1 proof-of-ingestion.
FRAMES = [
    ("Market — prices & FX (Yahoo)", market.fetch_market,
     ["hh_fut_usd_mmbtu", "ttf_eur_mwh", "jkm_usd_mmbtu", "brent_usd_bbl", "eurusd"]),
    ("Macro — industrial production, US & Euro (FRED)", macro.fetch_macro,
     ["us_ip_index", "euro_ip_index"]),
    ("Physical — US Lower-48 weekly storage (EIA)", physical.fetch_us_storage,
     ["us_working_gas_bcf"]),
    ("Physical — EU gas storage, Germany (GIE AGSI+)", physical.fetch_eu_storage_de,
     ["de_storage_pct", "de_gas_twh"]),
    ("Physical — EU LNG send-out & inventory, Spain (ALSI)", physical.fetch_es_lng,
     ["es_lng_sendout_gwh", "es_lng_inv_twh"]),
    ("Physical — Weather HDD, demand centres (Open-Meteo)", physical.fetch_hdd,
     ["hdd_amsterdam", "hdd_chicago", "hdd_beijing"]),
    ("Physical — Russian->EU flow, UA->SK (ENTSOG)", physical.fetch_entsog,
     ["ru_ua_transit_kwh_d"]),
    ("Risk — Geopolitical Risk incl. Russia (Caldara-Iacoviello)", risk.fetch_gpr,
     ["GPR", "GPRT", "GPRA", "GPRC_RUS"]),
    ("Risk — European Economic Policy Uncertainty (EPU)", risk.fetch_epu,
     ["epu_europe"]),
]


def main() -> None:
    ap = argparse.ArgumentParser(description="QF632 ingestion — reproduce M1 frames")
    ap.add_argument("--start", default=START_DEFAULT)
    ap.add_argument("--end", default=None)
    ap.add_argument("--refresh", action="store_true", help="ignore cache, re-fetch")
    args = ap.parse_args()

    out_lines: list[str] = []
    status: list[dict] = []

    for title, fn, expected in FRAMES:
        header = "=" * 78 + f"\n{title}"
        print("\n" + header)
        try:
            df = fn(start=args.start, end=args.end, refresh=args.refresh)
            ok = len(df) > 0
            cov = (f"{df['date'].min().date()} -> {df['date'].max().date()}"
                   if ok else "EMPTY")
            missing = [c for c in expected if c not in df.columns]
            body = df.head().to_string(index=False) if ok else "(no rows returned)"
            print(body)
            status.append({"frame": title.split(" — ")[0] + " — " + title.split(" — ")[1][:28],
                           "rows": len(df), "coverage": cov,
                           "missing_cols": ",".join(missing) or "—"})
            out_lines += [header, body, ""]
        except Exception as e:  # noqa: BLE001
            print(f"  !! FAILED: {type(e).__name__}: {e}")
            status.append({"frame": title[:40], "rows": 0, "coverage": "FAILED",
                           "missing_cols": "ALL"})
            out_lines += [header, f"FAILED: {e}", ""]

    proof = INTERIM_DIR / "proof_of_ingestion.txt"
    proof.write_text("\n".join(out_lines), encoding="utf-8")

    print("\n" + "=" * 78 + "\nINGESTION SUMMARY")
    print(pd.DataFrame(status).to_string(index=False))
    print(f"\nProof-of-ingestion written to: {proof}")
    print(f"Per-source parquet caches in:  {common.RAW_DIR}")


if __name__ == "__main__":
    main()
