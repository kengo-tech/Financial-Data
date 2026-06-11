# M3 Report Claims Check

## Purpose

This note checks whether the main claims in the M3 report are supported by the data, figures, code logic, and audit results.

The goal is to make the final conclusion defensible. We should avoid overstating the model as a strong short-horizon forecasting model. The safer framing is that the PCA/PCR framework provides evidence of regime-dependent structural association, especially for TTF-JKM.

---

## 1. Data and sample foundation

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| The M3 analysis uses `master_panel_daily.csv`. | `group_m3/data/master_panel_daily.csv` | Supported | The dataset has 1,934 rows and 32 columns, covering 2019-01-02 to 2026-06-01. |
| The model uses train period 2019-2025 and test period 2026. | M3 report Section 2 and Section 7 | Supported | Train/test split is clearly stated. |
| The 2026 Iran/Hormuz window is fully held out. | M3 report Section 2 and Section 7 | Supported | The report says scaler, PCA, and PCR are fit on train and only transformed on test. |
| The data pipeline avoids direct price-leg leakage. | M3 report feature-selection logic | Supported | Price legs are excluded from PCA features to avoid mechanically explaining spreads using their own components. |

### Assessment

The data foundation is acceptable. The key issue is not the existence of the dataset, but how sample size changes when the Russian pipeline proxy is included.

---

## 2. Pipeline variable and sample restriction

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| `ru_velke_kapusany_kwh_d` is economically meaningful. | M3 report PCA loading interpretation and pipeline-flow explanation | Supported | It captures Russian pipeline supply risk into Europe. |
| The pipeline variable is sample-restrictive. | Data audit | Supported | Including pipeline gives 1,390 usable rows. Excluding it gives 1,749 usable rows. |
| The pipeline model should be treated as a restricted-sample model. | Data audit and Section 10 robustness logic | Strongly supported | This should be explicitly stated in the final wording. |
| The post-2025 zero-flow treatment is internally consistent. | Pipeline zero audit | Supported | Post-2025 zero rate is 99.73%; post-2026 zero rate is 100.0%. |
| The main risk is post-2025 zero coding. | Audit result | Not the main issue | The main issue is the long initial missing period before the pipeline series becomes available. |

### Key numbers

| Case | Features | Raw rows | Final rows | Rows lost |
|---|---:|---:|---:|---:|
| With pipeline | 20 | 1,934 | 1,390 | 544 |
| Without pipeline | 19 | 1,934 | 1,749 | 185 |

### Assessment

The pipeline variable is useful but costly. It should remain in the main model only if we disclose that it restricts the sample. The no-pipeline robustness check is necessary and appropriate.

---

## 3. Euro IP concern

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| Euro IP caused major sample loss. | Data audit | Not supported in M3 panel | `euro_ip_index` has only 1.65% missingness in the M3 dataset. |
| Euro IP can be included in the M3 feature set. | Data audit | Mostly supported | It is not the main missing-data problem in the team version. |
| Euro IP should still be treated carefully. | M2 concern and feature audit | Supported | We should avoid overemphasizing it if its source or construction differs from M2. |

### Assessment

Euro IP is no longer the main problem in the team M3 panel. The primary data limitation is the Russian pipeline variable.

---

## 4. PCA claim

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| PCA is justified because raw features are collinear. | M3 report VIF analysis and correlation discussion | Supported | Raw GPR and IP-related variables are highly collinear. |
| K = 5 components is reasonable. | Scree plot and cumulative variance | Supported | K = 5 captures 69.4% of total feature variance. |
| PCA solves multicollinearity for the regression design. | VIF on PCs | Supported | Principal components are orthogonal, so VIF is approximately 1. |
| PCA factors have economic interpretation. | Loading heatmap and component table | Supported, but interpret carefully | PC labels are plausible but should be tied to loadings, not over-narrated. |

### Assessment

The PCA section is well supported. The strongest defensible claim is that PCA provides a lower-dimensional, orthogonal factor representation of correlated macro, physical, and risk variables.

---

## 5. PCR in-sample model fit

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| PCR explains TTF-HH spread variation moderately well in-sample. | R² train = 0.5080 | Supported | Moderate in-sample fit. |
| PCR explains TTF-JKM spread variation less strongly but still meaningfully in-sample. | R² train = 0.3749 | Supported | Weaker but meaningful in-sample fit. |
| The model is strongly predictive. | OOS results | Not supported | OOS results are unstable, especially for TTF-JKM. |

### Assessment

In-sample structure is reasonably supported. We should not convert this into a broad forecasting claim.

---

## 6. Regression diagnostics

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| Heteroscedasticity is present. | Breusch-Pagan p ≈ 0 | Supported | HC3 standard errors are appropriate for heteroscedasticity. |
| HC3 solves all residual issues. | Durbin-Watson and ACF | Not supported | HC3 addresses heteroscedasticity, not serial correlation. |
| Residual autocorrelation remains material. | DW train: TTF-HH = 0.071, TTF-JKM = 0.254 | Strongly supported | This is a major limitation. |
| PCR should be interpreted as structural association rather than clean short-horizon prediction. | Low DW and unstable OOS | Strongly supported | This is the safest framing. |

### Assessment

The diagnostics are strong because they are transparent. The weakness is not hidden. The final report should explicitly state that serial correlation remains.

---

## 7. Chow structural break tests

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| Ukraine 2022 is a valid positive control. | Chow test detects breaks for both spreads | Supported | This validates that the break framework can detect a known shock. |
| TTF-JKM breaks in the 2026 Iran/Hormuz window. | Chow 2026: TTF-JKM BREAK | Supported | This is one of the central findings. |
| TTF-HH also breaks in the 2026 window. | Chow 2026: TTF-HH NO BREAK in full model | Not supported | TTF-HH appears more stable in the full model. |
| The Iran/Hormuz result is asymmetric. | TTF-HH no break, TTF-JKM break | Strongly supported | This should be the core structural finding. |

### Assessment

The Chow test supports the regime-dependence thesis more strongly for TTF-JKM than for TTF-HH.

---

## 8. Out-of-sample evidence

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| TTF-HH generalises somewhat to 2026. | OOS R² = 0.2876 | Partially supported | Positive OOS R², but DW remains low. |
| TTF-JKM generalises to 2026. | OOS R² = -2.3555 | Not supported | The model performs worse than naive mean prediction. |
| TTF-JKM structurally shifts in 2026. | Negative OOS R² + Chow break | Supported | This supports the regime-break narrative. |
| The model is a reliable OOS forecaster. | OOS results and DW | Not supported | Avoid this claim. |

### Assessment

OOS evidence is not a forecasting win. It is evidence that the 2026 TTF-JKM relationship is different from the 2019-2025 training structure.

---

## 9. No-pipeline robustness

| Claim | Evidence | Status | Comment |
|---|---|---|---|
| Pipeline inclusion restricts the training sample. | Section 10 and audit | Supported | Full model n = 1,222 train; no-pipeline n = 1,581 train. |
| No-pipeline model checks whether conclusions are driven by sample restriction. | Section 10 | Supported | This is the correct robustness check. |
| TTF-JKM regime-break evidence is not solely driven by pipeline. | No-pipeline robustness | Supported if Chow break remains | This is an important defensible claim. |
| OOS forecasting is robust. | OOS comparison | Not fully supported | OOS remains unstable. |

### Assessment

Section 10 is an important fix. It makes the pipeline issue defensible. The conclusion should say that in-sample structure and TTF-JKM break evidence are robust, not that forecasting performance is robust.

---

## 10. Final defensible conclusion

Recommended final conclusion:

> The PCA/PCR framework provides evidence that the gas spread relationships are regime-dependent, especially for TTF-JKM. The Ukraine break validates the structural-break framework, while the 2026 Iran/Hormuz window shows an asymmetric result: TTF-HH is relatively more stable, whereas TTF-JKM breaks and fails out-of-sample. The no-pipeline robustness check shows that the TTF-JKM regime-break evidence is not solely driven by the Russian pipeline proxy. However, OOS performance remains unstable and residual autocorrelation remains material, so the model should be interpreted as structural/regime evidence rather than a fully reliable short-horizon forecasting model.

---

## 11. Claims we should avoid

Avoid saying:

- The model has strong forecasting power.
- The model is robust in all respects.
- TTF-HH and TTF-JKM behave the same way.
- The Iran/Hormuz regime is fully confirmed as a closure event.
- HC3 fixes all diagnostic problems.
- Pipeline inclusion has no sample impact.

---

## 12. Suggested final wording for the team

> Section 10 addresses the pipeline sample-restriction concern well. The no-pipeline robustness check supports the view that the main in-sample PCA/PCR structure and the TTF-JKM regime-break evidence are not solely driven by the Russian pipeline proxy. However, we should limit the robustness claim: OOS forecasting performance remains unstable, and Durbin-Watson indicates material residual autocorrelation. Therefore, the safest conclusion is that the model provides evidence of regime-dependent structural association, not a fully reliable short-horizon forecasting model.

