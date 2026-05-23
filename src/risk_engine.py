"""Risk scoring engine for boon-academy-intervention.

Implements deterministic weighted risk scoring (pure function, no I/O).
Signature is LOCKED per STATE.md — all downstream phases depend on it.

Patterns applied (02-RESEARCH.md):
- Pattern 1: vectorized component computation (avoid row-level Python loops)
- Pattern 2: .apply() only for daily_session_series (list column, unavoidably per-row)
- Pattern 3: pd.cut with right=False for left-closed threshold intervals (D-06)
- Pattern 4: _days_since_last_note accepts today as parameter (freeze_time compatibility)
- Pattern 5: df.copy() at function entry (purity + df.attrs preservation, Pitfall 8)
"""
import logging

import numpy as np
import pandas as pd

from src import config as cfg

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Module-level private constants
# ------------------------------------------------------------------

_ACTION_BY_LEVEL: dict[str, str] = {
    "CRITICAL": "Contact parent immediately",
    "HIGH": "Schedule check-in this week",
    "MEDIUM": "Monitor closely",
    "LOW": "On track",
}

_RISK_BINS: list = [-np.inf, cfg.RISK_THRESHOLD_MEDIUM, cfg.RISK_THRESHOLD_HIGH, cfg.RISK_THRESHOLD_CRITICAL, np.inf]

_RISK_LABELS: list[str] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

_WINDOW_DAYS: int = 14          # D-01/D-02 fixed denominator

_PRACTICE_CAP: float = 15.0    # D-02 cap — 15 questions/day

_NOTES_MAX_DAYS: int = 30      # D-04 cap — 30 days max penalty

_TREND_NEUTRAL: float = 50.0   # D-03 fallback for series with < 3 values


# ------------------------------------------------------------------
# Private helper functions
# ------------------------------------------------------------------

def _attendance_component(df: pd.DataFrame) -> pd.Series:
    """D-01: attendance risk component — 0 (perfect) to 100 (zero attendance)."""
    return ((1 - df["attendance_days"].astype(float) / _WINDOW_DAYS) * 100).clip(0, 100)


def _practice_component(df: pd.DataFrame) -> pd.Series:
    """D-02: practice risk component — 0 (cap met) to 100 (zero practice)."""
    avg = df["practice_total_q"].astype(float) / _WINDOW_DAYS
    return ((1 - (avg / _PRACTICE_CAP)).clip(lower=0) * 100).clip(0, 100)


def _trend_component_and_direction(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """D-03 + D-07: trend component (float) and direction label (string) from daily_session_series.

    Uses .apply for the list column (unavoidably per-row). Guards against NaN series (Pitfall 4)
    and short series (< 3 values). Returns (component_series, direction_series).
    """

    def _compute(series: object) -> tuple[float, str]:
        """Inner per-row computation — returns (component, direction)."""
        if not isinstance(series, list) or len(series) < 3:
            return (_TREND_NEUTRAL, "stable")
        last3 = float(np.nanmean(series[-3:]))
        first11 = float(np.nanmean(series[:11]))
        if last3 < first11:
            return (100.0, "declining")
        elif last3 > first11:
            return (0.0, "improving")
        else:
            return (0.0, "stable")

    results = df["daily_session_series"].apply(_compute)
    component = pd.Series([r[0] for r in results], index=df.index, dtype=float)
    direction = pd.Series([r[1] for r in results], index=df.index, dtype=pd.StringDtype())
    return component, direction


def _days_since_last_note(df: pd.DataFrame, today: pd.Timestamp) -> pd.Series:
    """D-04 helper: days elapsed since latest_note_date, capped at 30 (NaT → 30).

    today is a parameter (not internal pd.Timestamp.now()) so tests can inject
    a fixed timestamp under @freeze_time (Assumption A2 in RESEARCH.md).
    """
    return (
        (today - df["latest_note_date"])
        .dt.days
        .fillna(_NOTES_MAX_DAYS)
        .clip(lower=0, upper=_NOTES_MAX_DAYS)
        .astype(float)
    )


def _notes_component(days_since: pd.Series) -> pd.Series:
    """D-04: notes risk component — 0 (note today) to 100 (no note in 30+ days)."""
    return (days_since.clip(upper=_NOTES_MAX_DAYS) / _NOTES_MAX_DAYS * 100).clip(0, 100)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic weighted risk scoring to the student DataFrame.

    Implements D-01 through D-09 (CONTEXT.md) and RISK-01 through RISK-08 (REQUIREMENTS.md).

    Columns added (11 total):

    RISK-07 domain columns:
      - cfg.COL_ATTENDANCE_RATE    (attendance_days / 14, float 0.0-1.0)
      - cfg.COL_AVG_PRACTICE       (practice_total_q / 14, float)
      - cfg.COL_TREND_DIR          (string: 'declining' / 'stable' / 'improving')
      - cfg.COL_DAYS_SINCE_NOTE    (float 0-30, NaT → 30)

    D-09 component columns (audit trail):
      - cfg.COL_ATTENDANCE_COMPONENT  (D-01, float 0-100)
      - cfg.COL_PRACTICE_COMPONENT    (D-02, float 0-100)
      - cfg.COL_TREND_COMPONENT       (D-03, float 0/50/100)
      - cfg.COL_NOTES_COMPONENT       (D-04, float 0-100)

    Score and classification:
      - cfg.COL_RISK_SCORE         (D-05 weighted sum, float 0-100, rounded to 2dp)
      - cfg.COL_RISK_LEVEL         (D-06 pd.cut, string: LOW/MEDIUM/HIGH/CRITICAL)
      - cfg.COL_RECOMMENDED_ACTION (D-08 rule-based label, string)

    Wall-clock note: _days_since_last_note depends on pd.Timestamp.now(). Use
    @freeze_time('YYYY-MM-DD') in tests to get deterministic results.

    Pure function — caller's DataFrame is never mutated. df.copy() at function entry
    ensures both column immutability and df.attrs preservation (Pitfall 8).

    Args:
        df: One-row-per-student DataFrame produced by ingestion.ingest().

    Returns:
        New DataFrame (df.copy() base) with all 11 columns added.
    """
    # Purity guarantee — preserves df.attrs in pandas 2.2.3 (Pitfall 8)
    df = df.copy()

    # Called ONCE here — never inside .apply (Pitfall 7)
    today = pd.Timestamp.now().normalize()

    # ------------------------------------------------------------------
    # RISK-07 domain columns
    # ------------------------------------------------------------------
    df[cfg.COL_ATTENDANCE_RATE] = df["attendance_days"].astype(float) / _WINDOW_DAYS
    df[cfg.COL_AVG_PRACTICE] = df["practice_total_q"].astype(float) / _WINDOW_DAYS
    df[cfg.COL_DAYS_SINCE_NOTE] = _days_since_last_note(df, today)

    # ------------------------------------------------------------------
    # D-09 component scores
    # ------------------------------------------------------------------
    df[cfg.COL_ATTENDANCE_COMPONENT] = _attendance_component(df)
    df[cfg.COL_PRACTICE_COMPONENT] = _practice_component(df)
    trend_c, trend_d = _trend_component_and_direction(df)
    df[cfg.COL_TREND_COMPONENT] = trend_c
    df[cfg.COL_TREND_DIR] = trend_d
    df[cfg.COL_NOTES_COMPONENT] = _notes_component(df[cfg.COL_DAYS_SINCE_NOTE])

    # ------------------------------------------------------------------
    # D-05: weighted risk score
    # ------------------------------------------------------------------
    df[cfg.COL_RISK_SCORE] = (
        df[cfg.COL_ATTENDANCE_COMPONENT] * cfg.WEIGHT_ATTENDANCE
        + df[cfg.COL_PRACTICE_COMPONENT] * cfg.WEIGHT_PRACTICE
        + df[cfg.COL_TREND_COMPONENT] * cfg.WEIGHT_TREND
        + df[cfg.COL_NOTES_COMPONENT] * cfg.WEIGHT_NOTES
    ).round(2).clip(0, 100)

    # ------------------------------------------------------------------
    # D-06: risk level via pd.cut (left-closed intervals, right=False)
    # ------------------------------------------------------------------
    df[cfg.COL_RISK_LEVEL] = pd.cut(
        df[cfg.COL_RISK_SCORE],
        bins=_RISK_BINS,
        labels=_RISK_LABELS,
        right=False,
    ).astype(pd.StringDtype())

    # ------------------------------------------------------------------
    # D-08: recommended action from rule-based lookup
    # ------------------------------------------------------------------
    df[cfg.COL_RECOMMENDED_ACTION] = df[cfg.COL_RISK_LEVEL].map(_ACTION_BY_LEVEL).astype(pd.StringDtype())

    # Aggregate log only — no per-student identifiers (Security V7 / PII discipline)
    logger.info(
        f"Scored {len(df)} students — "
        f"CRITICAL={(df[cfg.COL_RISK_LEVEL] == 'CRITICAL').sum()}, "
        f"HIGH={(df[cfg.COL_RISK_LEVEL] == 'HIGH').sum()}, "
        f"MEDIUM={(df[cfg.COL_RISK_LEVEL] == 'MEDIUM').sum()}, "
        f"LOW={(df[cfg.COL_RISK_LEVEL] == 'LOW').sum()}"
    )

    return df
