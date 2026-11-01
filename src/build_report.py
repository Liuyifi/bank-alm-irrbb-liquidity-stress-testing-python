"""Build the nine-page recruitment Portfolio Case Study from reviewed outputs."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.shared import Inches, Pt, RGBColor

from .config import ROOT


OUTPUT = ROOT / "report/Banking_Book_Interest_Rate_and_Liquidity_Stress_Testing_Report.docx"
QR_IMAGE = ROOT / "report/assets/github_repository_qr.png"
REPOSITORY_URL = "https://github.com/Liuyifi/bank-alm-irrbb-liquidity-stress-testing-python"

NAVY = "17365D"
BLUE = "4472C4"
LIGHT_BLUE = "EAF2F8"
PALE_BLUE = "F4F8FC"
PALE_GREY = "F3F5F7"
MID_GREY = "6B7280"
GRID = "D9E1E8"
BLACK = "000000"
WHITE = "FFFFFF"


def million(value, decimals=3):
    return f"{value / 1e6:,.{decimals}f}"


def signed_million(value, decimals=3):
    return f"{value / 1e6:+,.{decimals}f}"


def signed_thousand(value, decimals=1):
    return f"{value / 1e3:+,.{decimals}f}"


def percent(value, decimals=2):
    return f"{value * 100:,.{decimals}f}%"


def _set_repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def _prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    keep = OxmlElement("w:cantSplit")
    tr_pr.append(keep)


def _set_cell_fill(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_cell_border(cell, color=GRID, size="4"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        edge = OxmlElement(f"w:{side}")
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), size)
        edge.set(qn("w:color"), color)
        borders.append(edge)
    tc_pr.append(borders)


def _set_cell_margins(cell, top=90, bottom=90, left=95, right=95):
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = OxmlElement("w:tcMar")
    for side, value in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    tc_pr.append(margins)


def _set_run_font(run, size=None, bold=None, color=BLACK, name="Arial"):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def _add_page_field(paragraph):
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    paragraph._p.append(field)


def _add_hyperlink(paragraph, text, url):
    relationship_id = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), BLUE)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.extend((color, underline))
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.extend((properties, text_node))
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def build():
    from .source_validation import validate_sources

    validate_sources()
    if not QR_IMAGE.is_file() or QR_IMAGE.stat().st_size == 0:
        raise FileNotFoundError(
            f"Local repository QR image is required before report build: {QR_IMAGE}"
        )

    payload = json.loads((ROOT / "data/processed/artifact_payload.json").read_text())
    metrics = payload["metrics"]
    lineage = payload["lineage"]
    qa_summary = json.loads((ROOT / "qa/checks.json").read_text())
    qa_checks = {item["check"]: item for item in qa_summary["checks"]}
    metric_rows = list(csv.DictReader((ROOT / "qa/current_metric_reconciliation.csv").open()))
    current_metric_passes = sum(row["status"] == "PASS" for row in metric_rows)
    formula_count = int(qa_checks["excel_formula_caches_present"]["detail"].split()[0])

    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.62)
    section.bottom_margin = Inches(0.58)
    section.left_margin = Inches(0.68)
    section.right_margin = Inches(0.68)
    section.header_distance = Inches(0.25)
    section.footer_distance = Inches(0.25)
    section.different_first_page_header_footer = True

    styles = document.styles
    for style in styles:
        for border in style.element.xpath(".//w:pBdr"):
            border.getparent().remove(border)
    for name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3", "Caption"):
        styles[name].font.name = "Arial"
        styles[name]._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Arial")
        styles[name]._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Arial")

    normal = styles["Normal"]
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08

    styles["Title"].font.size = Pt(25)
    styles["Title"].font.bold = True
    styles["Title"].font.color.rgb = RGBColor.from_string(NAVY)
    styles["Title"].paragraph_format.space_after = Pt(8)

    styles["Subtitle"].font.size = Pt(12)
    styles["Subtitle"].font.color.rgb = RGBColor.from_string(MID_GREY)
    styles["Subtitle"].paragraph_format.space_after = Pt(16)

    styles["Heading 1"].font.size = Pt(18)
    styles["Heading 1"].font.bold = True
    styles["Heading 1"].font.color.rgb = RGBColor.from_string(NAVY)
    styles["Heading 1"].paragraph_format.space_before = Pt(0)
    styles["Heading 1"].paragraph_format.space_after = Pt(8)
    styles["Heading 1"].paragraph_format.keep_with_next = True

    styles["Heading 2"].font.size = Pt(11.5)
    styles["Heading 2"].font.bold = True
    styles["Heading 2"].font.color.rgb = RGBColor.from_string(BLUE)
    styles["Heading 2"].paragraph_format.space_before = Pt(7)
    styles["Heading 2"].paragraph_format.space_after = Pt(4)
    styles["Heading 2"].paragraph_format.keep_with_next = True

    styles["Caption"].font.size = Pt(8)
    styles["Caption"].font.italic = True
    styles["Caption"].font.color.rgb = RGBColor.from_string(MID_GREY)
    styles["Caption"].paragraph_format.space_after = Pt(4)

    header = section.header.paragraphs[0]
    header.text = "Bank ALM / IRRBB & Liquidity Stress Testing | Yifei Liu"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header.runs:
        _set_run_font(run, 7.8, color=MID_GREY)
    section.first_page_header.paragraphs[0].text = ""

    def set_footer(footer):
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = paragraph.add_run("Yifei Liu | Portfolio Project    Page ")
        _set_run_font(run, 7.8, color=MID_GREY)
        _add_page_field(paragraph)

    set_footer(section.footer)
    set_footer(section.first_page_footer)

    properties = document.core_properties
    properties.title = "Bank ALM / IRRBB & Liquidity Stress Testing"
    properties.subject = (
        "Recruitment Portfolio Case Study in Treasury Risk, ALM, IRRBB and Liquidity Stress Testing"
    )
    properties.author = "Yifei Liu"
    properties.last_modified_by = "Yifei Liu"
    properties.comments = ""
    properties.keywords = ""
    properties.category = ""
    properties.created = datetime(2026, 11, 1, tzinfo=timezone.utc)
    properties.modified = datetime(2026, 11, 1, tzinfo=timezone.utc)

    def add_paragraph(text="", style=None, before=0, after=None, keep=False):
        paragraph = document.add_paragraph(style=style)
        paragraph.add_run(text)
        paragraph.paragraph_format.space_before = Pt(before)
        if after is not None:
            paragraph.paragraph_format.space_after = Pt(after)
        paragraph.paragraph_format.keep_with_next = keep
        return paragraph

    def add_rich_paragraph(parts, before=0, after=5, style=None):
        paragraph = document.add_paragraph(style=style)
        paragraph.paragraph_format.space_before = Pt(before)
        paragraph.paragraph_format.space_after = Pt(after)
        for text, bold in parts:
            run = paragraph.add_run(text)
            run.bold = bold
        return paragraph

    def add_bullet(text, level=0):
        paragraph = document.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
        paragraph.add_run(text)
        paragraph.paragraph_format.left_indent = Inches(0.18 + level * 0.16)
        paragraph.paragraph_format.first_line_indent = Inches(-0.12)
        paragraph.paragraph_format.space_after = Pt(2.5)
        paragraph.paragraph_format.line_spacing = 1.03
        for run in paragraph.runs:
            _set_run_font(run, 9.1)
        return paragraph

    def new_page(title):
        document.add_page_break()
        document.add_heading(title, level=1)

    def add_table(headers, rows, widths, font_size=8.5, aligns=None):
        table = document.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        for index, width in enumerate(widths):
            table.columns[index].width = Inches(width)
        for cell, text in zip(table.rows[0].cells, headers):
            cell.text = str(text)
        for row_data in rows:
            row = table.add_row()
            for cell, text in zip(row.cells, row_data):
                cell.text = str(text)
        _set_repeat_header(table.rows[0])
        for row_index, row in enumerate(table.rows):
            _prevent_row_split(row)
            for column_index, cell in enumerate(row.cells):
                cell.width = Inches(widths[column_index])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                _set_cell_border(cell)
                _set_cell_margins(cell)
                _set_cell_fill(cell, NAVY if row_index == 0 else (PALE_BLUE if row_index % 2 == 0 else WHITE))
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.paragraph_format.line_spacing = 1.03
                    alignment = (aligns or ["left"] * len(headers))[column_index]
                    paragraph.alignment = {
                        "left": WD_ALIGN_PARAGRAPH.LEFT,
                        "center": WD_ALIGN_PARAGRAPH.CENTER,
                        "right": WD_ALIGN_PARAGRAPH.RIGHT,
                    }[alignment]
                    for run in paragraph.runs:
                        _set_run_font(
                            run,
                            font_size,
                            bold=row_index == 0,
                            color=WHITE if row_index == 0 else BLACK,
                        )
        spacer = document.add_paragraph()
        spacer.paragraph_format.space_after = Pt(0)
        return table

    def add_kpi_grid(items, columns=2, metric_size=16, label_size=8.5):
        rows = (len(items) + columns - 1) // columns
        table = document.add_table(rows=rows, cols=columns)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        width = 7.0 / columns
        for row_index, row in enumerate(table.rows):
            _prevent_row_split(row)
            for column_index, cell in enumerate(row.cells):
                cell.width = Inches(width)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                _set_cell_border(cell, color="C9D8E8")
                _set_cell_margins(cell, top=110, bottom=110, left=110, right=110)
                _set_cell_fill(cell, LIGHT_BLUE if row_index % 2 == 0 else PALE_BLUE)
                item_index = row_index * columns + column_index
                cell.text = ""
                if item_index >= len(items):
                    continue
                metric_text, label_text = items[item_index]
                metric_paragraph = cell.paragraphs[0]
                metric_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                metric_paragraph.paragraph_format.space_after = Pt(2)
                metric_run = metric_paragraph.add_run(metric_text)
                _set_run_font(metric_run, metric_size, True, NAVY)
                label_paragraph = cell.add_paragraph()
                label_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                label_paragraph.paragraph_format.space_after = Pt(0)
                label_run = label_paragraph.add_run(label_text)
                _set_run_font(label_run, label_size, False, MID_GREY)
        spacer = document.add_paragraph()
        spacer.paragraph_format.space_after = Pt(0)
        return table

    def add_figure(filename, caption, alt_text, width=6.7):
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(1)
        run = paragraph.add_run()
        run.add_picture(str(ROOT / "outputs/figures" / filename), width=Inches(width))
        drawing_properties = run._r.xpath(".//wp:docPr")[0]
        drawing_properties.set("descr", alt_text)
        caption_paragraph = document.add_paragraph(caption, style="Caption")
        caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def add_workflow(stages):
        table = document.add_table(rows=len(stages) * 2 - 1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        for row_index, row in enumerate(table.rows):
            cell = row.cells[0]
            cell.width = Inches(5.7)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(0)
            if row_index % 2 == 0:
                _set_cell_fill(cell, LIGHT_BLUE if (row_index // 2) % 2 == 0 else PALE_GREY)
                _set_cell_border(cell, color=GRID)
                _set_cell_margins(cell, top=55, bottom=55, left=90, right=90)
                run = paragraph.add_run(stages[row_index // 2])
                _set_run_font(run, 8.5, True, NAVY)
            else:
                _set_cell_fill(cell, WHITE)
                _set_cell_border(cell, color=WHITE)
                _set_cell_margins(cell, top=0, bottom=0, left=0, right=0)
                run = paragraph.add_run("↓")
                _set_run_font(run, 9.5, True, BLUE)
        return table

    # Page 1: Portfolio cover
    portfolio_tag = add_paragraph("YIFEI LIU'S PORTFOLIO CASE STUDY", after=6)
    for run in portfolio_tag.runs:
        _set_run_font(run, 9.5, True, BLUE)
    document.add_paragraph("Bank ALM / IRRBB & Liquidity Stress Testing", style="Title")
    document.add_paragraph(
        "A Python, SQL and Excel Portfolio Study of Interest Rate Risk,\n"
        "EVE / NII Sensitivity and 90-Day Liquidity Stress",
        style="Subtitle",
    )
    document.add_heading("PROJECT SNAPSHOT", level=2)
    add_kpi_grid(
        [
            (f"USD {million(metrics['total_assets'], 0)}M", "Synthetic Banking Book"),
            (f"USD {signed_million(metrics['worst_delta_eve'])}M", "Worst Delta EVE"),
            (f"USD {signed_thousand(metrics['worst_delta_nii'])}K", "Worst 12M Delta NII"),
            ("≥90 Days", "Combined Stress Survival"),
        ],
        columns=2,
        metric_size=15.5,
        label_size=8.8,
    )
    document.add_heading("PROJECT INFORMATION", level=2)
    add_table(
        ["Field", "Content"],
        [
            ["Author", "Yifei Liu"],
            ["Target roles", "Treasury / ALM Analyst | Market Risk Analyst | Risk Analytics / Model Validation"],
            ["Core stack", "Python | SQL | DuckDB | Excel"],
            ["Risk focus", "ALM | IRRBB | Liquidity Stress Testing"],
            ["Portfolio", f"{metrics['positions']} synthetic contract / group records"],
            ["Positioning", "Reproducible ALM / IRRBB and liquidity stress-testing portfolio project"],
        ],
        [1.35, 5.65],
        font_size=8.6,
        aligns=["left", "left"],
    )
    repository_table = document.add_table(rows=1, cols=2)
    repository_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    repository_table.autofit = False
    qr_cell, repository_cell = repository_table.rows[0].cells
    qr_cell.width = Inches(1.35)
    repository_cell.width = Inches(5.65)
    for cell in repository_table.rows[0].cells:
        _set_cell_border(cell, color=GRID)
        _set_cell_margins(cell, top=70, bottom=70, left=90, right=90)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    qr_paragraph = qr_cell.paragraphs[0]
    qr_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    qr_run = qr_paragraph.add_run()
    qr_run.add_picture(str(QR_IMAGE), width=Inches(0.92))
    qr_properties = qr_run._r.xpath(".//wp:docPr")[0]
    qr_properties.set("descr", "QR code linking to the public GitHub repository")
    repository_cell.text = ""
    label_paragraph = repository_cell.paragraphs[0]
    label_run = label_paragraph.add_run("Repository\n")
    _set_run_font(label_run, 8.7, True, NAVY)
    _add_hyperlink(label_paragraph, REPOSITORY_URL, REPOSITORY_URL)
    scan_paragraph = repository_cell.add_paragraph("Scan the QR code to review the code, evidence and reproducible workflow.")
    scan_paragraph.paragraph_format.space_after = Pt(0)
    for run in scan_paragraph.runs:
        _set_run_font(run, 8.3, color=MID_GREY)

    # Page 2: Executive Summary
    new_page("Executive Summary")
    add_paragraph(
        "This portfolio case study assesses earnings sensitivity, long-term economic-value exposure "
        "and short-term liquidity resilience for a stylized banking book. I built the deterministic "
        "portfolio, contract-level cash-flow engine, scenario framework, daily liquidity ledger, "
        "DuckDB reconciliation layer and Excel management pack from reviewed public-source inputs.",
        after=7,
    )
    add_table(
        ["Portfolio evidence", "Evidence"],
        [
            ["Business problem", "Measure repricing mismatch, 12-month NII sensitivity, full-life EVE exposure and 90-day liquidity resilience together."],
            ["What I built", f"A deterministic {metrics['positions']}-record balance sheet, cash-flow engine, seven rate scenarios, three liquidity stresses and a reconciliation framework."],
            ["Key IRRBB result", f"{metrics['worst_eve_scenario']} is the dominant tested economic-value shock: Delta EVE is USD {signed_million(metrics['worst_delta_eve'])}m."],
            ["Earnings result", f"Worst 12-month Delta NII is much smaller at USD {signed_thousand(metrics['worst_delta_nii'])}k under the default behavioral assumptions."],
            ["Liquidity result", f"All scenarios survive at least 90 days; Combined finishes with USD {million(payload['liquidity_scenarios'][2]['remaining_liquidity_buffer'])}m available cash."],
            ["Validation", f"{qa_summary['pytest']['tests']} / {qa_summary['pytest']['tests']} pytest; {qa_summary['automated_check_count']} / {qa_summary['automated_check_count']} automated controls; {current_metric_passes} / {len(metric_rows)} metric reconciliations; Python / SQL difference below USD 0.01."],
        ],
        [1.55, 5.45],
        font_size=8.6,
        aligns=["left", "left"],
    )
    add_rich_paragraph(
        [("Main interpretation. ", True), ("The book is materially more exposed through long-term economic value than through first-year earnings under the default assumptions.", False)],
        before=4,
    )
    add_rich_paragraph(
        [("Main limitation. ", True), ("Behavioral deposit beta, maturity and runoff are modeled assumptions rather than empirically estimated bank parameters, and they materially affect both NII and EVE.", False)],
    )
    add_rich_paragraph(
        [("Professional boundary. ", True), ("This is a synthetic portfolio study, not a production bank model or a regulatory compliance calculation.", False)],
    )

    # Page 3: Business problem, data and portfolio
    new_page("Business Problem, Data and Portfolio Construction")
    add_paragraph(
        "Banks monitor repricing, NII, EVE and liquidity together because short-horizon earnings and "
        "long-horizon value can move differently, while funding stress can constrain the actions "
        "available to manage either exposure. This project links those views in one reproducible study.",
        after=6,
    )
    add_table(
        ["Area", "Portfolio design"],
        [
            ["Public calibration", f"Federal Reserve H.8, release {lineage['h8']['release_date']}; observation {lineage['h8']['observation_date']}; all US commercial banks, not seasonally adjusted."],
            ["Market rates", f"US Treasury Daily Treasury Par Yield Curve Rates, observation {lineage['treasury']['observation_date']}."],
            ["Portfolio size", f"USD {million(metrics['total_assets'], 0)}m of synthetic assets."],
            ["Record count", f"{metrics['positions']} synthetic contract / group records generated with deterministic seed {metrics['seed']}."],
            ["Products", "Loans, securities, deposits, borrowings and residual balance-sheet categories."],
            ["Behavioral assumptions", "Deposit beta, NMD maturity, runoff, liquidity haircuts, funding nonrenewal and commitment draws."],
        ],
        [1.55, 5.45],
        font_size=8.6,
        aligns=["left", "left"],
    )
    document.add_heading("OBSERVED AND MODELED", level=2)
    add_table(
        ["Observed public evidence", "Modeled portfolio assumptions"],
        [[
            "Treasury par yields; H.8 cash, securities, gross loans, deposits, borrowings and residual balance-sheet shares.",
            "Product splits, contractual dates, coupons, reset schedules, amortization, deposit behavior, runoff, haircuts and commitment draws.",
        ]],
        [3.5, 3.5],
        font_size=8.5,
        aligns=["left", "left"],
    )
    add_rich_paragraph(
        [("Governance distinction. ", True), ("Public aggregates anchor the size and broad composition of the book; they do not reveal a bank-specific contractual portfolio. All position-level details remain synthetic and traceable to documented assumptions.", False)],
        before=4,
    )
    document.add_heading("ANALYTICAL WORKFLOW", level=2)
    add_workflow(
        [
            "Official Public Sources",
            "Synthetic Banking Book",
            "Contract-Level Cash-Flow Engine",
            "NII | EVE | Liquidity Stress",
            "SQL / DuckDB Controls",
            "Excel Management Pack | Portfolio Report",
        ]
    )

    # Page 4: Repricing gap
    new_page("Repricing Gap and Balance-Sheet Structure")
    add_paragraph(
        "Rate-sensitive principal is assigned to the first contractual reset, or final maturity for "
        "fixed-rate instruments. Non-maturity deposits reprice monthly and therefore concentrate in "
        "the shortest bucket; non-rate-sensitive balances are excluded from RSA and RSL.",
        after=3,
    )
    add_figure(
        "repricing_gap.png",
        "Figure 1. Rate-sensitive assets and liabilities by next repricing bucket.",
        "Repricing gap chart comparing rate-sensitive assets and liabilities by tenor bucket",
        width=6.55,
    )
    repricing_rows = [row for row in payload["repricing_gap"] if row["bucket"] != "Non-rate-sensitive"]
    add_table(
        ["Bucket", "RSA USD m", "RSL USD m", "Gap USD m"],
        [[row["bucket"], million(row["rsa"], 2), million(row["rsl"], 2), signed_million(row["periodic_gap"], 2)] for row in repricing_rows],
        [2.55, 1.45, 1.45, 1.55],
        font_size=8.0,
        aligns=["left", "right", "right", "right"],
    )
    add_bullet("The overnight-to-one-month gap is USD -46.42m: more funding than assets can reprice immediately.")
    add_bullet("Assets beyond five years total approximately USD 42.15m with no rate-sensitive liabilities in that bucket, creating long-duration value exposure.")
    add_bullet("Gap direction alone does not determine NII because deposit pass-through depends on the modeled NMD beta.")

    # Page 5: NII
    new_page("12-Month NII Sensitivity")
    add_paragraph(
        "The 12-month analysis follows the existing book as it runs off. Fixed coupons remain "
        "unchanged until maturity; floating-rate assets reset on schedule; matured principal is not "
        "reinvested. The result is an existing-book sensitivity, not a forecast for a growing balance sheet.",
        after=3,
    )
    add_figure(
        "nii_sensitivity.png",
        "Figure 2. Twelve-month Delta NII under internal illustrative scenarios.",
        "NII sensitivity chart showing twelve-month change in net interest income by rate scenario",
        width=6.55,
    )
    add_table(
        ["Scenario", "NII USD m", "Delta USD k", "Delta / Base"],
        [[row["scenario"], million(row["nii"]), signed_thousand(row["delta_nii"]), percent(row["delta_nii_pct"], 2)] for row in payload["nii_scenarios"]],
        [2.55, 1.35, 1.45, 1.65],
        font_size=8.1,
        aligns=["left", "right", "right", "right"],
    )
    add_rich_paragraph(
        [("Key result. ", True), (f"{metrics['worst_nii_scenario']} produces the worst tested 12-month change at USD {signed_thousand(metrics['worst_delta_nii'])}k, small relative to EVE sensitivity.", False)],
        before=3,
        after=3,
    )
    add_rich_paragraph(
        [("Why this matters. ", True), ("A small default earnings impact does not mean the book is hedged. NMD beta sensitivity can reverse the NII direction because modeled deposit pass-through changes the funding-cost response.", False)],
        after=0,
    )

    # Page 6: EVE
    new_page("EVE / IRRBB Sensitivity")
    add_paragraph(
        "EVE measures the discounted value of asset cash flows less liability cash flows over the full "
        "modeled life. Floating coupons are reprojected under each stressed curve and NMD principal "
        "follows its behavioral maturity schedule; equity is excluded as a liability.",
        after=3,
    )
    add_figure(
        "eve_sensitivity.png",
        "Figure 3. Delta EVE under internal illustrative scenarios.",
        "EVE sensitivity chart showing change in economic value by interest-rate scenario",
        width=6.55,
    )
    add_table(
        ["Scenario", "EVE USD m", "Delta USD m", "Delta / equity proxy"],
        [[row["scenario"], million(row["eve"]), signed_million(row["delta_eve"]), percent(row["delta_eve_equity_proxy_pct"], 2)] for row in payload["eve_scenarios"]],
        [2.5, 1.35, 1.45, 1.7],
        font_size=8.1,
        aligns=["left", "right", "right", "right"],
    )
    add_rich_paragraph(
        [("Worst tested scenario. ", True), (f"{metrics['worst_eve_scenario']} reduces EVE by USD {signed_million(metrics['worst_delta_eve'])}m, equal to {percent(metrics['worst_delta_eve_equity_proxy_pct'], 2)} of the stylized equity residual proxy.", False)],
        before=3,
        after=3,
    )
    add_rich_paragraph(
        [("Interpretation. ", True), ("Long-lived fixed-rate asset cash flows remain exposed to higher discount rates even when first-year coupon income changes only modestly.", False)],
        after=3,
    )
    add_rich_paragraph(
        [("Boundary. ", True), ("The equity residual proxy is not regulatory capital, and this result is not a BCBS supervisory outlier test or a production IRRBB regulatory calculation.", False)],
        after=0,
    )

    # Page 7: Liquidity
    new_page("90-Day Liquidity Stress Testing")
    add_paragraph(
        "A daily ledger starts with cash and recognizes stress outflows, contractual inflows and timed "
        "government-security monetization. Securities can be monetized once after haircuts; later "
        "cash flows are excluded to prevent double counting.",
        after=3,
    )
    add_figure(
        "liquidity_survival.png",
        "Figure 4. Available cash through the 90-day stress horizon.",
        "Liquidity survival chart showing available cash by day for three stress scenarios",
        width=6.55,
    )
    add_table(
        ["Scenario", "Outflows USD m", "Recognized inflows USD m", "End buffer USD m", "Survival"],
        [[
            row["scenario"],
            million(row["total_outflow"], 2),
            million(row["recognized_inflow"], 2),
            million(row["remaining_liquidity_buffer"], 3),
            "≥90 days" if row["survival_censored"] else f"{row['survival_days']} days",
        ] for row in payload["liquidity_scenarios"]],
        [1.35, 1.35, 1.55, 1.45, 1.3],
        font_size=7.9,
        aligns=["left", "right", "right", "right", "center"],
    )
    add_rich_paragraph(
        [("Key result. ", True), (f"All three scenarios survive at least 90 days. Combined finishes with only USD {million(payload['liquidity_scenarios'][2]['remaining_liquidity_buffer'])}m of available cash, so the result is right-censored rather than evidence of indefinite survival.", False)],
        before=3,
        after=3,
    )
    add_rich_paragraph(
        [("Stress mechanics. ", True), ("The scenarios combine retail runoff, commitment drawdown, term nonrenewal, wholesale funding loss, security haircuts, monetization timing and an internal daily 75% inflow cap.", False)],
        after=3,
    )
    add_rich_paragraph(
        [("Implementation takeaway. ", True), ("The implementation uses a daily liquidity stock-and-flow ledger rather than only static scenario totals.", False)],
        after=0,
    )

    # Page 8: Validation
    new_page("Validation and Control Framework")
    add_paragraph(
        "The validation design checks source integrity, calculation consistency, independent control "
        "logic where feasible, saved Office artifacts and current-state metric reconciliation. This "
        "separates generated outputs from evidence that the outputs are internally consistent.",
        after=5,
    )
    add_kpi_grid(
        [
            (f"{qa_summary['pytest']['tests']} / {qa_summary['pytest']['tests']}", "pytest"),
            (f"{qa_summary['automated_check_count']} / {qa_summary['automated_check_count']}", "Automated Acceptance Controls"),
            (f"{metrics['core_checks_passed']} / {metrics['core_checks_passed']}", "Core Engine / Data Controls"),
            (f"{current_metric_passes} / {len(metric_rows)}", "Current Metric Reconciliations"),
            (f"USD {metrics['python_sql_max_difference']:.10f}", "Maximum Python / SQL Difference"),
        ],
        columns=3,
        metric_size=12.5,
        label_size=7.6,
    )
    document.add_heading("SQL CONTROL STRUCTURE", level=2)
    add_table(
        ["Classification", "Controls", "Meaning"],
        [
            ["Independent recomputation", "Balance sheet; repricing gap", "SQL recomputes results from position-level inputs without Python result columns."],
            ["Partial recomputation", "NII; EVE; liquidity", "SQL independently aggregates or reconstructs controls but reuses projected cash flows or discount inputs."],
        ],
        [1.65, 1.9, 3.45],
        font_size=8.2,
        aligns=["left", "left", "left"],
    )
    document.add_heading("ARTIFACT AND GOVERNANCE EVIDENCE", level=2)
    add_table(
        ["Artifact", "Evidence"],
        [
            ["Excel management pack", f"12 sheets; 15 native tables; 4 native charts; {formula_count} cached formulas; no external links or formula errors."],
            ["Portfolio report", "Nine-page render; reconciled core metrics; source names; repository and QR; author identity; model-boundary language; no local paths or unfinished text."],
            ["Source governance", "Versioned source lock, raw-to-processed lineage and fail-closed validation before analysis or artifact writes."],
        ],
        [1.65, 5.35],
        font_size=8.3,
        aligns=["left", "left"],
    )
    add_rich_paragraph(
        [("Validation boundary. ", True), ("The controls establish implementation consistency under documented synthetic assumptions; they do not empirically validate deposit behavior or turn the SQL layer into a second independent valuation engine.", False)],
        before=3,
        after=0,
    )

    # Page 9: Skills, limitations and repository
    new_page("Skills Demonstrated and Responsible Interpretation")
    document.add_heading("SKILLS DEMONSTRATED", level=2)
    add_table(
        ["Capability", "Evidence demonstrated in this project"],
        [
            ["Risk analytics", "NII sensitivity; EVE / IRRBB analysis; repricing gap; 90-day liquidity stress; NMD behavioral sensitivity."],
            ["Programming and data", "Python cash-flow modelling; SQL / DuckDB reconciliation; reproducible pipeline; structured controls; source lineage and fail-closed validation."],
            ["Risk communication & reporting", "Excel management pack; risk visualization; executive interpretation; concise model-boundary documentation."],
        ],
        [1.75, 5.25],
        font_size=8.6,
        aligns=["left", "left"],
    )
    document.add_heading("KEY LIMITATIONS", level=2)
    for limitation in (
        "The banking book is synthetic and calibrated to public industry aggregates rather than bank-level records.",
        "Deposit beta, behavioral maturity and runoff are modeled assumptions, not empirically estimated parameters.",
        "Mortgage prepayment, embedded options and dynamic customer migration are not modeled.",
        "Derivative hedges, hedge costs and optimization are outside scope.",
        "Liquidity results are internal scenario proxies; no formal LCR or NSFR is calculated.",
        "The study is not a BCBS standardized IRRBB implementation or a regulatory capital assessment.",
    ):
        add_bullet(limitation)
    document.add_heading("REPOSITORY AND SUPPORTING EVIDENCE", level=2)
    add_paragraph(
        "Full methodology, source lineage, validation evidence, reviewed outputs and reproducible code are available in the public repository.",
        after=3,
    )
    repository_paragraph = document.add_paragraph()
    repository_paragraph.paragraph_format.space_after = Pt(4)
    _add_hyperlink(repository_paragraph, REPOSITORY_URL, REPOSITORY_URL)
    add_paragraph(
        "This report is designed as a standalone recruitment attachment; the repository provides the deeper technical and audit trail for interview discussion.",
        after=0,
    )

    document.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
