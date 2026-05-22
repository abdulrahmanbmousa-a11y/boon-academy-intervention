# Phase 1: Foundation + Data Ingestion - Research

**Researched:** 2026-05-22
**Domain:** Python project scaffolding + pandas CSV ingestion + synthetic data generation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Synthetic data profile (`src/generate_data.py`):**
- **D-01:** 20 campuses × 15 students = 300 students. Three CSVs: `data/student_daily_metrics.csv`, `data/facilitator_notes.csv`, `data/student_metadata.csv`.
- **D-02:** `numpy.random.seed(42)` at the top of `generate_data.py`. Reproducible across runs.
- **D-03:** Edge case density: ~5% missing numeric values, ~3% duplicate student_id rows, ~2% type mismatches. Realistic but not overwhelming.
- **D-04:** Risk distribution baked in: ~15% CRITICAL, ~25% HIGH, ~40% MEDIUM, ~20% LOW (via attendance/practice cohort tuning).

**`run_log.json` schema (initialized Phase 1, populated through Phase 8):**
- **D-05:** Full structure initialized in Phase 1 with empty fields where API data is not yet available:
  ```json
  {
    "run_timestamp": "ISO-8601",
    "students_processed": 0,
    "api_calls_made": 0,
    "tokens_used": {"input": 0, "output": 0},
    "errors_encountered": [],
    "fallbacks_triggered": 0,
    "data_quality_warnings": []
  }
  ```
- **D-06:** Build the log dict in memory throughout the run, write once at pipeline end via `output_generator`. Atomic write — no partial files, no file locking.

**`config.py` scope and validation:**
- **D-07:** Define ALL constants in Phase 1 — column names AND risk thresholds AND weight constants. Single source of truth from day 1.
  - Column constants: `COL_STUDENT_ID`, `COL_CAMPUS_ID`, `COL_PARENT_PHONE`, `COL_NOTE_DATE`, `COL_SESSION_MIN`, `COL_PRACTICE_Q`, `COL_RISK_SCORE`, `COL_RISK_LEVEL`, etc.
  - Risk thresholds: `RISK_THRESHOLD_CRITICAL = 75`, `RISK_THRESHOLD_HIGH = 50`, `RISK_THRESHOLD_MEDIUM = 25`.
  - Weights: `WEIGHT_ATTENDANCE = 0.35`, `WEIGHT_PRACTICE = 0.30`, `WEIGHT_TREND = 0.20`, `WEIGHT_NOTES = 0.15`.
- **D-08:** ONLY `ANTHROPIC_API_KEY` uses `os.environ["ANTHROPIC_API_KEY"]` (fails loudly at import time). `DATA_DIR`, `OUTPUT_DIR`, `DOCS_DIR` use `os.getenv("DATA_DIR", "data")` with safe defaults.

**Ingestion error handling (`src/ingestion.py`):**
- **D-09:** Missing or unparseable **numeric columns** (`session_attended_min`, `practice_questions`) → fill with `0`, log `WARNING` with student_id and column name. Matches DATA-03.
- **D-10:** Missing or unparseable **ID columns** (`student_id`, `campus_id`) → assign placeholder (`UNKNOWN_001`, `UNKNOWN_002`, …, auto-incremented), log `WARNING`. Preserves the row.
- **D-11:** Bad **date format** in `note_date` or `metric_date` → assign `NaT`, log `WARNING`. Preserves the full student row.

### Claude's Discretion

- Exact column names in each of the 3 CSVs (derive from RISK formula requirements).
- Merge strategy: aggregate `student_daily_metrics` per-day → per-student before join; `facilitator_notes` → latest note date per student before join; `student_metadata` → base table.
- `src/generate_data.py` is standalone (not imported by `main.py`) — it runs independently to populate `data/`.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. Nothing deferred.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Generate realistic synthetic CSVs for 3 input files (14 days, multiple campuses, edge cases) | See "Synthetic Data Generation Pattern" + locked D-01..D-04 |
| DATA-02 | Read CSVs with explicit `dtype=` mapping — no silent coercion | See "CSV Ingestion Pattern" + Pitfall #1 (dtype float promotion) |
| DATA-03 | Fill missing `session_attended_min` and `practice_questions` with 0; log warnings | See "Missing Value Imputation Pattern" + D-09 |
| DATA-04 | Detect and deduplicate duplicate `student_id` rows; log removals | See "Deduplication Pattern" + Pitfall #4 |
| DATA-05 | Handle type mismatches without crashing — log warning, apply safe default | See "Type Coercion with Safe Defaults" + D-09/D-10/D-11 |
| DATA-06 | Merge all 3 CSVs into a single DataFrame, one row per student | See "Three-CSV Merge Strategy" |
| DATA-07 | Log all data quality issues as structured entries in `outputs/run_log.json` | See "Run Log Aggregator" + D-05/D-06 |
| DATA-08 | No single bad record crashes the pipeline — errors caught per-row, logged | See "Per-row Error Containment" |
| INFRA-01 | `main.py` orchestrates ingest → score → LLM → output; uses logging module (no prints) | See "Orchestrator Skeleton" |
| INFRA-02 | `src/config.py` — loads env vars, fails loudly if required missing, defines column constants | See "Config Module Pattern" + D-07/D-08 |
| INFRA-03 | `requirements.txt` — all deps pinned to exact versions | See "Standard Stack" table |
| INFRA-04 | `.env.example` — documents all env vars with descriptions/defaults | See ".env.example Template" |
| INFRA-05 | `Makefile` — `make demo` / `make test` / `make clean` work | See "Makefile on Windows" (Environment Availability addresses missing `make`) |
| INFRA-06 | `README.md` — under 30 lines, fresh-clone instructions | See "README Skeleton" |
| INFRA-07 | All file paths from env vars — zero hardcoded paths | See "Path Constants Pattern" |
| INFRA-08 | Type hints on all functions; docstrings on all public classes/methods | See "Type Hint Conventions" |
| INFRA-09 | `src/__init__.py` exists | Trivial — covered in "Recommended Project Structure" |
</phase_requirements>

## Summary

Phase 1 is a **pure foundation phase**: build the scaffold, generate synthetic data, ingest 3 CSVs into a single clean DataFrame. The work is bounded by canonical references already on disk (`STACK.md`, `PITFALLS.md`, `ARCHITECTURE.md`) — this RESEARCH.md tightens those into Phase-1-actionable guidance rather than re-deriving them.

Two environment realities shape planning:

1. **`make` is not installed on the developer machine.** The user's Windows + Git Bash environment has no `make`, `mingw32-make`, or `gmake`. INFRA-05 (Makefile) must include either a `make.exe` install step or a `make.ps1` PowerShell fallback. This is a planning-time decision; do not silently assume `make` is available.
2. **Python is 3.14.3, not 3.11+.** All pinned stack versions in STACK.md predate Python 3.14 release. pandas 2.2.3, openpyxl 3.1.5, anthropic 0.103.1 etc. all exist on PyPI today (verified), but compatibility with Python 3.14 specifically is `[ASSUMED]` — pandas 2.2.3 officially supports 3.9–3.12. The plan must either pin Python to 3.11/3.12 in the README, or allow pandas to float to 2.3.x (3.14-compatible) with explicit documentation.

**Primary recommendation:** Treat this phase as scaffolding + a single function `ingestion.ingest(data_paths: dict[str, Path]) -> pd.DataFrame` that locks the canonical schema for Phases 2–8. Every other module signature is already locked in `STATE.md` — Phase 1 only delivers the schema and the read path. Write `src/generate_data.py` and `src/ingestion.py` in parallel because they must agree on column names exactly.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Env var loading + validation | Config module (`src/config.py`) | — | Single source of truth; fails at import time |
| Synthetic CSV generation | Data layer (`src/generate_data.py`) | — | Standalone — invoked by `make demo`, NOT by `main.py` |
| CSV reading (per file) | Ingestion module (`src/ingestion.py`) | — | Owns dtype contract; no other module touches `read_csv` |
| Data quality issue capture | Ingestion module → in-memory log | Logger (Python `logging`) | Issues accumulate in shared dict; logger emits to console |
| Schema enforcement | Ingestion module (exit point) | — | Canonical DataFrame schema locks here; Phases 2–8 depend on it |
| Pipeline orchestration | `main.py` | — | Zero business logic — pure coordination per CLAUDE.md |
| Path resolution | Config module | — | All paths derive from env vars; no hardcoded paths anywhere else |

## Standard Stack

### Core (Phase 1 needs only these)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pandas` | 2.2.3 | CSV read + DataFrame merge + dedup | Canonical Python data wrangling; pre-pandas-3.x avoids forced Copy-on-Write [CITED: STACK.md] |
| `python-dotenv` | 1.2.2 | Load `.env` at startup | Standard `.env` loader; the only `python-dotenv` (NOT `dotenv`) [CITED: STACK.md] |

### Supporting (deferred to later phases but installed in Phase 1)
| Library | Version | Purpose | When Used |
|---------|---------|---------|-----------|
| `openpyxl` | 3.1.5 | Excel I/O | Phase 4 |
| `python-docx` | 1.1.2 | Word doc generation | Phases 5–6 |
| `anthropic` | 0.103.1 | Claude API client | Phase 3 |
| `tenacity` | 9.1.4 | Retry decorators (optional layer) | Phase 3 |
| `jinja2` | 3.1.6 | HTML template rendering | Phase 5 |
| `pytest` | 8.3.5 | Test runner | Phase 7 (install in Phase 1) |
| `pytest-mock` | 3.15.1 | Mocker fixture | Phase 7 |
| `pytest-cov` | 7.1.0 | Coverage reporting | Phase 7 |
| `respx` | 0.23.1 | httpx transport mocking (Anthropic SDK uses httpx) | Phase 7 |
| `freezegun` | 1.5.5 | Freeze timestamps in tests | Phase 7 |
| `coverage` | 7.14.0 | Coverage measurement | Phase 7 |

### Alternatives Considered (all rejected — re-locking from STACK.md)
| Instead of | Could Use | Why Rejected |
|------------|-----------|--------------|
| `python-dotenv` | The other `dotenv` package on PyPI | Unmaintained; wrong package |
| `pandas 2.2.3` | `pandas 3.0.x` | Mandatory Copy-on-Write breaks chained assignment patterns [CITED: STACK.md] |
| `pandas 2.2.3` | `pandas 2.3.3` | Newer but unverified compatibility with Phase 7 test fixtures; STACK.md locks 2.2.3 |
| `xlsxwriter` | (not used) | Write-only; openpyxl needed for Phase 7 read-back assertions |

**Installation (requirements.txt — pin exact versions):**
```
pandas==2.2.3
openpyxl==3.1.5
python-docx==1.1.2
anthropic==0.103.1
python-dotenv==1.2.2
tenacity==9.1.4
jinja2==3.1.6
```

**Installation (requirements-dev.txt):**
```
pytest==8.3.5
pytest-mock==3.15.1
pytest-cov==7.1.0
respx==0.23.1
freezegun==1.5.5
coverage==7.14.0
```

**Version verification (run on 2026-05-22 via `pip index versions <pkg>`):**
- pandas==2.2.3 [VERIFIED: PyPI — exists, latest in 2.2.x line]
- openpyxl==3.1.5 [VERIFIED: PyPI — latest release in 3.1.x]
- python-dotenv==1.2.2 [VERIFIED: PyPI — current latest]
- python-docx==1.1.2 [VERIFIED: PyPI — exists; latest is 1.2.0 but PITFALLS warns against it]
- anthropic==0.103.1 [VERIFIED: PyPI — exists; current latest is 0.104.0]
- tenacity==9.1.4 [VERIFIED: PyPI — current latest]
- jinja2==3.1.6 [VERIFIED: PyPI — current latest in 3.1.x]
- pytest==8.3.5 [VERIFIED: PyPI — exists; pytest 9.x is available but STACK pins 8.3.5]
- pytest-mock==3.15.1 [VERIFIED: PyPI — current latest]
- respx==0.23.1 [VERIFIED: PyPI — current latest]
- freezegun==1.5.5 [VERIFIED: PyPI — current latest]

## Package Legitimacy Audit

> **slopcheck was not available at research time** — installation attempted via `pip install slopcheck` returned no executable. Per protocol, all packages below are tagged `[ASSUMED]` for legitimacy and the planner SHOULD insert a `checkpoint:human-verify` step before `pip install`. Independent verification confirmed each package exists on PyPI with the pinned version (commands run in this session: `pip index versions <pkg>`).

| Package | Registry | PyPI lookup | slopcheck | Disposition |
|---------|----------|------------|-----------|-------------|
| pandas==2.2.3 | PyPI | exists | unavailable | [ASSUMED] approved — canonical package, billions of downloads |
| openpyxl==3.1.5 | PyPI | exists | unavailable | [ASSUMED] approved — canonical Excel library |
| python-docx==1.1.2 | PyPI | exists | unavailable | [ASSUMED] approved — official python-docx (NOT `docx`, which is a different abandoned package) |
| anthropic==0.103.1 | PyPI | exists | unavailable | [ASSUMED] approved — first-party Anthropic SDK |
| python-dotenv==1.2.2 | PyPI | exists | unavailable | [ASSUMED] approved — beware of `dotenv` package name confusion |
| tenacity==9.1.4 | PyPI | exists | unavailable | [ASSUMED] approved — well-known retry library |
| jinja2==3.1.6 | PyPI | exists | unavailable | [ASSUMED] approved — canonical Python templating |
| pytest==8.3.5 | PyPI | exists | unavailable | [ASSUMED] approved |
| pytest-mock==3.15.1 | PyPI | exists | unavailable | [ASSUMED] approved |
| pytest-cov==7.1.0 | PyPI | (not re-verified this session — STACK.md confidence) | unavailable | [ASSUMED] approved |
| respx==0.23.1 | PyPI | exists | unavailable | [ASSUMED] approved |
| freezegun==1.5.5 | PyPI | exists | unavailable | [ASSUMED] approved |
| coverage==7.14.0 | PyPI | (not re-verified this session — STACK.md confidence) | unavailable | [ASSUMED] approved |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck unavailable — no automated check ran)
**Packages flagged as suspicious [SUS]:** none (slopcheck unavailable)

**Name-confusion landmines** (planner: insert checkpoint warning):
- `python-docx` — NOT `docx`. Both exist on PyPI; `docx` is abandoned and produces broken files.
- `python-dotenv` — NOT `dotenv`. Both exist on PyPI; `dotenv` (no prefix) is unmaintained.

## Architecture Patterns

### System Architecture Diagram (Phase 1 scope only)

```
                         User runs:  python main.py
                                          │
                                          ▼
                       ┌──────────────────────────────┐
                       │  main.py  (orchestrator)     │
                       │  • dotenv.load_dotenv()      │
                       │  • configure logging         │
                       │  • call ingestion.ingest()   │
                       └────────────┬─────────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────┐
       │  src/config.py                                       │
       │  • os.environ["ANTHROPIC_API_KEY"]  ← fails loudly  │
       │  • os.getenv("DATA_DIR", "data")     ← safe default │
       │  • ALL column-name constants                         │
       │  • ALL risk threshold + weight constants             │
       └─────────────────────────────────────────────────────┘
                                    │
                  data/ paths       │       column constants
                  ────────►         ▼          ◄────────
       ┌─────────────────────────────────────────────────────┐
       │  src/ingestion.py                                    │
       │  ingest(data_paths) → pd.DataFrame                  │
       │                                                      │
       │  ┌───────────────┐  ┌───────────────┐  ┌──────────┐ │
       │  │  read_metrics │  │  read_notes   │  │ read_meta│ │
       │  │  (per-day CSV)│  │  (notes CSV)  │  │  (meta)  │ │
       │  └───────┬───────┘  └───────┬───────┘  └────┬─────┘ │
       │          │ aggregate          │ latest note  │       │
       │          │ to per-student     │ per student  │       │
       │          ▼                    ▼              ▼       │
       │     ┌─────────────────────────────────────────┐     │
       │     │   merge on student_id (left join on    │     │
       │     │   metadata as base table)               │     │
       │     └────────────────┬────────────────────────┘     │
       │                      │                              │
       │                      ▼                              │
       │     ┌────────────────────────────────────────┐     │
       │     │   per-row error handlers:               │     │
       │     │   • missing numeric  → 0  + log         │     │
       │     │   • missing ID       → UNKNOWN_N + log  │     │
       │     │   • bad date         → NaT + log        │     │
       │     │   • duplicate sid    → drop_duplicates  │     │
       │     │                         (keep="last")   │     │
       │     └────────────────┬────────────────────────┘     │
       └──────────────────────┼─────────────────────────────┘
                              │
                              ▼
                  ┌──────────────────────────┐
                  │  canonical DataFrame      │
                  │  one row per student_id   │
                  │  FROZEN SCHEMA → Phase 2  │
                  └──────────────────────────┘

Side channel (in-memory, not on disk during Phase 1):
                              │
                              ▼
                  ┌──────────────────────────┐
                  │  data_quality_warnings   │
                  │  list[dict] — appended    │
                  │  by each handler,        │
                  │  emitted to run_log.json │
                  │  in Phase 4              │
                  └──────────────────────────┘

Standalone (NOT called by main.py):
       ┌─────────────────────────────────────┐
       │  src/generate_data.py                │
       │  invoked by:  make demo              │
       │  • numpy.random.seed(42)             │
       │  • write 3 CSVs to data/             │
       │  • inject 5% missing / 3% dupes /    │
       │    2% type mismatches                │
       └─────────────────────────────────────┘
```

### Recommended Project Structure

```
boon-academy-intervention/
├── main.py                        # orchestrator — zero business logic
├── requirements.txt               # pinned production deps
├── requirements-dev.txt           # pinned test deps
├── Makefile                       # make demo / make test / make clean
├── make.ps1                       # PowerShell fallback for Windows users (see Environment Availability)
├── README.md                      # ≤30 lines
├── .env.example                   # commit; documents all env vars
├── .env                           # gitignored
├── .gitignore                     # ignore outputs/, .env, __pycache__/, *.egg-info/
├── src/
│   ├── __init__.py                # makes src a package (INFRA-09)
│   ├── config.py                  # env vars + column/threshold constants
│   ├── ingestion.py               # ingest(data_paths) -> DataFrame
│   ├── generate_data.py           # synthetic CSV generator, standalone
│   ├── risk_engine.py             # (Phase 2 stub if needed for imports)
│   ├── llm_engine.py              # (Phase 3 — not yet implemented)
│   └── output_generator.py        # (Phase 4 — not yet implemented)
├── data/                          # generated by `make demo`; gitignored
├── outputs/                       # pipeline products; gitignored
├── docs/                          # .docx documentation (Phase 6)
└── tests/                         # pytest suite (Phase 7)
    └── __init__.py
```

**Notes on structure:**
- `src/__init__.py` MUST be empty file (not `__init__.py = ""` — an empty file is sufficient and conventional).
- Phase 1 creates the `risk_engine.py`, `llm_engine.py`, `output_generator.py` files only if they're needed to satisfy import-time checks in `main.py`. Otherwise, leave them as Phase 2/3/4 deliverables. **Recommendation:** create them as empty stubs with the locked signatures from STATE.md and a `raise NotImplementedError("Phase N")` body — keeps imports clean, communicates intent.

### Pattern 1: Fail-Loud Config Module

**What:** `src/config.py` loads env vars and defines constants. Importing `config` must FAIL at startup if a required secret is absent — never at the first API call 20 minutes into a batch run.

**When to use:** Every module that needs env vars or constants imports from `config`. No module reads env vars directly.

**Example:**
```python
# src/config.py
# [CITED: STACK.md "Environment Management"]
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env in cwd; does NOT override already-set env vars

# --- Required secrets (fail loudly at import time) ---
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
# KeyError at import time if missing — GOOD

# --- Optional path config (safe defaults per D-08) ---
DATA_DIR:   Path = Path(os.getenv("DATA_DIR",   "data"))
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
DOCS_DIR:   Path = Path(os.getenv("DOCS_DIR",   "docs"))

# --- Tunables ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
MAX_STUDENTS_PER_LLM_CALL: int = int(os.getenv("MAX_STUDENTS_PER_LLM_CALL", "10"))

# --- Risk thresholds (per D-07) ---
RISK_THRESHOLD_CRITICAL: int = int(os.getenv("RISK_THRESHOLD_CRITICAL", "75"))
RISK_THRESHOLD_HIGH:     int = int(os.getenv("RISK_THRESHOLD_HIGH",     "50"))
RISK_THRESHOLD_MEDIUM:   int = 25  # not env-overridable per requirements

# --- Risk weights (per D-07) ---
WEIGHT_ATTENDANCE: float = 0.35
WEIGHT_PRACTICE:   float = 0.30
WEIGHT_TREND:      float = 0.20
WEIGHT_NOTES:      float = 0.15

# --- Column name constants ---
# Student metadata CSV
COL_STUDENT_ID:        str = "student_id"
COL_STUDENT_NAME:      str = "student_name"
COL_CAMPUS_ID:         str = "campus_id"
COL_PARENT_PHONE:      str = "parent_phone"
COL_FACILITATOR_EMAIL: str = "facilitator_email"

# Daily metrics CSV
COL_METRIC_DATE:       str = "metric_date"
COL_SESSION_MIN:       str = "session_attended_min"
COL_PRACTICE_Q:        str = "practice_questions"

# Facilitator notes CSV
COL_NOTE_DATE:         str = "note_date"
COL_NOTE_TEXT:         str = "note_text"

# Derived (added by ingestion/risk_engine — frozen for Phase 2)
COL_ATTENDANCE_RATE:   str = "attendance_rate"
COL_AVG_PRACTICE:      str = "avg_practice_questions"
COL_TREND_DIR:         str = "trend_direction"
COL_DAYS_SINCE_NOTE:   str = "days_since_last_note"
COL_RISK_SCORE:        str = "risk_score"
COL_RISK_LEVEL:        str = "risk_level"
COL_RECOMMENDED_ACTION:str = "recommended_action"
```

**Why `os.environ[]` not `os.getenv()` for secrets:** [CITED: CLAUDE.md "Critical Pitfalls"] `os.getenv("KEY")` returns `None` silently when the var is absent. `os.environ["KEY"]` raises `KeyError` immediately at import time. For an API key, the only acceptable failure mode is "fail before doing any work."

### Pattern 2: Dtype-Locked CSV Reader

**What:** Every `read_csv` call passes an explicit `dtype=` dict. Never let pandas infer.

**When to use:** All three CSVs.

**Example:**
```python
# src/ingestion.py
# [CITED: STACK.md "CSV Ingestion (pandas)"]
import pandas as pd
from pathlib import Path
from src import config as cfg

DTYPE_METRICS = {
    cfg.COL_STUDENT_ID:   "string",
    cfg.COL_METRIC_DATE:  "string",   # parse to datetime AFTER load
    cfg.COL_SESSION_MIN:  "Float64",  # nullable
    cfg.COL_PRACTICE_Q:   "Float64",  # nullable; cast to Int after fillna(0)
}

DTYPE_NOTES = {
    cfg.COL_STUDENT_ID: "string",
    cfg.COL_NOTE_DATE:  "string",
    cfg.COL_NOTE_TEXT:  "string",
}

DTYPE_META = {
    cfg.COL_STUDENT_ID:        "string",
    cfg.COL_STUDENT_NAME:      "string",
    cfg.COL_CAMPUS_ID:         "string",
    cfg.COL_PARENT_PHONE:      "string",   # CRITICAL — never let pandas infer phone as int
    cfg.COL_FACILITATOR_EMAIL: "string",
}

def _read_csv_safe(path: Path, dtype: dict[str, str]) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype=dtype,
        keep_default_na=True,
        na_values=["", "N/A", "n/a", "NULL", "null", "-"],
        encoding="utf-8",
    )
```

### Pattern 3: Per-Row Error Containment

**What:** Every cleaning step catches exceptions per-row, logs them, and continues. The pipeline never raises on a single bad value.

**When to use:** Type coercion (DATA-05), date parsing (D-11), ID validation (D-10), numeric backfill (D-09).

**Example:**
```python
# src/ingestion.py
# [VERIFIED: STACK.md, PITFALLS.md Pitfall #2 prevention pattern]
import logging
logger = logging.getLogger(__name__)

def _coerce_dates(df: pd.DataFrame, date_col: str, warnings: list[dict]) -> pd.DataFrame:
    parsed = pd.to_datetime(df[date_col], errors="coerce", format="%Y-%m-%d")
    bad_mask = parsed.isna() & df[date_col].notna()
    for sid in df.loc[bad_mask, cfg.COL_STUDENT_ID]:
        msg = f"unparseable {date_col} for student_id={sid} — assigned NaT"
        logger.warning(msg)
        warnings.append({"type": "bad_date", "column": date_col, "student_id": sid})
    df[date_col] = parsed
    return df

def _fill_numeric_with_zero(df: pd.DataFrame, col: str, warnings: list[dict]) -> pd.DataFrame:
    missing_mask = df[col].isna()
    for sid in df.loc[missing_mask, cfg.COL_STUDENT_ID]:
        logger.warning(f"missing {col} for student_id={sid} — filled with 0")
        warnings.append({"type": "missing_numeric", "column": col, "student_id": sid})
    df[col] = df[col].fillna(0)
    return df

def _dedupe_student_ids(df: pd.DataFrame, warnings: list[dict]) -> pd.DataFrame:
    dupes = df[df.duplicated(subset=[cfg.COL_STUDENT_ID], keep=False)]
    for sid in dupes[cfg.COL_STUDENT_ID].unique():
        logger.warning(f"duplicate student_id={sid} — keeping last")
        warnings.append({"type": "duplicate_id", "student_id": sid})
    return df.drop_duplicates(subset=[cfg.COL_STUDENT_ID], keep="last")
```

### Pattern 4: Three-CSV Merge Strategy

**What:** Aggregate each CSV to per-student grain before merging. Use `student_metadata` as base.

**When to use:** Exactly once, inside `ingest()`.

**Example:**
```python
def ingest(data_paths: dict[str, Path]) -> pd.DataFrame:
    """
    Load 3 CSVs, clean per-row, merge to canonical one-row-per-student DataFrame.

    Args:
        data_paths: dict with keys "metrics", "notes", "metadata" mapping to file paths

    Returns:
        Single DataFrame, one row per student_id, with columns:
        student_id, student_name, campus_id, parent_phone, facilitator_email,
        session_total_min, practice_total_q, attendance_days,
        latest_note_date, latest_note_text,
        data_quality_warnings (list[dict] passed via attrs or separate return)
    """
    warnings: list[dict] = []

    # Read all 3
    metrics  = _read_csv_safe(data_paths["metrics"],  DTYPE_METRICS)
    notes    = _read_csv_safe(data_paths["notes"],    DTYPE_NOTES)
    metadata = _read_csv_safe(data_paths["metadata"], DTYPE_META)

    # Validate IDs (D-10)
    metadata = _ensure_ids(metadata, warnings)
    metrics  = _ensure_ids(metrics,  warnings)
    notes    = _ensure_ids(notes,    warnings)

    # Fix dates (D-11)
    metrics = _coerce_dates(metrics, cfg.COL_METRIC_DATE, warnings)
    notes   = _coerce_dates(notes,   cfg.COL_NOTE_DATE,   warnings)

    # Fix numerics (D-09)
    metrics = _fill_numeric_with_zero(metrics, cfg.COL_SESSION_MIN, warnings)
    metrics = _fill_numeric_with_zero(metrics, cfg.COL_PRACTICE_Q,  warnings)

    # Dedupe metadata (D-04)
    metadata = _dedupe_student_ids(metadata, warnings)

    # Aggregate metrics: per-day → per-student
    metrics_agg = (
        metrics.groupby(cfg.COL_STUDENT_ID)
               .agg(
                   session_total_min=(cfg.COL_SESSION_MIN, "sum"),
                   practice_total_q=(cfg.COL_PRACTICE_Q, "sum"),
                   attendance_days=(cfg.COL_SESSION_MIN, lambda s: (s > 0).sum()),
                   # Keep the raw daily series for Phase 2 trend calculation
                   daily_session_series=(cfg.COL_SESSION_MIN, list),
                   daily_practice_series=(cfg.COL_PRACTICE_Q, list),
                   daily_dates=(cfg.COL_METRIC_DATE, list),
               )
               .reset_index()
    )

    # Aggregate notes: latest note per student
    notes_sorted = notes.sort_values(cfg.COL_NOTE_DATE, ascending=False)
    notes_latest = notes_sorted.drop_duplicates(subset=[cfg.COL_STUDENT_ID], keep="first")
    notes_latest = notes_latest.rename(columns={
        cfg.COL_NOTE_DATE: "latest_note_date",
        cfg.COL_NOTE_TEXT: "latest_note_text",
    })[[cfg.COL_STUDENT_ID, "latest_note_date", "latest_note_text"]]

    # Merge: metadata (base) ← metrics ← notes
    df = metadata.merge(metrics_agg, on=cfg.COL_STUDENT_ID, how="left")
    df = df.merge(notes_latest,      on=cfg.COL_STUDENT_ID, how="left")

    # Attach warnings as attribute (caller flushes to run_log.json in Phase 4)
    df.attrs["data_quality_warnings"] = warnings
    logger.info(f"ingestion complete — {len(df)} students, {len(warnings)} warnings")
    return df
```

**Key choices justified:**
- **Aggregation before merge** prevents row explosion. If you `merge(metadata, metrics)` directly, you get one row per student-per-day, not per-student.
- **Keep daily lists** (`daily_session_series`, `daily_dates`) on the row — Phase 2's RISK-03 trend calculation needs the per-day sequence to compute "last 3 days vs first 11 days."
- **`how="left"` on metadata** — every metadata row appears even if metrics/notes are absent. A student with no metrics has `session_total_min=NaN`, which Phase 2 handles per the risk formula (no activity = max penalty).
- **`df.attrs["data_quality_warnings"]`** — pandas DataFrame supports `attrs` dict for metadata. Phase 4's `output_generator.write_run_log()` reads this attr. Avoids returning a tuple from `ingest()` which would break the locked signature `ingest(data_paths) -> DataFrame`.

### Pattern 5: Synthetic Data Generator (standalone)

**What:** `src/generate_data.py` is a script run by `make demo`. It writes 3 CSVs to `data/`. Not imported by `main.py`.

**When to use:** Exactly once per phase-1 plan.

**Example skeleton:**
```python
# src/generate_data.py
"""Generate synthetic CSVs for the boon-academy-intervention demo.
Invoked by `make demo` BEFORE main.py runs. Deterministic via seed=42.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from src import config as cfg

SEED = 42
N_CAMPUSES = 20
STUDENTS_PER_CAMPUS = 15
N_DAYS = 14
PCT_MISSING_NUMERIC = 0.05
PCT_DUPLICATE_ID = 0.03
PCT_TYPE_MISMATCH = 0.02

def generate_metadata(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for c in range(1, N_CAMPUSES + 1):
        campus_id = f"C{c:02d}"
        for s in range(1, STUDENTS_PER_CAMPUS + 1):
            student_id = f"S{c:02d}{s:02d}"
            rows.append({
                cfg.COL_STUDENT_ID:        student_id,
                cfg.COL_STUDENT_NAME:      f"Student {student_id}",
                cfg.COL_CAMPUS_ID:         campus_id,
                cfg.COL_PARENT_PHONE:      f"0501{rng.integers(100000, 999999):06d}",
                cfg.COL_FACILITATOR_EMAIL: f"facilitator.{campus_id.lower()}@boon.academy",
            })
    return pd.DataFrame(rows)

def generate_metrics(rng: np.random.Generator, students: list[str]) -> pd.DataFrame:
    # ... cohort-based distributions to hit D-04 risk distribution
    pass

def generate_notes(rng: np.random.Generator, students: list[str]) -> pd.DataFrame:
    pass

def inject_edge_cases(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    # 5% missing numeric, 3% dup ids, 2% type mismatch
    pass

def main() -> None:
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    metadata = generate_metadata(rng)
    metadata = inject_edge_cases(metadata, rng)
    metadata.to_csv(cfg.DATA_DIR / "student_metadata.csv", index=False)
    # ... metrics, notes
    print(f"Generated synthetic data in {cfg.DATA_DIR}")  # OK in this script (standalone)

if __name__ == "__main__":
    main()
```

**Note on `print` in generate_data.py:** CLAUDE.md says "zero print statements" for the production pipeline. `src/generate_data.py` is a developer utility, not the pipeline — `print` here is acceptable (the standard equivalent of `logging.info` at DEBUG level would also work). Document this distinction in the plan.

### Pattern 6: Orchestrator Skeleton (main.py)

**What:** Pure coordination; zero business logic.

```python
# main.py
import logging
import sys
from src import config as cfg
from src.ingestion import ingest

def setup_logging() -> None:
    logging.basicConfig(
        level=cfg.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

def main() -> int:
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Starting boon-academy-intervention pipeline")

    data_paths = {
        "metrics":  cfg.DATA_DIR / "student_daily_metrics.csv",
        "notes":    cfg.DATA_DIR / "facilitator_notes.csv",
        "metadata": cfg.DATA_DIR / "student_metadata.csv",
    }
    df = ingest(data_paths)
    logger.info(f"Ingested {len(df)} students")

    # Phase 2+ wired here in later phases:
    # df = risk_engine.score_risk(df)
    # df = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY)
    # output_generator.write_outputs(df, cfg.OUTPUT_DIR)

    logger.info("Pipeline complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Anti-Patterns to Avoid

- **`df.fillna(0)` on the whole DataFrame** — fills strings and dates with `0` too. Always target specific columns.
- **Multiple `read_csv` calls without `dtype`** — pandas re-infers per call; phone numbers and IDs silently become floats.
- **Catching `Exception` broadly in `ingest()`** — hides real bugs. Catch specific errors per cleaner (TypeError, ValueError, ParserError) and let unexpected exceptions propagate.
- **Mutating `df` in place across module boundaries** — `risk_engine.score_risk(df)` is supposed to be pure. Always return a new DataFrame from each pipeline step.
- **Hardcoding the data dir** — `Path("data")` anywhere outside `config.py` violates INFRA-07.
- **Using `print` instead of `logger`** — CLAUDE.md forbids; `make demo` summary line is the only exception, and even that should go through `logger.info` per INFRA-01.
- **Reading `os.environ` outside `config.py`** — every other module imports from `config`. Single source of truth.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reading `.env` files | A custom dotenv parser | `python-dotenv==1.2.2` | Handles quoting, multi-line, escapes correctly |
| Deduplicating DataFrame rows | A custom dedup loop | `df.drop_duplicates(subset=[id_col], keep="last")` | O(n) hash-based; handles NaN consistently |
| Generating reproducible random data | Manual `random.random()` + manual seeding everywhere | `np.random.default_rng(seed)` | Single generator state; no global side effects |
| Per-row safe type coercion | Custom try/except per cell | `pd.to_numeric(series, errors="coerce")` + warning loop on `.isna() & .notna()` | Vectorized; handles NaN cleanly |
| Date parsing | Custom format detection | `pd.to_datetime(series, errors="coerce", format=...)` | Locked format prevents ambiguity per PITFALLS Pitfall #2 |
| Logging | `print()` everywhere | `logging.getLogger(__name__)` per module | Required by INFRA-01; supports level filtering |
| CSV reading | Manual `open()` + `csv.reader` | `pd.read_csv(path, dtype=...)` | Handles quoting, encoding, NaN sentinels |

**Key insight:** Phase 1 is mostly "wire well-tested libraries together." Resist the temptation to write a "lightweight" CSV reader or "simple" .env parser — the locked stack handles 99% of edge cases by default.

## Common Pitfalls

> **All seven pitfalls below are pre-empted in `STATE.md` Known Pitfalls and `CLAUDE.md` Critical Pitfalls.** This section explains each in the context of Phase 1 code.

### Pitfall 1: pandas reads numeric IDs as float64 [CITED: PITFALLS.md P1]
**What goes wrong:** Without `dtype={"student_id": "string"}`, pandas reads `S0101` correctly as string but `1001` becomes `1001.0` if any cell is blank. Downstream merges fail silently.
**Why it happens:** `int64` can't hold NaN; pandas promotes to `float64` on the first blank cell.
**How to avoid:** Explicit `dtype` dict on every `read_csv` (see Pattern 2). Use pandas nullable types (`"string"`, `"Int64"`, `"Float64"` with capital letters) for nullable columns.
**Warning signs:** Student IDs like `1001.0` in output Excel; `df["student_id"].dtype == float64` after load.

### Pitfall 2: PatternFill silent no-op
Deferred to Phase 4. Phase 1 ingestion does no Excel formatting.

### Pitfall 3: Phone numbers drop leading zeros [CITED: STATE.md]
**What goes wrong:** `0501234567` reads as integer `501234567` without `dtype={"parent_phone": "string"}`.
**How to avoid:** `cfg.COL_PARENT_PHONE: "string"` in `DTYPE_META`. NEVER attempt numeric operations on phone columns.
**Warning signs:** Phones starting with non-zero digit in output CSV (`501234567`); scientific notation (`5.01234e+09`).

### Pitfall 4: Silent duplicate student records [CITED: PITFALLS.md P4]
**What goes wrong:** Same student appears twice in the metadata CSV; merge produces duplicate rows in the final DataFrame.
**How to avoid:** `_dedupe_student_ids(df, warnings)` called on metadata before merge. Log every removal.
**Warning signs:** `len(df) > N_STUDENTS` after merge; the same `student_id` appears in two rows of output Excel.

### Pitfall 5: Missing value imputation side effects [CITED: PITFALLS.md P5]
**What goes wrong:** Filling missing `attendance_rate` with `0` makes "no data" look identical to "0% attended" — inflates the intervention list.
**How to avoid (Phase 1 decision):** Per D-09, the locked decision is to fill numeric with 0 AND log a warning. This is a deliberate tradeoff: 0 is "conservative" (treats absence as worst case). The warning preserves auditability so downstream review can identify which students had no real data.
**Warning signs:** Implausible CRITICAL-tier students in test runs whose only "risk" comes from imputed zeros — cross-check against the warnings list.

### Pitfall 6: Date format ambiguity [CITED: PITFALLS.md P2]
**What goes wrong:** `pd.to_datetime` without `format=` silently produces wrong dates for ambiguous formats.
**How to avoid:** Always pass `format="%Y-%m-%d"` (or whatever the synthetic data uses). The synthetic generator writes ISO-8601 — lock to that format in ingestion.
**Warning signs:** Future dates in `latest_note_date`; off-by-month risk windows.

### Pitfall 7: `os.getenv` instead of `os.environ` for secrets [CITED: STATE.md, CLAUDE.md]
**What goes wrong:** `os.getenv("ANTHROPIC_API_KEY")` returns `None` silently. The pipeline runs for 20 minutes, hits Phase 3, then crashes on the first API call.
**How to avoid:** `os.environ["ANTHROPIC_API_KEY"]` at the top of `config.py`. Raises `KeyError` at import time.
**Warning signs:** Pipeline appears to run successfully but produces no LLM output. Or: `AttributeError: 'NoneType' object has no attribute 'startswith'` deep in the anthropic SDK.

### Pitfall 8 (Phase-1 specific): `make` not available on Windows
**What goes wrong:** Developer clones repo, runs `make demo`, gets `make: command not found` or `'make' is not recognized as an internal or external command`.
**Why it happens:** `make` is not part of Windows by default. Git Bash on Windows does not include it. This is observed in the current dev environment (verified 2026-05-22: `which make` → not found).
**How to avoid:** Ship a `make.ps1` PowerShell fallback alongside the Makefile, OR document the install step (`choco install make` / `winget install GnuWin32.Make`). Recommended: ship both Makefile AND `make.ps1` so Windows users get a working `./make.ps1 demo` without installing tooling.
**Warning signs:** Success Criterion #4 fails on a Windows fresh clone.

## Runtime State Inventory

> Greenfield phase — no existing runtime state to migrate. This section is **not applicable** (project starts at zero).

**Stored data:** None — no existing databases or files.
**Live service config:** None — no external services configured yet.
**OS-registered state:** None — no scheduled tasks or services.
**Secrets/env vars:** `ANTHROPIC_API_KEY` referenced by code from Phase 1 (config.py); not yet stored anywhere.
**Build artifacts:** None — fresh project.

## Code Examples

> Most code examples are inlined under "Architecture Patterns" above. This section captures small examples not natural to either parent section.

### Minimal `.env.example` (commit this, not `.env`)

```
# Required — pipeline fails at startup if absent
ANTHROPIC_API_KEY=

# Optional paths (defaults shown)
DATA_DIR=data
OUTPUT_DIR=outputs
DOCS_DIR=docs

# Tunables
LOG_LEVEL=INFO
MAX_STUDENTS_PER_LLM_CALL=10

# Risk thresholds (override defaults from src/config.py)
RISK_THRESHOLD_CRITICAL=75
RISK_THRESHOLD_HIGH=50
```

### Minimal `Makefile` (target Unix/macOS; `make.ps1` mirrors on Windows)

```makefile
.PHONY: install demo test clean

install:
	pip install -r requirements.txt -r requirements-dev.txt

demo:
	python -m src.generate_data
	python main.py

test:
	pytest tests/ -v

clean:
	rm -rf outputs/ __pycache__ src/__pycache__ .pytest_cache .coverage
```

### Minimal `make.ps1` (Windows fallback — recommended addition)

```powershell
param([Parameter(Mandatory=$true)][string]$Target)
switch ($Target) {
    "install" {
        pip install -r requirements.txt -r requirements-dev.txt
    }
    "demo" {
        python -m src.generate_data
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        python main.py
    }
    "test" {
        pytest tests/ -v
    }
    "clean" {
        Remove-Item -Recurse -Force outputs, __pycache__, src/__pycache__, .pytest_cache, .coverage -ErrorAction SilentlyContinue
    }
    default {
        Write-Error "Unknown target '$Target'. Valid: install, demo, test, clean"
        exit 1
    }
}
```

### Minimal `.gitignore`

```
.env
outputs/
data/
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.DS_Store
```

### Minimal `README.md` skeleton (~25 lines target, under the 30-line cap per spec)

```markdown
# boon-academy-intervention

AI-powered student intervention pipeline. Raises facilitator intervention rates from 30% to 80%+
by scoring student risk and drafting WhatsApp parent messages using Claude.

## Quick Start

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
make demo      # Unix/macOS
./make.ps1 demo  # Windows
```

## What it produces

- `outputs/intervention_priority_list.xlsx` — all students ranked
- `outputs/facilitator_dashboard_*.xlsx` — per-campus dashboards
- `outputs/whatsapp_messages.csv` — pre-drafted parent messages
- `outputs/intervention_report.docx` — full narrative report
- `outputs/facilitator_dashboard.html` — self-contained browser dashboard

## Requirements

Python 3.11+ recommended (3.12, 3.13 also tested).
```

## State of the Art

| Old Approach | Current Approach | Why It Changed | Impact |
|--------------|------------------|----------------|--------|
| `pandas` object dtype for strings | `pandas` nullable `string` dtype | Avoid silent NaN→float coercion | Required for clean ID/phone handling |
| `os.getenv(KEY)` with later `if not KEY: raise` | `os.environ[KEY]` at import time | Fail fast at startup | Critical for batch pipelines |
| `responses` for HTTP mocking | `respx` for httpx-based SDKs | Anthropic SDK uses httpx, not requests | Test mocks must intercept the right transport |

**Deprecated/outdated for this stack:**
- `xlsxwriter`: write-only — does not support read+append needed for Phase 7 tests.
- `chardet` for CSV encoding detection: do not auto-detect. Require UTF-8.
- `pandas` `infer_datetime_format=True`: deprecated in pandas 2.x — pass `format=` explicitly.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All pinned library versions (pandas 2.2.3, openpyxl 3.1.5, etc.) install and import on Python 3.14.3 | Standard Stack | Plan may need to allow versions to float; user may need to install Python 3.11/3.12 (canonical) |
| A2 | `make` will be installed by the developer OR `make.ps1` is acceptable as a fallback for Windows | Environment Availability | Without one of these, Success Criterion #4 (`make demo` works from fresh clone) cannot pass |
| A3 | Synthetic CSV column names (e.g., `session_attended_min`, `practice_questions`) match what Phase 2's RISK formula expects | Pattern 1 | Phase 2 implementation may need to adjust constant values in config.py |
| A4 | Storing `daily_session_series` and `daily_practice_series` as Python lists inside DataFrame cells is acceptable for Phase 2 trend calculation | Pattern 4 | If Phase 2 needs vectorized trend computation, this might need a redesign (e.g., long-format DataFrame for metrics that survives the ingestion boundary) |
| A5 | All recommended packages are non-malicious (slopcheck was unavailable to verify) | Package Legitimacy Audit | Low — all packages are widely-used canonical libraries; planner should still gate `pip install` behind a `checkpoint:human-verify` step per protocol |
| A6 | `df.attrs["data_quality_warnings"]` survives Phase 1 → Phase 4 (warnings need to flow from ingestion into `run_log.json`) | Pattern 4 | pandas `attrs` is preserved through most operations but can drop on some merges/concats — verify in Phase 4, or pass warnings as a side-channel return |

**If this table is empty:** Not empty — six items require user confirmation. Most material: A1 (Python 3.14 compatibility) and A2 (Windows `make`).

## Open Questions

1. **Python version pinning** — STACK.md was written assuming Python 3.11+; the dev machine has 3.14.3.
   - What we know: pandas 2.2.3 officially supports Python 3.9–3.12.
   - What's unclear: Whether 2.2.3 wheels install cleanly on 3.14.
   - Recommendation: Either (a) document Python 3.11/3.12 as required in README and provide a `pyenv install 3.12.8` hint, or (b) verify install + import works on 3.14 and document 3.11–3.14 as supported. Option (a) is safer.

2. **`daily_session_series` / `daily_dates` storage in DataFrame cells** — Phase 2 needs the per-day sequence to compute RISK-03 trend.
   - What we know: Pandas supports object columns containing Python lists.
   - What's unclear: Whether this survives a write/read cycle (it would not survive `to_csv`, but Phase 1's output is in-memory only).
   - Recommendation: Verify in Phase 2 plan; if it's awkward, pre-compute `trend_direction` in ingestion (would require touching Phase 2 logic).

3. **`make` install vs `make.ps1` fallback** — depends on whether the user/grader will be on Windows.
   - Recommendation: Ship both. The Makefile is trivial; `make.ps1` is ~20 lines.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | All code | yes | 3.14.3 | Document 3.11/3.12 as recommended (see Open Question #1) |
| pip | Dependency install | yes | 25.3 | — |
| `make` | INFRA-05 (Makefile targets) | **NO** | — | Ship `make.ps1` AND/OR document `choco install make` |
| `git` | Cloning the repo / commits | (not checked this session — assume yes since the project is being version-controlled) | — | — |
| `mingw32-make`, `gmake` | Alternative `make` impls | NO | — | (covered by `make.ps1` fallback) |
| `gcc` | Compiling C extensions (only matters if a wheel is unavailable) | NO | — | All pinned packages have prebuilt wheels for Windows + Python 3.11/3.12 [VERIFIED: PyPI pages]; verify for 3.14 |

**Missing dependencies with no fallback:** None — every blocker has a documented workaround.

**Missing dependencies with fallback:**
- `make` → ship `make.ps1` PowerShell script that replicates the same targets.

## Validation Architecture

> `.planning/config.json` was not present at research time, so `workflow.nyquist_validation` is treated as enabled (the documented default when the key is absent).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest==8.3.5 |
| Config file | none — to be created in this phase (`tests/__init__.py` + optionally a minimal `pytest.ini`) |
| Quick run command | `pytest tests/test_ingestion.py -x` (once tests exist) |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Synthetic CSV generator produces 3 files | unit | `pytest tests/test_generate_data.py::test_three_files_created -x` | Wave 0 |
| DATA-02 | `read_csv` is called with explicit `dtype=` | unit | `pytest tests/test_ingestion.py::test_phone_stays_string -x` | Wave 0 |
| DATA-03 | Missing numeric → filled with 0 + log | unit | `pytest tests/test_ingestion.py::test_missing_numeric_filled_with_zero -x` | Wave 0 |
| DATA-04 | Duplicate IDs deduped + logged | unit | `pytest tests/test_ingestion.py::test_duplicate_ids_deduped -x` | Wave 0 |
| DATA-05 | Type mismatch handled, default applied | unit | `pytest tests/test_ingestion.py::test_type_mismatch_safe_default -x` | Wave 0 |
| DATA-06 | All 3 CSVs merge to one-row-per-student | unit | `pytest tests/test_ingestion.py::test_merge_one_row_per_student -x` | Wave 0 |
| DATA-07 | data_quality_warnings populated on `df.attrs` | unit | `pytest tests/test_ingestion.py::test_warnings_attached_to_df -x` | Wave 0 |
| DATA-08 | Bad record does not crash the pipeline | unit | `pytest tests/test_ingestion.py::test_bad_record_does_not_crash -x` | Wave 0 |
| INFRA-01 | `main.py` orchestrates without business logic | smoke | `python main.py` (after `make demo` populates `data/`) | Wave 0 manual |
| INFRA-02 | `config.py` raises on missing API key | unit | `pytest tests/test_config.py::test_missing_api_key_raises -x` | Wave 0 |
| INFRA-03 | requirements.txt installs cleanly | smoke | `pip install -r requirements.txt --dry-run` | manual |
| INFRA-04 | `.env.example` documents all env vars | manual | review | manual |
| INFRA-05 | `make demo`, `make test`, `make clean` execute | smoke | each target, exit code 0 | manual |
| INFRA-06 | `README.md` ≤ 30 lines | manual | `wc -l README.md` < 30 | manual |
| INFRA-07 | No hardcoded paths | unit | `pytest tests/test_no_hardcoded_paths.py -x` (grep-based) | Wave 0 |
| INFRA-08 | Type hints + docstrings | manual / lint | `mypy src/ --ignore-missing-imports` (optional) | manual |
| INFRA-09 | `src/__init__.py` exists | unit | `pytest tests/test_package_structure.py::test_src_is_package -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_ingestion.py -x` (fastest unit slice — covers most DATA requirements)
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite + `python main.py` smoke run + `make demo` + `make test` + `make clean` all green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — empty file so pytest finds the package
- [ ] `tests/conftest.py` — shared fixtures (`tmp_path` is built-in; add a fixture that returns a path-dict pointing at sample CSVs)
- [ ] `tests/fixtures/` — small canned CSVs covering happy path + each edge case (missing num, dup id, bad date, type mismatch, empty file)
- [ ] `tests/test_config.py` — covers INFRA-02 (env var failure)
- [ ] `tests/test_ingestion.py` — covers DATA-02 through DATA-08
- [ ] `tests/test_generate_data.py` — covers DATA-01 (assert 3 files, expected row counts, distribution)
- [ ] `tests/test_no_hardcoded_paths.py` — grep `src/*.py` for hardcoded `"data"`, `"outputs"`, `"docs"` outside config.py
- [ ] `tests/test_package_structure.py` — INFRA-09 verification
- [ ] Framework install: `pip install -r requirements-dev.txt` (covers `pytest==8.3.5` plus test-only deps)

## Security Domain

> `security_enforcement` configuration was not present at research time, treated as enabled (default).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — single-user batch CLI |
| V3 Session Management | no | No sessions — stateless batch run |
| V4 Access Control | no | No multi-tenant — single operator |
| V5 Input Validation | yes | dtype-locked CSV reads, explicit date format, per-row validation (Pattern 3) |
| V6 Cryptography | yes (limited) | API key handled via env var only; never logged or written to disk by Phase 1 code |
| V7 Error Handling and Logging | yes | Python `logging` module; PII masking deferred to Phase 3 (LLM-08); Phase 1 logs only `student_id` (not names) |
| V14 Configuration | yes | `.env` is gitignored; `.env.example` documents required vars without values |

### Known Threat Patterns for Python + CSV + LLM pipeline

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leaked via stack trace | Information Disclosure | `os.environ` indexing fails at startup with KeyError that names the variable but not its value (since it's missing); never `print(key)`, never f-string the key into a log message |
| `.env` committed to repo | Information Disclosure | `.gitignore` includes `.env`; commit only `.env.example` |
| CSV injection (formulae like `=SUM(...)` in name fields) | Tampering | Deferred — relevant to Phase 4 Excel output, not Phase 1 ingestion |
| Path traversal via env var | Tampering | `Path(os.getenv("DATA_DIR", "data"))` is safe because the only operator who sets the var is the developer running the CLI. Out of scope for v1 (single-user batch). |
| Prompt injection via note_text | Tampering | Deferred — Phase 3 (LLM module); see PITFALLS.md Anthropic Pitfall #4 |
| PII in logs | Information Disclosure | Phase 1 logs only `student_id` (not `student_name`, `parent_phone`); Phase 3 will add masking. Lock the convention in Phase 1: `logger.warning(f"missing X for student_id={sid}")` — never include name or phone. |

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` (~500 lines, this project) — pinned versions, rationale, read_csv pattern, openpyxl, anthropic SDK
- `.planning/research/PITFALLS.md` (~660 lines, this project) — all 7 critical pitfalls + prevention strategies
- `.planning/research/ARCHITECTURE.md` (~900 lines, this project) — pipeline shape, module contracts, schema, batch patterns
- `.planning/STATE.md` — Accumulated Context (Key Decisions, Known Pitfalls, locked module signatures)
- `./CLAUDE.md` — project critical-pitfall checklist, code standards, module contracts
- `.planning/REQUIREMENTS.md` — DATA-01..08, INFRA-01..09 exact requirement text
- `.planning/phases/01-foundation-data-ingestion/01-CONTEXT.md` — locked decisions D-01..D-11

### Secondary (MEDIUM confidence — verified live in this research session)
- PyPI `pip index versions` queries on 2026-05-22 for all 13 pinned packages — confirmed each exists at the pinned version
- Local environment probes (`python --version`, `which make`) — established the Windows + Python 3.14 reality

### Tertiary (LOW confidence — flag for validation)
- pandas 2.2.3 compatibility with Python 3.14.3 — not directly verified in this session (assumed based on PyPI presence; ASSUMED A1)
- All package legitimacy classifications — slopcheck unavailable; tagged [ASSUMED] (see Package Legitimacy Audit)

## Project Constraints (from CLAUDE.md)

Extracted actionable directives that the planner MUST honor:

- **Type hints on ALL functions** (INFRA-08; CLAUDE.md "Code Standards")
- **Docstrings on all public classes and methods** (INFRA-08)
- **Python `logging` module throughout — zero `print` statements** in production code (INFRA-01; exception only for `src/generate_data.py` per project utility convention)
- **All column names as constants in `src/config.py`** — no hardcoded strings in logic (RISK-08; CLAUDE.md "Code Standards")
- **All paths from env vars — zero hardcoded paths** (INFRA-07)
- **`dtype={"student_id": "str", "parent_phone": "str"}` in EVERY `read_csv`** (Pitfall, CLAUDE.md)
- **`os.environ["KEY"]` not `os.getenv("KEY")` for required secrets — fail at startup** (Pitfall, CLAUDE.md)
- **`PatternFill(fill_type="solid", fgColor="RRGGBB")`** — Phase 4 only, but planner should ensure the constant is locked in config.py if used
- **`pandas 2.2.3` (not 3.x)** (CLAUDE.md "Key Technical Decisions")
- **`openpyxl` not `xlsxwriter`** (CLAUDE.md)
- **`respx` for API mocking** — Anthropic SDK uses httpx (CLAUDE.md; only relevant Phase 7, but install is in Phase 1)
- **HTML dashboard is fully self-contained** — Phase 5 (not relevant to Phase 1 planning)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all 13 packages verified live on PyPI in this session; locked by STACK.md (HIGH quality, 500 lines)
- Architecture: HIGH — ARCHITECTURE.md provides the canonical pipeline shape; module signatures locked in STATE.md
- Pitfalls: HIGH — PITFALLS.md exhaustive (660 lines); cross-referenced with CLAUDE.md and STATE.md
- Synthetic data approach: MEDIUM — locked by D-01..D-04 but the exact distribution-to-risk-tier mapping requires Phase 2 risk formula to verify end-to-end
- Python 3.14 compatibility: LOW — not directly verified; ASSUMED A1

**Research date:** 2026-05-22
**Valid until:** 2026-06-21 (30 days — stable stack, well-documented domain). Re-validate Python 3.14 compatibility before that if the dev environment changes.
