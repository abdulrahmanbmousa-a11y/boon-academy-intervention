"""Configuration module for boon-academy-intervention.

Single source of truth for all environment variables, file paths, column name constants,
risk threshold constants, and weight constants. All downstream modules import from here.

D-07: ALL constants (column names + risk thresholds + weights) are defined here from day 1.
D-08: ONLY ANTHROPIC_API_KEY uses os.environ (fail-loud); paths use os.getenv with safe defaults.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # reads .env in cwd; does NOT override already-set env vars

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required secrets — fail loudly at import time if absent (D-08, Pitfall #7)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
# KeyError at import time if missing — intentional

# ---------------------------------------------------------------------------
# Optional paths — safe string defaults via os.getenv (D-08)
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
DOCS_DIR: Path = Path(os.getenv("DOCS_DIR", "docs"))

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
MAX_STUDENTS_PER_LLM_CALL: int = int(os.getenv("MAX_STUDENTS_PER_LLM_CALL", "10"))
LLM_MAX_WORKERS: int = int(os.getenv("LLM_MAX_WORKERS", "5"))

# LLM tunables — all env-overridable, safe defaults (D-09)
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
_llm_enabled_raw = os.getenv("LLM_ENABLED", "true").lower()
if _llm_enabled_raw not in ("true", "false"):
    raise ValueError(
        f"LLM_ENABLED must be 'true' or 'false', got {_llm_enabled_raw!r}"
    )
LLM_ENABLED: bool = _llm_enabled_raw == "true"
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "10"))

# ---------------------------------------------------------------------------
# Risk thresholds (D-07) — CRITICAL and HIGH are env-overridable; MEDIUM is fixed
# ---------------------------------------------------------------------------
RISK_THRESHOLD_CRITICAL: int = int(os.getenv("RISK_THRESHOLD_CRITICAL", "75"))
RISK_THRESHOLD_HIGH: int = int(os.getenv("RISK_THRESHOLD_HIGH", "50"))
RISK_THRESHOLD_MEDIUM: int = 25  # not env-overridable

# ---------------------------------------------------------------------------
# Weight constants (D-07) — must sum to 1.0
# ---------------------------------------------------------------------------
WEIGHT_ATTENDANCE: float = 0.35
WEIGHT_PRACTICE: float = 0.30
WEIGHT_TREND: float = 0.20
WEIGHT_NOTES: float = 0.15

# ---------------------------------------------------------------------------
# Column name constants (D-07) — all 17 columns across the 3 CSVs + derived
# ---------------------------------------------------------------------------

# Student metadata CSV
COL_STUDENT_ID: str = "student_id"
COL_STUDENT_NAME: str = "student_name"
COL_CAMPUS_ID: str = "campus_id"
COL_PARENT_PHONE: str = "parent_phone"
COL_FACILITATOR_EMAIL: str = "facilitator_email"

# Daily metrics CSV
COL_METRIC_DATE: str = "metric_date"
COL_SESSION_MIN: str = "session_attended_min"
COL_PRACTICE_Q: str = "practice_questions"

# Facilitator notes CSV
COL_NOTE_DATE: str = "note_date"
COL_NOTE_TEXT: str = "note_text"

# Derived columns (added by ingestion/risk_engine — frozen for Phase 2+)
COL_ATTENDANCE_RATE: str = "attendance_rate"
COL_AVG_PRACTICE: str = "avg_practice_questions"
COL_TREND_DIR: str = "trend_direction"
COL_DAYS_SINCE_NOTE: str = "days_since_last_note"
COL_RISK_SCORE: str = "risk_score"
COL_RISK_LEVEL: str = "risk_level"
COL_RECOMMENDED_ACTION: str = "recommended_action"

# D-09 component score columns (Phase 2)
COL_ATTENDANCE_COMPONENT: str = "attendance_component"
COL_PRACTICE_COMPONENT: str = "practice_component"
COL_TREND_COMPONENT: str = "trend_component"
COL_NOTES_COMPONENT: str = "notes_component"

# LLM output columns (Phase 3 — D-06)
COL_FACILITATOR_SUMMARY: str = "facilitator_summary"
COL_WHATSAPP_MESSAGE: str = "whatsapp_message"
COL_GENERATED_BY: str = "generated_by"
COL_LLM_ERROR_REASON: str = "llm_error_reason"

# ---------------------------------------------------------------------------
# Phase 4 output formatting constants (D-10)
# ---------------------------------------------------------------------------
COLOR_CRITICAL: str = "FFFFCCCC"   # light red  (8-char openpyxl ARGB, fill_type="solid")
COLOR_HIGH: str = "FFFFE5CC"       # light orange
COLOR_MEDIUM: str = "FFFFFFCC"     # light yellow
COLOR_LOW: str = "FFCCFFCC"        # light green
COLOR_HEADER: str = "FF1F4E79"     # dark navy (header row background)
FONT_WHITE: str = "FFFFFFFF"       # white (header row text color)

# Rank column (derived in _write_priority_list, not from risk_engine)
COL_RANK: str = "rank"

# OUT-01 column order — 12 columns, exact sequence for intervention_priority_list.xlsx
OUTPUT_COLS_PRIORITY: tuple[str, ...] = (
    COL_RANK, COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
    COL_FACILITATOR_EMAIL, COL_RISK_SCORE, COL_RISK_LEVEL,
    COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
    COL_DAYS_SINCE_NOTE, COL_RECOMMENDED_ACTION,
)

# OUT-02 campus dashboard columns — standard 12 + 3 LLM columns = 15 total (D-05)
OUTPUT_COLS_CAMPUS: tuple[str, ...] = OUTPUT_COLS_PRIORITY + (
    COL_FACILITATOR_SUMMARY, COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
)

# OUT-05 HTML dashboard display columns — 16 columns (D-02)
# Component score columns are required so the dashboard breakdown panel works (CR-01)
DISPLAY_COLS_DASHBOARD: tuple[str, ...] = (
    COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
    COL_RISK_SCORE, COL_RISK_LEVEL,
    COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
    COL_DAYS_SINCE_NOTE, COL_FACILITATOR_SUMMARY,
    COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
    COL_ATTENDANCE_COMPONENT, COL_PRACTICE_COMPONENT,
    COL_TREND_COMPONENT, COL_NOTES_COMPONENT,
)
