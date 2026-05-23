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

# LLM tunables — all env-overridable, safe defaults (D-09)
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "30"))

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
