"""
Physical / fundamentals — reproduces the five M1 "Physical" frames.

Frames & target schema:
  us_storage     : date, us_working_gas_bcf                 (EIA, weekly)
  eu_storage_de  : date, de_storage_pct, de_gas_twh         (GIE AGSI+, daily) [needs GIE key]
  es_lng         : date, es_lng_sendout_gwh, es_lng_inv_twh (GIE ALSI, daily)  [needs GIE key]
  hdd            : date, hdd_amsterdam, hdd_chicago, hdd_beijing  (Open-Meteo ERA5, daily)
  entsog         : date, ru_ua_transit_kwh_d                (ENTSOG, daily, best-effort)

Keyless: hdd (Open-Meteo), us_storage (EIA dnav xls fallback), entsog.
Key-gated: eu_storage_de, es_lng (GIE free x-key -> .env GIE_API_KEY).
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

from .common import (START_DEFAULT, HDD_BASE_C, cached, http_get, get_key,
                     tidy_dates, clip_range, log)

# --------------------------------------------------------------------------- #
# US weekly working gas storage — EIA
# --------------------------------------------------------------------------- #
EIA_DNAV_XLS = "https://www.eia.gov/dnav/ng/hist_xls/NW2_EPG0_SWO_R48_BCFw.xls"
EIA_SERIES = "NW2_EPG0_SWO_R48_BCF"


def _us_storage_api(key: str, start: str) -> pd.DataFrame:
    url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
    params = {
        "api_key": key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": EIA_SERIES,
        "start": start,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }
    j = http_get(url, params=params).json()
    rows = j["response"]["data"]
    df = pd.DataFrame(rows)[["period", "value"]]
    df.columns = ["date", "us_working_gas_bcf"]
    df["us_working_gas_bcf"] = pd.to_numeric(df["us_working_gas_bcf"], errors="coerce")
    return df


def _us_storage_dnav() -> pd.DataFrame:
    """Keyless fallback: EIA dnav 'Download Series History' xls."""
    r = http_get(EIA_DNAV_XLS)
    xls = pd.ExcelFile(io.BytesIO(r.content))
    # dnav layout: sheet 'Data 1', row 0 = "Back to Contents", row 1 = headers
    sheet = "Data 1" if "Data 1" in xls.sheet_names else xls.sheet_names[-1]
    # dnav layout: row0 "Back to Contents", row1 "Sourcekey", row2 "Date"/title, data from row3
    df = xls.parse(sheet, skiprows=3, header=None)
    df = df.iloc[:, :2]
    df.columns = ["date", "us_working_gas_bcf"]
    df["us_working_gas_bcf"] = pd.to_numeric(df["us_working_gas_bcf"], errors="coerce")
    return df


def fetch_us_storage(start: str = START_DEFAULT, end: str | None = None,
                     refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        key = get_key("EIA_API_KEY")
        df = None
        if key:
            try:
                df = _us_storage_api(key, start)
            except Exception as e:  # noqa: BLE001
                log.warning("us_storage: EIA API failed (%s), trying dnav", type(e).__name__)
        if df is None:
            df = _us_storage_dnav()
        df = tidy_dates(df, "date")
        return clip_range(df, start, end)

    return cached("physical_us_storage", _fetch, refresh=refresh)


# --------------------------------------------------------------------------- #
# GIE AGSI+ (EU gas storage) & ALSI (EU LNG) — needs free x-key
# --------------------------------------------------------------------------- #
def _gie_paginate(base: str, country: str, start: str, end: str | None, key: str) -> pd.DataFrame:
    """Page through a GIE AGSI/ALSI country series. Returns the raw records frame."""
    to = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    headers = {"x-key": key}
    page, last = 1, 1
    records: list[dict] = []
    while page <= last:
        params = {"country": country, "from": start, "to": to, "size": 300, "page": page}
        j = http_get(base, params=params, headers=headers).json()
        records.extend(j.get("data", []))
        last = int(j.get("last_page", 1))
        page += 1
    return pd.DataFrame(records)


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace({"-": np.nan, "": np.nan}), errors="coerce")


def fetch_eu_storage_de(start: str = START_DEFAULT, end: str | None = None,
                        refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        key = get_key("GIE_API_KEY")
        if not key:
            log.warning("eu_storage_de: GIE_API_KEY not set -> emitting empty schema. "
                        "Register a free key at https://agsi.gie.eu/account and add to .env")
            return pd.DataFrame(columns=["date", "de_storage_pct", "de_gas_twh"])
        raw = _gie_paginate("https://agsi.gie.eu/api", "DE", start, end, key)
        df = pd.DataFrame({
            "date": pd.to_datetime(raw["gasDayStart"]),
            "de_storage_pct": _to_num(raw["full"]),
            "de_gas_twh": _to_num(raw["gasInStorage"]),
        })
        df = tidy_dates(df, "date")
        return clip_range(df, start, end)

    return cached("physical_eu_storage_de", _fetch, refresh=refresh)


def fetch_es_lng(start: str = START_DEFAULT, end: str | None = None,
                 refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        key = get_key("GIE_API_KEY")
        if not key:
            log.warning("es_lng: GIE_API_KEY not set -> emitting empty schema. "
                        "Register a free key at https://alsi.gie.eu/account and add to .env")
            return pd.DataFrame(columns=["date", "es_lng_sendout_gwh", "es_lng_inv_twh"])
        raw = _gie_paginate("https://alsi.gie.eu/api", "ES", start, end, key)
        # ALSI 'inventory' is nested: {"lng": <10^3 m3>, "gwh": <GWh>}.
        # M1's es_lng_inv_twh maps to inventory.lng (matches M1 proof = 2259.35).
        inv_lng = raw["inventory"].apply(lambda d: d.get("lng") if isinstance(d, dict) else d)
        df = pd.DataFrame({
            "date": pd.to_datetime(raw["gasDayStart"]),
            "es_lng_sendout_gwh": _to_num(raw["sendOut"]),
            "es_lng_inv_twh": _to_num(inv_lng),
        })
        df = tidy_dates(df, "date")
        return clip_range(df, start, end)

    return cached("physical_es_lng", _fetch, refresh=refresh)


# --------------------------------------------------------------------------- #
# Weather HDD — Open-Meteo ERA5 (keyless)
# --------------------------------------------------------------------------- #
HDD_CITIES = {
    "hdd_amsterdam": (52.37, 4.90),
    "hdd_chicago": (41.88, -87.63),
    "hdd_beijing": (39.90, 116.40),
}


def _city_hdd(lat: float, lon: float, start: str, end: str) -> pd.Series:
    url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": "temperature_2m_mean", "timezone": "UTC",
    }
    j = http_get(url, params=params).json()["daily"]
    s = pd.Series(j["temperature_2m_mean"], index=pd.to_datetime(j["time"]), dtype="float64")
    return (HDD_BASE_C - s).clip(lower=0.0)  # HDD = max(0, 18 - Tmean)


def fetch_hdd(start: str = START_DEFAULT, end: str | None = None,
              refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        # ERA5 archive lags ~5 days; cap end accordingly to avoid trailing nulls.
        cap = (pd.Timestamp.today() - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
        e = min(end, cap) if end else cap
        cols = {name: _city_hdd(lat, lon, start, e) for name, (lat, lon) in HDD_CITIES.items()}
        wide = pd.concat(cols, axis=1).reset_index().rename(columns={"index": "date"})
        wide = tidy_dates(wide, "date")
        return clip_range(wide, start, end)

    return cached("physical_hdd", _fetch, refresh=refresh)


# --------------------------------------------------------------------------- #
# ENTSOG Russian->EU / UA->SK transit (best-effort, keyless)
# --------------------------------------------------------------------------- #
# Velke Kapusany = principal Ukraine->Slovakia transit point into the EU.
ENTSOG_POINT = "Velke Kapusany / Uzhgorod"


def fetch_entsog(start: str = START_DEFAULT, end: str | None = None,
                 refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        to = end or pd.Timestamp.today().strftime("%Y-%m-%d")
        url = "https://transparency.entsog.eu/api/v1/operationalData"
        params = {
            "forceDownload": "true", "isTransportData": "true",
            "dataset": "1", "indicator": "Physical Flow",
            "periodType": "day", "timezone": "CET",
            "periodize": "0", "limit": -1,
            "pointDirection": "",  # filled by name match below
            "from": start, "to": to,
        }
        try:
            # Query by point name; ENTSOG matches on pointLabel substring.
            params["pointLabel"] = ENTSOG_POINT.split("/")[0].strip()
            j = http_get(url, params=params, timeout=120).json()
            rows = j.get("operationalData", [])
            if not rows:
                raise ValueError("no rows")
            df = pd.DataFrame(rows)
            df = df[["periodFrom", "value"]].copy()
            df.columns = ["date", "ru_ua_transit_kwh_d"]
            df["ru_ua_transit_kwh_d"] = pd.to_numeric(df["ru_ua_transit_kwh_d"], errors="coerce")
            df = df.groupby(df["date"].astype(str).str[:10])["ru_ua_transit_kwh_d"].sum().reset_index()
            df = tidy_dates(df, "date")
            return clip_range(df, start, end)
        except Exception as e:  # noqa: BLE001
            log.warning("entsog: best-effort fetch failed (%s) -> empty schema. "
                        "Point/indicator keys may need manual confirmation.", type(e).__name__)
            return pd.DataFrame(columns=["date", "ru_ua_transit_kwh_d"])

    return cached("physical_entsog_ru_transit", _fetch, refresh=refresh)


if __name__ == "__main__":
    for fn in (fetch_hdd, fetch_us_storage, fetch_eu_storage_de, fetch_es_lng, fetch_entsog):
        print("#", fn.__name__)
        print(fn(refresh=True).head().to_string(index=False), "\n")
