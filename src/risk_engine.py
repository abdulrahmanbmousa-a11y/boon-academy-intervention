"""Risk scoring engine stub for boon-academy-intervention.

Phase 2 will implement deterministic weighted risk scoring (pure function, no I/O).
Signature is LOCKED per STATE.md — all downstream phases depend on it.
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic weighted risk scoring to the student DataFrame.

    Phase 2 implementation: computes COL_RISK_SCORE, COL_RISK_LEVEL, and
    COL_RECOMMENDED_ACTION for each student using weight constants from config.py.
    Pure function — no I/O, no side effects.

    Args:
        df: One-row-per-student DataFrame produced by ingestion.ingest().

    Returns:
        DataFrame with COL_RISK_SCORE, COL_RISK_LEVEL, COL_RECOMMENDED_ACTION columns added.

    Raises:
        NotImplementedError: Until Phase 2 is implemented.
    """
    raise NotImplementedError("Phase 2")
