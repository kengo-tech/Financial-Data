"""
Regime labelling for the M1 episodes.

- covid          : non-geopolitical demand shock (CONTROL)
- ru_war         : 2022 Russian invasion — confirmed European pipeline-supply shock
                   (POSITIVE CONTROL for the break-detection framework)
- iran_war_2025  : Jun 2025 "Twelve-Day War" (Israel-Iran). Strikes near Bandar
                   Abbas + Hormuz-closure THREATS, but the strait stayed OPEN —
                   an elevated-risk precursor, not a chokepoint closure.
- hormuz_2026    : 2026 Strait-of-Hormuz crisis — the actual LNG/oil CHOKEPOINT
                   event (CANDIDATE regime to be tested). Iran declared the strait
                   closed; commercial traffic fell >90%.
- normal         : LNG-arbitrage / Law-of-One-Price baseline

Event dates verified 2026-06 against public sources (Wikipedia "Twelve-Day War"
and "2026 Strait of Hormuz crisis", Britannica, ICG). See ROADMAP.
"""
from __future__ import annotations

import pandas as pd

# COVID-19 demand shock (control)
COVID_START = pd.Timestamp("2020-03-11")    # WHO pandemic declaration
COVID_END = pd.Timestamp("2020-06-30")

# Russian invasion of Ukraine — confirmed pipeline-supply shock (positive control)
RU_WAR_START = pd.Timestamp("2022-02-24")
RU_WAR_END = pd.Timestamp("2023-12-31")     # acute European energy-crisis window

# Jun 2025 Twelve-Day War (Israel-Iran) — elevated risk, NO strait closure
IRAN_WAR_2025_START = pd.Timestamp("2025-06-13")  # Israel "Rising Lion" strikes
IRAN_WAR_2025_END = pd.Timestamp("2025-06-24")    # ceasefire

# 2026 Strait-of-Hormuz crisis — actual chokepoint closure (candidate regime)
HORMUZ_2026_START = pd.Timestamp("2026-02-28")    # US/Israel "Epic Fury" strikes
HORMUZ_2026_END = pd.Timestamp("2026-12-31")      # open-ended (closure ongoing; Iran
#   declared strait closed 2026-03-04, refused to reopen after the 2026-04-08 ceasefire)

# Order matters only if windows overlap (these do not).
WINDOWS = [
    ("covid", COVID_START, COVID_END),
    ("ru_war", RU_WAR_START, RU_WAR_END),
    ("iran_war_2025", IRAN_WAR_2025_START, IRAN_WAR_2025_END),
    ("hormuz_2026", HORMUZ_2026_START, HORMUZ_2026_END),
]

# Canonical label order for reporting / value_counts.
ORDER = ["normal", "covid", "ru_war", "iran_war_2025", "hormuz_2026"]


def label_regime(dates: pd.Series) -> pd.Series:
    """Map a date Series to regime labels (later window wins on overlap; else 'normal')."""
    d = pd.to_datetime(dates)
    out = pd.Series("normal", index=d.index, dtype="object")
    for name, lo, hi in WINDOWS:
        out = out.mask((d >= lo) & (d <= hi), name)
    return out


def describe() -> str:
    notes = {
        "iran_war_2025": "  (Twelve-Day War; threats, strait stayed OPEN)",
        "hormuz_2026": "  (actual closure; primary candidate chokepoint regime)",
    }
    lines = ["REGIME WINDOWS (event dates verified against public sources):"]
    for name, lo, hi in WINDOWS:
        lines.append(f"  {name:14s} {lo.date()} -> {hi.date()}{notes.get(name, '')}")
    return "\n".join(lines)
