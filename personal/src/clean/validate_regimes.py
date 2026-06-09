"""
Regime validation — data-driven confirmation that the labelled windows coincide
with structural breaks in prices / spreads / risk indices.

Run:  python -m src.clean.validate_regimes
Writes: data/interim/regime_validation.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.common import INTERIM_DIR  # noqa: E402
from src.clean import regimes  # noqa: E402

VARS = ["ttf_usd_mmbtu", "hh_fut_usd_mmbtu", "jkm_usd_mmbtu", "brent_usd_bbl",
        "spread_ttf_hh", "spread_ttf_jkm", "GPR", "GPRC_RUS"]


def _before_during(cl: pd.DataFrame, lo, hi, nbefore: int = 20) -> pd.DataFrame:
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    dur = cl[(cl.date >= lo) & (cl.date <= hi)]
    bef = cl[cl.date < lo].tail(nbefore)
    rows = []
    for c in VARS:
        b, d = bef[c].mean(), dur[c].mean()
        rows.append(dict(var=c, before=round(b, 2), during=round(d, 2),
                         delta=round(d - b, 2),
                         pct=f"{(d / b - 1) * 100:+.0f}%" if b == b and b != 0 else "—",
                         during_peak=round(dur[c].max(), 2)))
    return pd.DataFrame(rows)


def main() -> None:
    cl = pd.read_parquet(INTERIM_DIR / "master_clean.parquet")
    cl["date"] = pd.to_datetime(cl["date"])

    out = ["REGIME VALIDATION\n" + regimes.describe(), ""]
    out.append("[A] REGIME MEANS (level)")
    out.append(cl.groupby("regime")[VARS].mean().reindex(regimes.ORDER).round(2).to_string())

    for name, lo, hi in [("iran_war_2025", regimes.IRAN_WAR_2025_START, regimes.IRAN_WAR_2025_END),
                         ("hormuz_2026", regimes.HORMUZ_2026_START, cl.date.max())]:
        out.append("\n" + "=" * 80)
        out.append(f"[B] {name}: 20-day before vs during")
        out.append(_before_during(cl, lo, hi).to_string(index=False))

    out.append("\n" + "=" * 80)
    out.append("[C] Daily around Hormuz onset (2026-02-20 .. 03-12)")
    win = cl[(cl.date >= "2026-02-20") & (cl.date <= "2026-03-12")][
        ["date", "ttf_usd_mmbtu", "jkm_usd_mmbtu", "brent_usd_bbl",
         "spread_ttf_hh", "spread_ttf_jkm", "regime"]]
    out.append(win.round(2).to_string(index=False))

    text = "\n".join(out)
    print(text)
    (INTERIM_DIR / "regime_validation.txt").write_text(text, encoding="utf-8")
    print(f"\nwritten: {INTERIM_DIR / 'regime_validation.txt'}")


if __name__ == "__main__":
    main()
