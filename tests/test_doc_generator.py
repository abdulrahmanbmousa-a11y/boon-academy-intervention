"""Tests for src/doc_generator.py — write_docs() PDF output."""
import os
from pathlib import Path

import pandas as pd
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")

from src import config as cfg
from src.doc_generator import write_docs


@pytest.fixture()
def minimal_df() -> pd.DataFrame:
    """Minimal 2-row DataFrame satisfying write_docs() column requirements."""
    return pd.DataFrame({
        cfg.COL_STUDENT_ID: ["S001", "S002"],
        cfg.COL_STUDENT_NAME: ["Alice", "Bob"],
        cfg.COL_CAMPUS_ID: ["C01", "C01"],
        cfg.COL_PARENT_PHONE: ["0501111111", "0502222222"],
        cfg.COL_FACILITATOR_EMAIL: ["f@c01.sa", "f@c01.sa"],
        cfg.COL_RISK_SCORE: [88.0, 45.0],
        cfg.COL_RISK_LEVEL: ["CRITICAL", "MEDIUM"],
        cfg.COL_ATTENDANCE_RATE: [0.2, 0.7],
        cfg.COL_AVG_PRACTICE: [1.0, 5.0],
        cfg.COL_TREND_DIR: ["declining", "stable"],
        cfg.COL_DAYS_SINCE_NOTE: [20, 4],
        cfg.COL_RECOMMENDED_ACTION: ["Contact parent", "Monitor"],
        cfg.COL_FACILITATOR_SUMMARY: ["Alice at risk", None],
        cfg.COL_WHATSAPP_MESSAGE: ["Msg for Alice", None],
        cfg.COL_GENERATED_BY: ["llm", None],
        cfg.COL_LLM_ERROR_REASON: [None, None],
        cfg.COL_ATTENDANCE_COMPONENT: [31.5, 7.0],
        cfg.COL_PRACTICE_COMPONENT: [27.0, 12.0],
        cfg.COL_TREND_COMPONENT: [20.0, 10.0],
        cfg.COL_NOTES_COMPONENT: [9.5, 3.0],
    })


@pytest.fixture()
def minimal_run_log() -> dict:
    """Minimal run_log dict for doc generation."""
    return {
        "run_timestamp": "2026-05-30T10:00:00+00:00",
        "students_processed": 2,
        "api_calls_made": 1,
        "tokens_used": {"input": 100, "output": 50},
        "errors_encountered": [],
        "fallbacks_triggered": 0,
        "data_quality_warnings": [],
    }


@pytest.fixture()
def doc_paths(minimal_df: pd.DataFrame, minimal_run_log: dict, tmp_path: Path) -> dict[str, Path]:
    """Run write_docs() into tmp_path and return the result dict."""
    return write_docs(minimal_df, minimal_run_log, tmp_path)


_EXPECTED_PDF_KEYS = [
    "analysis_pdf",
    "architecture",
    "security",
    "engineering_decisions",
    "data_handling",
    "scalability",
    "system_design",
    "alternatives",
]

_EXPECTED_ALL_KEYS = ["analysis_md"] + _EXPECTED_PDF_KEYS


def test_write_docs_returns_all_keys(doc_paths: dict[str, Path]) -> None:
    """write_docs() returns a dict containing all 9 expected keys."""
    for key in _EXPECTED_ALL_KEYS:
        assert key in doc_paths, f"Missing key {key!r} in write_docs() result: {list(doc_paths.keys())}"


def test_write_docs_all_files_exist(doc_paths: dict[str, Path]) -> None:
    """Every Path value returned by write_docs() points to a file that exists on disk."""
    for key, path in doc_paths.items():
        assert isinstance(path, Path), f"Expected Path for key {key!r}, got {type(path)}"
        assert path.exists(), f"File missing for key {key!r}: {path}"


def test_write_docs_pdf_files_have_pdf_magic(doc_paths: dict[str, Path]) -> None:
    """Every PDF output file starts with b'%PDF-' (valid PDF magic bytes)."""
    for key in _EXPECTED_PDF_KEYS:
        path = doc_paths[key]
        magic = path.read_bytes()[:5]
        assert magic == b"%PDF-", (
            f"Key {key!r} at {path.name}: expected PDF magic b'%PDF-', got {magic!r}"
        )


def test_write_docs_pdf_files_nonempty(doc_paths: dict[str, Path]) -> None:
    """Every PDF output file is larger than 1 KB — contains real content."""
    for key in _EXPECTED_PDF_KEYS:
        path = doc_paths[key]
        size = path.stat().st_size
        assert size > 1024, (
            f"Key {key!r} at {path.name}: expected > 1024 bytes, got {size} bytes"
        )


def test_write_docs_analysis_md_is_markdown(doc_paths: dict[str, Path]) -> None:
    """analysis.md ends in .md and contains the expected section headers."""
    path = doc_paths["analysis_md"]
    assert path.suffix == ".md", f"Expected .md extension, got {path.suffix}"
    content = path.read_text(encoding="utf-8")
    for section in ("## Diagnosis", "## What You Found", "## What You Built"):
        assert section in content, f"Expected section {section!r} in analysis.md"


def test_write_docs_pdf_filenames(doc_paths: dict[str, Path]) -> None:
    """Each PDF key maps to a file with the expected .pdf extension and filename."""
    expected_names = {
        "analysis_pdf": "analysis.pdf",
        "architecture": "architecture.pdf",
        "security": "security.pdf",
        "engineering_decisions": "engineering_decisions.pdf",
        "data_handling": "data_handling.pdf",
        "scalability": "scalability.pdf",
        "system_design": "system_design.pdf",
        "alternatives": "alternatives.pdf",
    }
    for key, expected_name in expected_names.items():
        actual_name = doc_paths[key].name
        assert actual_name == expected_name, (
            f"Key {key!r}: expected filename {expected_name!r}, got {actual_name!r}"
        )


def test_write_docs_creates_docs_dir(
    minimal_df: pd.DataFrame, minimal_run_log: dict, tmp_path: Path
) -> None:
    """write_docs() creates a non-existent docs_dir without error."""
    nested = tmp_path / "deep" / "docs"
    assert not nested.exists()
    result = write_docs(minimal_df, minimal_run_log, nested)
    assert nested.exists()
    assert len(result) == 9
