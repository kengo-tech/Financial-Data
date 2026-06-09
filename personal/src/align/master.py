"""
Master grid construction + PIT alignment.

Pipeline:
  1. master daily index = gas trading days (union where any of HH/TTF/JKM trades)
  2. for each series: stamp available_at (release_calendar), then
     pd.merge_asof(direction='backward') onto the master cutoff
  3. leakage check: assert available_at <= cutoff and event_date <= cutoff for all
  4. write data/interim/master_pit.parquet (values) + master_pit_audit.parquet (+PIT cols)

Run:  python -m src.align.master  [--demo 2022-02-25]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.common import RAW_DIR, INTERIM_DIR, log  # noqa: E402
from src.align.release_calendar import SERIES  # noqa: E402

PRICE_COLS = ["hh_fut_usd_mmbtu", "ttf_eur_mwh", "jkm_usd_mmbtu"]

# Max age (days) a carried observation may have since its last release. Beyond this
# the value reverts to NaN (honestly missing) rather than being stale-forwarded
# forever — e.g. a monthly series that gets discontinued must not propagate a
# years-old value into the present. Tolerances exceed each series' normal release
# cadence so live series are never nulled.
TOLERANCE_BY_FREQ = {
    "daily (trading)": 7,
    "daily (gas-day)": 10,
    "daily": 14,
    "weekly": 14,
    "monthly": 45,
}


def load_cache(name: str) -> pd.DataFrame:
    return pd.read_parquet(RAW_DIR / f"{name}.parquet")


def make_master_index(market: pd.DataFrame) -> pd.DatetimeIndex:
    """Gas trading calendar = dates where at least one gas benchmark trades."""
    mask = market[PRICE_COLS].notna().any(axis=1)
    return pd.DatetimeIndex(sorted(market.loc[mask, "date"].unique()))


def build_master() -> pd.DataFrame:
    market = load_cache("market_prices_fx")
    idx = make_master_index(market)
    master = pd.DataFrame({"date": idx})
    master["cutoff"] = master["date"]  # decision cutoff = end of trading day D

    for spec in SERIES:
        key, cols = spec["key"], spec["cols"]
        df = load_cache(spec["cache"])[["date"] + cols].dropna(how="all", subset=cols).copy()
        df[f"{key}__available_at"] = df["date"].apply(spec["avail"])
        df = df.rename(columns={"date": f"{key}__event_date"})
        right = (df[[f"{key}__event_date", f"{key}__available_at"] + cols]
                 .sort_values(f"{key}__available_at"))
        tol = pd.Timedelta(days=TOLERANCE_BY_FREQ.get(spec["freq"], 14))
        master = pd.merge_asof(
            master.sort_values("cutoff"),
            right,
            left_on="cutoff", right_on=f"{key}__available_at",
            direction="backward", tolerance=tol,
        )
    return master.reset_index(drop=True)


def leakage_check(master: pd.DataFrame) -> list[str]:
    """Return a list of violations. Empty list == no look-ahead leakage."""
    problems = []
    for spec in SERIES:
        key = spec["key"]
        av, ev = f"{key}__available_at", f"{key}__event_date"
        sub = master.dropna(subset=[av])
        if not (sub[av] <= sub["cutoff"]).all():
            problems.append(f"{key}: available_at > cutoff on {(sub[av] > sub['cutoff']).sum()} rows")
        if not (sub[ev] <= sub["cutoff"]).all():
            problems.append(f"{key}: event_date > cutoff on {(sub[ev] > sub['cutoff']).sum()} rows")
    return problems


def staleness_table(master: pd.DataFrame) -> pd.DataFrame:
    """For each series: typical age (trading days) of the carried observation."""
    rows = []
    for spec in SERIES:
        key = spec["key"]
        ev = f"{key}__event_date"
        age = (master["cutoff"] - master[ev]).dt.days
        rows.append(dict(series=key, freq=spec["freq"],
                         age_min=int(age.min()), age_median=int(age.median()),
                         age_max=int(age.max()), lag_rule=spec["lag_note"]))
    return pd.DataFrame(rows)


def audit_demo(master: pd.DataFrame, date: str) -> pd.DataFrame:
    """Show, for one master date, what each series knew (event vs available)."""
    row = master.loc[master["date"] == pd.Timestamp(date)]
    if row.empty:
        # fall back to the next available trading day
        row = master.loc[master["date"] >= pd.Timestamp(date)].head(1)
    r = row.iloc[0]
    out = []
    for spec in SERIES:
        key = spec["key"]
        ev, av = r.get(f"{key}__event_date"), r.get(f"{key}__available_at")
        out.append(dict(series=key, freq=spec["freq"],
                        event_date=str(pd.Timestamp(ev).date()) if pd.notna(ev) else "—",
                        available_at=str(pd.Timestamp(av).date()) if pd.notna(av) else "—",
                        age_days=(r["cutoff"] - ev).days if pd.notna(ev) else None))
    return pd.DataFrame(out), str(r["date"].date())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", default="2022-02-25",
                    help="master date to audit (default: first trading day after RU invasion)")
    args = ap.parse_args()

    master = build_master()
    value_cols = [c for spec in SERIES for c in spec["cols"]]

    # 1) leakage check
    problems = leakage_check(master)
    print("=" * 78)
    print("LEAKAGE CHECK (available_at <= cutoff AND event_date <= cutoff, all series)")
    if problems:
        for p in problems:
            print("  !! VIOLATION:", p)
        raise SystemExit("Leakage check FAILED — see violations above.")
    print(f"  PASS — no look-ahead across {len(SERIES)} series, {len(master)} trading days.")

    # 2) staleness summary
    print("\n" + "=" * 78 + "\nSTALENESS (age of carried obs, in days, on the master grid)")
    print(staleness_table(master).to_string(index=False))

    # 3) one-day PIT demo
    demo_df, demo_date = audit_demo(master, args.demo)
    print("\n" + "=" * 78 + f"\nPIT DEMO @ master date {demo_date} (decision cutoff = close of day)")
    print(demo_df.to_string(index=False))

    # 4) write outputs
    audit_path = INTERIM_DIR / "master_pit_audit.parquet"
    values_path = INTERIM_DIR / "master_pit.parquet"
    master.drop(columns=["cutoff"]).to_parquet(audit_path, index=False)
    master[["date"] + value_cols].to_parquet(values_path, index=False)

    txt = INTERIM_DIR / "alignment_audit.txt"
    with open(txt, "w", encoding="utf-8") as fh:
        fh.write(f"Master grid: {len(master)} trading days "
                 f"{master['date'].min().date()} -> {master['date'].max().date()}\n\n")
        fh.write("STALENESS\n" + staleness_table(master).to_string(index=False) + "\n\n")
        fh.write(f"PIT DEMO @ {demo_date}\n" + demo_df.to_string(index=False) + "\n")

    print("\n" + "=" * 78 + "\nMASTER (values) head:")
    print(master[["date"] + value_cols].head().to_string(index=False))
    print(f"\nshape: {master[['date'] + value_cols].shape}  "
          f"({master['date'].min().date()} -> {master['date'].max().date()})")
    print(f"written: {values_path}\n         {audit_path}\n         {txt}")


if __name__ == "__main__":
    main()
