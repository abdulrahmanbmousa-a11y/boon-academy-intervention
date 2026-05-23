"""Tests for src/output_generator.py — private helper functions.

Covers _write_whatsapp_csv (OUT-03) and _write_run_log (OUT-06).
Each helper is tested independently using tmp_path for isolation.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from src import config as cfg
from src.output_generator import _write_whatsapp_csv, _write_run_log


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Minimal DataFrame with 4 rows covering all risk levels.

    Columns match the full enriched DataFrame schema including LLM outputs.
    """
    return pd.DataFrame(
        {
            cfg.COL_STUDENT_ID: ["S001", "S002", "S003", "S004"],
            cfg.COL_STUDENT_NAME: ["Alice", "Bob", "Carol", "Dave"],
            cfg.COL_PARENT_PHONE: ["0501234567", "0502345678", "0503456789", "0504567890"],
            cfg.COL_FACILITATOR_EMAIL: [
                "fac1@boon.sa",
                "fac1@boon.sa",
                "fac2@boon.sa",
                "fac2@boon.sa",
            ],
            cfg.COL_CAMPUS_ID: ["ALPHA", "ALPHA", "BETA", "BETA"],
            cfg.COL_RISK_LEVEL: ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            cfg.COL_WHATSAPP_MESSAGE: [
                "Message for Alice",
                "Message for Bob",
                "",
                "",
            ],
            cfg.COL_GENERATED_BY: ["llm", "template", "", ""],
        }
    )


@pytest.fixture
def sample_run_log() -> dict:
    """Minimal run_log dict matching main.py schema (D-06)."""
    return {
        "run_timestamp": "2026-01-01T00:00:00+00:00",
        "students_processed": 10,
        "api_calls_made": 2,
        "tokens_used": {"input": 100, "output": 50},
        "errors_encountered": [],
        "fallbacks_triggered": 0,
        "data_quality_warnings": [],
    }


# ---------------------------------------------------------------------------
# _write_whatsapp_csv tests
# ---------------------------------------------------------------------------


def test_whatsapp_csv_only_critical_high(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    """CSV output contains only CRITICAL and HIGH rows; MEDIUM and LOW are filtered out."""
    path = _write_whatsapp_csv(sample_df, tmp_path)
    result = pd.read_csv(path, dtype=str)
    assert set(result[cfg.COL_RISK_LEVEL].unique()) <= {"CRITICAL", "HIGH"}, (
        f"Expected only CRITICAL/HIGH in CSV, got: {result[cfg.COL_RISK_LEVEL].unique()}"
    )
    assert len(result) == 2, f"Expected 2 rows (CRITICAL+HIGH), got {len(result)}"


def test_whatsapp_csv_columns(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    """CSV has exactly the required 8 columns in the specified order."""
    path = _write_whatsapp_csv(sample_df, tmp_path)
    result = pd.read_csv(path, dtype=str)
    expected_cols = [
        cfg.COL_STUDENT_ID,
        cfg.COL_STUDENT_NAME,
        cfg.COL_PARENT_PHONE,
        cfg.COL_FACILITATOR_EMAIL,
        cfg.COL_CAMPUS_ID,
        cfg.COL_RISK_LEVEL,
        cfg.COL_WHATSAPP_MESSAGE,
        cfg.COL_GENERATED_BY,
    ]
    assert list(result.columns) == expected_cols, (
        f"Column mismatch.\nExpected: {expected_cols}\nGot:      {list(result.columns)}"
    )


def test_whatsapp_csv_encoding_bom(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    """File bytes start with UTF-8 BOM (b'\\xef\\xbb\\xbf') for Excel compatibility."""
    path = _write_whatsapp_csv(sample_df, tmp_path)
    raw_bytes = path.read_bytes()
    assert raw_bytes[:3] == b"\xef\xbb\xbf", (
        f"Expected UTF-8 BOM at start of file, got: {raw_bytes[:6]!r}"
    )


def test_whatsapp_csv_returns_path(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    """Return value is a Path object pointing to the written file."""
    result = _write_whatsapp_csv(sample_df, tmp_path)
    assert isinstance(result, Path), f"Expected Path, got {type(result)}"
    assert result.exists(), f"Returned path does not exist: {result}"
    assert result.name == "whatsapp_messages.csv"


# ---------------------------------------------------------------------------
# _write_run_log tests
# ---------------------------------------------------------------------------


def test_run_log_keys(sample_run_log: dict, tmp_path: Path) -> None:
    """JSON output contains all 7 required top-level keys from the run_log schema."""
    path = _write_run_log(sample_run_log, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    required_keys = {
        "run_timestamp",
        "students_processed",
        "api_calls_made",
        "tokens_used",
        "errors_encountered",
        "fallbacks_triggered",
        "data_quality_warnings",
    }
    missing = required_keys - set(data.keys())
    assert not missing, f"Missing keys in run_log.json: {missing}"


def test_run_log_returns_path(sample_run_log: dict, tmp_path: Path) -> None:
    """Return value is a Path object pointing to the written JSON file."""
    result = _write_run_log(sample_run_log, tmp_path)
    assert isinstance(result, Path), f"Expected Path, got {type(result)}"
    assert result.exists(), f"Returned path does not exist: {result}"
    assert result.name == "run_log.json"


def test_run_log_default_str_handles_non_serializable(tmp_path: Path) -> None:
    """run_log containing a datetime object serializes without raising TypeError."""
    import datetime

    run_log_with_datetime = {
        "run_timestamp": datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        "students_processed": 5,
        "api_calls_made": 1,
        "tokens_used": {"input": 50, "output": 25},
        "errors_encountered": [],
        "fallbacks_triggered": 0,
        "data_quality_warnings": [],
    }
    # Must not raise TypeError — default=str handles datetime objects
    path = _write_run_log(run_log_with_datetime, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    # datetime was serialized as a string — confirm it is readable
    assert isinstance(data["run_timestamp"], str), (
        f"Expected run_timestamp as str, got {type(data['run_timestamp'])}"
    )
