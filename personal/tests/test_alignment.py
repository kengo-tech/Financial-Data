"""
Leakage / PIT integrity tests for the aligned master grid.

Runnable two ways:
    pytest tests/test_alignment.py
    python tests/test_alignment.py        # plain asserts + summary
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.align.master import build_master, TOLERANCE_BY_FREQ  # noqa: E402
from src.align.release_calendar import SERIES  # noqa: E402

_MASTER = build_master()


def test_no_lookahead_available_at():
    """Every carried observation became available on or before the decision cutoff."""
    for spec in SERIES:
        av = f"{spec['key']}__available_at"
        sub = _MASTER.dropna(subset=[av])
        assert (sub[av] <= sub["cutoff"]).all(), f"{spec['key']}: available_at > cutoff"


def test_event_date_not_in_future():
    """The underlying event never post-dates the decision cutoff."""
    for spec in SERIES:
        ev = f"{spec['key']}__event_date"
        sub = _MASTER.dropna(subset=[ev])
        assert (sub[ev] <= sub["cutoff"]).all(), f"{spec['key']}: event_date > cutoff"


def test_daily_fundamentals_strictly_lagged():
    """T+1 published series (GIE storage/LNG) must never use same-day data."""
    for key in ("de_storage", "es_lng"):
        ev = f"{key}__event_date"
        sub = _MASTER.dropna(subset=[ev])
        assert (sub[ev] < sub["cutoff"]).all(), f"{key}: same-day leakage (event == cutoff)"


def test_stale_data_not_carried_forever():
    """A discontinued series must revert to NaN, not propagate an ancient value.

    Invariant enforced by merge_asof(tolerance=...): the gap between the decision
    cutoff and the most recent *release* (available_at) never exceeds the series'
    tolerance window. This is what nulls euro_ip after it stops updating in 2023.
    """
    for spec in SERIES:
        av = f"{spec['key']}__available_at"
        tol = TOLERANCE_BY_FREQ.get(spec["freq"], 14)
        sub = _MASTER.dropna(subset=[av])
        gap = (sub["cutoff"] - sub[av]).dt.days
        assert gap.max() <= tol, (
            f"{spec['key']}: availability gap {gap.max()}d exceeds tolerance {tol}d")


def test_master_shape_and_span():
    assert len(_MASTER) > 1500, "too few trading days"
    assert _MASTER["date"].min() <= pd.Timestamp("2019-01-02")
    assert _MASTER["date"].is_monotonic_increasing
    # core spread inputs must be essentially complete
    for c in ("hh_fut_usd_mmbtu", "ttf_eur_mwh"):
        assert _MASTER[c].notna().mean() > 0.95, f"{c} too sparse"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
