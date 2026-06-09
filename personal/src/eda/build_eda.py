"""
Phase 4 — Exploratory Data Analysis. Produces the figures & tables for the M2 memo.

Outputs (figures/ and reports/):
  fig1_prices.png            three benchmarks (USD/MMBtu) + Brent, regime-shaded
  fig2_spreads.png           TTF-HH & TTF-JKM spreads, regime-shaded
  fig3_corr_by_regime.png    correlation structure: full vs normal vs ru_war vs hormuz_2026
  fig4_missing_map.png       missingness of the PIT-aligned master (proves no fabrication)
  fig5_pca.png               scree + PC1/PC2 loadings (M3 preview)
  reports/eda_summary.csv    per-series count/missing/mean/std/skew/kurt/range/span
  reports/stationarity.csv   ADF + KPSS verdicts

Run:  python -m src.eda.build_eda
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.common import INTERIM_DIR, PROJECT_ROOT, log  # noqa: E402
from src.clean import regimes  # noqa: E402

warnings.filterwarnings("ignore")
FIG = PROJECT_ROOT / "figures"
REPORTS = PROJECT_ROOT / "reports"
FIG.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

REGIME_COLORS = {
    "covid": "tab:gray",
    "ru_war": "tab:red",
    "iran_war_2025": "tab:orange",
    "hormuz_2026": "tab:purple",
}


def shade_regimes(ax):
    """Shade each regime window and add a legend handle."""
    for name, lo, hi in regimes.WINDOWS:
        ax.axvspan(lo, hi, color=REGIME_COLORS[name], alpha=0.13, lw=0, label=name)


# --------------------------------------------------------------------------- #
def summary_table(clean: pd.DataFrame) -> pd.DataFrame:
    num = clean.select_dtypes("number")
    rows = []
    for c in num.columns:
        s = num[c]
        valid = clean.loc[s.notna(), "date"]
        rows.append(dict(
            series=c, n=int(s.notna().sum()),
            missing_pct=round(s.isna().mean() * 100, 1),
            mean=round(s.mean(), 3), std=round(s.std(), 3),
            skew=round(s.skew(), 2), kurt=round(s.kurt(), 2),
            min=round(s.min(), 3), max=round(s.max(), 3),
            first=str(valid.min().date()) if len(valid) else "—",
            last=str(valid.max().date()) if len(valid) else "—",
        ))
    return pd.DataFrame(rows)


def fig_prices(clean):
    fig, ax = plt.subplots(figsize=(11, 5))
    for c, lab in [("ttf_usd_mmbtu", "TTF (EU)"), ("hh_fut_usd_mmbtu", "Henry Hub (US)"),
                   ("jkm_usd_mmbtu", "JKM (Asia)")]:
        ax.plot(clean["date"], clean[c], lw=1.0, label=lab)
    ax.set_ylabel("USD / MMBtu")
    ax2 = ax.twinx()
    ax2.plot(clean["date"], clean["brent_usd_bbl"], lw=0.8, color="black", alpha=0.4, label="Brent (rhs)")
    ax2.set_ylabel("Brent USD/bbl", color="gray")
    shade_regimes(ax)
    h1, l1 = ax.get_legend_handles_labels()
    # de-dup regime labels
    seen, H, L = set(), [], []
    for h, l in zip(h1, l1):
        if l not in seen:
            seen.add(l); H.append(h); L.append(l)
    ax.legend(H, L, loc="upper left", fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(FIG / "fig1_prices.png", dpi=130); plt.close(fig)


def fig_spreads(clean):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.axhline(0, color="black", lw=0.6)
    ax.plot(clean["date"], clean["spread_ttf_hh"], lw=1.0, label="TTF - HH", color="tab:blue")
    ax.plot(clean["date"], clean["spread_ttf_jkm"], lw=1.0, label="TTF - JKM", color="tab:green")
    shade_regimes(ax)
    seen, H, L = set(), [], []
    for h, l in zip(*ax.get_legend_handles_labels()):
        if l not in seen:
            seen.add(l); H.append(h); L.append(l)
    ax.legend(H, L, loc="upper left", fontsize=8, ncol=2)
    ax.set_ylabel("USD / MMBtu")
    fig.tight_layout(); fig.savefig(FIG / "fig2_spreads.png", dpi=130); plt.close(fig)


CORR_VARS = ["z_dlog_hh", "z_dlog_ttf", "z_dlog_jkm", "z_dlog_brent",
             "z_us_storage", "z_de_storage_logit", "z_es_sendout",
             "z_hdd_ams", "z_gpr", "z_gprc_rus", "z_epu_europe"]


def fig_corr_by_regime(scaled):
    panels = [("full sample", scaled),
              ("normal", scaled[scaled.regime == "normal"]),
              ("ru_war", scaled[scaled.regime == "ru_war"]),
              ("hormuz_2026", scaled[scaled.regime == "hormuz_2026"])]
    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    for ax, (title, df) in zip(axes.ravel(), panels):
        cm = df[CORR_VARS].corr()
        im = ax.imshow(cm, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(len(CORR_VARS))); ax.set_xticklabels(CORR_VARS, rotation=90, fontsize=7)
        ax.set_yticks(range(len(CORR_VARS))); ax.set_yticklabels(CORR_VARS, fontsize=7)
        ax.set_title(f"{title}  (n={len(df)})", fontsize=10)
        for i in range(len(CORR_VARS)):
            for j in range(len(CORR_VARS)):
                v = cm.iloc[i, j]
                if abs(v) >= 0.3:
                    ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6,
                            color="white" if abs(v) > 0.6 else "black")
    fig.colorbar(im, ax=axes, shrink=0.6, label="correlation")
    fig.savefig(FIG / "fig3_corr_by_regime.png", dpi=130, bbox_inches="tight"); plt.close(fig)


def fig_missing_map(master_pit):
    cols = [c for c in master_pit.columns if c != "date"]
    M = master_pit[cols].isna().T.astype(int)
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.imshow(M, aspect="auto", cmap="Greys", interpolation="nearest",
              extent=[0, len(master_pit), len(cols), 0])
    yrs = master_pit["date"].dt.year
    ticks = [i for i in range(len(master_pit)) if i == 0 or yrs.iloc[i] != yrs.iloc[i - 1]]
    ax.set_xticks(ticks); ax.set_xticklabels([str(yrs.iloc[i]) for i in ticks])
    ax.set_yticks(range(len(cols))); ax.set_yticklabels(cols, fontsize=7)
    ax.set_title("Missingness of the PIT-aligned master  (black = NaN)", fontsize=11)
    fig.tight_layout(); fig.savefig(FIG / "fig4_missing_map.png", dpi=130); plt.close(fig)


PCA_FEATURES = ["z_dlog_hh", "z_dlog_ttf", "z_dlog_jkm", "z_dlog_brent",
                "z_us_storage", "z_de_gas_twh", "z_de_storage_logit",
                "z_es_sendout", "z_es_inv", "z_hdd_ams", "z_hdd_chi", "z_hdd_bei",
                "z_gpr", "z_gprt", "z_gpra", "z_gprc_rus", "z_epu_europe", "z_us_ip_yoy"]


def fig_pca(scaled):
    from sklearn.decomposition import PCA
    X = scaled[PCA_FEATURES].dropna()
    pca = PCA().fit(X)
    evr = pca.explained_variance_ratio_
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
    a1.bar(range(1, len(evr) + 1), evr, color="tab:blue", alpha=0.7)
    a1.plot(range(1, len(evr) + 1), np.cumsum(evr), "-o", color="black", ms=3, label="cumulative")
    a1.set_xlabel("principal component"); a1.set_ylabel("explained variance ratio")
    a1.set_title(f"Scree (n={len(X)}, {len(PCA_FEATURES)} features)"); a1.legend(fontsize=8)
    load = pd.DataFrame(pca.components_[:2].T, index=PCA_FEATURES, columns=["PC1", "PC2"])
    load = load.sort_values("PC1")
    y = range(len(load))
    a2.barh(y, load["PC1"], height=0.4, label="PC1", color="tab:red", alpha=0.7)
    a2.barh([i + 0.4 for i in y], load["PC2"], height=0.4, label="PC2", color="tab:green", alpha=0.7)
    a2.set_yticks([i + 0.2 for i in y]); a2.set_yticklabels(load.index, fontsize=7)
    a2.axvline(0, color="black", lw=0.6); a2.legend(fontsize=8)
    a2.set_title(f"PC1/PC2 loadings (PC1={evr[0]*100:.0f}%, PC2={evr[1]*100:.0f}%)")
    fig.tight_layout(); fig.savefig(FIG / "fig5_pca.png", dpi=130); plt.close(fig)
    return evr, load


STAT_VARS = ["spread_ttf_hh", "spread_ttf_jkm", "d_spread_ttf_hh", "d_spread_ttf_jkm",
             "z_dlog_ttf", "z_gpr", "z_us_storage"]


def stationarity_table(scaled) -> pd.DataFrame:
    from statsmodels.tsa.stattools import adfuller, kpss
    rows = []
    for c in STAT_VARS:
        s = scaled[c].dropna()
        adf_p = adfuller(s, autolag="AIC")[1]
        try:
            kpss_p = kpss(s, regression="c", nlags="auto")[1]
        except Exception:
            kpss_p = np.nan
        # ADF null = unit root (non-stationary); KPSS null = stationary
        verdict = ("stationary" if adf_p < 0.05 and (kpss_p > 0.05 or np.isnan(kpss_p))
                   else "non-stationary" if adf_p >= 0.05 else "borderline")
        rows.append(dict(series=c, adf_p=round(adf_p, 4),
                         kpss_p=round(kpss_p, 4) if kpss_p == kpss_p else "NA",
                         verdict=verdict))
    return pd.DataFrame(rows)


def main():
    clean = pd.read_parquet(INTERIM_DIR / "master_clean.parquet")
    scaled = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "master_scaled.parquet")
    master_pit = pd.read_parquet(INTERIM_DIR / "master_pit.parquet")
    for d in (clean, scaled, master_pit):
        d["date"] = pd.to_datetime(d["date"])

    summ = summary_table(clean)
    summ.to_csv(REPORTS / "eda_summary.csv", index=False)
    log.info("wrote eda_summary.csv (%d series)", len(summ))

    fig_prices(clean)
    fig_spreads(clean)
    fig_corr_by_regime(scaled)
    fig_missing_map(master_pit)
    evr, load = fig_pca(scaled)

    stat = stationarity_table(scaled)
    stat.to_csv(REPORTS / "stationarity.csv", index=False)

    print("=" * 78, "\nEDA SUMMARY (head):")
    print(summ.head(8).to_string(index=False))
    print("\nSTATIONARITY (ADF null=unit root; KPSS null=stationary):")
    print(stat.to_string(index=False))
    print(f"\nPCA: PC1={evr[0]*100:.0f}%  PC2={evr[1]*100:.0f}%  PC3={evr[2]*100:.0f}%  "
          f"(top-3 cumulative {np.cumsum(evr)[2]*100:.0f}%)")
    print("PC1 extremes:", load['PC1'].idxmin(), f"{load['PC1'].min():.2f} ..",
          load['PC1'].idxmax(), f"{load['PC1'].max():.2f}")
    print("\nfigures ->", FIG)
    print("tables  ->", REPORTS / "eda_summary.csv", "|", REPORTS / "stationarity.csv")


if __name__ == "__main__":
    main()
