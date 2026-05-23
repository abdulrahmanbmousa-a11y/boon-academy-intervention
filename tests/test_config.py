"""Tests for src/config.py — env var loading, fail-loud behavior, and constant definitions.

Covers D-07 (all constants defined from day 1) and D-08 (only ANTHROPIC_API_KEY fails loudly).
"""
import importlib
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def clean_config_module():
    """Remove src.config from sys.modules before and after each test to force reimport."""
    sys.modules.pop("src.config", None)
    yield
    sys.modules.pop("src.config", None)


class TestFailLoudBehavior:
    """D-08: ANTHROPIC_API_KEY must raise KeyError at import time if absent."""

    def test_missing_api_key_raises(self, monkeypatch):
        """With ANTHROPIC_API_KEY removed from environment, importing src.config raises KeyError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(KeyError):
            import src.config  # noqa: F401
            importlib.reload(src.config)

    def test_api_key_loads_when_present(self, monkeypatch):
        """With ANTHROPIC_API_KEY set, src.config.ANTHROPIC_API_KEY equals that value."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-abc123")
        import src.config as cfg
        assert cfg.ANTHROPIC_API_KEY == "test-key-abc123"


class TestPathDefaults:
    """D-08: DATA_DIR/OUTPUT_DIR/DOCS_DIR use os.getenv with safe defaults (NOT fail-loud)."""

    def test_path_defaults(self, monkeypatch):
        """With DATA_DIR/OUTPUT_DIR/DOCS_DIR unset, config exposes expected Path defaults."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
        monkeypatch.delenv("DATA_DIR", raising=False)
        monkeypatch.delenv("OUTPUT_DIR", raising=False)
        monkeypatch.delenv("DOCS_DIR", raising=False)
        import src.config as cfg
        assert cfg.DATA_DIR == Path("data")
        assert cfg.OUTPUT_DIR == Path("outputs")
        assert cfg.DOCS_DIR == Path("docs")


class TestColumnConstants:
    """D-07: All 21 column constants defined in config.py from day 1 (17 from Phase 1 + 4 D-09 component columns from Phase 2)."""

    EXPECTED_COLUMN_CONSTANTS = [
        "COL_STUDENT_ID",
        "COL_STUDENT_NAME",
        "COL_CAMPUS_ID",
        "COL_PARENT_PHONE",
        "COL_FACILITATOR_EMAIL",
        "COL_METRIC_DATE",
        "COL_SESSION_MIN",
        "COL_PRACTICE_Q",
        "COL_NOTE_DATE",
        "COL_NOTE_TEXT",
        "COL_ATTENDANCE_RATE",
        "COL_AVG_PRACTICE",
        "COL_TREND_DIR",
        "COL_DAYS_SINCE_NOTE",
        "COL_RISK_SCORE",
        "COL_RISK_LEVEL",
        "COL_RECOMMENDED_ACTION",
        "COL_ATTENDANCE_COMPONENT",
        "COL_PRACTICE_COMPONENT",
        "COL_TREND_COMPONENT",
        "COL_NOTES_COMPONENT",
    ]

    def test_column_constants_defined(self, monkeypatch):
        """All 21 column name constants exist and are non-empty strings."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
        import src.config as cfg
        for name in self.EXPECTED_COLUMN_CONSTANTS:
            value = getattr(cfg, name)
            assert isinstance(value, str), f"{name} must be a str, got {type(value)}"
            assert len(value) > 0, f"{name} must be a non-empty string"


class TestRiskThresholdConstants:
    """D-07: Risk threshold constants defined with correct values."""

    def test_risk_threshold_constants(self, monkeypatch):
        """RISK_THRESHOLD_CRITICAL==75, RISK_THRESHOLD_HIGH==50, RISK_THRESHOLD_MEDIUM==25."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
        import src.config as cfg
        assert cfg.RISK_THRESHOLD_CRITICAL == 75
        assert cfg.RISK_THRESHOLD_HIGH == 50
        assert cfg.RISK_THRESHOLD_MEDIUM == 25


class TestWeightConstants:
    """D-07: Weight constants defined and sum to exactly 1.0."""

    def test_weight_constants_sum_to_one(self, monkeypatch):
        """WEIGHT_ATTENDANCE + WEIGHT_PRACTICE + WEIGHT_TREND + WEIGHT_NOTES == 1.0."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
        import src.config as cfg
        total = cfg.WEIGHT_ATTENDANCE + cfg.WEIGHT_PRACTICE + cfg.WEIGHT_TREND + cfg.WEIGHT_NOTES
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"
