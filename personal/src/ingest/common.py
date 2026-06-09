"""
公共工具层 (common utilities) for the QF632 ingestion package.

目标 (goal): 复现 Milestone 1 proof-of-ingestion 的精确 schema，从互联网抓取
2019-01-01 至今的数据。所有 fetch 函数遵循统一契约：

    fetch_*(start, end, refresh=False) -> pd.DataFrame

返回的 DataFrame 第一列恒为 `date` (datetime64[ns], 升序, event_date 语义)，
其余列名与 M1 proof-of-ingestion 完全一致。`available_at` 的 point-in-time
标注在 align 阶段 (src/align/) 完成，ingestion 只产出 event_date。
"""
from __future__ import annotations

import io
import time
import logging
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import requests

# --------------------------------------------------------------------------- #
# Paths & config
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
RAW_DIR.mkdir(parents=True, exist_ok=True)
INTERIM_DIR.mkdir(parents=True, exist_ok=True)

START_DEFAULT = "2019-01-01"  # M1 baseline start
HDD_BASE_C = 18.0             # heating-degree-day base temperature (°C)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest")

# Load .env if present (keys are optional; most sources are keyless).
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


def get_key(name: str) -> Optional[str]:
    """Read an API key from the environment (.env already loaded). None if unset."""
    import os
    val = os.environ.get(name)
    return val.strip() if val else None


# --------------------------------------------------------------------------- #
# HTTP helper with retry/backoff
# --------------------------------------------------------------------------- #
_UA = "Mozilla/5.0 (QF632-research; contact: group4)"


def http_get(url: str, *, params: dict | None = None, headers: dict | None = None,
             timeout: int = 60, retries: int = 4, backoff: float = 2.0) -> requests.Response:
    """GET with retries. Raises the last exception if all attempts fail."""
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=h, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001 - we want to retry on anything
            last = e
            wait = backoff ** (attempt - 1)
            log.warning("GET failed (%d/%d) %s -> %s; retry in %.0fs",
                        attempt, retries, url.split("?")[0], type(e).__name__, wait)
            time.sleep(wait)
    raise RuntimeError(f"GET exhausted retries: {url}") from last


# --------------------------------------------------------------------------- #
# Date / frame standardization
# --------------------------------------------------------------------------- #
def tidy_dates(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """Coerce `col` to tz-naive midnight datetime, sort ascending, drop dup dates."""
    out = df.copy()
    out[col] = pd.to_datetime(out[col]).dt.tz_localize(None).dt.normalize()
    out = (out.dropna(subset=[col])
              .drop_duplicates(subset=[col], keep="last")
              .sort_values(col)
              .reset_index(drop=True))
    # date column first
    cols = [col] + [c for c in out.columns if c != col]
    return out[cols]


def clip_range(df: pd.DataFrame, start: str, end: Optional[str], col: str = "date") -> pd.DataFrame:
    out = df[df[col] >= pd.Timestamp(start)]
    if end:
        out = out[out[col] <= pd.Timestamp(end)]
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Parquet cache
# --------------------------------------------------------------------------- #
def cache_path(name: str) -> Path:
    return RAW_DIR / f"{name}.parquet"


def cached(name: str, fn: Callable[[], pd.DataFrame], refresh: bool = False) -> pd.DataFrame:
    """Return cached parquet if present (and not refresh), else fetch + write."""
    p = cache_path(name)
    if p.exists() and not refresh:
        log.info("cache hit  : %s", name)
        return pd.read_parquet(p)
    log.info("fetching   : %s", name)
    df = fn()
    df.to_parquet(p, index=False)
    log.info("cached     : %s  (%d rows, %s -> %s)", name, len(df),
             df["date"].min().date() if len(df) else "—",
             df["date"].max().date() if len(df) else "—")
    return df


def read_excel_url(url: str, **kwargs) -> pd.DataFrame:
    """Download an .xls/.xlsx into memory and parse with pandas."""
    r = http_get(url)
    return pd.read_excel(io.BytesIO(r.content), **kwargs)
