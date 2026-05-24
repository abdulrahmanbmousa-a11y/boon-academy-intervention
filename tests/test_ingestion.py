"""Tests for src/ingestion.py — covers DATA-02 through DATA-08.

Each test maps to one or more DATA-* requirements from REQUIREMENTS.md.
All tests use committed fixture CSVs under tests/fixtures/ (immutable inputs).
"""
import logging
import pathlib

import pandas as pd
import pytest

from src import config as cfg
from src.ingestion import ingest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# DATA-02: dtype preservation
# ---------------------------------------------------------------------------

def test_phone_stays_string(sample_csv_paths: dict) -> None:
    """DATA-02: parent_phone must be loaded as StringDtype, never promoted to int/float."""
    df = ingest(sample_csv_paths)
    assert df[cfg.COL_PARENT_PHONE].dtype == pd.StringDtype(), (
        f"Expected StringDtype for parent_phone, got {df[cfg.COL_PARENT_PHONE].dtype}"
    )
    # Every non-null phone must start with "0" (leading-zero preservation — Pitfall #3)
    non_null_phones = df[cfg.COL_PARENT_PHONE].dropna()
    assert all(str(p).startswith("0") for p in non_null_phones), (
        "One or more parent_phone values lost leading zero — dtype coercion bug"
    )


def test_student_id_is_string(sample_csv_paths: dict) -> None:
    """DATA-02: student_id must be loaded as StringDtype, never inferred as int/float."""
    df = ingest(sample_csv_paths)
    assert df[cfg.COL_STUDENT_ID].dtype == pd.StringDtype(), (
        f"Expected StringDtype for student_id, got {df[cfg.COL_STUDENT_ID].dtype}"
    )


# ---------------------------------------------------------------------------
# DATA-03: missing numeric imputation
# ---------------------------------------------------------------------------

def test_missing_values_filled_with_zero(sample_csv_paths: dict) -> None:
    """DATA-03 / TEST-02: Missing session_attended_min / practice_questions must be filled with 0."""
    data_paths = {
        "metadata": FIXTURES_DIR / "student_metadata_happy.csv",
        "metrics": FIXTURES_DIR / "student_daily_metrics_missing_numeric.csv",
        "notes": FIXTURES_DIR / "facilitator_notes_happy.csv",
    }
    df = ingest(data_paths)

    # No NaN in aggregated totals after fill
    assert df["session_total_min"].notna().all(), "session_total_min has NaN after imputation"
    assert df["practice_total_q"].notna().all(), "practice_total_q has NaN after imputation"

    # At least one missing_numeric warning must have been recorded
    warnings = df.attrs.get("data_quality_warnings", [])
    missing_types = [w["type"] for w in warnings]
    assert "missing_numeric" in missing_types, (
        "Expected at least one 'missing_numeric' warning in df.attrs['data_quality_warnings']"
    )


# ---------------------------------------------------------------------------
# DATA-04: duplicate student_id deduplication
# ---------------------------------------------------------------------------

def test_duplicate_student_ids_deduplicated(sample_csv_paths: dict) -> None:
    """DATA-04 / TEST-02: Duplicate student_id rows in metadata must be deduplicated (keep='last')."""
    data_paths = {
        "metadata": FIXTURES_DIR / "student_metadata_with_dupes.csv",
        "metrics": FIXTURES_DIR / "student_daily_metrics_happy.csv",
        "notes": FIXTURES_DIR / "facilitator_notes_happy.csv",
    }
    df = ingest(data_paths)

    assert df[cfg.COL_STUDENT_ID].is_unique, (
        "student_id column contains duplicates after deduplication"
    )

    # At least one duplicate_id warning must have been recorded
    warnings = df.attrs.get("data_quality_warnings", [])
    dup_types = [w["type"] for w in warnings]
    assert "duplicate_id" in dup_types, (
        "Expected at least one 'duplicate_id' warning in df.attrs['data_quality_warnings']"
    )


# ---------------------------------------------------------------------------
# DATA-05: type mismatch safe default
# ---------------------------------------------------------------------------

def test_type_mismatch_safe_default() -> None:
    """DATA-05: Type mismatches (e.g., 'abc' in parent_phone) must not raise; row is preserved."""
    data_paths = {
        "metadata": FIXTURES_DIR / "student_metadata_type_mismatch.csv",
        "metrics": FIXTURES_DIR / "student_daily_metrics_happy.csv",
        "notes": FIXTURES_DIR / "facilitator_notes_happy.csv",
    }
    # Must not raise — per-row error containment (DATA-08 spirit)
    df = ingest(data_paths)

    # The row with abc phone must still appear in output
    assert len(df) >= 1, "ingest returned empty DataFrame — rows were dropped instead of preserved"

    # student_id S0102 (the row with abc phone) must be present
    assert "S0102" in df[cfg.COL_STUDENT_ID].values, (
        "S0102 row (with abc phone) was dropped — expected it to be preserved"
    )


# ---------------------------------------------------------------------------
# DATA-06: one row per student after merge
# ---------------------------------------------------------------------------

def test_merge_one_row_per_student(sample_csv_paths: dict) -> None:
    """DATA-06: Merged DataFrame must have exactly one row per student_id from metadata."""
    df = ingest(sample_csv_paths)

    # Happy fixture has 5 unique students
    expected_count = 5
    assert len(df) == expected_count, (
        f"Expected {expected_count} rows, got {len(df)}"
    )
    assert df[cfg.COL_STUDENT_ID].is_unique, (
        "student_id is not unique after merge — duplicate rows present"
    )


# ---------------------------------------------------------------------------
# DATA-07: data_quality_warnings attached to DataFrame
# ---------------------------------------------------------------------------

def test_warnings_attached_to_df() -> None:
    """DATA-07: df.attrs['data_quality_warnings'] must be a list of dicts with a 'type' key."""
    data_paths = {
        "metadata": FIXTURES_DIR / "student_metadata_with_dupes.csv",
        "metrics": FIXTURES_DIR / "student_daily_metrics_missing_numeric.csv",
        "notes": FIXTURES_DIR / "facilitator_notes_happy.csv",
    }
    df = ingest(data_paths)

    assert "data_quality_warnings" in df.attrs, (
        "df.attrs does not contain 'data_quality_warnings'"
    )
    warnings = df.attrs["data_quality_warnings"]
    assert isinstance(warnings, list), (
        f"Expected list, got {type(warnings)}"
    )

    valid_types = {"missing_numeric", "duplicate_id", "bad_date", "missing_id", "type_mismatch"}
    for entry in warnings:
        assert isinstance(entry, dict), f"Warning entry is not a dict: {entry!r}"
        assert "type" in entry, f"Warning entry missing 'type' key: {entry!r}"
        assert entry["type"] in valid_types, (
            f"Unknown warning type {entry['type']!r}, expected one of {valid_types}"
        )


# ---------------------------------------------------------------------------
# DATA-08: bad records do not crash
# ---------------------------------------------------------------------------

def test_bad_date_format_safe_default() -> None:
    """DATA-08 / TEST-02: Unparseable dates in metrics must not crash ingest; bad_date warning emitted."""
    data_paths = {
        "metadata": FIXTURES_DIR / "student_metadata_happy.csv",
        "metrics": FIXTURES_DIR / "student_daily_metrics_bad_dates.csv",
        "notes": FIXTURES_DIR / "facilitator_notes_happy.csv",
    }
    # Must not raise
    df = ingest(data_paths)

    assert isinstance(df, pd.DataFrame), "ingest did not return a DataFrame"

    warnings = df.attrs.get("data_quality_warnings", [])
    bad_date_types = [w["type"] for w in warnings]
    assert "bad_date" in bad_date_types, (
        "Expected at least one 'bad_date' warning in df.attrs['data_quality_warnings']"
    )


def test_empty_csv_does_not_crash() -> None:
    """DATA-08 / TEST-02: All-empty inputs (header only) must return 0-row DataFrame without raising."""
    data_paths = {
        "metadata": FIXTURES_DIR / "empty.csv",
        "metrics": FIXTURES_DIR / "empty.csv",
        "notes": FIXTURES_DIR / "empty.csv",
    }
    # Must not raise
    df = ingest(data_paths)

    assert isinstance(df, pd.DataFrame), "ingest did not return a DataFrame"
    assert len(df) == 0, f"Expected 0 rows for all-empty input, got {len(df)}"


# ---------------------------------------------------------------------------
# Security V7: PII-safe logging assertion (caplog)
# ---------------------------------------------------------------------------

def test_pii_safe_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Security V7: logger.warning/info must include only student_id — never student_name/phone/note_text."""
    data_paths = {
        "metadata": FIXTURES_DIR / "student_metadata_with_dupes.csv",
        "metrics": FIXTURES_DIR / "student_daily_metrics_missing_numeric.csv",
        "notes": FIXTURES_DIR / "facilitator_notes_happy.csv",
    }

    with caplog.at_level(logging.WARNING, logger="src.ingestion"):
        df = ingest(data_paths)

    # Known PII values from the fixture files — must NOT appear in any log message
    pii_values = [
        "Student S0101",
        "Student S0102",
        "Student S0201",
        "Student S0202",
        "Student S0301",
        "0501234567",
        "0501345678",
        "0501456789",
        "0501567890",
        "0501678901",
        "Missed class today",
        "Strong performance this week",
        "Parent meeting scheduled",
        "Disengaged in group work",
        "Submitted late assignment",
    ]

    all_log_text = " ".join(record.message for record in caplog.records)
    for pii in pii_values:
        assert pii not in all_log_text, (
            f"PII value {pii!r} found in log output — Security V7 violation"
        )
