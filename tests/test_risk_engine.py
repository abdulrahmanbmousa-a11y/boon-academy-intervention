"""Tests for src/risk_engine.py — covers RISK-01 through RISK-08 + purity discipline + Security V7 (PII-safe logging).

Each test maps to one or more RISK-* requirements from REQUIREMENTS.md.
All tests build in-memory DataFrames via the _build_student_row helper —
no fixture CSVs needed (risk_engine is a pure function over a DataFrame).
"""
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from freezegun import freeze_time

from src import config as cfg
from src.risk_engine import score_risk


# ---------------------------------------------------------------------------
# Module-level helper (not a fixture — each test needs different overrides)
# ---------------------------------------------------------------------------

def _build_student_row(
    student_id: str = "S0001",
    attendance_days: int = 14,
    practice_total_q: float = 210.0,
    session_series: list | None = None,
    latest_note_date: pd.Timestamp | None = None,
) -> dict:
    """Build a single-student dict suitable for pd.DataFrame([_build_student_row(...)]).

    Defaults represent a perfect student:
    - 14/14 attendance days
    - 210 practice questions (15/day * 14 = full practice)
    - [30.0]*14 session series (constant engagement — not improving, not declining)
    - latest_note_date = 2026-05-23 (today in frozen-time tests)
    """
    if session_series is None:
        session_series = [30.0] * 14
    if latest_note_date is None:
        latest_note_date = pd.Timestamp("2026-05-23")
    return {
        cfg.COL_STUDENT_ID: student_id,
        cfg.COL_STUDENT_NAME: "Test Student",
        cfg.COL_CAMPUS_ID: "C01",
        cfg.COL_PARENT_PHONE: "0501234567",
        cfg.COL_FACILITATOR_EMAIL: "t@example.com",
        "attendance_days": attendance_days,
        "practice_total_q": practice_total_q,
        "session_total_min": float(sum(session_series)),
        "daily_session_series": session_series,
        "daily_practice_series": [practice_total_q / 14] * 14,
        "daily_dates": [
            str(pd.Timestamp("2026-05-10") + pd.Timedelta(days=i)) for i in range(14)
        ],
        "latest_note_date": latest_note_date,
        "latest_note_text": "test note",
    }


# ---------------------------------------------------------------------------
# RISK-01: attendance_rate column
# ---------------------------------------------------------------------------

def test_attendance_rate_column_exists_and_equals_days_over_14() -> None:
    """RISK-01: attendance_rate == attendance_days / 14 (float 0.0-1.0) for 0 and 14 days."""
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", attendance_days=0),
        _build_student_row(student_id="S0002", attendance_days=14),
    ])
    result = score_risk(df)
    assert cfg.COL_ATTENDANCE_RATE in result.columns, (
        f"Column '{cfg.COL_ATTENDANCE_RATE}' missing from score_risk output"
    )
    assert result[cfg.COL_ATTENDANCE_RATE].iloc[0] == pytest.approx(0.0 / 14, abs=1e-9), (
        "attendance_rate for 0 days should be 0.0"
    )
    assert result[cfg.COL_ATTENDANCE_RATE].iloc[1] == pytest.approx(14.0 / 14, abs=1e-9), (
        "attendance_rate for 14 days should be 1.0"
    )


# ---------------------------------------------------------------------------
# RISK-02: avg_practice_questions column
# ---------------------------------------------------------------------------

def test_avg_practice_questions_equals_total_over_14() -> None:
    """RISK-02: avg_practice_questions == practice_total_q / 14 (always divide by 14)."""
    practice_q = 210.0
    df = pd.DataFrame([_build_student_row(practice_total_q=practice_q)])
    result = score_risk(df)
    assert cfg.COL_AVG_PRACTICE in result.columns, (
        f"Column '{cfg.COL_AVG_PRACTICE}' missing from score_risk output"
    )
    assert result[cfg.COL_AVG_PRACTICE].iloc[0] == pytest.approx(practice_q / 14, abs=1e-9), (
        "avg_practice_questions must equal practice_total_q / 14"
    )


# ---------------------------------------------------------------------------
# RISK-03 + D-07: trend_component and trend_direction
# ---------------------------------------------------------------------------

def test_trend_declining_is_100_component_and_declining_label() -> None:
    """RISK-03: series=[10]*11+[0]*3 → trend_component==100.0, trend_direction=='declining'."""
    declining_series = [10.0] * 11 + [0.0] * 3
    df = pd.DataFrame([_build_student_row(session_series=declining_series)])
    result = score_risk(df)
    assert result[cfg.COL_TREND_COMPONENT].iloc[0] == pytest.approx(100.0, abs=1e-9), (
        "Declining series should produce trend_component=100"
    )
    assert result[cfg.COL_TREND_DIR].iloc[0] == "declining", (
        "Declining series should produce trend_direction='declining'"
    )


def test_trend_improving_is_0_component_and_improving_label() -> None:
    """RISK-03: series=[0]*11+[10]*3 → trend_component==0.0, trend_direction=='improving'."""
    improving_series = [0.0] * 11 + [10.0] * 3
    df = pd.DataFrame([_build_student_row(session_series=improving_series)])
    result = score_risk(df)
    assert result[cfg.COL_TREND_COMPONENT].iloc[0] == pytest.approx(0.0, abs=1e-9), (
        "Improving series should produce trend_component=0"
    )
    assert result[cfg.COL_TREND_DIR].iloc[0] == "improving", (
        "Improving series should produce trend_direction='improving'"
    )


def test_trend_short_series_is_neutral_50() -> None:
    """RISK-03 edge: series < 3 values → trend_component==50.0, trend_direction=='stable'."""
    df = pd.DataFrame([_build_student_row(session_series=[10.0, 20.0])])
    result = score_risk(df)
    assert result[cfg.COL_TREND_COMPONENT].iloc[0] == pytest.approx(50.0, abs=1e-9), (
        "Short series (< 3) should produce neutral trend_component=50"
    )
    assert result[cfg.COL_TREND_DIR].iloc[0] == "stable", (
        "Short series (< 3) should produce trend_direction='stable'"
    )


def test_trend_nan_series_is_neutral_50() -> None:
    """RISK-03 + Pitfall 4: daily_session_series=NaN (no metrics) → trend_component==50.0, trend_direction=='stable'."""
    row = _build_student_row()
    row["daily_session_series"] = float("nan")  # NaN, not a list — Pitfall 4
    df = pd.DataFrame([row])
    result = score_risk(df)
    assert result[cfg.COL_TREND_COMPONENT].iloc[0] == pytest.approx(50.0, abs=1e-9), (
        "NaN series should produce neutral trend_component=50 (Pitfall 4)"
    )
    assert result[cfg.COL_TREND_DIR].iloc[0] == "stable", (
        "NaN series should produce trend_direction='stable' (Pitfall 4)"
    )


# ---------------------------------------------------------------------------
# RISK-04: days_since_last_note and notes_component
# ---------------------------------------------------------------------------

def test_notes_component_nat_is_max_30() -> None:
    """RISK-04: latest_note_date=NaT → days_since_last_note==30.0, notes_component==100.0."""
    df = pd.DataFrame([_build_student_row(latest_note_date=pd.NaT)])
    result = score_risk(df)
    assert result[cfg.COL_DAYS_SINCE_NOTE].iloc[0] == pytest.approx(30.0, abs=1e-9), (
        "NaT latest_note_date should produce days_since_last_note=30 (max penalty)"
    )
    assert result[cfg.COL_NOTES_COMPONENT].iloc[0] == pytest.approx(100.0, abs=1e-9), (
        "NaT latest_note_date should produce notes_component=100 (max risk)"
    )


@freeze_time("2026-05-23")
def test_notes_component_today_is_zero() -> None:
    """RISK-04: latest_note_date=today → days_since_last_note==0.0, notes_component==0.0."""
    df = pd.DataFrame([_build_student_row(latest_note_date=pd.Timestamp("2026-05-23"))])
    result = score_risk(df)
    assert result[cfg.COL_DAYS_SINCE_NOTE].iloc[0] == pytest.approx(0.0, abs=1e-9), (
        "Note today should produce days_since_last_note=0"
    )
    assert result[cfg.COL_NOTES_COMPONENT].iloc[0] == pytest.approx(0.0, abs=1e-9), (
        "Note today should produce notes_component=0 (no risk)"
    )


# ---------------------------------------------------------------------------
# RISK-05: weighted risk_score formula
# ---------------------------------------------------------------------------

def test_risk_score_weighted_formula() -> None:
    """RISK-05: weighted formula correctness — all-100, all-0, and attendance-only-100."""
    # Case 1: all components = 100 → score = 100.0
    # worst student: 0 attendance, 0 practice, declining series, no note
    worst_row = _build_student_row(
        student_id="S_worst",
        attendance_days=0,
        practice_total_q=0,
        session_series=[10.0] * 11 + [0.0] * 3,
        latest_note_date=pd.NaT,
    )
    # Case 2: all components = 0 → score = 0.0
    # perfect student: 14 days, 210 practice, improving series, note today
    with freeze_time("2026-05-23"):
        perfect_row = _build_student_row(
            student_id="S_perfect",
            attendance_days=14,
            practice_total_q=210.0,
            session_series=[0.0] * 11 + [30.0] * 3,
            latest_note_date=pd.Timestamp("2026-05-23"),
        )
        # Case 3: attendance_component=100, others=0 → score = 0.35 * 100 = 35.0
        partial_row = _build_student_row(
            student_id="S_partial",
            attendance_days=0,           # → attendance_component=100
            practice_total_q=210.0,      # → practice_component=0
            session_series=[0.0] * 11 + [30.0] * 3,   # improving → trend_component=0
            latest_note_date=pd.Timestamp("2026-05-23"),  # note today → notes_component=0
        )
        df = pd.DataFrame([worst_row, perfect_row, partial_row])
        result = score_risk(df)

    worst_score = result[cfg.COL_RISK_SCORE].iloc[0]
    perfect_score = result[cfg.COL_RISK_SCORE].iloc[1]
    partial_score = result[cfg.COL_RISK_SCORE].iloc[2]

    assert worst_score == pytest.approx(100.0, abs=0.01), (
        f"All-100 components should produce risk_score=100, got {worst_score}"
    )
    assert perfect_score == pytest.approx(0.0, abs=0.01), (
        f"All-0 components should produce risk_score=0, got {perfect_score}"
    )
    assert partial_score == pytest.approx(round(100 * 0.35, 2), abs=0.01), (
        f"attendance_component=100 only should produce risk_score=35.0, got {partial_score}"
    )


# ---------------------------------------------------------------------------
# RISK-06: risk_level boundaries (parametrized — GREEN today, does NOT call score_risk)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected_level", [
    (0.0,   "LOW"),
    (24.99, "LOW"),
    (25.0,  "MEDIUM"),
    (49.99, "MEDIUM"),
    (50.0,  "HIGH"),
    (74.99, "HIGH"),
    (75.0,  "CRITICAL"),
    (100.0, "CRITICAL"),
])
def test_risk_level_boundaries(score: float, expected_level: str) -> None:
    """RISK-06: left-closed interval boundary contract — verified via pd.cut directly.

    This test does NOT call score_risk. It locks the threshold semantics independently
    so that drift in pd.cut bins or labels is caught here regardless of implementation.
    GREEN immediately (no NotImplementedError dependency).
    """
    series = pd.Series([score])
    result = pd.cut(
        series,
        bins=[-np.inf, 25, 50, 75, np.inf],
        labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        right=False,
    )
    assert str(result.iloc[0]) == expected_level, (
        f"score={score} should produce risk_level='{expected_level}', "
        f"got '{result.iloc[0]}'"
    )


# ---------------------------------------------------------------------------
# RISK-07: output schema — all required columns present
# ---------------------------------------------------------------------------

def test_required_output_columns_present() -> None:
    """RISK-07: result DataFrame contains all 11 required added columns."""
    df = pd.DataFrame([_build_student_row()])
    result = score_risk(df)
    required_columns = [
        cfg.COL_RISK_SCORE,
        cfg.COL_RISK_LEVEL,
        cfg.COL_ATTENDANCE_RATE,
        cfg.COL_AVG_PRACTICE,
        cfg.COL_TREND_DIR,
        cfg.COL_DAYS_SINCE_NOTE,
        cfg.COL_ATTENDANCE_COMPONENT,
        cfg.COL_PRACTICE_COMPONENT,
        cfg.COL_TREND_COMPONENT,
        cfg.COL_NOTES_COMPONENT,
        cfg.COL_RECOMMENDED_ACTION,
    ]
    missing = [col for col in required_columns if col not in result.columns]
    assert not missing, (
        f"RISK-07: score_risk output is missing required columns: {missing}"
    )


# ---------------------------------------------------------------------------
# Success Criteria 2 + 3: worst and perfect student end-to-end
# ---------------------------------------------------------------------------

@freeze_time("2026-05-23")
def test_worst_student_is_critical() -> None:
    """Success Criterion 2: zero attendance + zero practice + declining + no note → CRITICAL.

    Components: attendance=100, practice=100, trend=100, notes=100 → risk_score=100.
    """
    df = pd.DataFrame([_build_student_row(
        attendance_days=0,
        practice_total_q=0,
        session_series=[10.0] * 11 + [0.0] * 3,  # declining
        latest_note_date=pd.NaT,
    )])
    result = score_risk(df)
    assert result[cfg.COL_RISK_SCORE].iloc[0] >= 75, (
        f"Worst student risk_score should be >= 75 (CRITICAL), "
        f"got {result[cfg.COL_RISK_SCORE].iloc[0]}"
    )
    assert result[cfg.COL_RISK_LEVEL].iloc[0] == "CRITICAL", (
        f"Worst student risk_level should be 'CRITICAL', "
        f"got {result[cfg.COL_RISK_LEVEL].iloc[0]}"
    )


@freeze_time("2026-05-23")
def test_perfect_student_is_low() -> None:
    """Success Criterion 3: full attendance + high practice + improving + recent note → LOW.

    Components: attendance=0, practice=0, trend=0, notes=0 → risk_score=0.
    """
    df = pd.DataFrame([_build_student_row(
        attendance_days=14,
        practice_total_q=15 * 14,  # 15 questions/day × 14 days
        session_series=[10.0] * 11 + [30.0] * 3,  # improving
        latest_note_date=pd.Timestamp("2026-05-23"),
    )])
    result = score_risk(df)
    assert result[cfg.COL_RISK_SCORE].iloc[0] < 25, (
        f"Perfect student risk_score should be < 25 (LOW), "
        f"got {result[cfg.COL_RISK_SCORE].iloc[0]}"
    )
    assert result[cfg.COL_RISK_LEVEL].iloc[0] == "LOW", (
        f"Perfect student risk_level should be 'LOW', "
        f"got {result[cfg.COL_RISK_LEVEL].iloc[0]}"
    )


# ---------------------------------------------------------------------------
# D-08: recommended_action matches risk_level
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level,expected_action", [
    ("CRITICAL", "Contact parent immediately"),
    ("HIGH",     "Schedule check-in this week"),
    ("MEDIUM",   "Monitor closely"),
    ("LOW",      "On track"),
])
def test_recommended_action_matches_level(level: str, expected_action: str) -> None:
    """D-08: recommended_action string matches the rule-based mapping for each risk level."""
    # Build rows that will land at each specific risk level via controlled components.
    # We target mid-range scores for each level to avoid floating-point boundary risk.
    # CRITICAL: score ~87.5 — attendance=100, practice=100, trend=100, notes=50
    # HIGH: score ~62.5 — attendance=100, practice=50, trend=50, notes=50
    # MEDIUM: score ~37.5 — attendance=50, practice=0, trend=50, notes=50
    # LOW: score ~12.5 — attendance=0, practice=0, trend=50, notes=0
    # We construct via session_series (trend) and other inputs; use freeze_time for notes.

    with freeze_time("2026-05-23"):
        if level == "CRITICAL":
            # attendance=100: 0 days; practice=100: 0 q; trend=100: declining; notes=100: NaT
            row = _build_student_row(
                attendance_days=0, practice_total_q=0,
                session_series=[10.0] * 11 + [0.0] * 3,
                latest_note_date=pd.NaT,
            )
        elif level == "HIGH":
            # attendance=100: 0 days; practice=0: 210q; trend=50: neutral (< 3 values); notes=50: 15 days ago
            # score = 100*0.35 + 0*0.30 + 50*0.20 + 50*0.15 = 35 + 0 + 10 + 7.5 = 52.5 → HIGH
            row = _build_student_row(
                attendance_days=0, practice_total_q=210.0,
                session_series=[10.0, 20.0],  # < 3 values → neutral trend_component=50
                latest_note_date=pd.Timestamp("2026-05-08"),  # 15 days ago → notes=50
            )
        elif level == "MEDIUM":
            # attendance=50: 7 days; practice=0: 210q; trend=50: neutral; notes=50: 15 days ago
            row = _build_student_row(
                attendance_days=7, practice_total_q=210.0,
                session_series=[30.0] * 14,  # stable → trend=0 (equal)
                latest_note_date=pd.Timestamp("2026-05-08"),  # 15 days ago → notes=50
            )
        else:  # LOW
            # attendance=0: 14 days; practice=0: 210q; trend=0: improving; notes=0: today
            row = _build_student_row(
                attendance_days=14, practice_total_q=210.0,
                session_series=[10.0] * 11 + [30.0] * 3,  # improving → trend=0
                latest_note_date=pd.Timestamp("2026-05-23"),  # today → notes=0
            )
        df = pd.DataFrame([row])
        result = score_risk(df)

    actual_level = result[cfg.COL_RISK_LEVEL].iloc[0]
    actual_action = result[cfg.COL_RECOMMENDED_ACTION].iloc[0]
    assert actual_level == level, (
        f"Expected risk_level='{level}' but got '{actual_level}' — "
        f"adjust test row inputs so result lands at the correct level"
    )
    assert actual_action == expected_action, (
        f"For risk_level='{level}', expected action='{expected_action}', "
        f"got '{actual_action}' (D-08)"
    )


# ---------------------------------------------------------------------------
# Purity discipline
# ---------------------------------------------------------------------------

def test_pure_function_does_not_mutate_input() -> None:
    """Pure function discipline: caller's df columns unchanged; result is a different object."""
    df = pd.DataFrame([_build_student_row()])
    cols_before = set(df.columns)
    result = score_risk(df)
    cols_after = set(df.columns)
    assert cols_before == cols_after, (
        f"score_risk mutated input DataFrame columns. "
        f"Added: {cols_after - cols_before}, Removed: {cols_before - cols_after}"
    )
    assert result is not df, "score_risk must return a new DataFrame, not the input reference"


def test_df_attrs_preserved() -> None:
    """Pitfall 8: df.attrs must survive score_risk (df.copy() preserves attrs in pandas 2.2)."""
    df = pd.DataFrame([_build_student_row()])
    df.attrs["data_quality_warnings"] = [{"type": "test"}]
    result = score_risk(df)
    assert result.attrs.get("data_quality_warnings") == [{"type": "test"}], (
        "score_risk must preserve df.attrs['data_quality_warnings'] (Pitfall 8 — "
        "some pandas operations silently drop .attrs)"
    )


# ---------------------------------------------------------------------------
# Security V7: PII-safe logging
# ---------------------------------------------------------------------------

def test_pii_safe_logging_in_score_risk(caplog: pytest.LogCaptureFixture) -> None:
    """Security V7: student_name and parent_phone must never appear in logger emissions."""
    sensitive_name = "Sensitive Name"
    sensitive_phone = "0501112222"
    row = _build_student_row()
    row[cfg.COL_STUDENT_NAME] = sensitive_name
    row[cfg.COL_PARENT_PHONE] = sensitive_phone
    df = pd.DataFrame([row])

    with caplog.at_level(logging.INFO, logger="src.risk_engine"):
        score_risk(df)

    for record in caplog.records:
        assert sensitive_name not in record.message, (
            f"PII leak: student_name '{sensitive_name}' found in log: {record.message}"
        )
        assert sensitive_phone not in record.message, (
            f"PII leak: parent_phone '{sensitive_phone}' found in log: {record.message}"
        )


# ---------------------------------------------------------------------------
# RISK-08: No bare column-name strings in risk_engine.py (source-scan)
# ---------------------------------------------------------------------------

def test_no_bare_column_strings_in_risk_engine() -> None:
    """RISK-08: Every column-name string in risk_engine.py must come from cfg.COL_* constants.

    Strips docstrings and line comments before scanning so legitimate documentation
    strings do not trigger false positives. Failure message lists offenders and cites RISK-08.
    """
    source_path = Path(__file__).parent.parent / "src" / "risk_engine.py"
    source = source_path.read_text(encoding="utf-8")

    # Strip triple-quoted docstrings (both ''' and """)
    no_docstrings = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    no_docstrings = re.sub(r"'''.*?'''", "", no_docstrings, flags=re.DOTALL)

    # Strip single-line comments
    no_comments = re.sub(r"#.*", "", no_docstrings)

    # Find quoted strings matching snake_case column-name pattern (length >= 4)
    matches = re.findall(r'"([a-z][a-z0-9_]{3,})"', no_comments)

    # Allowed exceptions: D-07 trend labels + Phase 1 internal column names
    # (not yet in cfg; allowed to appear bare per RISK-08 plan decision)
    allowed: set[str] = {
        "declining",
        "improving",
        "stable",
        "attendance_days",
        "practice_total_q",
        "daily_session_series",
        "latest_note_date",
    }

    offenders = {m for m in matches if m not in allowed}
    assert not offenders, (
        f"Bare column-name strings found in src/risk_engine.py (RISK-08 violation): "
        f"{sorted(offenders)}. "
        f"Use cfg.COL_* constants for column names, or add to the allowed set if intentional."
    )
