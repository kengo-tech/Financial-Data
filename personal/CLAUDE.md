# QF632 Group Project — Claude 工作上下文

> 本文件是 Claude Code 在本仓库工作时的常驻提示。任何方法论或工程约定变更，请同步更新此文件。

## 1. 项目身份
- 课程：SMU QF632 Financial Data Science
- 团队：Group 4
- 题目原件：[references/QF632_Group_Project_Brief.pdf](references/QF632_Group_Project_Brief.pdf)
- 当前活跃文档：[ROADMAP.md](ROADMAP.md)（Milestone 2 计划）

## 2. 里程碑
| # | 截止 | 状态 | 产出 |
| --- | --- | --- | --- |
| M1 Feasibility Proposal | 2026-05-30 | ✅ 已交 | [references/QF632_Milestone1_Group4.docx](references/QF632_Milestone1_Group4.docx) |
| **M2 Preprocessing & EDA** | **2026-06-06** | ⏳ 进行中 | 见 ROADMAP.md |
| M3 Modeling & Diagnostics | 2026-06-13 | ⛔ 未开始 | regression/PCA 诊断 |
| Final Quant Pitch | 2026-06-16 | ⛔ 未开始 | 15-min 演示 + 5-min Q&A |

## 3. 研究论点（来自 M1，勿擅自修改）
- **正常态**：跨流域（TTF 欧洲、HH 美国、JKM 亚洲）LNG 套利使价差服从 Law of One Price。
- **异常**：地缘政治供给冲击（管道断供、海运 chokepoint）引入 *security-of-supply 风险溢价*，破坏套利纪律。
- **三个区间**：
  - 2020 COVID：非地缘 demand shock，**对照组**。
  - 2022 俄乌：管道供给冲击，**正控（confirmed positive control）**。
  - 2025–26 伊朗 / 霍尔木兹（候选 LNG+oil chokepoint，**待检验**），实为两段（日期已核实）：
    - `iran_war_2025` 2025-06-13~06-24（12 天战争，威胁未封锁，前导期）
    - `hormuz_2026` 2026-02-28~（实际封锁，主候选 regime；数据验证 03-02 TTF 单日 +39%，HH 不动）
- 方法学指示性而非锁定：在数据驱动下可调整。

## 4. 数据资产清单与 ingestion 状态（2026-06-06 重抓）

> 本机无队友 M1 源码；以 **M1 proof-of-ingestion 为目标 schema 从互联网复现**。
> 入口：`python -m src.ingest.run_all --start 2019-01-01 [--refresh]`。代码：`src/ingest/`。

| 类 | M1 列名 | 实际源（keyless?） | 状态 |
| --- | --- | --- | --- |
| Market | `hh_fut_usd_mmbtu,ttf_eur_mwh,jkm_usd_mmbtu,brent_usd_bbl,eurusd` | yfinance `NG=F/TTF=F/JKM=F/BZ=F/EURUSD=X`（✓keyless） | ✅ 2019→2026 精确 |
| Macro | `us_ip_index,euro_ip_index` | FRED fredgraph.csv（✓keyless） | ✅ US 精确；euro 序列略异 |
| Physical | `us_working_gas_bcf` | EIA dnav xls（✓keyless，无需 key） | ✅ 周度精确 |
| Physical | `de_storage_pct,de_gas_twh` | GIE AGSI+ API（key 已配） | ✅ 2019→2026 精确 |
| Physical | `es_lng_sendout_gwh,es_lng_inv_twh` | GIE ALSI API（key 已配；`inventory.lng` 嵌套字段） | ✅ 2019→2026 精确 |
| Physical | `hdd_amsterdam,hdd_chicago,hdd_beijing` | Open-Meteo ERA5（✓keyless） | ✅ 精确 |
| Physical | `ru_ua_transit_kwh_d` | ENTSOG transparency API | ⏸️ M3（point key 待定位） |
| Risk | `GPR,GPRT,GPRA,GPRC_RUS` | Iacoviello `data_gpr_export.xls`（✓keyless） | ✅ 精确含 GPRC_RUS |
| Risk | `epu_europe` | policyuncertainty.com xlsx（✓keyless） | ✅ 精确 |

样本期 2019-01-01 至今。**HDD base=18°C；HDD = max(0, 18 − Tmean)**。
- 关键修正 vs M1 Table 0：HH/TTF/JKM/Brent/FX 实为 **yfinance**（非 EIA API）；US 周库存走 **EIA dnav xls 可 keyless**（不必 EIA key）；GIE 储气/LNG 在 M1 proof 中是 **DE / ES** 单国，非 EU 聚合（队友 Telegram 那份 2022+ 是 EU 聚合，仅作交叉校验）。
- ENTSOG / GIE 之外**全部 keyless**；GIE 免费 key：https://agsi.gie.eu/account（即时）。

## 5. 工程约定（硬性）
1. **时区**：所有 timestamp 转 `UTC`，仅画图时换回当地 TZ。
2. **PIT 双列**：任何观测必须有 `event_date` 与 `available_at`；合并一律 `pd.merge_asof(direction='backward', on='available_at')`。**绝不 join on `event_date`**。
3. **发布时延**：在 `src/align/release_calendar.py` 维护单一真源；估计 lag 时**保守取上限**（如 INDPRO 取 T+20 而非真实 T+17）。
4. **数据流**：`data/raw/`（API dump，不修改）→ `data/interim/`（对齐未缩放）→ `data/processed/`（缩放、建模就绪）。
5. **缩放**：建模代码只能用滚动/扩展窗口 z-score（默认 252d，min_periods=126）。全样本 z-score 只允许出现在描述性 EDA 表。
6. **缺失值有出处**：每次填充返回值 + provenance flag（`stale` / `pit_ffill` / `event_zero`），不静默 reindex。
7. **regime 极值不动**：2020 COVID、2022 RU war、2025 Iran 区间的异常值**仅 flag 不 winsorize**——这些是研究对象本身。
8. **可重现**：`make ingest && make align && make clean && make eda` 在干净环境下能端到端跑通；API key 走 `.env`，绝不入库。

## 6. 关键 Don'ts
- ❌ 不要按 `event_date` join 月度宏观——直接 look-ahead leakage。
- ❌ 不要对 2022 TTF 价格峰值做 winsorize / clip——抹掉了正控信号。
- ❌ 不要在建模代码里用全样本 `mean()/std()` 做 normalization——隐式 leakage。
- ❌ 不要把 ENTSOG = 0 当缺失——它是真实管道关闭事件。
- ❌ 不要静默把不同市场的节假日 forward-fill 而不打 `stale=True`。
- ❌ 不要在没有 release-date 表的情况下合并新数据源。
- ❌ 不要随意覆盖 M1 的论点边界（如把 Iran regime 默认为 confirmed）。

## 7. 目录结构
```
QF632_project/
├── CLAUDE.md                # 本文件
├── ROADMAP.md               # M2 计划
├── references/              # 题目 PDF、M1 docx（只读）
├── data/
│   ├── raw/                 # API dump 缓存
│   ├── interim/             # PIT 对齐后未缩放
│   └── processed/           # 缩放、建模就绪 parquet
├── src/
│   ├── ingest/              # 各数据源拉取（M1 脚本迁移）
│   ├── align/               # master calendar / PIT / merge_asof
│   └── clean/               # missing / outlier / scale
├── notebooks/               # EDA & 探索
├── reports/                 # M2/M3 提交 docx + eda_summary.csv
└── figures/                 # 关键图 (PNG/SVG)
```

## 8. 待开展工作的优先级
按 ROADMAP.md 的 Phase 1 → 5 顺序推进。当前焦点：Phase 1 工程化与 ingestion 回放。

## 9. 沟通约定
- 截止时间是硬约束：M2 必须 2026-06-06 当日提交。任何风险（API 失败、对齐 bug）24h 内升级。
- 任何对设计决策的修改，先编辑 ROADMAP.md，再在本文件末尾追加一行 `## Changelog` 摘要。

---
## Changelog
- 2026-06-05  初始化 CLAUDE.md 与 ROADMAP.md；复制 M1 docx 与题目 PDF 到 `references/`；建立目录骨架。
- 2026-06-06  确认本机无队友 ingestion 源码；以 M1 proof 为 schema 从互联网重抓，建成 `src/ingest/` 包。8 frame 中 6 个 keyless 精确复现（2019→2026，逐行对上 M1）；ENTSOG 推迟 M3。yfinance 已验证可回溯 TTF/JKM 到 2019（战前基线恢复）。
- 2026-06-06  配置 GIE key；德国储气(AGSI+) + 西班牙 LNG(ALSI) 两表补齐，2019→2026 逐行对上 M1（75.23/189.1272；338.7/2259.35）。**现 8 frame 中 7 个精确复现**，仅 ENTSOG 待 M3。
- 2026-06-06  Phase 2 时序对齐完成：`src/align/`（release_calendar + master）。master 1870 交易日×22 列，全程 `merge_asof(backward, on=available_at)` + 频率级 tolerance（停更转 NaN）。`tests/test_alignment.py` 5/5 PASS（含 no-lookahead 证明）。产物 `data/interim/master_pit.parquet`。euro_ip 旧序列 2023 停更已由 tolerance 诚实置 NaN。
- 2026-06-06  Phase 3 清洗完成：`src/clean/`（regimes + scaling + build_clean）。派生 `ttf_usd_mmbtu` + 两 spread；price/fx ffill≤2d+stale flag；robust-MAD outlier 仅 flag（入侵窗口 sanity 通过，JKM 低流动性显著）；rolling-z(252/126) 因果缩放已验证无 leakage。产物 `data/interim/master_clean.parquet` + `data/processed/master_scaled.parquet` + `outliers.csv`。
- 2026-06-06  Iran/Hormuz 日期联网核实并改两窗口（iran_war_2025 / hormuz_2026），纠正了"June 2025 即封锁"的误判（实际封锁在 2026-02/03）。`src/clean/validate_regimes.py` 数据验证 break 落在 regime 边界（03-02 TTF +39%，HH 不动）→ `data/interim/regime_validation.txt`。
- 2026-06-06  Phase 4 EDA 完成：`src/eda/build_eda.py` → 5 图(`figures/`) + 2 表(`reports/eda_summary.csv`, `stationarity.csv`)。关键：spread_ttf_hh 非平稳(ADF p=0.15)→M3 需差分/regime 条件化；PCA top3=56%，PC1=地缘压力/储气因子。
- 2026-06-06  Phase 5 完成：`src/report/build_m2_docx.py`（python-docx，Node 不可用）→ `reports/QF632_Milestone2_Group4.docx`（5–6 页，5 图 + 13 表 + proof-of-ingestion 附录）。**M2 全流程完成，待用户目检提交**（本机无 Word/LibreOffice，仅结构校验）。
