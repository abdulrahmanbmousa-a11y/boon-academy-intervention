"""Output file generation for boon-academy-intervention.

Phase 4 implements write_outputs() and its private helpers for writing all output
files from the fully-enriched one-row-per-student DataFrame.

D-05 / D-06: Writes 6 output files including run_log.json built in-memory by main.py
per CONTEXT.md D-05 and D-06. The run_log dict is constructed throughout the pipeline
run and flushed once at the end via this module — no incremental writes anywhere.

D-01 (Signature): write_outputs(df, output_dir, run_log) — run_log is a required
positional parameter. Plan 04-01 implements _write_whatsapp_csv and _write_run_log.
Plans 04-02 and 04-03 add the remaining helpers and complete write_outputs().
"""
import json
import logging
from pathlib import Path

import pandas as pd
from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from src import config as cfg

logger = logging.getLogger(__name__)


def _write_whatsapp_csv(df: pd.DataFrame, output_dir: Path) -> Path:
    """Write whatsapp_messages.csv for all CRITICAL and HIGH risk students.

    Filters the DataFrame to CRITICAL and HIGH risk_level rows only,
    selects exactly 8 columns in the OUT-03 specified order, and writes
    a UTF-8 BOM CSV file so Excel opens it without garbled characters.

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
        output_dir: Directory to write the CSV file into.

    Returns:
        Path to the written whatsapp_messages.csv file.
    """
    df_copy = df.copy()
    mask = df_copy[cfg.COL_RISK_LEVEL].isin(["CRITICAL", "HIGH"])
    cols = [
        cfg.COL_STUDENT_ID,
        cfg.COL_STUDENT_NAME,
        cfg.COL_PARENT_PHONE,
        cfg.COL_FACILITATOR_EMAIL,
        cfg.COL_CAMPUS_ID,
        cfg.COL_RISK_LEVEL,
        cfg.COL_WHATSAPP_MESSAGE,
        cfg.COL_GENERATED_BY,
    ]
    path = output_dir / "whatsapp_messages.csv"
    df_copy.loc[mask, cols].to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("Wrote whatsapp CSV: %s (%d rows)", path, mask.sum())
    return path


def _write_run_log(run_log: dict, output_dir: Path) -> Path:
    """Write run_log.json from the in-memory run_log dict (D-06).

    Serializes the run_log dict to JSON with indent=2. Uses default=str
    to safely handle any datetime or Path objects that may be present
    without raising TypeError.

    Args:
        run_log: Pipeline run metadata dict with 7 required keys:
            run_timestamp, students_processed, api_calls_made, tokens_used,
            errors_encountered, fallbacks_triggered, data_quality_warnings.
        output_dir: Directory to write run_log.json into.

    Returns:
        Path to the written run_log.json file.
    """
    path = output_dir / "run_log.json"
    path.write_text(json.dumps(run_log, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote run log: %s", path)
    return path


def _write_html_dashboard(df: pd.DataFrame, output_dir: Path) -> Path:
    """Write facilitator_dashboard.html — fully self-contained HTML file (OUT-05).

    Renders the dashboard.html.j2 Jinja2 template with all student records
    embedded as a JS const (studentsData). The output file requires no server
    and no network requests — it works via file:// in any modern browser.

    JSON injection safety (CLAUDE.md critical pitfall): json.dumps().replace("</", "<\\/")
    prevents </script> in student data from breaking the HTML script tag.

    Jinja2 is loaded lazily inside this function (not at module import) to avoid
    importing jinja2 unless the dashboard helper is actually called.

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
        output_dir: Directory to write facilitator_dashboard.html into.

    Returns:
        Path to the written facilitator_dashboard.html file.
    """
    from jinja2 import Environment, FileSystemLoader  # lazy import — D-01

    df_copy = df.copy()

    # Select display columns; replace NaN/NA with None so json.dumps serialises cleanly
    display_cols = list(cfg.DISPLAY_COLS_DASHBOARD)
    records = (
        df_copy[display_cols]
        .where(df_copy[display_cols].notna(), other=None)
        .to_dict(orient="records")
    )

    # T-05-01: prevent </script> injection from student data (CLAUDE.md critical pitfall)
    students_json = json.dumps(records).replace("</", "<\\/")

    # Campus filter options — sorted unique campus IDs from data
    campus_ids: list[str] = sorted(
        df_copy[cfg.COL_CAMPUS_ID].dropna().unique().tolist()
    )

    # Load Jinja2 template from src/templates/dashboard.html.j2 (file-adjacent resource)
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,  # students_json is pre-serialised JSON, not user HTML
    )
    template = env.get_template("dashboard.html.j2")

    run_timestamp = str(pd.Timestamp.now().isoformat())
    html = template.render(
        students_json=students_json,
        campus_ids=campus_ids,
        run_timestamp=run_timestamp,
    )

    path = output_dir / "facilitator_dashboard.html"
    path.write_text(html, encoding="utf-8")
    logger.info("Wrote HTML dashboard: %s (%d students)", path, len(df_copy))
    return path


def _write_report(df: pd.DataFrame, run_log: dict, output_dir: Path) -> Path:
    """Write intervention_report.docx — programmatic python-docx builder (OUT-04).

    Builds a 7-section Word document using only Document(), add_heading(),
    add_paragraph(), and add_table() — no OxmlElement, no custom styles (D-10).
    All headings use built-in levels (level=0/1/2) per D-11. All tables use
    style="Table Grid" per D-12. Section order follows D-13.

    Sections produced (D-13 order):
      1. Cover page — title, run date, campus count, students processed
      2. Executive Summary — narrative paragraph + risk breakdown table
      3. Top 10 Most At-Risk Students — ranked table (capped at 10 rows, T-05-06)
      4. Campus Summary — per-campus totals, critical/high counts, coverage %
      5. Student Deep-Dives — up to 4 sections, one per risk tier (D-08 graceful degradation)
      6. Data Quality Notes — warnings from run_log['data_quality_warnings']
      7. Methodology Appendix — weighted formula table + risk threshold paragraphs

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
            Must contain COL_RISK_LEVEL, COL_RISK_SCORE, COL_STUDENT_NAME,
            COL_CAMPUS_ID, COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
            COL_DAYS_SINCE_NOTE, COL_FACILITATOR_SUMMARY, COL_RECOMMENDED_ACTION.
            Component columns (COL_*_COMPONENT) are optional — missing columns are
            handled gracefully with "N/A" fallback.
        run_log: Pipeline run metadata dict. Keys used: run_timestamp,
            students_processed, data_quality_warnings.
        output_dir: Directory to write intervention_report.docx into.

    Returns:
        Path to the written intervention_report.docx file.
    """
    df_copy = df.copy()
    doc = Document()

    # -----------------------------------------------------------------------
    # Section 1 — Cover page
    # -----------------------------------------------------------------------
    doc.add_heading("Boon Academy — Student Intervention Report", level=0)
    doc.add_paragraph(f"Run date: {run_log.get('run_timestamp', 'N/A')}")
    campus_count = df_copy[cfg.COL_CAMPUS_ID].nunique()
    doc.add_paragraph(f"Campuses: {campus_count}")
    doc.add_paragraph(
        f"Students processed: {run_log.get('students_processed', len(df_copy))}"
    )

    # -----------------------------------------------------------------------
    # Section 2 — Executive Summary
    # -----------------------------------------------------------------------
    doc.add_heading("Executive Summary", level=1)

    total = len(df_copy)
    risk_counts = df_copy[cfg.COL_RISK_LEVEL].value_counts()
    critical_count = int(risk_counts.get("CRITICAL", 0))
    high_count = int(risk_counts.get("HIGH", 0))
    medium_count = int(risk_counts.get("MEDIUM", 0))
    low_count = int(risk_counts.get("LOW", 0))

    critical_pct = (critical_count / total * 100) if total > 0 else 0.0
    doc.add_paragraph(
        f"Of {total} students, {critical_count} ({critical_pct:.0f}%) are at CRITICAL "
        "risk requiring immediate intervention. The pipeline has generated prioritised "
        "facilitator action items and drafted WhatsApp parent messages for all CRITICAL "
        "and HIGH risk students."
    )

    # Risk breakdown table: header + 4 risk level rows, 3 columns
    risk_table = doc.add_table(rows=5, cols=3, style="Table Grid")
    risk_table.cell(0, 0).text = "Risk Level"
    risk_table.cell(0, 1).text = "Count"
    risk_table.cell(0, 2).text = "% of Total"

    for row_idx, (level, count) in enumerate(
        [
            ("CRITICAL", critical_count),
            ("HIGH", high_count),
            ("MEDIUM", medium_count),
            ("LOW", low_count),
        ],
        start=1,
    ):
        pct = (count / total * 100) if total > 0 else 0.0
        risk_table.cell(row_idx, 0).text = level
        risk_table.cell(row_idx, 1).text = str(count)
        risk_table.cell(row_idx, 2).text = f"{pct:.1f}%"

    # -----------------------------------------------------------------------
    # Section 3 — Top 10 Most At-Risk Students (T-05-06: hard cap at 10 rows)
    # -----------------------------------------------------------------------
    doc.add_heading("Top 10 Most At-Risk Students", level=1)

    top10 = df_copy.nlargest(10, cfg.COL_RISK_SCORE)
    top10_table = doc.add_table(rows=len(top10) + 1, cols=5, style="Table Grid")
    top10_table.cell(0, 0).text = "Rank"
    top10_table.cell(0, 1).text = "Student Name"
    top10_table.cell(0, 2).text = "Campus"
    top10_table.cell(0, 3).text = "Risk Score"
    top10_table.cell(0, 4).text = "Risk Level"

    for row_idx, (_, student) in enumerate(top10.iterrows(), start=1):
        top10_table.cell(row_idx, 0).text = str(row_idx)
        top10_table.cell(row_idx, 1).text = str(student[cfg.COL_STUDENT_NAME])
        top10_table.cell(row_idx, 2).text = str(student[cfg.COL_CAMPUS_ID])
        top10_table.cell(row_idx, 3).text = f"{student[cfg.COL_RISK_SCORE]:.1f}"
        top10_table.cell(row_idx, 4).text = str(student[cfg.COL_RISK_LEVEL])

    # -----------------------------------------------------------------------
    # Section 4 — Campus Summary
    # -----------------------------------------------------------------------
    doc.add_heading("Campus Summary", level=1)

    campus_groups = df_copy.groupby(cfg.COL_CAMPUS_ID, dropna=True)
    campus_table = doc.add_table(
        rows=campus_count + 1, cols=5, style="Table Grid"
    )
    campus_table.cell(0, 0).text = "Campus"
    campus_table.cell(0, 1).text = "Total Students"
    campus_table.cell(0, 2).text = "Critical"
    campus_table.cell(0, 3).text = "High"
    campus_table.cell(0, 4).text = "Intervention Coverage %"

    for row_idx, (campus_id, campus_df) in enumerate(campus_groups, start=1):
        c_total = len(campus_df)
        c_critical = int((campus_df[cfg.COL_RISK_LEVEL] == "CRITICAL").sum())
        c_high = int((campus_df[cfg.COL_RISK_LEVEL] == "HIGH").sum())
        c_coverage = (
            round((c_critical + c_high) / c_total * 100, 1) if c_total > 0 else 0.0
        )
        campus_table.cell(row_idx, 0).text = str(campus_id)
        campus_table.cell(row_idx, 1).text = str(c_total)
        campus_table.cell(row_idx, 2).text = str(c_critical)
        campus_table.cell(row_idx, 3).text = str(c_high)
        campus_table.cell(row_idx, 4).text = f"{c_coverage}%"

    # -----------------------------------------------------------------------
    # Section 5 — Student Deep-Dives (D-08: graceful degradation — skip empty tiers)
    # -----------------------------------------------------------------------
    doc.add_heading("Student Deep-Dives", level=1)

    # End-user-facing component columns — always present in enriched DataFrame
    component_cols = [
        cfg.COL_ATTENDANCE_RATE,
        cfg.COL_AVG_PRACTICE,
        cfg.COL_TREND_DIR,
        cfg.COL_DAYS_SINCE_NOTE,
    ]
    component_labels = [
        "Attendance Rate",
        "Avg Practice Questions",
        "Trend Direction",
        "Days Since Last Note",
    ]

    for tier in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        tier_df = df_copy[df_copy[cfg.COL_RISK_LEVEL] == tier]
        if tier_df.empty:
            continue  # D-08: skip tier with no students — no section added
        student = tier_df.nlargest(1, cfg.COL_RISK_SCORE).iloc[0]
        doc.add_heading(
            f"{tier} — {student[cfg.COL_STUDENT_NAME]}", level=2
        )
        doc.add_paragraph(
            f"Campus: {student[cfg.COL_CAMPUS_ID]} | "
            f"Risk Score: {student[cfg.COL_RISK_SCORE]:.1f} | "
            f"Level: {student[cfg.COL_RISK_LEVEL]}"
        )

        # Component scores table: header + 4 component rows, 2 columns
        comp_table = doc.add_table(
            rows=len(component_cols) + 1, cols=2, style="Table Grid"
        )
        comp_table.cell(0, 0).text = "Component"
        comp_table.cell(0, 1).text = "Score"
        for comp_row_idx, (col, label) in enumerate(
            zip(component_cols, component_labels), start=1
        ):
            value = (
                student[col] if col in df_copy.columns else "N/A"
            )
            comp_table.cell(comp_row_idx, 0).text = label
            comp_table.cell(comp_row_idx, 1).text = str(value)

        facilitator_summary = student.get(cfg.COL_FACILITATOR_SUMMARY, "N/A") or "N/A"
        recommended_action = student.get(cfg.COL_RECOMMENDED_ACTION, "N/A") or "N/A"
        doc.add_paragraph(f"Facilitator Summary: {facilitator_summary}")
        doc.add_paragraph(f"Recommended Action: {recommended_action}")

    # -----------------------------------------------------------------------
    # Section 6 — Data Quality Notes
    # -----------------------------------------------------------------------
    doc.add_heading("Data Quality Notes", level=1)

    warnings = run_log.get("data_quality_warnings", [])
    if not warnings:
        doc.add_paragraph("No data quality issues detected in this run.")
    else:
        for w in warnings:
            doc.add_paragraph(f"• {w}")

    # -----------------------------------------------------------------------
    # Section 7 — Methodology Appendix
    # -----------------------------------------------------------------------
    doc.add_heading("Methodology Appendix", level=1)
    doc.add_heading("Risk Score Formula", level=2)
    doc.add_paragraph(
        "Risk score (0-100) is computed as a weighted sum of four components:"
    )

    # Weights table: header + 4 component rows, 2 columns
    weights_table = doc.add_table(rows=5, cols=2, style="Table Grid")
    weights_table.cell(0, 0).text = "Component"
    weights_table.cell(0, 1).text = "Weight"
    weights_table.cell(1, 0).text = "Attendance Rate"
    weights_table.cell(1, 1).text = f"{cfg.WEIGHT_ATTENDANCE:.0%}"
    weights_table.cell(2, 0).text = "Avg Practice Questions"
    weights_table.cell(2, 1).text = f"{cfg.WEIGHT_PRACTICE:.0%}"
    weights_table.cell(3, 0).text = "Trend Direction"
    weights_table.cell(3, 1).text = f"{cfg.WEIGHT_TREND:.0%}"
    weights_table.cell(4, 0).text = "Days Since Last Note"
    weights_table.cell(4, 1).text = f"{cfg.WEIGHT_NOTES:.0%}"

    doc.add_heading("Risk Level Thresholds", level=2)
    doc.add_paragraph(f"CRITICAL: score >= {cfg.RISK_THRESHOLD_CRITICAL}")
    doc.add_paragraph(
        f"HIGH: {cfg.RISK_THRESHOLD_HIGH} <= score < {cfg.RISK_THRESHOLD_CRITICAL}"
    )
    doc.add_paragraph(
        f"MEDIUM: {cfg.RISK_THRESHOLD_MEDIUM} <= score < {cfg.RISK_THRESHOLD_HIGH}"
    )
    doc.add_paragraph(f"LOW: score < {cfg.RISK_THRESHOLD_MEDIUM}")

    # -----------------------------------------------------------------------
    # Save — str() required on Windows for python-docx 1.1.2 (STATE.md constraint)
    # -----------------------------------------------------------------------
    path = output_dir / "intervention_report.docx"
    doc.save(str(path))
    logger.info("Wrote Word report: %s (%d students)", path, len(df_copy))
    return path


def _write_priority_list(df: pd.DataFrame, output_dir: Path) -> Path:
    """Write intervention_priority_list.xlsx — all students ranked by risk_score desc.

    Produces a 12-column Excel file (OUTPUT_COLS_PRIORITY) with:
    - Row 1: navy header (COLOR_HEADER fill, white bold font)
    - Rows 2+: data rows color-coded by risk_level
    - freeze_panes="A2" — header row always visible when scrolling
    - Auto column widths capped at 60 chars + 2 padding

    Args:
        df: Fully enriched one-row-per-student DataFrame.
        output_dir: Directory to write the Excel file into.

    Returns:
        Path to the written intervention_priority_list.xlsx file.
    """
    df_copy = df.copy()

    # Sort descending by risk_score and assign sequential ranks
    df_sorted = df_copy.sort_values(cfg.COL_RISK_SCORE, ascending=False).reset_index(
        drop=True
    )
    df_sorted[cfg.COL_RANK] = df_sorted.index + 1

    # Select the 12 output columns in the correct order
    df_out = df_sorted[list(cfg.OUTPUT_COLS_PRIORITY)]

    # Create workbook and write header row (row 1)
    wb = Workbook()
    ws = wb.active
    ws.title = "Intervention Priority List"
    header_fill = PatternFill(fill_type="solid", fgColor=cfg.COLOR_HEADER)
    header_font = Font(bold=True, color=cfg.FONT_WHITE)
    for col_idx, col_name in enumerate(cfg.OUTPUT_COLS_PRIORITY, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.fill = header_fill
        cell.font = header_font

    # Build fill map once before the data-row loop (not per-cell — see research pitfall)
    fill_map = {
        "CRITICAL": PatternFill(fill_type="solid", fgColor=cfg.COLOR_CRITICAL),
        "HIGH": PatternFill(fill_type="solid", fgColor=cfg.COLOR_HIGH),
        "MEDIUM": PatternFill(fill_type="solid", fgColor=cfg.COLOR_MEDIUM),
        "LOW": PatternFill(fill_type="solid", fgColor=cfg.COLOR_LOW),
    }

    # Write data rows starting at row 2
    for row_idx, (_, row) in enumerate(df_out.iterrows(), start=2):
        risk_level = row[cfg.COL_RISK_LEVEL]
        row_fill = fill_map.get(risk_level)
        for col_idx, col_name in enumerate(cfg.OUTPUT_COLS_PRIORITY, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=row[col_name])
            if row_fill:
                cell.fill = row_fill

    # Auto column widths — None guard is mandatory (str(None)=="None" underestimates)
    for col_cells in ws.columns:
        max_len = max(
            (len(str(c.value)) for c in col_cells if c.value is not None),
            default=10,
        )
        ws.column_dimensions[get_column_letter(col_cells[0].column)].width = (
            min(max_len, 60) + 2
        )

    # Freeze header row and save
    ws.freeze_panes = "A2"
    path = output_dir / "intervention_priority_list.xlsx"
    wb.save(path)
    logger.info("Wrote priority list: %s (%d rows)", path, len(df_out))
    return path


def _write_campus_dashboards(
    df: pd.DataFrame, output_dir: Path
) -> dict[str, Path]:
    """Write one facilitator_dashboard_{campus_id}.xlsx per unique campus.

    Each campus file has 15 columns (OUTPUT_COLS_CAMPUS = 12 standard + 3 LLM):
    - Row 1: navy header (same styling as priority list)
    - Row 2: summary stats row (bold, light grey fill) — total, CRITICAL, HIGH, coverage%
    - Rows 3+: student data rows color-coded by risk_level
    - freeze_panes="A2" — only the header row is frozen (D-08)
    - MEDIUM/LOW rows have None in the 3 LLM columns (D-06 — empty, not "N/A")
    - NaN campus_id rows are excluded via dropna=True in groupby

    Args:
        df: Fully enriched one-row-per-student DataFrame.
        output_dir: Directory to write the Excel files into.

    Returns:
        Dict mapping "campus_{campus_id}" keys to Path objects for each written file.
    """
    df_copy = df.copy()
    results: dict[str, Path] = {}

    # LLM column names — cells for MEDIUM/LOW students are written as None (D-06)
    llm_col_names = {
        cfg.COL_FACILITATOR_SUMMARY,
        cfg.COL_WHATSAPP_MESSAGE,
        cfg.COL_GENERATED_BY,
    }

    # Build fill map once (shared across all campus files)
    fill_map = {
        "CRITICAL": PatternFill(fill_type="solid", fgColor=cfg.COLOR_CRITICAL),
        "HIGH": PatternFill(fill_type="solid", fgColor=cfg.COLOR_HIGH),
        "MEDIUM": PatternFill(fill_type="solid", fgColor=cfg.COLOR_MEDIUM),
        "LOW": PatternFill(fill_type="solid", fgColor=cfg.COLOR_LOW),
    }

    # Group by campus, excluding NaN campus_ids (dropna=True prevents _nan.xlsx files)
    for campus_id, campus_df in df_copy.groupby(cfg.COL_CAMPUS_ID, dropna=True):
        campus_df = campus_df.sort_values(
            cfg.COL_RISK_SCORE, ascending=False
        ).reset_index(drop=True)
        campus_df[cfg.COL_RANK] = campus_df.index + 1

        # Compute summary stats for row 2
        total = len(campus_df)
        critical_count = int((campus_df[cfg.COL_RISK_LEVEL] == "CRITICAL").sum())
        high_count = int((campus_df[cfg.COL_RISK_LEVEL] == "HIGH").sum())
        coverage_pct = (
            round((critical_count + high_count) / total * 100, 1) if total > 0 else 0.0
        )

        # Select 15 output columns
        df_out = campus_df[list(cfg.OUTPUT_COLS_CAMPUS)]

        # Create workbook and write header row (row 1)
        wb = Workbook()
        ws = wb.active
        ws.title = str(campus_id)
        header_fill = PatternFill(fill_type="solid", fgColor=cfg.COLOR_HEADER)
        header_font = Font(bold=True, color=cfg.FONT_WHITE)
        for col_idx, col_name in enumerate(cfg.OUTPUT_COLS_CAMPUS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font

        # Write summary row (row 2) — bold, light grey fill
        summary_fill = PatternFill(fill_type="solid", fgColor="FFEEEEEE")
        summary_font = Font(bold=True)
        summary_values = [
            "Summary",
            "",
            "",
            str(campus_id),
            "",
            "",
            "",
            f"Total: {total}",
            f"CRITICAL: {critical_count}",
            f"HIGH: {high_count}",
            f"Coverage: {coverage_pct}%",
            "",
            "",
            "",
            "",
        ]
        for col_idx, val in enumerate(summary_values, start=1):
            cell = ws.cell(row=2, column=col_idx, value=val)
            cell.fill = summary_fill
            cell.font = summary_font

        # Write data rows starting at row 3
        for row_idx, (_, row) in enumerate(df_out.iterrows(), start=3):
            risk_level = row[cfg.COL_RISK_LEVEL]
            row_fill = fill_map.get(risk_level)
            is_llm_eligible = risk_level in ("CRITICAL", "HIGH")
            for col_idx, col_name in enumerate(cfg.OUTPUT_COLS_CAMPUS, start=1):
                if col_name in llm_col_names and not is_llm_eligible:
                    value = None  # D-06: empty cell, not "N/A"
                else:
                    value = row[col_name]
                    # Normalise pandas NA to Python None for openpyxl
                    if value is pd.NA:
                        value = None
                    elif not isinstance(value, (str, int, float, bool)) and value is not None:
                        try:
                            if pd.isna(value):
                                value = None
                        except (TypeError, ValueError):
                            pass
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                if row_fill:
                    cell.fill = row_fill

        # Auto column widths (same pattern as priority list)
        for col_cells in ws.columns:
            max_len = max(
                (len(str(c.value)) for c in col_cells if c.value is not None),
                default=10,
            )
            ws.column_dimensions[get_column_letter(col_cells[0].column)].width = (
                min(max_len, 60) + 2
            )

        # Freeze header row only (D-08: freeze_panes="A2")
        ws.freeze_panes = "A2"
        path = output_dir / f"facilitator_dashboard_{campus_id}.xlsx"
        wb.save(path)
        logger.info("Wrote campus dashboard: %s (%d students)", path, total)
        results[f"campus_{campus_id}"] = path

    return results


def write_outputs(
    df: pd.DataFrame,
    output_dir: Path,
    run_log: dict,
) -> dict[str, Path]:
    """Write all Phase 4 output files for the intervention pipeline.

    Orchestrates four private helpers — one per output type — and returns a unified
    dict mapping semantic keys to resolved Path objects (D-01, D-02).

    D-03: Creates output_dir (including parents) if it does not exist — idempotent.
    D-04: Delegates to four independently-testable private helpers.
    D-09: Phase 5 adds _write_html_dashboard() (OUT-05) called after run_log.

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
        output_dir: Directory to write all output files into (cfg.OUTPUT_DIR).
        run_log: In-memory run metadata dict built throughout the pipeline run (D-05/D-06).
                 Keys: run_timestamp, students_processed, api_calls_made, tokens_used,
                 errors_encountered, fallbacks_triggered, data_quality_warnings.

    Returns:
        Dict mapping output file keys to their resolved Path objects.
        Keys: "priority_list", "campus_{campus_id}" per campus, "whatsapp", "run_log", "dashboard".
    """
    output_dir.mkdir(parents=True, exist_ok=True)   # D-03

    if df.empty:
        logger.warning(
            "write_outputs called with empty DataFrame — no student data to write"
        )

    paths: dict[str, Path] = {}

    priority_path = _write_priority_list(df, output_dir)
    paths["priority_list"] = priority_path

    campus_paths = _write_campus_dashboards(df, output_dir)
    paths.update(campus_paths)

    whatsapp_path = _write_whatsapp_csv(df, output_dir)
    paths["whatsapp"] = whatsapp_path

    run_log_path = _write_run_log(run_log, output_dir)
    paths["run_log"] = run_log_path

    dashboard_path = _write_html_dashboard(df, output_dir)
    paths["dashboard"] = dashboard_path

    logger.info(
        "All outputs written to %s — keys: %s",
        output_dir,
        list(paths.keys()),
    )
    return paths
