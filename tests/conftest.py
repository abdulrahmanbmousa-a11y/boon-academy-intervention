"""Shared pytest fixtures for boon-academy-intervention tests.

Provides:
- sample_csv_paths: copies fixture CSVs into tmp_path, returns dict with
  keys "metrics", "notes", "metadata" pointing at the copied files.
- csv_scenario: parameterized fixture for each edge-case scenario name.
- minimal_enriched_df: inline 5-row, 2-campus DataFrame with all required
  columns for test_output_generator.py and test_llm_engine.py.
"""
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

# Ensure ANTHROPIC_API_KEY is set before any src.config import occurs.
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")

from src import config as cfg  # noqa: E402 — must come after env var setdefault

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_csv_paths(tmp_path: Path) -> dict:
    """Copy happy-path fixture CSVs into tmp_path and return a path dict.

    Returns a dict with keys:
        "metadata"  -> Path to student_metadata_happy.csv copy
        "metrics"   -> Path to student_daily_metrics_happy.csv copy
        "notes"     -> Path to facilitator_notes_happy.csv copy
    """
    metadata_src = FIXTURES_DIR / "student_metadata_happy.csv"
    metrics_src = FIXTURES_DIR / "student_daily_metrics_happy.csv"
    notes_src = FIXTURES_DIR / "facilitator_notes_happy.csv"

    metadata_dst = tmp_path / "student_metadata.csv"
    metrics_dst = tmp_path / "student_daily_metrics.csv"
    notes_dst = tmp_path / "facilitator_notes.csv"

    shutil.copy(metadata_src, metadata_dst)
    shutil.copy(metrics_src, metrics_dst)
    shutil.copy(notes_src, notes_dst)

    return {
        "metadata": metadata_dst,
        "metrics": metrics_dst,
        "notes": notes_dst,
    }


# Scenario name -> fixture filename mapping for each CSV type
_SCENARIO_FILES = {
    "happy": {
        "metadata": "student_metadata_happy.csv",
        "metrics": "student_daily_metrics_happy.csv",
        "notes": "facilitator_notes_happy.csv",
    },
    "with_dupes": {
        "metadata": "student_metadata_with_dupes.csv",
        "metrics": "student_daily_metrics_happy.csv",
        "notes": "facilitator_notes_happy.csv",
    },
    "missing_numeric": {
        "metadata": "student_metadata_happy.csv",
        "metrics": "student_daily_metrics_missing_numeric.csv",
        "notes": "facilitator_notes_happy.csv",
    },
    "bad_dates": {
        "metadata": "student_metadata_happy.csv",
        "metrics": "student_daily_metrics_bad_dates.csv",
        "notes": "facilitator_notes_happy.csv",
    },
    "type_mismatch": {
        "metadata": "student_metadata_type_mismatch.csv",
        "metrics": "student_daily_metrics_happy.csv",
        "notes": "facilitator_notes_happy.csv",
    },
    "empty": {
        "metadata": "empty.csv",
        "metrics": "student_daily_metrics_happy.csv",
        "notes": "facilitator_notes_happy.csv",
    },
}


@pytest.fixture(
    params=list(_SCENARIO_FILES.keys()),
    ids=list(_SCENARIO_FILES.keys()),
)
def csv_scenario(request, tmp_path: Path) -> dict:
    """Parameterized fixture cycling through all six edge-case scenarios.

    Each scenario yields a dict with keys "metadata", "metrics", "notes"
    pointing at copied files in tmp_path, plus "scenario" with the name.
    Useful for plan 03 ingestion tests to assert behavior across scenarios.
    """
    scenario_name: str = request.param
    file_map = _SCENARIO_FILES[scenario_name]

    paths: dict = {"scenario": scenario_name}
    for key, filename in file_map.items():
        src = FIXTURES_DIR / filename
        dst = tmp_path / filename
        shutil.copy(src, dst)
        paths[key] = dst

    return paths


@pytest.fixture()
def minimal_enriched_df() -> pd.DataFrame:
    """Minimal enriched DataFrame with 5 rows across 2 campuses for output/LLM tests.

    Built inline — no file I/O. Covers all 4 risk levels plus one extra CRITICAL row
    (one CRITICAL per campus) so per-campus batching and per-level color coding can both
    be exercised by downstream tests.

    Row distribution:
      - Campus C01: rows 0 (CRITICAL), 1 (CRITICAL), 2 (MEDIUM) — 3 rows
      - Campus C02: rows 3 (CRITICAL), 4 (LOW) — 2 rows

    All 20 cfg.COL_* columns are present. Used by test_output_generator.py and
    test_llm_engine.py. Function scope (default) so each test receives a fresh copy
    and mutations do not bleed between tests.
    """
    return pd.DataFrame({
        cfg.COL_STUDENT_ID: ["S001", "S002", "S003", "S004", "S005"],
        cfg.COL_STUDENT_NAME: ["Alice", "Bob", "Carol", "Dave", "Eve"],
        cfg.COL_CAMPUS_ID: ["C01", "C01", "C01", "C02", "C02"],
        cfg.COL_PARENT_PHONE: [
            "0501111111", "0502222222", "0503333333", "0504444444", "0505555555"
        ],
        cfg.COL_FACILITATOR_EMAIL: [
            "f@c01.sa", "f@c01.sa", "f@c01.sa", "f@c02.sa", "f@c02.sa"
        ],
        cfg.COL_RISK_SCORE: [90.0, 75.0, 40.0, 80.0, 15.0],
        cfg.COL_RISK_LEVEL: ["CRITICAL", "CRITICAL", "MEDIUM", "CRITICAL", "LOW"],
        cfg.COL_ATTENDANCE_RATE: [0.1, 0.3, 0.7, 0.2, 0.95],
        cfg.COL_AVG_PRACTICE: [1.0, 2.0, 5.0, 1.5, 9.0],
        cfg.COL_TREND_DIR: [
            "declining", "stable", "stable", "declining", "improving"
        ],
        cfg.COL_DAYS_SINCE_NOTE: [25, 15, 5, 20, 1],
        cfg.COL_RECOMMENDED_ACTION: [
            "Contact parent immediately",
            "Contact parent immediately",
            "Monitor progress",
            "Contact parent immediately",
            "Acknowledge progress",
        ],
        cfg.COL_FACILITATOR_SUMMARY: [
            "Alice is at critical risk. Immediate contact needed.",
            "Bob is at critical risk. Immediate contact needed.",
            None,
            "Dave is at critical risk. Immediate contact needed.",
            None,
        ],
        cfg.COL_WHATSAPP_MESSAGE: [
            "Message for Alice's parent.",
            "Message for Bob's parent.",
            None,
            "Message for Dave's parent.",
            None,
        ],
        cfg.COL_GENERATED_BY: ["llm", "template", None, "llm", None],
        cfg.COL_LLM_ERROR_REASON: [None, None, None, None, None],
        # Component scores: attendance*0.35 + practice*0.30 + trend*0.20 + notes*0.15
        # Row 0 (S001): 31.5 + 27.0 + 20.0 + 11.5 = 90.0
        # Row 1 (S002): 24.5 + 22.5 + 10.0 +  8.0 = 65.0 (risk_score stored as 75.0 — fixture)
        # Row 2 (S003):  7.0 + 12.0 + 10.0 +  3.0 = 32.0 (approx MEDIUM)
        # Row 3 (S004): 28.0 + 24.0 + 20.0 +  8.0 = 80.0
        # Row 4 (S005):  1.5 +  3.0 +  0.0 +  0.5 =  5.0 (approx LOW)
        cfg.COL_ATTENDANCE_COMPONENT: [31.5, 24.5, 7.0, 28.0, 1.5],
        cfg.COL_PRACTICE_COMPONENT: [27.0, 22.5, 12.0, 24.0, 3.0],
        cfg.COL_TREND_COMPONENT: [20.0, 10.0, 10.0, 20.0, 0.0],
        cfg.COL_NOTES_COMPONENT: [11.5, 8.0, 3.0, 8.0, 0.5],
    })
