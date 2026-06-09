"""
Build the Milestone 2 submission document (reports/QF632_Milestone2_Group4.docx).

Professional typography: booktabs-style tables (horizontal rules only, no vertical
lines, right-aligned + decimal-consistent numerics), a ruled masthead, page-number
footer, justified body with run-in bold sub-heads, and sequentially numbered figures.
Tables/figures are computed from the actual parquet artifacts (no transcription).

Run:  python -m src.report.build_m2_docx
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from src.ingest.common import RAW_DIR, INTERIM_DIR, PROJECT_ROOT  # noqa: E402
from src.align.release_calendar import SERIES  # noqa: E402
from src.align.master import TOLERANCE_BY_FREQ  # noqa: E402
from src.clean import regimes  # noqa: E402

FIG = PROJECT_ROOT / "figures"
REPORTS = PROJECT_ROOT / "reports"
ACCENT = RGBColor(0x1F, 0x49, 0x7D)      # deep navy
ACCENT_HEX = "1F497D"
GREY = RGBColor(0x6A, 0x6A, 0x6A)
RULE = "9DB3CC"                           # light accent for hairlines
CONTENT_IN = 6.5                          # Letter, 1-inch margins

# ----------------------------------------------------------------------------- #
# low-level XML helpers
# ----------------------------------------------------------------------------- #
def _border_el(edge, sz, color):
    el = OxmlElement(f"w:{edge}")
    if sz is None:
        el.set(qn("w:val"), "nil")
    else:
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
    return el


def _cell_borders(cell, top=None, bottom=None, color=ACCENT_HEX):
    tcPr = cell._tc.get_or_add_tcPr()
    old = tcPr.find(qn("w:tcBorders"))
    if old is not None:
        tcPr.remove(old)
    b = OxmlElement("w:tcBorders")
    b.append(_border_el("top", top, color))
    b.append(_border_el("bottom", bottom, color))
    b.append(_border_el("left", None, color))
    b.append(_border_el("right", None, color))
    tcPr.append(b)


def _row_no_split(row, header=False):
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))
    if header:
        trPr.append(OxmlElement("w:tblHeader"))


def _table_cell_margins(table, top=46, bottom=46, left=110, right=110):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:w"), str(val))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblPr.append(mar)


def _para_border(p, edge="bottom", sz=12, color=ACCENT_HEX, space=2):
    pPr = p._p.get_or_add_pPr()
    pbdr = pPr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        pPr.append(pbdr)
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    pbdr.append(el)


def _page_field(p):
    run = p.add_run()
    for t, kind in [("begin", "w:fldChar"), (" PAGE ", "w:instrText"), ("end", "w:fldChar")]:
        el = OxmlElement(kind)
        if kind == "w:fldChar":
            el.set(qn("w:fldCharType"), t)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = t
        run._r.append(el)
    run.font.size = Pt(8)
    run.font.color.rgb = GREY


# ----------------------------------------------------------------------------- #
# numeric formatting
# ----------------------------------------------------------------------------- #
def _is_num(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str):
        try:
            float(v)
            return True
        except ValueError:
            return False
    return False


def _col_decimals(values):
    dp = 0
    for v in values:
        if v is None or v == "" or not _is_num(v):
            continue
        x = round(float(v), 4)
        for d in range(0, 5):
            if round(x, d) == x:
                dp = max(dp, d)
                break
    return dp


def _fmt(v, dp):
    if v is None or v == "":
        return ""
    if _is_num(v):
        return f"{float(v):.{dp}f}"
    return str(v)


# ----------------------------------------------------------------------------- #
# content helpers
# ----------------------------------------------------------------------------- #
def add_table(doc, headers, rows, widths=None, font_pt=9):
    n = len(headers)
    # detect numeric columns + per-column decimals
    numeric, decimals = [], {}
    for j in range(n):
        col = [r[j] for r in rows]
        is_num = len(col) > 0 and all((c is None or c == "" or _is_num(c)) for c in col) \
            and any(_is_num(c) for c in col)
        numeric.append(is_num)
        if is_num:
            decimals[j] = _col_decimals(col)

    t = doc.add_table(rows=1, cols=n)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _table_cell_margins(t)

    # header
    hdr = t.rows[0]
    for j, htext in enumerate(headers):
        cell = hdr.cells[j]
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT if numeric[j] else WD_ALIGN_PARAGRAPH.LEFT
        run = para.add_run(str(htext))
        run.bold = True
        run.font.size = Pt(font_pt)
        run.font.color.rgb = ACCENT
        _cell_borders(cell, top=12, bottom=8)
    _row_no_split(hdr, header=True)

    # body
    for ri, r in enumerate(rows):
        cells = t.add_row().cells
        last = ri == len(rows) - 1
        for j, v in enumerate(r):
            cell = cells[j]
            cell.text = ""
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT if numeric[j] else WD_ALIGN_PARAGRAPH.LEFT
            txt = _fmt(v, decimals[j]) if numeric[j] else ("" if v is None else str(v))
            run = para.add_run(txt)
            run.font.size = Pt(font_pt)
            _cell_borders(cell, top=None, bottom=(12 if last else None))
        _row_no_split(t.rows[-1])

    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Inches(w)
    # keep the whole (small) table together — no mid-table page break / orphan header
    for row in t.rows[:-1]:
        for cell in row.cells:
            for para in cell.paragraphs:
                para.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def add_fig(doc, path, number, caption, width=6.4):
    if not Path(path).exists():
        doc.add_paragraph(f"[missing figure: {path}]")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(4)
    p.add_run().add_picture(str(path), width=Inches(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(10)
    r = c.add_run(f"Figure {number}.  ")
    r.bold = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = ACCENT
    r2 = c.add_run(caption)
    r2.italic = True
    r2.font.size = Pt(8.5)
    r2.font.color.rgb = GREY


def body(doc, text, justify=True, space=6):
    p = doc.add_paragraph()
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(space)
    p.add_run(text).font.size = Pt(10)
    return p


def lead(doc, lead_phrase, rest, space=6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(space)
    r = p.add_run(lead_phrase + " ")
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = ACCENT
    p.add_run(rest).font.size = Pt(10)
    return p


def note(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(text)
    r.font.size = Pt(8.5)
    r.italic = True
    r.font.color.rgb = GREY
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(text).font.size = Pt(10)
    return p


def h(doc, text):
    return doc.add_heading(text, level=1)


# ----------------------------------------------------------------------------- #
# data pulls
# ----------------------------------------------------------------------------- #
def pit_demo_row(date="2022-02-25"):
    aud = pd.read_parquet(INTERIM_DIR / "master_pit_audit.parquet")
    aud["date"] = pd.to_datetime(aud["date"])
    row = aud.loc[aud["date"] == pd.Timestamp(date)].iloc[0]
    out = []
    for spec in SERIES:
        k = spec["key"]
        ev, av = row.get(f"{k}__event_date"), row.get(f"{k}__available_at")
        if pd.isna(ev):
            continue
        out.append([k, spec["freq"], str(pd.Timestamp(ev).date()),
                    str(pd.Timestamp(av).date()), (row["date"] - ev).days])
    return out


def regime_means():
    cl = pd.read_parquet(INTERIM_DIR / "master_clean.parquet")
    vars_ = ["spread_ttf_hh", "spread_ttf_jkm", "ttf_usd_mmbtu",
             "hh_fut_usd_mmbtu", "GPR", "GPRC_RUS"]
    disp = ["TTF–HH", "TTF–JKM", "TTF", "HH", "GPR", "GPRC_RUS"]
    g = cl.groupby("regime")[vars_].mean().reindex(regimes.ORDER).round(2)
    rows = [[r] + [g.loc[r, c] for c in vars_] for r in g.index]
    return ["regime"] + disp, rows


# ----------------------------------------------------------------------------- #
def main():
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.space_after = Pt(6)
    h1 = doc.styles["Heading 1"]
    h1.font.name = "Calibri"
    h1.font.size = Pt(14)
    h1.font.bold = True
    h1.font.color.rgb = ACCENT
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    h1.paragraph_format.keep_with_next = True

    # footer with page number
    footer = doc.sections[0].footer
    fp = footer.paragraphs[0]
    fp.text = ""
    fp.paragraph_format.tab_stops.add_tab_stop(Inches(CONTENT_IN), WD_TAB_ALIGNMENT.RIGHT)
    _para_border(fp, edge="top", sz=4, color="CCCCCC", space=4)
    r = fp.add_run("QF632 Milestone 2  ·  Group 4")
    r.font.size = Pt(8); r.font.color.rgb = GREY
    fp.add_run("\tPage ").font.size = Pt(8)
    _page_field(fp)

    # ---- masthead ----
    t1 = doc.add_paragraph()
    t1.paragraph_format.space_after = Pt(2)
    r = t1.add_run("QF632 Financial Data Science — Group Project")
    r.bold = True; r.font.size = Pt(15); r.font.color.rgb = ACCENT
    t2 = doc.add_paragraph()
    t2.paragraph_format.space_after = Pt(2)
    r = t2.add_run("Milestone 2  ·  Preprocessing & Exploratory Data Analysis")
    r.bold = True; r.font.size = Pt(12)
    t3 = doc.add_paragraph()
    t3.paragraph_format.space_after = Pt(2)
    r = t3.add_run("Group 4      ·      6 June 2026")
    r.font.size = Pt(9.5); r.italic = True; r.font.color.rgb = GREY
    rule = doc.add_paragraph()
    rule.paragraph_format.space_after = Pt(10)
    _para_border(rule, edge="bottom", sz=12, color=ACCENT_HEX, space=1)

    # ---- 1. Overview ----
    h(doc, "1. Dataset & Pipeline Overview")
    body(doc, "We test whether the pricing linkage between European (TTF), U.S. (Henry Hub) and "
              "Asian (JKM) natural-gas benchmarks — normally disciplined by LNG arbitrage (Law of "
              "One Price) — becomes regime-dependent under geopolitical supply stress. This "
              "milestone documents the data engineering behind that test: a reproducible ingestion "
              "layer, a point-in-time (PIT) alignment that prevents look-ahead bias, and the "
              "missing-data and scaling decisions that make the mosaic model-ready.")
    body(doc, "All series were re-acquired from public sources over 2019-01-02 → 2026-06-05 and "
              "reconciled row-for-row against the Milestone 1 proof of ingestion (Appendix A). The "
              "aligned master spans 1,870 gas trading days.")
    add_table(doc,
              ["Source family", "Series (M1 columns)", "Freq.", "Access", "Coverage"],
              [["Market (Yahoo / yfinance)", "HH, TTF, JKM, Brent, EUR/USD", "daily", "keyless",
                "2019–2026 · exact"],
               ["Macro (FRED)", "US INDPRO; Euro IP", "monthly", "keyless", "US→2026; euro→2024*"],
               ["US storage (EIA)", "Lower-48 working gas", "weekly", "keyless", "2019–2026"],
               ["EU storage (GIE AGSI+)", "DE % full; TWh", "daily", "x-key", "2019–2026 · exact"],
               ["EU LNG (GIE ALSI)", "ES send-out; inventory", "daily", "x-key", "2019–2026 · exact"],
               ["Weather (Open-Meteo ERA5)", "HDD AMS / CHI / BEI", "daily", "keyless", "2019–2026"],
               ["Risk (Caldara–Iacoviello)", "GPR / GPRT / GPRA / GPRC_RUS", "monthly", "keyless",
                "2019–2026 · exact"],
               ["Risk (policyuncertainty)", "EU EPU", "monthly", "keyless", "2019–2026"]],
              widths=[1.55, 1.95, 0.6, 0.9, 1.5], font_pt=8.5)
    note(doc, "*Euro IP (OECD MEI series) was discontinued in 2024; it is retained but reverts to "
              "NaN thereafter (staleness rule, §2). Russian→EU pipeline flow (ENTSOG) is deferred "
              "to Milestone 3 (point-key resolution pending) — it is highly collinear with the "
              "war-regime indicator and the EU-storage drawdown, so M2 does not depend on it.")

    # ---- 2. Alignment ----
    h(doc, "2. Time-Series Structural Alignment")
    lead(doc, "Master calendar.", "The decision grid is the union of gas trading days. Every "
              "observation carries two dates: event_date (the period it describes) and available_at "
              "(when it was first publishable in reality). All joins use "
              "pandas.merge_asof(direction='backward') keyed on available_at — never on event_date "
              "— so a value enters the grid only once a market participant could actually have "
              "known it.")
    lead(doc, "Publication lags.", "Each series carries a conservative (upper-bound) release rule "
              "and a frequency-based staleness tolerance, beyond which a discontinued series reverts "
              "to NaN rather than being carried forward indefinitely:")
    add_table(doc, ["Series", "Freq.", "available_at rule", "Stale tol."],
              [[s["key"], s["freq"], s["lag_note"], f"{TOLERANCE_BY_FREQ.get(s['freq'], 14)} d"]
               for s in SERIES],
              widths=[1.0, 1.15, 3.55, 0.8], font_pt=8.5)
    lead(doc, "Leakage proof.", "A point-in-time snapshot on 2022-02-25 (first trading day after "
              "the Russian invasion) makes the lag structure explicit — on that day the model knew "
              "only January macro/risk values, not February's:")
    add_table(doc, ["Series", "Freq.", "event_date", "available_at", "age (d)"],
              pit_demo_row("2022-02-25"), widths=[1.15, 1.25, 1.15, 1.15, 0.8], font_pt=8.5)
    body(doc, "A unit-test suite (tests/test_alignment.py) asserts available_at ≤ cutoff and "
              "event_date ≤ cutoff for all nine series across all 1,870 days, that T+1 fundamentals "
              "are never used same-day, and that no series is stale-forwarded beyond tolerance — "
              "all five tests pass.")

    # ---- 3. Missing / scale ----
    h(doc, "3. Scale Disparities & Missing Data")
    lead(doc, "Missing data.", "Values are handled by mechanism, with provenance flags — never "
              "silently imputed:")
    add_table(doc, ["Situation", "Treatment", "Rationale"],
              [["Cross-market holidays (price/FX)", "forward-fill ≤ 2 trading days, flag stale",
                "short-horizon mean-reverting; 2–3 cells/series"],
               ["Monthly/weekly before first release", "leave NaN (no backfill)",
                "back-filling would fabricate early signal"],
               ["Discontinued series (euro IP)", "NaN past tolerance window",
                "avoid propagating a years-old value"],
               ["ENTSOG flow = 0 (when added)", "keep 0, flag zero",
                "0 is a real pipeline shut-in, not missing"]],
              widths=[2.05, 2.25, 2.2], font_pt=8.5)
    lead(doc, "Outliers.", "Extremes are flagged, never winsorized — the 2020/2022/2026 regime "
              "extremes ARE the object of study. A rolling 30-day robust-MAD screen (k=6) writes 161 "
              "flags to outliers.csv; as a sanity check the invasion window (2022-02-24…03-15) "
              "surfaces TTF, JKM and both spreads. The screen also exposes JKM's low-liquidity "
              "quoting (flat runs punctuated by jumps), an operational caveat carried into the pitch.")
    lead(doc, "Scaling.", "Dual-track and strictly causal. Levels (with spreads) live in "
              "master_clean.parquet; the modelling matrix master_scaled.parquet uses log-returns "
              "and a rolling 252-day z-score (min 126) — never full-sample statistics, which would "
              "leak the future. Bounded storage % uses a logit; LNG send-out uses log1p; index "
              "levels use YoY. TTF is converted to USD/MMBtu (× EUR/USD ÷ 3.41214) so the spreads "
              "are unit-consistent.")

    # ---- 4. EDA ----
    h(doc, "4. Exploratory Findings")
    body(doc, "The cross-basin spreads collapse to near-zero in calm periods (Law of One Price) and "
              "blow out under supply stress: TTF–HH peaks near 90 USD/MMBtu during the 2022 energy "
              "crisis and re-widens during the 2026 Hormuz closure, while U.S. Henry Hub barely "
              "moves — it is insulated from the chokepoint.")
    add_fig(doc, FIG / "fig2_spreads.png", 1,
            "Cross-basin spreads (USD/MMBtu) with regime shading. Near-zero under Law-of-One-Price; "
            "TTF–HH blows out to ~90 in the 2022 war and re-widens in the 2026 Hormuz closure.", 6.4)
    add_fig(doc, FIG / "fig1_prices.png", 2,
            "Benchmarks in common units, Brent on the right axis. Henry Hub stays low and stable "
            "while TTF and JKM spike together under stress.", 6.4)
    body(doc, "Regime means confirm the structure: the European supply premium and Russia-specific "
              "geopolitical risk peak in the 2022 war, while the 2026 Hormuz closure lifts TTF, JKM "
              "and Brent together as Henry Hub stays flat.")
    hdr, rows = regime_means()
    add_table(doc, hdr, rows, widths=[1.15, 0.95, 0.95, 0.8, 0.7, 0.8, 1.15], font_pt=9)
    add_fig(doc, FIG / "fig3_corr_by_regime.png", 3,
            "Correlation structure by regime (|r| ≥ 0.3 annotated). Cross-basin co-movement "
            "reorganises as supply stress sets in.", 6.5)
    add_fig(doc, FIG / "fig4_missing_map.png", 4,
            "Missingness of the PIT-aligned master (black = NaN): pre-first-release gaps and the "
            "euro-IP discontinuation — no fabricated fills.", 6.3)
    add_fig(doc, FIG / "fig5_pca.png", 5,
            "PCA preview (M3). PC1 (~29%) contrasts geopolitical risk with storage; the first three "
            "components explain ≈ 56% of variance.", 6.4)
    body(doc, "Stationarity (ADF + KPSS, reports/stationarity.csv): spread_ttf_hh is non-stationary "
              "in levels (persistent regime level-shifts), so Milestone 3 will difference it or "
              "condition on regime; spread_ttf_jkm and all z-scored daily features are stationary. "
              "Regime validation (validate_regimes.py): the structural break lands exactly on "
              "2026-03-02 (TTF +39% in one day, Henry Hub −9%), confirming the Hormuz boundary "
              "data-drivenly.")

    # ---- 5. Operational notes ----
    h(doc, "5. Operational Notes (pitch readiness)")
    bullet(doc, "JKM is thinly traded — stale quotes punctuated by jumps; any cross-basin strategy "
                "faces real execution friction and bid-ask cost on the Asian leg.")
    bullet(doc, "Regimes are calibrated to verified event dates: COVID (control), 2022 Russia "
                "(positive control), the Jun-2025 Twelve-Day War (precursor — strait stayed open), "
                "and the Feb–Mar 2026 Hormuz closure (candidate chokepoint regime).")
    bullet(doc, "The pipeline is reproducible end-to-end (ingest → align → clean → eda → report); "
                "API keys live in .env and are never committed.")

    # ---- Appendix ----
    doc.add_page_break()
    h(doc, "Appendix A — Proof of Ingestion (first 5 rows)")
    body(doc, "Re-ingested from public sources; values match the Milestone 1 submission exactly.",
         space=8)
    appendix = [
        ("Market — prices & FX (Yahoo)", "market_prices_fx",
         ["date", "hh_fut_usd_mmbtu", "ttf_eur_mwh", "jkm_usd_mmbtu", "brent_usd_bbl", "eurusd"]),
        ("Physical — EU gas storage, Germany (GIE AGSI+)", "physical_eu_storage_de",
         ["date", "de_storage_pct", "de_gas_twh"]),
        ("Physical — EU LNG send-out & inventory, Spain (ALSI)", "physical_es_lng",
         ["date", "es_lng_sendout_gwh", "es_lng_inv_twh"]),
        ("Physical — US Lower-48 weekly storage (EIA)", "physical_us_storage",
         ["date", "us_working_gas_bcf"]),
        ("Physical — Weather HDD (Open-Meteo)", "physical_hdd",
         ["date", "hdd_amsterdam", "hdd_chicago", "hdd_beijing"]),
        ("Risk — Geopolitical Risk incl. Russia (Caldara–Iacoviello)", "risk_gpr",
         ["date", "GPR", "GPRT", "GPRA", "GPRC_RUS"]),
        ("Risk — European EPU (policyuncertainty)", "risk_epu_europe",
         ["date", "epu_europe"]),
        ("Macro — industrial production (FRED)", "macro_industrial_production",
         ["date", "us_ip_index", "euro_ip_index"]),
    ]
    for title, cache, cols in appendix:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(title)
        r.bold = True; r.font.size = Pt(9.5); r.font.color.rgb = ACCENT
        df = pd.read_parquet(RAW_DIR / f"{cache}.parquet")[cols]
        df = df.dropna(subset=[cols[1]]).head(5)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        rows = [[(None if pd.isna(v) else (str(v) if i == 0 else v))
                 for i, v in enumerate(rec)] for rec in df.values.tolist()]
        w = [0.9, 1.2, 1.1, 1.1, 1.1, 1.1] if cache == "market_prices_fx" else None
        add_table(doc, cols, rows, widths=w, font_pt=8)

    out = REPORTS / "QF632_Milestone2_Group4.docx"
    doc.save(str(out))
    print(f"written: {out}")


if __name__ == "__main__":
    main()
