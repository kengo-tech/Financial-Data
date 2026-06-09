"""
Phase 3 — missing / outlier / scale. Consumes the PIT-aligned master and emits:

  data/interim/master_clean.parquet   levels + spreads + provenance flags + regime
  data/processed/master_scaled.parquet rolling-z modelling matrix (no full-sample stats)
  data/interim/outliers.csv            robust-MAD flags (values NOT modified)

Run:  python -m src.clean.build_clean
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.common import INTERIM_DIR, PROJECT_ROOT, log  # noqa: E402
from src.clean import regimes, scaling  # noqa: E402

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

MWH_PER_MMBTU = 3.41214  # 1 MWh = 3.41214 MMBtu
PRICE_FX = ["hh_fut_usd_mmbtu", "ttf_eur_mwh", "jkm_usd_mmbtu",
            "brent_usd_bbl", "eurusd", "usdcny"]
FFILL_LIMIT = 2  # trading days — cross-market holiday bridge only


# --------------------------------------------------------------------------- #
def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Differentiated missing-value handling with provenance flags.

    - price/fx: forward-fill <=2 trading days (cross-market holidays), flag stale
    - monthly/weekly PIT columns: leave NaN before first release / after a series
      is discontinued (no backfill — would fabricate early signal)
    """
    out = df.copy()
    for c in PRICE_FX:
        was_na = out[c].isna()
        out[c] = out[c].ffill(limit=FFILL_LIMIT)
        out[f"{c}_stale"] = was_na & out[c].notna()
    return out


def derive_spreads(df: pd.DataFrame) -> pd.DataFrame:
    """Common-unit TTF (USD/MMBtu) and the two core cross-basin spreads."""
    out = df.copy()
    out["ttf_usd_mmbtu"] = out["ttf_eur_mwh"] * out["eurusd"] / MWH_PER_MMBTU
    out["spread_ttf_hh"] = out["ttf_usd_mmbtu"] - out["hh_fut_usd_mmbtu"]
    out["spread_ttf_jkm"] = out["ttf_usd_mmbtu"] - out["jkm_usd_mmbtu"]
    return out


def flag_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Robust-MAD outlier flags on price log-returns & spread changes (flag only)."""
    rows = []
    targets = {
        "hh_fut_usd_mmbtu": scaling.log_return(df["hh_fut_usd_mmbtu"]),
        "ttf_usd_mmbtu": scaling.log_return(df["ttf_usd_mmbtu"]),
        "jkm_usd_mmbtu": scaling.log_return(df["jkm_usd_mmbtu"]),
        "brent_usd_bbl": scaling.log_return(df["brent_usd_bbl"]),
        "spread_ttf_hh": df["spread_ttf_hh"].diff(),
        "spread_ttf_jkm": df["spread_ttf_jkm"].diff(),
    }
    any_flag = pd.Series(False, index=df.index)
    for name, series in targets.items():
        flags, robz = scaling.rolling_mad_outliers(series)
        any_flag = any_flag | flags.fillna(False)
        for i in df.index[flags.fillna(False)]:
            rows.append(dict(date=df.at[i, "date"], series=name,
                             change=round(float(series[i]), 4),
                             robust_z=round(float(robz[i]), 1)))
    out = df.copy()
    out["is_outlier_any"] = any_flag
    outliers = pd.DataFrame(rows).sort_values(["date", "series"]) if rows else pd.DataFrame()
    return out, outliers


def build_scaled(clean: pd.DataFrame) -> pd.DataFrame:
    """Rolling-z modelling matrix. Causal transforms only (252d / 126 min)."""
    z = scaling.rolling_z
    lr = scaling.log_return
    out = pd.DataFrame({"date": clean["date"], "regime": clean["regime"]})

    # Targets: spread levels and daily changes
    out["spread_ttf_hh"] = clean["spread_ttf_hh"]
    out["spread_ttf_jkm"] = clean["spread_ttf_jkm"]
    out["d_spread_ttf_hh"] = clean["spread_ttf_hh"].diff()
    out["d_spread_ttf_jkm"] = clean["spread_ttf_jkm"].diff()

    # Price momentum (z of log-returns)
    out["z_dlog_hh"] = z(lr(clean["hh_fut_usd_mmbtu"]))
    out["z_dlog_ttf"] = z(lr(clean["ttf_usd_mmbtu"]))
    out["z_dlog_jkm"] = z(lr(clean["jkm_usd_mmbtu"]))
    out["z_dlog_brent"] = z(lr(clean["brent_usd_bbl"]))

    # Physical fundamentals (z of level; bounded storage% via logit)
    out["z_us_storage"] = z(clean["us_working_gas_bcf"])
    out["z_de_gas_twh"] = z(clean["de_gas_twh"])
    out["z_de_storage_logit"] = z(scaling.logit(clean["de_storage_pct"]))
    out["z_es_sendout"] = z(np.log1p(clean["es_lng_sendout_gwh"]))
    out["z_es_inv"] = z(clean["es_lng_inv_twh"])
    out["z_hdd_ams"] = z(clean["hdd_amsterdam"])
    out["z_hdd_chi"] = z(clean["hdd_chicago"])
    out["z_hdd_bei"] = z(clean["hdd_beijing"])

    # Risk indices (z of level; already unit-free)
    for c in ["GPR", "GPRT", "GPRA", "GPRC_RUS", "epu_europe"]:
        out[f"z_{c.lower()}"] = z(clean[c])

    # Macro (YoY then z)
    out["z_us_ip_yoy"] = z(scaling.yoy(clean["us_ip_index"]))
    out["z_euro_ip_yoy"] = z(scaling.yoy(clean["euro_ip_index"]))
    return out


def main() -> None:
    master = pd.read_parquet(INTERIM_DIR / "master_pit.parquet")
    log.info("loaded master_pit: %s", master.shape)

    clean = handle_missing(master)
    clean = derive_spreads(clean)
    clean["regime"] = regimes.label_regime(clean["date"])
    clean, outliers = flag_outliers(clean)

    scaled = build_scaled(clean)

    # --- write artifacts ---
    clean_path = INTERIM_DIR / "master_clean.parquet"
    scaled_path = PROCESSED_DIR / "master_scaled.parquet"
    outliers_path = INTERIM_DIR / "outliers.csv"
    clean.to_parquet(clean_path, index=False)
    scaled.to_parquet(scaled_path, index=False)
    outliers.to_csv(outliers_path, index=False)

    # --- report ---
    print("=" * 78)
    print(regimes.describe())
    print("\nregime row counts:")
    print(clean["regime"].value_counts().reindex(regimes.ORDER).to_string())

    print("\n" + "=" * 78)
    print("MISSING — price/fx forward-filled (<=2d) cells per column:")
    for c in PRICE_FX:
        print(f"  {c:20s} filled={int(clean[f'{c}_stale'].sum())}")

    print("\n" + "=" * 78)
    print(f"OUTLIERS flagged (robust MAD, k=6): {len(outliers)} rows "
          f"across {outliers['series'].nunique() if len(outliers) else 0} series")
    if len(outliers):
        # sanity: the invasion week must surface as a TTF/spread outlier
        war = outliers[(outliers["date"] >= "2022-02-24") & (outliers["date"] <= "2022-03-15")]
        print(f"  invasion-window (2022-02-24..03-15) flags: {len(war)}  "
              f"-> {sorted(war['series'].unique())}")
        print("  sample (largest |robust_z|):")
        print(outliers.reindex(outliers['robust_z'].abs().sort_values(ascending=False).index)
              .head(6).to_string(index=False))

    print("\n" + "=" * 78)
    print("SCALED matrix (processed) — leakage guard: rolling 252d / min 126 only")
    print(f"  shape={scaled.shape}; z-cols warm-up NaN (first ~126d) is expected")
    print(scaled[["date", "regime", "spread_ttf_hh", "z_dlog_ttf",
                  "z_de_storage_logit", "z_gpr"]].dropna().head().to_string(index=False))

    print("\nwritten:")
    print(f"  {clean_path}")
    print(f"  {scaled_path}")
    print(f"  {outliers_path}")


if __name__ == "__main__":
    main()
