from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "group_m3" / "data" / "master_panel_daily.csv"

df = pd.read_csv(DATA)

FEATURES_WITH_PIPELINE = [
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

FEATURES_NO_PIPELINE = [
    c for c in FEATURES_WITH_PIPELINE
    if c != "ru_velke_kapusany_kwh_d"
]

def cleaning_impact(features):
    x = df[features].copy()
    thresh = int(0.6 * len(features))

    x1 = x.dropna(thresh=thresh)
    x2 = x1.ffill()
    x3 = x2.dropna()

    return {
        "n_features": len(features),
        "raw_rows": len(x),
        "after_thresh": len(x1),
        "after_ffill": len(x2),
        "after_final_dropna": len(x3),
        "rows_lost_final": len(x) - len(x3),
    }

out = pd.DataFrame([
    {"case": "with_pipeline", **cleaning_impact(FEATURES_WITH_PIPELINE)},
    {"case": "without_pipeline", **cleaning_impact(FEATURES_NO_PIPELINE)},
])

print(out.to_string(index=False))

out.to_csv("group_m3_data_audit/pipeline_sensitivity_sample_impact.csv", index=False)
