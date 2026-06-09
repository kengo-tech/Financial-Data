# QF632 Group Project Roadmap

## Project Title

**Predicting the JKM-TTF LNG Price Spread from European Gas Fundamentals**

## Current Status

Last updated: 2026-06-09
Current focus: **Milestone 3 - Modelling and Diagnostics**

This roadmap replaces the previous mixed-language version. It summarizes the current project status, completed work for Milestone 1 and Milestone 2, known limitations, and the required tasks for Milestone 3 and the final presentation.

---

# 1. Project Objective

## 1.1 Research Question

This project studies whether the relationship between European natural gas prices and Asian LNG prices changes under geopolitical supply-risk regimes.

The main target is the **JKM-TTF LNG price spread**.

* **JKM** represents the Asian LNG benchmark.
* **TTF** represents the European natural gas benchmark.
* The spread is interpreted as a signal of LNG arbitrage pressure and regional supply-demand imbalance.

## 1.2 Economic Thesis

In normal market conditions, LNG cargoes should flow toward the region offering the higher netback price. This creates an arbitrage link between regional gas prices.

However, under geopolitical supply stress, the spread may reflect more than transportation economics. It may also price:

* European gas storage tightness
* LNG send-out into Europe
* Weather-driven gas demand
* Pipeline disruption risk
* Oil-market stress
* Geopolitical risk
* Security-of-supply premium

## 1.3 Modelling Principle

The project should not model raw gas price levels as the primary target.

The preferred modelling target is:

* changes in the JKM-TTF spread, or
* stationary transformations of the spread.

This follows the Team Guide instruction to avoid modelling non-stationary price levels directly.

---

# 2. Team Guide Alignment

The Team Guide requires the project to focus on:

1. A clear LNG-arbitrage thesis.
2. Reproducible data ingestion.
3. Time-series alignment without look-ahead bias.
4. Missing-data, outlier, and scale treatment.
5. Linear Regression and PCA only.
6. Diagnostic proof, not only performance metrics.
7. Operational interpretation for the final pitch.

## 2.1 Required Methods

The project should use:

* Linear Regression
* PCA
* Regression diagnostics
* PCA diagnostics

The project should avoid unnecessary complex models such as neural networks, tree models, or game-theoretic models. The grading emphasis is on parsimony, transparency, diagnostics, and economic interpretation.

---

# 3. Milestone Timeline

| Date    | Milestone                      | Required Output                                                                      | Current Status |
| ------- | ------------------------------ | ------------------------------------------------------------------------------------ | -------------- |
| May 30  | M1 - Feasibility Proposal      | Thesis, data source plan, proof of ingestion                                         | Completed      |
| June 6  | M2 - Preprocessing and EDA     | Time-series alignment, no-leakage design, missing-data treatment, scaling, EDA plots | Completed      |
| June 13 | M3 - Modelling and Diagnostics | Linear Regression and/or PCA outputs with diagnostic evidence                        | In progress    |
| June 16 | Final Pitch                    | 15-minute institutional-style quant pitch                                            | Not started    |

---

# 4. Repository Structure

Current key folders and files:

```text
personal/
├── data/
│   ├── raw/
│   ├── interim/
│   │   ├── master_pit.parquet
│   │   ├── master_pit_audit.parquet
│   │   ├── master_clean.parquet
│   │   ├── alignment_audit.txt
│   │   ├── proof_of_ingestion.txt
│   │   ├── outliers.csv
│   │   └── regime_validation.txt
│   └── processed/
│       └── master_scaled.parquet
│
├── figures/
│   ├── fig1_prices.png
│   ├── fig2_spreads.png
│   ├── fig3_corr_by_regime.png
│   ├── fig4_missing_map.png
│   └── fig5_pca.png
│
├── reports/
│   ├── QF632_Milestone2_Group4.docx
│   ├── QF632_Milestone2_Group4.pdf
│   ├── eda_summary.csv
│   └── stationarity.csv
│
├── src/
│   ├── ingest/
│   ├── align/
│   ├── clean/
│   ├── eda/
│   └── report/
│
├── tests/
│   └── test_alignment.py
│
├── requirements.txt
├── .env.example
├── .gitignore
├── CLAUDE.md
└── ROADMAP.md
```

---

# 5. Milestone 1 Status

## 5.1 M1 Objective

Milestone 1 was a feasibility proposal. Its goal was to show that the project has:

* a feasible research question,
* a clear economic thesis,
* accessible data sources,
* and proof that the required data can be ingested.

## 5.2 M1 Completed Items

The repository contains M1 documents and proof-of-ingestion outputs.

| Data Category | Dataset                                                | Status              |
| ------------- | ------------------------------------------------------ | ------------------- |
| Market        | Henry Hub futures, TTF futures, JKM futures, Brent, FX | Completed           |
| Macro         | US Industrial Production                               | Completed           |
| Macro         | Euro Industrial Production                             | Partially completed |
| Physical      | US gas storage                                         | Completed           |
| Physical      | Germany gas storage                                    | Completed           |
| Physical      | Spain LNG send-out and inventory                       | Completed           |
| Physical      | Weather HDD                                            | Completed           |
| Risk          | GPR, GPRT, GPRA, GPRC_RUS                              | Completed           |
| Risk          | European EPU                                           | Completed           |
| Physical      | ENTSOG Russian-to-EU pipeline flow                     | Not completed       |

## 5.3 M1 Limitation

ENTSOG pipeline flow is not yet reproducible in the current pipeline. It remains conceptually important, but it should not be treated as a completed model input unless it is fixed and validated.

---

# 6. Milestone 2 Status

## 6.1 M2 Objective

Milestone 2 required:

1. Time-series structural alignment.
2. No look-ahead bias.
3. Missing-data handling.
4. Outlier treatment.
5. Scale transformation.
6. EDA plots and summary tables.
7. A written M2 memo.

## 6.2 M2 Completed Outputs

Milestone 2 is substantially completed.

| Output                  | File                                    | Status    |
| ----------------------- | --------------------------------------- | --------- |
| Proof of ingestion      | `data/interim/proof_of_ingestion.txt`   | Completed |
| PIT-aligned dataset     | `data/interim/master_pit.parquet`       | Completed |
| PIT audit dataset       | `data/interim/master_pit_audit.parquet` | Completed |
| Alignment audit         | `data/interim/alignment_audit.txt`      | Completed |
| Clean dataset           | `data/interim/master_clean.parquet`     | Completed |
| Scaled modelling matrix | `data/processed/master_scaled.parquet`  | Completed |
| Outlier table           | `data/interim/outliers.csv`             | Completed |
| EDA summary             | `reports/eda_summary.csv`               | Completed |
| Stationarity tests      | `reports/stationarity.csv`              | Completed |
| M2 report               | `reports/QF632_Milestone2_Group4.docx`  | Completed |
| M2 report PDF           | `reports/QF632_Milestone2_Group4.pdf`   | Completed |

## 6.3 Time-Series Alignment

The master grid covers daily trading days from 2019 to 2026.

The alignment design follows a point-in-time principle:

* Each observation has an event date.
* Each observation has an available-at timestamp.
* Features are aligned based on what would have been known at the decision time.
* Future data is not backfilled into earlier dates.

This is important because the project combines mixed-frequency data:

* daily prices,
* weekly storage,
* monthly macro data,
* daily weather data,
* daily GIE gas data,
* monthly geopolitical risk data.

## 6.4 Missing Data Treatment

Current treatment:

| Data Issue                     | Treatment                                          |
| ------------------------------ | -------------------------------------------------- |
| Cross-market holidays          | Forward-fill up to 2 trading days with stale flags |
| Weekly EIA storage             | Point-in-time forward-fill after release           |
| Monthly macro data             | Point-in-time forward-fill after release           |
| First-release NaN values       | Kept as NaN                                        |
| Outliers                       | Flag only, not winsorized                          |
| Large geopolitical price moves | Preserved as meaningful regime information         |

## 6.5 Scaling

The modelling matrix uses rolling transformations to avoid full-sample leakage.

Important rules:

* Rolling 252-day z-scores are used.
* Full-sample z-scores are not used for model features.
* Raw and scaled datasets are stored separately.

Main M3 modelling file:

```text
data/processed/master_scaled.parquet
```

---

# 7. EDA Findings

## 7.1 Price and Spread Behaviour

The EDA figures show that cross-basin gas spreads behave differently across regimes.

Main interpretation:

* Normal periods show tighter LNG arbitrage.
* The Russia-Ukraine war period shows a large European supply shock.
* Candidate Hormuz-related stress periods should be tested carefully, not assumed.

## 7.2 Correlation by Regime

The regime correlation plot suggests that the relationship between gas prices, oil, storage, LNG send-out, and risk variables is not stable across all periods.

This supports the thesis that LNG spreads may become regime-dependent under supply stress.

## 7.3 Preliminary PCA Work

A preliminary PCA figure already exists from M2 EDA.

Current interpretation:

* PC1 appears related to geopolitical pressure and European supply stress.
* PC2 may capture a separate macro or demand-related factor.

This is useful preparation for M3, but M3 still needs formal PCA diagnostics and interpretation.

---

# 8. Known Limitations and Design Decisions

This section converts current weaknesses into explicit modelling decisions.

## 8.1 Euro Industrial Production Missingness

Issue:

* `euro_ip_index` has substantial missingness after 2024.
* Using `z_euro_ip_yoy` in the baseline regression may reduce the usable sample size or create avoidable missing-data complications.

Decision:

* Keep Euro IP in the dataset as an auxiliary macro control.
* Do not use `z_euro_ip_yoy` in the M3 baseline regression.
* Use it only in robustness checks if the missing-data issue is resolved or if the sample restriction is clearly disclosed.

Baseline wording:

```text
Euro IP is retained as an auxiliary macro control, but excluded from the baseline model due to substantial post-2024 missingness.
```

## 8.2 ENTSOG Pipeline Flow Not Yet Reproducible

Issue:

* Russian-to-EU pipeline flow is conceptually important.
* However, the current ENTSOG endpoint is not yet reproducible in the pipeline.

Decision:

* Do not rely on `ru_ua_transit_kwh_d` in the M3 baseline regression.
* Use observable proxies for European supply stress instead.

Baseline proxy set:

* Germany gas storage
* Germany storage percentage or logit storage
* Spain LNG send-out
* Spain LNG inventory
* Weather HDD
* GPR and EPU
* Regime labels

Baseline wording:

```text
Pipeline flow is conceptually important, but due to current endpoint limitations, the baseline model uses storage, LNG send-out, weather, risk indices, and regime labels as observable proxies for European supply stress.
```

## 8.3 Hormuz 2026 Regime Framing

Issue:

* The previous wording described Hormuz 2026 too strongly as an actual closure or fully verified structural break.
* This creates overclaim risk.

Decision:

* Treat Hormuz 2026 as a candidate chokepoint-disruption regime.
* Do not assume it is a confirmed structural break.
* Let the empirical tests decide whether it behaves like a persistent regime shift or a temporary risk spike.

Baseline wording:

```text
Hormuz 2026 is treated as a candidate chokepoint-disruption regime, not as an assumed structural break or fully verified closure.
```

---

# 9. M3 Baseline Modelling Plan

## 9.1 M3 Objective

Milestone 3 requires preliminary modelling outputs and diagnostic proof.

The goal is not to maximize predictive performance. The goal is to show:

* a defensible model,
* economically meaningful coefficients,
* proper diagnostics,
* and transparent limitations.

## 9.2 Main Target

Preferred target:

```text
d_spread_ttf_jkm
```

Reason:

* The Team Guide focuses on JKM-TTF.
* The project should avoid raw non-stationary price levels.
* Stationarity tests show that spread changes are safer for regression.

Secondary target:

```text
d_spread_ttf_hh
```

This can be used as a supporting comparison, but it should not replace the JKM-TTF focus.

## 9.3 Baseline Feature Set

Baseline features should be lagged where appropriate.

Suggested baseline features:

| Variable             | Interpretation                    |
| -------------------- | --------------------------------- |
| `z_de_storage_logit` | European storage tightness        |
| `z_de_gas_twh`       | European gas inventory level      |
| `z_es_sendout`       | LNG entering the European grid    |
| `z_es_inv`           | LNG inventory                     |
| `z_hdd_ams`          | European weather demand           |
| `z_dlog_brent`       | Global energy risk                |
| `z_gpr`              | Global geopolitical risk          |
| `z_gprc_rus`         | Russia-specific geopolitical risk |
| Regime dummies       | Structural stress periods         |

Variables to avoid in the baseline:

| Variable              | Reason                           |
| --------------------- | -------------------------------- |
| `z_euro_ip_yoy`       | Missingness after 2024           |
| `ru_ua_transit_kwh_d` | ENTSOG endpoint not reproducible |
| Raw price levels      | Non-stationarity risk            |

## 9.4 Linear Regression Deliverables

P5 should produce:

| Deliverable                   | Suggested File                      |
| ----------------------------- | ----------------------------------- |
| Regression results table      | `outputs/m3/lr_results.csv`         |
| Residual vs fitted plot       | `outputs/m3/residual_vs_fitted.png` |
| VIF table                     | `outputs/m3/vif_table.csv`          |
| Durbin-Watson or residual ACF | `outputs/m3/residual_acf.png`       |
| Information decay results     | `outputs/m3/information_decay.csv`  |
| Information decay plot        | `outputs/m3/information_decay.png`  |

Minimum required diagnostics:

1. Residual-vs-fitted plot.
2. VIF for multicollinearity.
3. Durbin-Watson or residual ACF for autocorrelation.
4. Robust standard errors, preferably Newey-West or HAC.

## 9.5 Information Decay Test

The information decay test should compare model performance under different signal lags.

Suggested lags:

* 0 weeks
* 1 week
* 2 weeks
* 4 weeks

Purpose:

* If predictive power decays quickly, the project can argue that real-time or paid data may have economic value.
* If predictive power does not decay, the free delayed data may be sufficient for this macro-style signal.

---

# 10. PCA Plan for M3

## 10.1 Objective

PCA should be used to manage correlated inputs and extract interpretable factors.

It is not used as a black-box performance booster. It is used for:

* reducing multicollinearity,
* summarizing European supply stress,
* interpreting factor structure,
* supporting the regression.

## 10.2 PCA Deliverables

P6 should produce:

| Deliverable                      | Suggested File                          |
| -------------------------------- | --------------------------------------- |
| PCA scree plot                   | `outputs/m3/pca_scree.png`              |
| PCA loadings table               | `outputs/m3/pca_loadings.csv`           |
| PCA explained variance table     | `outputs/m3/pca_explained_variance.csv` |
| PCA component regression results | `outputs/m3/pca_regression_results.csv` |
| PCA interpretation notes         | `outputs/m3/pca_interpretation.md`      |

## 10.3 Expected PCA Interpretation

Possible interpretation:

| Component | Possible Meaning                                |
| --------- | ----------------------------------------------- |
| PC1       | European supply stress or geopolitical pressure |
| PC2       | Weather-driven demand or macro-energy factor    |
| PC3       | LNG logistics or inventory factor               |

This interpretation must be based on loadings, not guessed.

---

# 11. Final Pitch Structure

The final 15-minute pitch should follow this structure:

1. Research question and LNG arbitrage thesis.
2. Data pipeline and point-in-time alignment.
3. M2 preprocessing and EDA findings.
4. Linear Regression model and diagnostics.
5. PCA model and factor interpretation.
6. Information decay and value of timeliness.
7. Operational realities.
8. Limitations and conclusion.

## 11.1 Recommended Final Message

```text
We find that the JKM-TTF spread is better understood as a regime-dependent LNG arbitrage signal than as a stable linear relationship. European storage, LNG send-out, weather, and geopolitical risk help explain spread changes, but the results are sensitive to regime definitions and data timeliness.
```

---

# 12. Immediate To-Do List

## 12.1 Highest Priority

| Priority | Task                                                       | Owner    | Status |
| -------- | ---------------------------------------------------------- | -------- | ------ |
| 1        | Confirm `master_scaled.parquet` as the official M3 dataset | P4 / all | To do  |
| 2        | Run baseline LR on `d_spread_ttf_jkm`                      | P5       | To do  |
| 3        | Produce LR diagnostics: residual plot, VIF, DW/ACF         | P5       | To do  |
| 4        | Run information decay test                                 | P5       | To do  |
| 5        | Formalize PCA scree and loadings                           | P6       | To do  |
| 6        | Run PCA component regression                               | P6       | To do  |
| 7        | Prepare M3 write-up or slides                              | P1       | To do  |

## 12.2 Secondary Tasks

| Task                                   | Reason                                  |
| -------------------------------------- | --------------------------------------- |
| Run Engle-Granger cointegration test   | Required by Team Guide foundation logic |
| Check whether Euro IP can be refreshed | Optional robustness only                |
| Attempt ENTSOG repair                  | Optional, not baseline-critical         |
| Review Hormuz 2026 external evidence   | Avoid overclaim in final pitch          |

---

# 13. Recommended M3 Baseline Statement

Use this wording in the M3 memo:

```text
Our baseline M3 model uses the processed point-in-time dataset from Milestone 2. The dependent variable is the daily change in the JKM-TTF spread. We exclude Euro IP from the baseline due to substantial post-2024 missingness and exclude ENTSOG pipeline flow because the endpoint is not yet reproducible. Instead, we proxy European supply stress using storage, LNG send-out, weather, geopolitical risk indices, and regime labels. Hormuz 2026 is treated as a candidate chokepoint-disruption regime rather than an assumed structural break.
```

---

# 14. Change Log

## 2026-06-09

* Rewrote the roadmap fully in English.
* Clarified M1, M2, M3, and final presentation status.
* Added M3 baseline modelling restrictions.
* Downgraded Euro IP to an auxiliary macro control.
* Downgraded ENTSOG flow to an optional, non-baseline input.
* Reframed Hormuz 2026 as a candidate disruption regime.
* Added concrete M3 deliverables for Linear Regression and PCA.
