"""
Scaling & robust-outlier helpers.

CRITICAL (CLAUDE.md rule): modelling features use ROLLING / expanding windows
only — never full-sample mean/std (that leaks future information). `rolling_z`
defaults to a 252-trading-day window (min 126). Full-sample z is permitted ONLY
for descriptive EDA tables, never for the processed modelling matrix.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WINDOW = 252
MIN_PERIODS = 126


def log_return(s: pd.Series) -> pd.Series:
    return np.log(s.astype("float64")).diff()


def rolling_z(s: pd.Series, window: int = WINDOW, min_periods: int = MIN_PERIODS) -> pd.Series:
    """Causal z-score: (x - rolling_mean) / rolling_std, no future leakage."""
    mu = s.rolling(window, min_periods=min_periods).mean()
    sd = s.rolling(window, min_periods=min_periods).std()
    return (s - mu) / sd.replace(0.0, np.nan)


def yoy(s: pd.Series, periods: int = 252) -> pd.Series:
    """Year-on-year change (≈252 trading days) — de-trends index levels."""
    return s.pct_change(periods, fill_method=None)


def logit(p: pd.Series) -> pd.Series:
    """Logit of a bounded series. Accepts % (0-100) or fraction (0-1)."""
    x = p.astype("float64")
    if x.max(skipna=True) > 1.5:
        x = x / 100.0
    x = x.clip(1e-4, 1 - 1e-4)
    return np.log(x / (1 - x))


def rolling_mad_outliers(s: pd.Series, window: int = 30, k: float = 6.0):
    """Robust outlier flag via rolling median absolute deviation.

    Returns (flags: bool Series, robust_z: Series). Values are NOT modified —
    flagging only (regime extremes must be preserved, per CLAUDE.md).
    """
    med = s.rolling(window, min_periods=window // 2).median()
    mad = (s - med).abs().rolling(window, min_periods=window // 2).median()
    robust_z = 0.6745 * (s - med) / mad.replace(0.0, np.nan)
    return robust_z.abs() > k, robust_z
