"""
Market prices & FX — reproduces the M1 "Market — prices & FX" frame.

Target schema (exact M1 column names):
    date, hh_fut_usd_mmbtu, ttf_eur_mwh, jkm_usd_mmbtu, brent_usd_bbl, eurusd
Optional extra (listed in M1 Table 0 coverage matrix): usdcny

Source: Yahoo Finance via yfinance. Verified 2026-06: NG=F / TTF=F / JKM=F /
BZ=F / EURUSD=X all return data from 2019-01-02 with first values matching the
M1 proof-of-ingestion exactly (NG=2.958, TTF=22.475, JKM=8.970, Brent=54.910).
"""
from __future__ import annotations

import warnings

import pandas as pd

from .common import START_DEFAULT, cached, tidy_dates, clip_range, log

warnings.filterwarnings("ignore")

# M1 column name  ->  Yahoo ticker
TICKERS = {
    "hh_fut_usd_mmbtu": "NG=F",     # Henry Hub natural gas futures, USD/MMBtu
    "ttf_eur_mwh":      "TTF=F",    # Dutch TTF gas futures, EUR/MWh
    "jkm_usd_mmbtu":    "JKM=F",    # LNG Japan/Korea Marker futures, USD/MMBtu
    "brent_usd_bbl":    "BZ=F",     # Brent crude futures, USD/bbl
    "eurusd":           "EURUSD=X",
    "usdcny":           "USDCNY=X",
}


def _download_close(ticker: str, start: str, end: str | None) -> pd.Series:
    """Download one ticker's daily Close as a Series indexed by date."""
    import yfinance as yf
    df = yf.download(ticker, start=start, end=end, progress=False,
                     auto_adjust=False, threads=False)
    if df is None or len(df) == 0:
        log.warning("market: %s returned no data", ticker)
        return pd.Series(dtype="float64")
    # yfinance may return MultiIndex columns (field, ticker)
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"]
        s = close[ticker] if ticker in close.columns else close.iloc[:, 0]
    else:
        s = df["Close"]
    s.index = pd.to_datetime(s.index)
    return s.astype("float64")


def fetch_market(start: str = START_DEFAULT, end: str | None = None,
                 refresh: bool = False, include_usdcny: bool = True) -> pd.DataFrame:
    """Return the M1 market frame (date + 5 core columns [+ usdcny])."""
    def _fetch() -> pd.DataFrame:
        cols = dict(TICKERS)
        if not include_usdcny:
            cols.pop("usdcny", None)
        frames = []
        for name, tkr in cols.items():
            s = _download_close(tkr, start, end)
            frames.append(s.rename(name))
        wide = pd.concat(frames, axis=1)
        wide = wide.reset_index().rename(columns={"index": "date", "Date": "date"})
        wide = tidy_dates(wide, "date")
        return clip_range(wide, start, end)

    return cached("market_prices_fx", _fetch, refresh=refresh)


if __name__ == "__main__":
    df = fetch_market(refresh=True)
    print(df.head().to_string(index=False))
