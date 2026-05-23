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
    D-09: Phase 5 will add _write_report() and _write_html_dashboard() here.

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
        output_dir: Directory to write all output files into (cfg.OUTPUT_DIR).
        run_log: In-memory run metadata dict built throughout the pipeline run (D-05/D-06).
                 Keys: run_timestamp, students_processed, api_calls_made, tokens_used,
                 errors_encountered, fallbacks_triggered, data_quality_warnings.

    Returns:
        Dict mapping output file keys to their resolved Path objects.
        Keys: "priority_list", "campus_{campus_id}" per campus, "whatsapp", "run_log".
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

    logger.info(
        "All outputs written to %s — keys: %s",
        output_dir,
        list(paths.keys()),
    )
    return paths
