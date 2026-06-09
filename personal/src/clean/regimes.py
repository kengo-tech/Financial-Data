"""
Regime labelling for the M1/M2 episodes.

- covid          : non-geopolitical demand shock (CONTROL)
- ru_war         : 2022 Russian invasion — confirmed European pipeline-supply shock
                   (POSITIVE CONTROL for the break-detection framework)
- iran_war_2025  : Jun 2025 Israel-Iran conflict. This is treated as an
                   elevated geopolitical-risk precursor, not as a confirmed
                   Strait-of-Hormuz closure.
- hormuz_2026    : candidate Strait-of-Hormuz chokepoint-disruption regime.
                   We do not assume a legally complete or fully verified
                   closure in the baseline. Instead, this window is treated as
                   a candidate disruption regime whose persistence and economic
                   relevance must be tested empirically.
- normal         : LNG-arbitrage / Law-of-One-Price baseline

Note: Hormuz 2026 is intentionally framed as a candidate disruption regime,
not as an assumed structural break. The empirical tests decide whether it
behaves like a persistent regime shift or a temporary risk spike.
"""
from __future__ import annotations

import pandas as pd

# COVID-19 demand shock (control)
COVID_START = pd.Timestamp("2020-03-11")
COVID_END = pd.Timestamp("2020-06-30")

# Russian invasion of Ukraine — confirmed pipeline-supply shock (positive control)
RU_WAR_START = pd.Timestamp("2022-02-24")
RU_WAR_END = pd.Timestamp("2023-12-31")

# Jun 2025 Israel-Iran conflict — elevated risk, not treated as confirmed closure
IRAN_WAR_2025_START = pd.Timestamp("2025-06-13")
IRAN_WAR_2025_END = pd.Timestamp("2025-06-24")

# 2026 Strait-of-Hormuz candidate disruption window.
# Kept as an open-ended candidate regime for testing; do not describe as a
# fully verified structural break unless supported by external evidence.
HORMUZ_2026_START = pd.Timestamp("2026-02-28")
HORMUZ_2026_END = pd.Timestamp("2026-12-31")

# Order matters only if windows overlap.
WINDOWS = [
    ("covid", COVID_START, COVID_END),
    ("ru_war", RU_WAR_START, RU_WAR_END),
    ("iran_war_2025", IRAN_WAR_2025_START, IRAN_WAR_2025_END),
    ("hormuz_2026", HORMUZ_2026_START, HORMUZ_2026_END),
]

# Canonical label order for reporting / value_counts.
ORDER = ["normal", "covid", "ru_war", "iran_war_2025", "hormuz_2026"]


def label_regime(dates: pd.Series) -> pd.Series:
    """Map a date Series to regime labels; else 'normal'."""
    d = pd.to_datetime(dates)
    out = pd.Series("normal", index=d.index, dtype="object")
    for name, lo, hi in WINDOWS:
        out = out.mask((d >= lo) & (d <= hi), name)
    return out


def describe() -> str:
    notes = {
        "iran_war_2025": "  (elevated-risk precursor; not a confirmed closure)",
        "hormuz_2026": "  (candidate chokepoint-disruption regime; test empirically)",
    }
    lines = ["REGIME WINDOWS (candidate labels for empirical testing):"]
    for name, lo, hi in WINDOWS:
        lines.append(f"  {name:14s} {lo.date()} -> {hi.date()}{notes.get(name, '')}")
    return "\n".join(lines)