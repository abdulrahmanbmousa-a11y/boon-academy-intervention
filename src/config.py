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
