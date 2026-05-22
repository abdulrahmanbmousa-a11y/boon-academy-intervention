"""Shared pytest fixtures for boon-academy-intervention tests.

Provides:
- sample_csv_paths: copies fixture CSVs into tmp_path, returns dict with
  keys "metrics", "notes", "metadata" pointing at the copied files.
- csv_scenario: parameterized fixture for each edge-case scenario name.
"""
import os
import shutil
from pathlib import Path

import pytest

# Ensure ANTHROPIC_API_KEY is set before any src.config import occurs.
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")

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
