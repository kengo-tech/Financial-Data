"""
Macro — industrial production (US & Euro area). Reproduces M1 "Macro" frame.

Target schema:
    date, us_ip_index, euro_ip_index   (monthly, index level)

Source: FRED, fetched keyless via the public fredgraph.csv endpoint (no API key
required). US = INDPRO. Euro area = first available of a candidate list of
total-industry production indices.
"""
from __future__ import annotations

import io

import pandas as pd

from .common import START_DEFAULT, cached, http_get, tidy_dates, clip_range, log

US_SERIES = "INDPRO"  # Industrial Production: Total Index, monthly, index 2017=100
# Euro-area total industry production candidates (try in order until one returns).
EURO_CANDIDATES = [
    "PRINTO01EZM661S",   # Production: Total industry, Euro area, index, SA, monthly
    "PRINTO01EZM661N",   # same, NSA
    "EA19PRMNTO01IXOBSAM",
]


def _fred_csv(series_id: str, start: str) -> pd.Series:
    """Fetch one FRED series via fredgraph.csv (keyless). Returns Series[date]->value."""
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    r = http_get(url, params={"id": series_id, "cosd": start}, timeout=60, retries=5)
    df = pd.read_csv(io.BytesIO(r.content))
    # columns: observation_date (or DATE), <SERIES_ID>
    date_col = df.columns[0]
    val_col = df.columns[1]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    s = df.set_index(date_col)[val_col].dropna()
    return s


def fetch_macro(start: str = START_DEFAULT, end: str | None = None,
                refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        us = _fred_csv(US_SERIES, start).rename("us_ip_index")

        euro = None
        for sid in EURO_CANDIDATES:
            try:
                euro = _fred_csv(sid, start).rename("euro_ip_index")
                if len(euro):
                    log.info("macro: euro IP series = %s (%d obs)", sid, len(euro))
                    break
            except Exception as e:  # noqa: BLE001
                log.warning("macro: euro candidate %s failed: %s", sid, type(e).__name__)
        if euro is None:
            euro = pd.Series(dtype="float64", name="euro_ip_index")

        wide = pd.concat([us, euro], axis=1).reset_index()
        wide = wide.rename(columns={wide.columns[0]: "date"})
        wide = tidy_dates(wide, "date")
        return clip_range(wide, start, end)

    return cached("macro_industrial_production", _fetch, refresh=refresh)


if __name__ == "__main__":
    print(fetch_macro(refresh=True).head().to_string(index=False))
