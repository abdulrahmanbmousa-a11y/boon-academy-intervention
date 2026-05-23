"""boon-academy-intervention pipeline orchestrator.

Pure coordination only — zero business logic here (CLAUDE.md rule).
Loads config, sets up logging, chains the four pipeline functions in order,
and manages the in-memory run_log dict (D-06: built throughout, written once at end).
"""
import logging
import sys
from datetime import datetime, timezone

from src import config as cfg
from src import llm_engine
from src import output_generator
from src.ingestion import ingest
from src.risk_engine import score_risk


def setup_logging() -> None:
    """Configure root logger for the pipeline run.

    Uses LOG_LEVEL from cfg (env-overridable). Outputs to stderr so stdout
    stays clean for any future scripted consumption.
    """
    logging.basicConfig(
        level=cfg.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main() -> int:
    """Run the full boon-academy-intervention pipeline.

    Orchestrates: ingest -> score_risk -> enrich_with_llm -> write_outputs.
    Scaffolds the in-memory run_log dict (D-05 schema) that is built throughout
    the run and written once at pipeline end via output_generator (D-06).

    Returns:
        0 on success; non-zero on unrecoverable error.
    """
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Starting boon-academy-intervention pipeline")

    # D-05: initialize full run_log schema in memory at pipeline start.
    # D-06: this dict is built throughout the run; written ONCE at the end via write_outputs.
    run_log: dict[str, object] = {
        "run_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "students_processed": 0,
        "api_calls_made": 0,
        "tokens_used": {"input": 0, "output": 0},
        "errors_encountered": [],
        "fallbacks_triggered": 0,
        "data_quality_warnings": [],
    }

    # Build data paths from cfg (all paths derive from cfg.DATA_DIR — INFRA-07)
    data_paths = {
        "metrics": cfg.DATA_DIR / "student_daily_metrics.csv",
        "notes": cfg.DATA_DIR / "facilitator_notes.csv",
        "metadata": cfg.DATA_DIR / "student_metadata.csv",
    }

    try:
        # Phase 1: Ingestion
        df = ingest(data_paths)
        run_log["students_processed"] = len(df)

        # Capture data quality warnings from ingestion (D-06: accumulate into run_log)
        run_log["data_quality_warnings"] = df.attrs.get("data_quality_warnings", [])
        logger.info("Ingested %d students", len(df))

        if df.empty:
            logger.error("Ingestion returned zero students — aborting pipeline")
            return 1

        # Phase 2: Risk scoring
        df = score_risk(df)
        logger.info("Scored %d students", len(df))

        # Phase 3: LLM enrichment
        df, llm_counts = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY)
        run_log["api_calls_made"] = llm_counts["api_calls_made"]
        run_log["tokens_used"] = llm_counts["tokens_used"]
        run_log["fallbacks_triggered"] = llm_counts["fallbacks_triggered"]
        logger.info(
            "LLM enrichment complete — api_calls=%d, fallbacks=%d",
            llm_counts["api_calls_made"],
            llm_counts["fallbacks_triggered"],
        )

        # Phase 4: Output generation — D-06: single write-at-end point
        paths = output_generator.write_outputs(df, cfg.OUTPUT_DIR, run_log)
        logger.info("Outputs written: %s", list(paths.keys()))

    except Exception:
        logger.exception("Unrecoverable pipeline error")
        run_log["errors_encountered"].append("unrecoverable_error")
        # Best-effort write of partial run_log
        try:
            cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_generator._write_run_log(run_log, cfg.OUTPUT_DIR)
        except Exception:
            pass
        return 1

    logger.info("Pipeline complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
