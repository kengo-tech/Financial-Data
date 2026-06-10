from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "group_m3" / "data" / "master_panel_daily.csv"
OUT_DIR = ROOT / "group_m3_data_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS_FROM_NOTEBOOK = [
    "brent_usd_bbl",
    "usdcny",
    "eurusd",
    "carbon_grn_usd",
    "eu_storage_pct",
    "eu_lng_sendout_gwh",
    "ru_velke_kapusany_kwh_d",
    "wind_northsea_kmh",
    "hdd_amsterdam",
    "hdd_chicago",
    "hdd_seoul",
    "us_working_gas_bcf",
    "us_ip_index",
    "euro_ip_index",
    "kr_ip_yoy",
    "GPR",
    "GPRT",
    "GPRA",
    "epu_europe",
    "brent_usd_mmbtu",
]

FOCUS_COLS = [
    "date",
    "euro_ip_index",
    "ru_velke_kapusany_kwh_d",
    "regime",
    "hormuz_2026",
    "spread_ttf_hh",
    "spread_ttf_jkm",
    "ttf_usd_mmbtu",
    "jkm_usd_mmbtu",
    "hh_fut_usd_mmbtu",
]


def detect_date_col(df: pd.DataFrame) -> str | None:
    candidates = ["date", "Date", "datetime", "timestamp", "event_date"]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def longest_na_run(s: pd.Series) -> int:
    is_na = s.isna().to_numpy()
    max_run = 0
    cur = 0
    for v in is_na:
        if v:
            cur += 1
            max_run = max(max_run, cur)
        else:
            cur = 0
    return max_run


def longest_zero_run(s: pd.Series) -> int:
    vals = pd.to_numeric(s, errors="coerce")
    is_zero = (vals == 0).fillna(False).to_numpy()
    max_run = 0
    cur = 0
    for v in is_zero:
        if v:
            cur += 1
            max_run = max(max_run, cur)
        else:
            cur = 0
    return max_run


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing file: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    date_col = detect_date_col(df)

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col).reset_index(drop=True)

    # 1. Basic summary
    basic = {
        "file": str(DATA_PATH),
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "date_col": date_col,
        "date_min": df[date_col].min() if date_col else None,
        "date_max": df[date_col].max() if date_col else None,
    }

    # 2. Column inventory
    pd.DataFrame({"column": df.columns}).to_csv(OUT_DIR / "columns.csv", index=False)

    # 3. Missingness
    miss = (
        df.isna().mean()
        .mul(100)
        .round(2)
        .reset_index()
        .rename(columns={"index": "column", 0: "missing_pct"})
        .sort_values("missing_pct", ascending=False)
    )
    miss.to_csv(OUT_DIR / "missingness_all_columns.csv", index=False)

    # 4. Feature availability from notebook
    feature_rows = []
    for col in FEATURE_COLS_FROM_NOTEBOOK:
        if col in df.columns:
            s = df[col]
            row = {
                "feature": col,
                "present": True,
                "missing_pct": round(float(s.isna().mean() * 100), 2),
                "non_missing_count": int(s.notna().sum()),
                "first_valid_index": s.first_valid_index(),
                "last_valid_index": s.last_valid_index(),
                "longest_na_run": longest_na_run(s),
            }
            if pd.api.types.is_numeric_dtype(s):
                row["zero_count"] = int((pd.to_numeric(s, errors="coerce") == 0).sum())
                row["zero_pct"] = round(float((pd.to_numeric(s, errors="coerce") == 0).mean() * 100), 2)
                row["longest_zero_run"] = longest_zero_run(s)
            else:
                row["zero_count"] = None
                row["zero_pct"] = None
                row["longest_zero_run"] = None
        else:
            row = {
                "feature": col,
                "present": False,
                "missing_pct": None,
                "non_missing_count": 0,
                "first_valid_index": None,
                "last_valid_index": None,
                "longest_na_run": None,
                "zero_count": None,
                "zero_pct": None,
                "longest_zero_run": None,
            }
        feature_rows.append(row)

    feature_audit = pd.DataFrame(feature_rows)
    feature_audit.to_csv(OUT_DIR / "notebook_feature_audit.csv", index=False)

    # 5. Focus columns
    focus_rows = []
    for col in FOCUS_COLS:
        if col in df.columns:
            s = df[col]
            row = {
                "column": col,
                "present": True,
                "missing_pct": round(float(s.isna().mean() * 100), 2),
                "non_missing_count": int(s.notna().sum()),
                "first_valid_index": s.first_valid_index(),
                "last_valid_index": s.last_valid_index(),
                "longest_na_run": longest_na_run(s),
            }
            if pd.api.types.is_numeric_dtype(s):
                vals = pd.to_numeric(s, errors="coerce")
                row["zero_count"] = int((vals == 0).sum())
                row["zero_pct"] = round(float((vals == 0).mean() * 100), 2)
                row["longest_zero_run"] = longest_zero_run(s)
            else:
                row["zero_count"] = None
                row["zero_pct"] = None
                row["longest_zero_run"] = None
        else:
            row = {
                "column": col,
                "present": False,
                "missing_pct": None,
                "non_missing_count": 0,
                "first_valid_index": None,
                "last_valid_index": None,
                "longest_na_run": None,
                "zero_count": None,
                "zero_pct": None,
                "longest_zero_run": None,
            }
        focus_rows.append(row)

    focus_audit = pd.DataFrame(focus_rows)
    focus_audit.to_csv(OUT_DIR / "focus_columns_audit.csv", index=False)

    # 6. Sample impact of notebook-style cleaning
    present_features = [c for c in FEATURE_COLS_FROM_NOTEBOOK if c in df.columns]
    sample_rows = []
    if present_features:
        x = df[present_features].copy()
        thresh = int(0.6 * len(present_features))

        x_after_thresh = x.dropna(thresh=thresh)
        x_after_ffill = x_after_thresh.ffill()
        x_final = x_after_ffill.dropna()

        sample_rows.append({"step": "raw_feature_matrix", "n_rows": len(x), "n_cols": len(x.columns)})
        sample_rows.append({"step": "drop_rows_with_more_than_40pct_missing", "n_rows": len(x_after_thresh), "n_cols": len(x_after_thresh.columns)})
        sample_rows.append({"step": "after_ffill", "n_rows": len(x_after_ffill), "n_cols": len(x_after_ffill.columns)})
        sample_rows.append({"step": "after_final_dropna", "n_rows": len(x_final), "n_cols": len(x_final.columns)})

    sample_impact = pd.DataFrame(sample_rows)
    sample_impact.to_csv(OUT_DIR / "sample_impact_notebook_cleaning.csv", index=False)

    # 7. Pipeline special check around 2025
    pipeline_summary = []
    pipe_col = "ru_velke_kapusany_kwh_d"
    if pipe_col in df.columns and date_col:
        tmp = df[[date_col, pipe_col]].copy()
        tmp[pipe_col] = pd.to_numeric(tmp[pipe_col], errors="coerce")

        for label, mask in [
            ("pre_2025", tmp[date_col] < "2025-01-01"),
            ("post_2025", tmp[date_col] >= "2025-01-01"),
            ("post_2026", tmp[date_col] >= "2026-01-01"),
        ]:
            part = tmp.loc[mask, pipe_col]
            pipeline_summary.append({
                "window": label,
                "n_rows": len(part),
                "missing_pct": round(float(part.isna().mean() * 100), 2) if len(part) else None,
                "zero_pct": round(float((part == 0).mean() * 100), 2) if len(part) else None,
                "mean": round(float(part.mean()), 4) if part.notna().any() else None,
                "min": round(float(part.min()), 4) if part.notna().any() else None,
                "max": round(float(part.max()), 4) if part.notna().any() else None,
            })

    pipeline_df = pd.DataFrame(pipeline_summary)
    pipeline_df.to_csv(OUT_DIR / "pipeline_zero_audit.csv", index=False)

    # 8. Human-readable summary
    lines = []
    lines.append("# Group M3 data audit summary")
    lines.append("")
    lines.append("## Basic file summary")
    for k, v in basic.items():
        lines.append(f"- {k}: {v}")

    lines.append("")
    lines.append("## Highest missingness columns")
    for _, row in miss.head(20).iterrows():
        lines.append(f"- {row['column']}: {row['missing_pct']}%")

    lines.append("")
    lines.append("## Notebook feature audit")
    for _, row in feature_audit.iterrows():
        status = "present" if row["present"] else "MISSING"
        lines.append(
            f"- {row['feature']}: {status}, missing={row['missing_pct']}%, "
            f"zero={row['zero_pct']}%, longest_NA_run={row['longest_na_run']}, "
            f"longest_zero_run={row['longest_zero_run']}"
        )

    lines.append("")
    lines.append("## Sample impact of notebook-style cleaning")
    if not sample_impact.empty:
        for _, row in sample_impact.iterrows():
            lines.append(f"- {row['step']}: {row['n_rows']} rows x {row['n_cols']} cols")

    lines.append("")
    lines.append("## Pipeline zero audit")
    if not pipeline_df.empty:
        for _, row in pipeline_df.iterrows():
            lines.append(
                f"- {row['window']}: n={row['n_rows']}, missing={row['missing_pct']}%, "
                f"zero={row['zero_pct']}%, min={row['min']}, max={row['max']}"
            )
    else:
        lines.append("- Pipeline column not found or date column not found.")

    lines.append("")
    lines.append("## Initial interpretation checklist")
    lines.append("- Euro IP should not cause a large sample collapse. Check `euro_ip_index` missingness and longest NA run.")
    lines.append("- Pipeline zeros should be distinguished from missing values. Check post-2025 zero percentage.")
    lines.append("- If the final sample remains close to the raw sample, `dropna` is not too destructive.")
    lines.append("- If the final sample falls sharply, the model may be driven by missing-data filtering.")

    (OUT_DIR / "audit_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("=" * 80)
    print("Group M3 data audit complete")
    print(f"Rows x cols: {len(df)} x {len(df.columns)}")
    if date_col:
        print(f"Date range: {df[date_col].min()} -> {df[date_col].max()}")
    print(f"Written: {OUT_DIR / 'audit_summary.md'}")
    print(f"Written: {OUT_DIR / 'notebook_feature_audit.csv'}")
    print(f"Written: {OUT_DIR / 'sample_impact_notebook_cleaning.csv'}")
    print(f"Written: {OUT_DIR / 'pipeline_zero_audit.csv'}")


if __name__ == "__main__":
    main()
