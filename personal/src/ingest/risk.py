"""
Risk indices — reproduces the two M1 "Risk" frames.

Frames & target schema:
  gpr : date, GPR, GPRT, GPRA, GPRC_RUS   (Caldara-Iacoviello, monthly)
  epu : date, epu_europe                  (policyuncertainty.com, monthly)

Both keyless (public Excel files).
"""
from __future__ import annotations

import pandas as pd

from .common import START_DEFAULT, cached, read_excel_url, tidy_dates, clip_range, log

GPR_MAIN = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"
GPR_COUNTRY = "https://www.matteoiacoviello.com/gpr_files/data_gpr_country_export.xls"
EPU_EUROPE = "https://www.policyuncertainty.com/media/Europe_Policy_Uncertainty_Data.xlsx"


def _find_col(df: pd.DataFrame, *cands: str) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for c in cands:
        if c.lower() in low:
            return low[c.lower()]
    return None


def fetch_gpr(start: str = START_DEFAULT, end: str | None = None,
              refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        main = read_excel_url(GPR_MAIN)
        dcol = _find_col(main, "month", "date")
        main["date"] = pd.to_datetime(main[dcol], errors="coerce")
        # The main export file already carries GPR/GPRT/GPRA and the country
        # column GPRC_RUS (verified 2026-06); no separate country file needed.
        keep = {"date": "date"}
        for c in ("GPR", "GPRT", "GPRA", "GPRC_RUS"):
            col = _find_col(main, c)
            if col:
                keep[col] = c
            else:
                log.warning("gpr: column %s not found in main file", c)
        df = main[list(keep)].rename(columns=keep)
        if "GPRC_RUS" not in df.columns:
            df["GPRC_RUS"] = pd.NA

        df = tidy_dates(df, "date")
        return clip_range(df, start, end)

    return cached("risk_gpr", _fetch, refresh=refresh)


def fetch_epu(start: str = START_DEFAULT, end: str | None = None,
              refresh: bool = False) -> pd.DataFrame:
    def _fetch() -> pd.DataFrame:
        raw = read_excel_url(EPU_EUROPE)
        ycol = _find_col(raw, "Year")
        mcol = _find_col(raw, "Month")
        vcol = _find_col(raw, "European_News_Index", "Europe_News_Index",
                         "European News Index", "European_News_Based_Index")
        if vcol is None:
            # fall back to the last numeric column
            num = raw.select_dtypes("number").columns
            vcol = num[-1]
            log.warning("epu: index column guessed as '%s'", vcol)
        df = raw.dropna(subset=[ycol, mcol]).copy()
        df["date"] = pd.to_datetime(
            dict(year=df[ycol].astype(int), month=df[mcol].astype(int), day=1))
        df = df[["date", vcol]].rename(columns={vcol: "epu_europe"})
        df["epu_europe"] = pd.to_numeric(df["epu_europe"], errors="coerce")
        df = tidy_dates(df, "date")
        return clip_range(df, start, end)

    return cached("risk_epu_europe", _fetch, refresh=refresh)


if __name__ == "__main__":
    print(fetch_gpr(refresh=True).head().to_string(index=False), "\n")
    print(fetch_epu(refresh=True).head().to_string(index=False))
