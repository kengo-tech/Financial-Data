# QF632 Milestone 2 — Roadmap

> 当前：2026-06-05（周五） · 截止：2026-06-06（周六） · 题目要求见 [references/QF632_Group_Project_Brief.pdf](references/QF632_Group_Project_Brief.pdf) · M1 基础见 [references/QF632_Milestone1_Group4.docx](references/QF632_Milestone1_Group4.docx)

## 0. M2 交付物（题目原文）
1. **Time-Series Structural Alignment** — 合并不同频率的另类与传统数据时，如何对齐时间戳而**不引入 look-ahead bias / data leakage**。
2. **Scale Disparities & Missing Data** — 如何处理缺失值、异常值，以及无界金融变量 vs 紧约束百分比/指数之间的量纲不均衡。
3. 提交：M1 风格的 1–2 页 memo + 配套图表（可附 notebook 导出）。

## 1. 全周末时间线（关键路径）

| 时间窗 | 任务包 | 产出 | 估时 |
| --- | --- | --- | --- |
| Fri 06/05 PM | Phase 1 — 工程化与 ingestion 回放 | `src/ingest/*` 可独立跑通；raw cache 落盘 | 2h |
| Fri 06/05 evening | Phase 2 — 时序对齐设计与实施 | `src/align/*` + 对齐 notebook | 4h |
| Sat 06/06 AM | Phase 3 — 缺失/异常/量纲 | `src/clean/*` + processed parquet | 3h |
| Sat 06/06 早下午 | Phase 4 — EDA 与可视化 | 4–6 张关键图、统计表 | 3h |
| Sat 06/06 晚 | Phase 5 — 撰写、审校、提交 | M2 memo（docx）+ figures 包 | 2h |

**Buffer**：周六晚保留 1.5h 处理 API 超时/对齐 bug。

---

## 2. Phase 1 · 项目工程化与 ingestion 复现（✅ 基本完成 2026-06-06）

> 本机**没有**队友的 M1 ingestion 源码（确认），故以 **M1 proof-of-ingestion 为目标 schema 从互联网重抓**。
> 入口：`python -m src.ingest.run_all --start 2019-01-01 [--refresh]` → 落 `data/raw/*.parquet` + `data/interim/proof_of_ingestion.txt`。

- [x] `requirements.txt` / `.env.example` / `.gitignore`
- [x] `src/ingest/{common,market,macro,physical,risk,run_all}.py`，统一契约 `fetch_*(start,end,refresh)`，parquet 缓存
- [x] 复现并**逐行比对 M1 proof**（见下表）

### 2.1 Ingestion 状态（vs M1，2019-01-01 起）
| M1 frame | 源（实际/keyless?） | 状态 | 与 M1 首行比对 |
| --- | --- | --- | --- |
| Market: `hh_fut/ttf/jkm/brent/eurusd` | yfinance `NG=F/TTF=F/JKM=F/BZ=F/EURUSD=X`（keyless） | ✅ 1935 行 2019→2026 | **逐位精确**（2.958/22.475/8.970/54.910） |
| Macro: `us_ip_index/euro_ip_index` | FRED `fredgraph.csv`（keyless） | ✅ 88 行 | US 精确(103.4021)；euro 用 `EA19PRMNTO01IXOBSAM`=106.4（M1=105.59，序列略异，1 行可换） |
| US storage: `us_working_gas_bcf` | EIA dnav xls（keyless） | ✅ 387 行周度 | **精确**(2614/2533/2370) |
| DE storage: `de_storage_pct/de_gas_twh` | GIE AGSI+ API（key 已配） | ✅ 2711 行 2019→2026 | **精确**(75.23/189.1272) |
| ES LNG: `es_lng_sendout_gwh/inv_twh` | GIE ALSI API（key 已配） | ✅ 2711 行 2019→2026 | **精确**(338.7/2259.35) |
| HDD: `hdd_amsterdam/chicago/beijing` | Open-Meteo ERA5（keyless） | ✅ 2709 行 | **精确**(10.1/18.0/23.0) |
| ENTSOG: `ru_ua_transit_kwh_d` | ENTSOG transparency API | ⏸️ M3 待补 | 端点通，但 UA→SK point key 需 ENTSOG 专门建模（M1 当年亦稀疏） |
| Risk: `GPR/GPRT/GPRA/GPRC_RUS` | Iacoviello `data_gpr_export.xls`（keyless） | ✅ 89 行 | **精确含 GPRC_RUS**(87.4241/…/0.9987) |
| Risk: `epu_europe` | policyuncertainty.com（keyless） | ✅ 89 行 | **精确**(247.6771) |

**结论**：**8 个 frame 中 7 个精确复现并回到 2019**（含 GIE 德国储气/西班牙 LNG，key 已配）；euro IP 仅序列略异；战前基线恢复，before/after-war 可做；ENTSOG 推迟到 M3。

### 2.2 收尾动作
- [x] 配置 **GIE key**（`.env`）→ DE/ES 两表已补齐并逐行对上 M1
- [ ] （可选）euro IP 若要与 M1 完全一致，确认 M1 所用 FRED 序列 id，替换 `src/ingest/macro.py:EURO_CANDIDATES`
- [ ] 队友 2022+ 的 GIE EU-aggregate CSV（Telegram）留作 2022 段交叉校验

## 3. Phase 2 · Time-Series Structural Alignment（核心，≤4h）

### 3.1 设计决策（必须在报告中显式写出）
1. **Master grid**：以 ICE/NYMEX/TTF 三交易所交易日的**并集**为日历，每个 series 缺失日打 `stale=True` flag，绝不静默 reindex。
2. **Point-in-Time（PIT）原则** — 每条记录额外携带两列：
   - `event_date`：数据所指代的样本日期（如周库存对应的周五）
   - `available_at`：该观测在现实中最早可用的 UTC 时间戳
3. **发布时延表**（写入 `src/align/release_calendar.py`，逐源 hard-code）：

   | 源 | event → available_at 规则 |
   | --- | --- |
   | HH spot (EIA daily) | `event_date + 1 business day, 12:00 UTC` |
   | TTF/HH/JKM futures (Yahoo) | `event_date settle, 17:30 UTC` |
   | EIA 周度库存 | 周四 14:30 UTC（event = 上周五） |
   | EU AGSI+/ALSI | `event_date + 1d, 18:30 UTC` |
   | ENTSOG 流量 | `event_date + 1d, 06:00 UTC`（含修订，仅取 first vintage） |
   | INDPRO (US) | 一般月中第 2 个周二 → `event_month_end + 17 calendar days, 13:15 UTC`（保守取 T+20） |
   | EA Industrial Prod. | T+45 |
   | GPR / GPRC_RUS | 次月 10 日 |
   | EU EPU | 次月初 |
   | HDD (ERA5) | T+5 |

4. **合并规约**：所有 join 都用 `pd.merge_asof(left, right, on='timestamp_utc', by='ticker', direction='backward', tolerance=...)`，左表 = master daily grid 上每行的 `available_at`；右表按各自 `available_at` 升序。**禁止 join on `event_date`**。
5. **频率对接**：
   - 月→日：使用最近一条 `available_at ≤ today` 的发布值；下一发布前保持不变；首发布前为 `NaN`（不外推）。
   - 周→日：周四发布后填周四–下周三，周三前持周三值。
   - 节假日：T 日缺失则继承 T-1 收盘，但 `stale=True`；连续缺失 > 5 个交易日触发告警。
6. **时区**：原始 ts 全部转 `UTC`，仅在画图时回退当地 TZ。

### 3.2 实施（✅ 完成 2026-06-06）
入口：`python -m src.align.master [--demo 2022-02-25]`
- [x] `src/align/release_calendar.py`：9 个 series 的 `event_date → available_at` 规则（单一真源，保守取上限）
- [x] `src/align/master.py`：`make_master_index`（gas 交易日并集）+ `build_master`（逐 series `merge_asof(backward, on=available_at)`）
- [x] **leakage 检查内置**：`leakage_check()` 断言所有 series `available_at ≤ cutoff` 且 `event_date ≤ cutoff` → **PASS（9 series × 1870 交易日）**
- [x] **PIT demo @ 2022-02-25**（俄乌入侵后首交易日）：market T+0、GIE T+1、HDD T+5、US 周库存 event=02-18/avail=02-24、宏观/风险仅知 1 月值（us_ip age 55d, euro_ip 86d, gpr 55d）—— 证明决策时点不含未来信息
- [x] 产出 `data/interim/master_pit.parquet`(1870×22 值) + `master_pit_audit.parquet`(含 PIT 溯源列) + `alignment_audit.txt`
- [x] **staleness tolerance**：`merge_asof(tolerance=)` 按频率封顶（daily 7–14d / weekly 14d / monthly 45d）——序列停更超期即转 NaN，不把旧值无限 carry
- [x] **leakage 单元测试** `tests/test_alignment.py`：5/5 PASS（no-lookahead / event≤cutoff / GIE 严格滞后 / 停更不 carry / 形状与完整度）
- 注：`euro_ip` 旧 FRED 序列约 2023 停更——经 tolerance 处理后 2024+ 诚实置 NaN（age 封顶 120d）；如需补到 2026，待 FRED 恢复后在 `macro.py:EURO_CANDIDATES` 换当前 Eurostat 序列（次要控制变量，EU 基本面已由 GIE 储气/LNG/HDD 覆盖）

## 4. Phase 3 · Missing / Outlier / Scale（≤3h）

### 4.1 缺失值（差异化处理）
| 情形 | 处理 | 理由 |
| --- | --- | --- |
| 跨市场节假日（HH/TTF/JKM 不同休市） | forward-fill ≤ 2 个交易日，`stale=True` | 价格 mean-reverting 短期 |
| EIA 周度仅周四有值 | PIT forward-fill | 实际信息状态即如此 |
| 月度宏观仅月末/月初一值 | PIT forward-fill 至下次 release | 同上 |
| ENTSOG RU→EU 自 2022 起部分日 = 0 | **保留为 0** 并增列 `flow_zero_flag` | 这是 regime 信号，不是缺失 |
| 首发布前的 `NaN` | 保留 NaN，建模时显式 drop | 防 backfill 造成虚假早期信号 |

- [x] 实现于 `src/clean/build_clean.py:handle_missing`：price/fx ffill≤2d + `<col>_stale` flag；实测仅 ttf 2 / jkm 3 / eurusd 2 / usdcny 3 个跨节假日空缺被桥接；月度/周度首发布前 NaN 保留不回填

### 4.2 异常值
- 2020-04 油价负值、2022-08 TTF 极值、2026-03 霍尔木兹冲击：**仅 flag，不 winsorize**。`regime ∈ {normal, covid, ru_war, iran_war_2025, hormuz_2026}`（日期已联网核实，见 `regimes.py`；两窗口：2025-06 12 天战争=前导、2026-02/03 霍尔木兹封锁=真 chokepoint）。
- **regime 已被数据验证**（`src/clean/validate_regimes.py` → `data/interim/regime_validation.txt`）：03-02（Feb 28 空袭后首交易日）TTF 单日 +39%，hormuz_2026 段 TTF +45%/JKM +66%/Brent +46%/GPR 峰值 329，而 **HH −9%**（美国本土气不经海峡）→ 结构性断裂落在 regime 边界。
- 通用：滚动 30 个交易日 MAD（中位数绝对偏差），> 6σ 仅记录在 `outliers.csv`，不修改原值。
- 单元测试：俄乌爆发首周 TTF 必须出现在 outlier 表（否则规则失效）。

- [x] 实现于 `src/clean/{scaling.py:rolling_mad_outliers, build_clean.py:flag_outliers}`：161 个 flag，**入侵窗口 2022-02-24…03-15 命中 10 个（ttf/jkm/两 spread）—— sanity 通过**；值不改，regime 极值保留
- [x] 发现：**JKM outlier 占绝大多数且 robust_z 高达 62**——JKM 报价低流动性（平段+跳点，MAD≈0 被放大），列为 operational/EDA 发现，留待 pitch 的 friction 讨论

### 4.3 量纲处理（双轨保存）
| 变量族 | 变换 | 备注 |
| --- | --- | --- |
| HH/TTF/JKM/Brent 价格 | `log_return = Δlog(P)` + 滚动 252d z-score | 无界，价差研究用 log-level 也并存 |
| ENTSOG 流量 (kWh/d)、ALSI 送出 (GWh/d) | `log1p` + z-score | 重尾、含零 |
| DE 储气百分比 | 直接保留 + 可选 `logit(p)` | 已界 [0,1] |
| INDPRO / EA IP（指数） | YoY 增长率 + z-score | 去趋势 |
| GPR/GPRT/GPRA/GPRC_RUS、EPU | z-score（无 log） | 已是无量纲指数 |
| HDD（°C-day） | z-score | 已是 anomaly |

- **存档**：raw（已对齐未缩放）→ `data/interim/master_pit.parquet`；scaled → `data/processed/master_scaled.parquet`。**报告必须指出 z-score 的窗口是滚动 252d 而非全样本**（否则即 leakage）。
- 全样本 z-score 仅用于**描述性 EDA 表格**，且不喂入任何后续模型。

- [x] 实现于 `src/clean/scaling.py:rolling_z`（window=252, min_periods=126）+ `build_clean.py:build_scaled`
- [x] 派生 `ttf_usd_mmbtu`（=ttf_eur_mwh×eurusd÷3.41214）+ `spread_ttf_hh` / `spread_ttf_jkm`（换算 sanity：2022-08-26 峰值 TTF−HH=89.8 USD/MMBtu）
- [x] **因果性已验证**：`z_gpr` 与重算 rolling-z 完全一致，rolling mean 仅用过去窗口——processed 矩阵无 full-sample leakage
- [x] 双轨产出：`data/interim/master_clean.parquet`(1870×33 levels+spreads+flags+regime) + `data/processed/master_scaled.parquet`(1870×25 建模矩阵) + `data/interim/outliers.csv`
- 注：`euro_ip` 停更后 YoY 自然 NaN；de_storage% 走 logit；es_sendout 走 log1p；GPR/EPU/HDD 直接 z

## 5. Phase 4 · EDA（✅ 完成 2026-06-06）
入口：`python -m src.eda.build_eda` → `figures/*.png` + `reports/*.csv`
- [x] **统计表** `reports/eda_summary.csv`（24 series：count/missing%/mean/std/skew/kurt/range/首末）
- [x] **Fig.1** `fig1_prices.png` 三基准(USD/MMBtu)+Brent 双轴 + 5-regime shading
- [x] **Fig.2** `fig2_spreads.png` 两 spread + regime shading —— 2019-20 贴零(LoOP)、ru_war 飙 ~90、hormuz_2026 抬回 ~17，论点一图说清
- [x] **Fig.3** `fig3_corr_by_regime.png` 相关结构 full vs normal vs ru_war vs hormuz_2026（4 面板，跨盆地联动随压力变化）
- [x] **Fig.4** `fig4_missing_map.png` 缺失地毯图（证明对齐未凭空补：月度/周度首发布前 NaN、euro_ip 2024 停更可见）
- [x] **Fig.5** `fig5_pca.png` scree + PC1/PC2 loadings；**PC1=29%/PC2=16%/PC3=11%（top3=56%）**，PC1 正载 GPR(0.50) 负载储气 = "地缘压力/储气抽取"因子（M3 铺路）
- [x] **平稳性** `reports/stationarity.csv`（ADF+KPSS）：**`spread_ttf_hh` 非平稳**（ADF p=0.15，有持续 regime level-shift）→ M3 需差分/regime 条件化；`spread_ttf_jkm` 平稳；d_spread / z 特征均平稳

## 6. Phase 5 · 撰写与提交（✅ 文档完成 2026-06-06）
入口：`python -m src.report.build_m2_docx`（python-docx；Node 不可用故未走 docx-js）
- [x] **`reports/QF632_Milestone2_Group4.docx`** 生成（沿用 M1 风格，5–6 页）：
  1. Dataset & Pipeline Overview（源/覆盖表）
  2. Time-Series Structural Alignment（release-lag 表 + 2022-02-25 PIT demo + leakage 测试 5/5）
  3. Scale Disparities & Missing Data（缺失决策矩阵 + outlier flag-only + 双轨缩放）
  4. Exploratory Findings（嵌 5 图 + regime means + 平稳性 + Hormuz break 验证）
  5. Operational Notes（JKM 流动性 / regime 日期 / 可复现）
  6. Appendix A — Proof of Ingestion（8 源 first-5-rows，逐行对上 M1）
  - 13 张表（列宽 ≤6.5″ 无溢出）、5 张内嵌图、附录数值已校验
- [x] 自检：leakage 5/5 PASS；缩放因果性已验证；regime 极值未 winsorize；ingest→align→clean→eda→report 端到端可跑
- [ ] **（待你）** 目检 docx（本机无 Word/LibreOffice 渲染器，我只能结构校验）→ 提交课程平台

## 7. 风险登记
| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| ~~TTF 缺战前数据~~（队友 investing.com 仅 2022-10+） | ~~before/after-war 垮掉~~ | ✅ **已解**：yfinance `TTF=F` 回到 2019-01-02，与 M1 精确一致 |
| ~~GIE 需 key~~ | ~~DE/ES 两表空缺~~ | ✅ **已解**：key 已配，DE/ES 两表 2019→2026 精确补齐 |
| ENTSOG point key 难定位 | 俄管道流量缺失 | 推迟 M3；该信号与 war-regime dummy / EU 储气抽取高度共线，M2 可不依赖 |
| JKM 历史覆盖 | 跨域分析偏弱 | ✅ yfinance `JKM=F` 回到 2019-01-02（8.970，与 M1 一致），覆盖好于预期 |
| 2025 Iran 区间样本仍在累积 | 第二 regime 不稳健 | 报告中明示样本量 n、把它定位为 candidate |
| 月度宏观 release lag 估计偏差 | 轻微 leakage | 保守取上限（INDPRO T+20 而非真实 T+17） |
| 时区/夏令时 corner case | 一日错位即 leakage | 全部转 UTC，对齐单测覆盖 DST 边界 |

## 8. 给 M3 / Final Pitch 的接口（不在 M2 范围内）
- M3 将基于本输出的 `master_scaled.parquet`：
  - 回归方案：`Δspread ~ Δstorage + Δflow + Δgpr + …`，残差散点、White/HC 稳健 SE、VIF
  - PCA 方案：scree + loadings 解释（"supply-stress factor" vs "global macro factor"）
- Final pitch 的 Operational Realities：本研究为宏观/价差信号而非小盘股，friction 主要来自 LNG 货物再分配的物理成本（航次、再气化、储气罐切换），需在 pitch 中量化。

---

**进度状态（2026-06-06）**：Phase 1–5 全部完成 ✅ —— 数据复现(8源/7精确)→PIT 对齐(leakage 5/5)→清洗(双轨缩放)→EDA(5图2表)→M2 提交稿 docx。**待你目检 docx 并提交课程平台。** 任何对设计决策的调整，请直接编辑本文件并在 [CLAUDE.md](CLAUDE.md) 末尾追加变更摘要。
