"""Tests for src/generate_data.py — TDD RED phase.

All 7 tests verify the deterministic synthetic data generator satisfies:
- D-01: 3 CSV files, 300 students x 20 campuses x 14 days
- D-02: numpy.random.default_rng(42) reproducibility (byte-identical across runs)
- D-03: 5% missing numeric, 3% duplicate IDs edge cases injected
- Pitfall #3: parent_phone leading zero preserved

Tests use monkeypatch.setattr(cfg, 'DATA_DIR', tmp_path) to isolate output
from the real data/ directory (T-02-05 threat mitigation).
"""
import hashlib
import os

import pandas as pd
import pytest

# Ensure API key is set before config import
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")

from src import config as cfg  # noqa: E402
from src import generate_data  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_generator(monkeypatch, tmp_path):
    """Patch DATA_DIR to tmp_path, run main(), return tmp_path."""
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    generate_data.main()
    return tmp_path


# ---------------------------------------------------------------------------
# Tests — D-01
# ---------------------------------------------------------------------------

def test_three_files_created(monkeypatch, tmp_path):
    """D-01: main() writes exactly 3 CSV files to DATA_DIR."""
    out_dir = _run_generator(monkeypatch, tmp_path)
    files = sorted(p.name for p in out_dir.iterdir())
    assert files == [
        "facilitator_notes.csv",
        "student_daily_metrics.csv",
        "student_metadata.csv",
    ], f"Unexpected files in DATA_DIR: {files}"


def test_metadata_row_count_300(monkeypatch, tmp_path):
    """D-01: student_metadata.csv has exactly 300 unique student_ids.

    Total row count may exceed 300 due to ~3% duplicate injection (D-03),
    but unique student_ids must be exactly 300 (20 campuses x 15 students).
    """
    out_dir = _run_generator(monkeypatch, tmp_path)
    df = pd.read_csv(
        out_dir / "student_metadata.csv",
        dtype={cfg.COL_STUDENT_ID: "str", cfg.COL_PARENT_PHONE: "str"},
    )
    unique_ids = df[cfg.COL_STUDENT_ID].nunique()
    assert unique_ids == 300, (
        f"Expected 300 unique student_ids (20 campuses x 15), got {unique_ids}"
    )
    # Total rows may be up to ~309 (3% dupes on 300 = ~9 extra rows)
    assert len(df) <= 320, f"Too many total rows: {len(df)} (expected <= 320)"
    assert len(df) >= 300, f"Too few total rows: {len(df)} (expected >= 300)"


def test_metrics_approximate_row_count(monkeypatch, tmp_path):
    """D-01: student_daily_metrics.csv has between 3990 and 4410 data rows.

    Base: 300 students x 14 days = 4200 rows; ±5% tolerance for edge cases.
    """
    out_dir = _run_generator(monkeypatch, tmp_path)
    df = pd.read_csv(
        out_dir / "student_daily_metrics.csv",
        dtype={cfg.COL_STUDENT_ID: "str"},
    )
    row_count = len(df)
    assert 3990 <= row_count <= 4410, (
        f"Metrics row count {row_count} outside expected range [3990, 4410]"
    )


def test_campus_count(monkeypatch, tmp_path):
    """D-01: student_metadata.csv has exactly 20 unique campus_ids."""
    out_dir = _run_generator(monkeypatch, tmp_path)
    df = pd.read_csv(
        out_dir / "student_metadata.csv",
        dtype={cfg.COL_STUDENT_ID: "str", cfg.COL_PARENT_PHONE: "str"},
    )
    campus_count = df[cfg.COL_CAMPUS_ID].nunique()
    assert campus_count == 20, (
        f"Expected 20 unique campus_ids (N_CAMPUSES=20), got {campus_count}"
    )


# ---------------------------------------------------------------------------
# Tests — D-02 (determinism)
# ---------------------------------------------------------------------------

def test_deterministic_across_runs(monkeypatch, tmp_path):
    """D-02: Running main() twice with SEED=42 produces byte-identical student_metadata.csv.

    Uses a second tmp_path-like directory to avoid file collision.
    Validates that np.random.default_rng(42) produces reproducible output.
    """
    import tempfile
    from pathlib import Path

    # First run
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    generate_data.main()
    hash1 = hashlib.sha256(
        (tmp_path / "student_metadata.csv").read_bytes()
    ).hexdigest()

    # Second run into a separate directory
    with tempfile.TemporaryDirectory() as td2:
        second_dir = Path(td2)
        monkeypatch.setattr(cfg, "DATA_DIR", second_dir)
        generate_data.main()
        hash2 = hashlib.sha256(
            (second_dir / "student_metadata.csv").read_bytes()
        ).hexdigest()

    assert hash1 == hash2, (
        f"Non-deterministic output detected!\n  Run 1: {hash1}\n  Run 2: {hash2}\n"
        "Ensure generate_data.py uses np.random.default_rng(SEED) not global np.random.seed."
    )


# ---------------------------------------------------------------------------
# Tests — Pitfall #3 (leading zero on parent_phone)
# ---------------------------------------------------------------------------

def test_phone_format(monkeypatch, tmp_path):
    """Pitfall #3: Every parent_phone string starts with '0' (leading zero preserved).

    Ensures dtype='str' in read_csv keeps the leading zero and the generator
    produces realistic Saudi/Gulf phone numbers starting with '0'.
    """
    out_dir = _run_generator(monkeypatch, tmp_path)
    df = pd.read_csv(
        out_dir / "student_metadata.csv",
        dtype={cfg.COL_STUDENT_ID: "str", cfg.COL_PARENT_PHONE: "str"},
    )
    phones = df[cfg.COL_PARENT_PHONE].dropna()
    bad = phones[~phones.str.startswith("0")]
    assert len(bad) == 0, (
        f"{len(bad)} phone numbers do not start with '0': {bad.tolist()[:5]}"
    )


# ---------------------------------------------------------------------------
# Tests — D-03 (edge case injection)
# ---------------------------------------------------------------------------

def test_edge_cases_injected(monkeypatch, tmp_path):
    """D-03: Verify both duplicate student_ids and blank numeric cells are injected.

    - student_metadata.csv must have at least 1 duplicate student_id (3% of 300 ~= 9)
    - student_daily_metrics.csv must have at least 1 blank session_attended_min cell
    """
    out_dir = _run_generator(monkeypatch, tmp_path)

    # Check duplicate student_ids in metadata
    meta_df = pd.read_csv(
        out_dir / "student_metadata.csv",
        dtype={cfg.COL_STUDENT_ID: "str", cfg.COL_PARENT_PHONE: "str"},
    )
    id_counts = meta_df[cfg.COL_STUDENT_ID].value_counts()
    dupes = id_counts[id_counts > 1]
    assert len(dupes) >= 1, (
        f"No duplicate student_ids found in metadata. "
        f"Expected at least 1 (3% of 300 = ~9). "
        f"Check inject_edge_cases() PCT_DUPLICATE_ID logic."
    )

    # Check missing numeric cells in metrics
    metrics_df = pd.read_csv(
        out_dir / "student_daily_metrics.csv",
        dtype={cfg.COL_STUDENT_ID: "str"},
    )
    blank_session = metrics_df[cfg.COL_SESSION_MIN].isna().sum()
    assert blank_session >= 1, (
        f"No blank session_attended_min cells found in metrics. "
        f"Expected at least ~210 (5% of ~4200). "
        f"Check inject_edge_cases() PCT_MISSING_NUMERIC logic."
    )
