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
    df_copy[mask][cols].to_csv(path, index=False, encoding="utf-8-sig")
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


def write_outputs(df: pd.DataFrame, output_dir: Path) -> dict[str, Path]:
    """Write all 6 output files for the intervention pipeline.

    Phase 4 implementation: writes intervention_priority_list.xlsx,
    facilitator_dashboard_*.xlsx (one per campus), whatsapp_messages.csv,
    intervention_report.docx, facilitator_dashboard.html, and run_log.json.

    D-05 / D-06: run_log.json is built in-memory by main.py throughout the run
    (schema: run_timestamp, students_processed, api_calls_made, tokens_used,
    errors_encountered, fallbacks_triggered, data_quality_warnings) and written
    exactly once here at pipeline end — no partial writes, no file locking needed.

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
        output_dir: Directory to write all output files into (cfg.OUTPUT_DIR).

    Returns:
        Dict mapping output file keys to their resolved Path objects.

    Raises:
        NotImplementedError: Until Phase 4 plans 04-02 and 04-03 are implemented.
    """
    raise NotImplementedError("Phase 4")
