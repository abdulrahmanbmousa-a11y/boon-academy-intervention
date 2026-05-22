"""Output file generation stub for boon-academy-intervention.

Phase 4 will implement writing all 6 output files including run_log.json.
Signature is LOCKED per STATE.md — all downstream phases depend on it.

D-05 / D-06: Writes 6 output files including run_log.json built in-memory by main.py
per CONTEXT.md D-05 and D-06. The run_log dict is constructed throughout the pipeline
run and flushed once at the end via this module — no incremental writes anywhere.
"""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


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
        NotImplementedError: Until Phase 4 is implemented.
    """
    raise NotImplementedError("Phase 4")
