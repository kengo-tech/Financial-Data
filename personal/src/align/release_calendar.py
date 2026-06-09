"""
Release calendar — single source of truth for point-in-time (PIT) availability.

每个 series 携带两类日期:
  event_date    : 观测所指代的样本日期 (raw ingest 产出的 `date`)
  available_at  : 该观测在现实中最早可被使用的日期 (= release rule applied to event_date)

合并时一律 `merge_asof(..., on='available_at', direction='backward')`，绝不 join
on event_date —— 这是防 look-ahead / data-leakage 的关键。

发布时延按"保守取上限"原则估计 (宁可标记得比现实更晚，也不要更早)。
"""
from __future__ import annotations

import pandas as pd


# --- availability rules: event_date -> available_at -------------------------- #
def same_day(d: pd.Timestamp) -> pd.Timestamp:
    """Exchange settle known at close of the same day."""
    return d


def t_plus(n: int):
    """Daily series available n calendar days after the event (publication lag)."""
    return lambda d: d + pd.Timedelta(days=n)


def month_end_plus(n: int):
    """Monthly series (event dated 1st of month) available n days after month-end."""
    return lambda d: (d + pd.offsets.MonthEnd(1)) + pd.Timedelta(days=n)


# --- series registry --------------------------------------------------------- #
# key          : short id used for the PIT provenance columns
# cache        : parquet name under data/raw/
# cols         : value columns to carry (must match M1 schema)
# avail        : event_date -> available_at
# lag_note     : human-readable release rule for the report
SERIES = [
    dict(key="market", cache="market_prices_fx",
         cols=["hh_fut_usd_mmbtu", "ttf_eur_mwh", "jkm_usd_mmbtu",
               "brent_usd_bbl", "eurusd", "usdcny"],
         avail=same_day, freq="daily (trading)",
         lag_note="T+0 exchange settle (known at close of day)"),
    dict(key="us_storage", cache="physical_us_storage",
         cols=["us_working_gas_bcf"],
         avail=t_plus(6), freq="weekly",
         lag_note="EIA weekly report: week-ending Fri released following Thu (≈T+6)"),
    dict(key="de_storage", cache="physical_eu_storage_de",
         cols=["de_storage_pct", "de_gas_twh"],
         avail=t_plus(1), freq="daily (gas-day)",
         lag_note="GIE AGSI+ gas-day published next morning (T+1)"),
    dict(key="es_lng", cache="physical_es_lng",
         cols=["es_lng_sendout_gwh", "es_lng_inv_twh"],
         avail=t_plus(1), freq="daily (gas-day)",
         lag_note="GIE ALSI gas-day published next morning (T+1)"),
    dict(key="hdd", cache="physical_hdd",
         cols=["hdd_amsterdam", "hdd_chicago", "hdd_beijing"],
         avail=t_plus(5), freq="daily",
         lag_note="Open-Meteo ERA5 reanalysis lag ≈ T+5"),
    dict(key="us_ip", cache="macro_industrial_production",
         cols=["us_ip_index"],
         avail=month_end_plus(20), freq="monthly",
         lag_note="FRED INDPRO released mid next month (conservative month-end +20d)"),
    dict(key="euro_ip", cache="macro_industrial_production",
         cols=["euro_ip_index"],
         avail=month_end_plus(45), freq="monthly",
         lag_note="Eurostat euro-area IP released ≈ month-end +45d"),
    dict(key="gpr", cache="risk_gpr",
         cols=["GPR", "GPRT", "GPRA", "GPRC_RUS"],
         avail=month_end_plus(10), freq="monthly",
         lag_note="Caldara-Iacoviello GPR updated ≈ 10th of next month"),
    dict(key="epu", cache="risk_epu_europe",
         cols=["epu_europe"],
         avail=month_end_plus(7), freq="monthly",
         lag_note="EPU Europe published early next month (≈ month-end +7d)"),
]
