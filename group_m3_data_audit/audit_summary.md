# Group M3 data audit summary

## Basic file summary
- file: C:\Users\kutsu\OneDrive\デスクトップ\KENGO\SMU\Class\QF632-G1-Financial Data Science\Project\Financial-Data\group_m3\data\master_panel_daily.csv
- n_rows: 1934
- n_cols: 32
- date_col: date
- date_min: 2019-01-02 00:00:00
- date_max: 2026-06-01 00:00:00

## Highest missingness columns
- ru_velke_kapusany_kwh_d: 28.13%
- carbon_grn_usd: 9.57%
- kr_ip_yoy: 1.65%
- euro_ip_index: 1.65%
- us_ip_index: 1.65%
- GPR: 1.45%
- GPRT: 1.45%
- GPRA: 1.45%
- GPRC_RUS: 1.45%
- epu_europe: 1.24%
- us_working_gas_bcf: 0.31%
- wind_northsea_kmh: 0.16%
- hdd_amsterdam: 0.16%
- hdd_chicago: 0.16%
- hdd_seoul: 0.16%
- henry_hub_spot_usd_mmbtu: 0.05%
- ttf_usd: 0.0%
- spread_ttf_hh: 0.0%
- spread_ttf_jkm: 0.0%
- spread_jkm_hh: 0.0%

## Notebook feature audit
- brent_usd_bbl: present, missing=0.0%, zero=0.0%, longest_NA_run=0, longest_zero_run=0
- usdcny: present, missing=0.0%, zero=0.0%, longest_NA_run=0, longest_zero_run=0
- eurusd: present, missing=0.0%, zero=0.0%, longest_NA_run=0, longest_zero_run=0
- carbon_grn_usd: present, missing=9.57%, zero=0.0%, longest_NA_run=185, longest_zero_run=0
- eu_storage_pct: present, missing=0.0%, zero=0.0%, longest_NA_run=0, longest_zero_run=0
- eu_lng_sendout_gwh: present, missing=0.0%, zero=0.0%, longest_NA_run=0, longest_zero_run=0
- ru_velke_kapusany_kwh_d: present, missing=28.13%, zero=19.13%, longest_NA_run=544, longest_zero_run=368
- wind_northsea_kmh: present, missing=0.16%, zero=0.0%, longest_NA_run=3, longest_zero_run=0
- hdd_amsterdam: present, missing=0.16%, zero=12.31%, longest_NA_run=3, longest_zero_run=14
- hdd_chicago: present, missing=0.16%, zero=31.54%, longest_NA_run=3, longest_zero_run=71
- hdd_seoul: present, missing=0.16%, zero=36.04%, longest_NA_run=3, longest_zero_run=97
- us_working_gas_bcf: present, missing=0.31%, zero=0.0%, longest_NA_run=6, longest_zero_run=0
- us_ip_index: present, missing=1.65%, zero=0.0%, longest_NA_run=32, longest_zero_run=0
- euro_ip_index: present, missing=1.65%, zero=0.0%, longest_NA_run=32, longest_zero_run=0
- kr_ip_yoy: present, missing=1.65%, zero=0.0%, longest_NA_run=32, longest_zero_run=0
- GPR: present, missing=1.45%, zero=0.0%, longest_NA_run=28, longest_zero_run=0
- GPRT: present, missing=1.45%, zero=0.0%, longest_NA_run=28, longest_zero_run=0
- GPRA: present, missing=1.45%, zero=0.0%, longest_NA_run=28, longest_zero_run=0
- epu_europe: present, missing=1.24%, zero=0.0%, longest_NA_run=24, longest_zero_run=0
- brent_usd_mmbtu: present, missing=0.0%, zero=0.0%, longest_NA_run=0, longest_zero_run=0

## Sample impact of notebook-style cleaning
- raw_feature_matrix: 1934 rows x 20 cols
- drop_rows_with_more_than_40pct_missing: 1910 rows x 20 cols
- after_ffill: 1910 rows x 20 cols
- after_final_dropna: 1390 rows x 20 cols

## Pipeline zero audit
- pre_2025: n=1565, missing=34.76%, zero=0.13%, min=0.0, max=1011142119.0
- post_2025: n=369, missing=0.0%, zero=99.73%, min=0.0, max=388500101.0
- post_2026: n=108, missing=0.0%, zero=100.0%, min=0.0, max=0.0

## Initial interpretation checklist
- Euro IP should not cause a large sample collapse. Check `euro_ip_index` missingness and longest NA run.
- Pipeline zeros should be distinguished from missing values. Check post-2025 zero percentage.
- If the final sample remains close to the raw sample, `dropna` is not too destructive.
- If the final sample falls sharply, the model may be driven by missing-data filtering.