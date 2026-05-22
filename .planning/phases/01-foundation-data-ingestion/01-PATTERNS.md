# Phase 1: Foundation + Data Ingestion - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 14 new files (0 modified)
**Analogs found:** 14 / 14 (all derived from planning docs — greenfield project)

## Greenfield Notice

This project has zero existing source code. The codebase contains only planning documents.
For every file listed below, the "closest analog" is a documented pattern in one of:
- `.planning/research/STACK.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`
- `.planning/phases/01-foundation-data-ingestion/01-RESEARCH.md` (inlines the 6 canonical patterns)
- `.planning/STATE.md` (locked module signatures)
- `CLAUDE.md` (project standards + critical pitfalls)

The planner MUST treat the cited code blocks in 01-RESEARCH.md as the literal templates to copy. Each excerpt below is reproduced from there with its source line range.

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `src/__init__.py` | package marker | n/a | INFRA-09 directive in 01-RESEARCH.md L306 | exact (trivially empty) |
| `src/config.py` | config | request-response (synchronous import) | 01-RESEARCH.md Pattern 1 L315-374 | exact |
| `src/ingestion.py` | service | batch / CRUD (file-I/O read + transform) | 01-RESEARCH.md Patterns 2-4 L385-538 | exact |
| `src/generate_data.py` | utility (standalone script) | batch / file-I/O write | 01-RESEARCH.md Pattern 5 L553-609 | exact |
| `src/risk_engine.py` (stub) | service | pure transform | STATE.md L94 + 01-RESEARCH.md L307 | role-match (stub only) |
| `src/llm_engine.py` (stub) | service | request-response (external API) | STATE.md L95 + 01-RESEARCH.md L307 | role-match (stub only) |
| `src/output_generator.py` (stub) | service | file-I/O write | STATE.md L96 + 01-RESEARCH.md L307 | role-match (stub only) |
| `main.py` | orchestrator (controller) | pipeline | 01-RESEARCH.md Pattern 6 L617-654 | exact |
| `requirements.txt` | config | n/a | 01-RESEARCH.md "Installation" L134-143 | exact |
| `requirements-dev.txt` | config | n/a | 01-RESEARCH.md "Installation (dev)" L146-153 | exact |
| `.env.example` | config | n/a | 01-RESEARCH.md L740-756 | exact |
| `.gitignore` | config | n/a | 01-RESEARCH.md L805-816 | exact |
| `Makefile` | config (build) | n/a | 01-RESEARCH.md L760-775 | exact |
| `make.ps1` | config (build, Windows) | n/a | 01-RESEARCH.md L779-801 | exact |
| `README.md` | docs | n/a | 01-RESEARCH.md L820-847 | exact |

## Pattern Assignments

### `src/config.py` (config, fail-loud env loader)

**Analog:** 01-RESEARCH.md Pattern 1 (lines 315-374) + CLAUDE.md "Critical Pitfalls" §7

**Imports pattern** (01-RESEARCH.md L317-322):
```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env in cwd; does NOT override already-set env vars
```

**Fail-loud secret pattern** (01-RESEARCH.md L325-326 + CLAUDE.md "Critical Pitfalls"):
```python
# --- Required secrets (fail loudly at import time) ---
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
# KeyError at import time if missing — GOOD
```
**Rule:** `os.environ["KEY"]` for secrets; `os.getenv("KEY", default)` for optional paths/tunables. CLAUDE.md and PITFALL #7 forbid the inverse.

**Safe-default optional paths** (01-RESEARCH.md L329-336):
```python
DATA_DIR:   Path = Path(os.getenv("DATA_DIR",   "data"))
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
DOCS_DIR:   Path = Path(os.getenv("DOCS_DIR",   "docs"))

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
MAX_STUDENTS_PER_LLM_CALL: int = int(os.getenv("MAX_STUDENTS_PER_LLM_CALL", "10"))
```

**Risk thresholds + weights (D-07)** (01-RESEARCH.md L338-347):
```python
RISK_THRESHOLD_CRITICAL: int = int(os.getenv("RISK_THRESHOLD_CRITICAL", "75"))
RISK_THRESHOLD_HIGH:     int = int(os.getenv("RISK_THRESHOLD_HIGH",     "50"))
RISK_THRESHOLD_MEDIUM:   int = 25  # not env-overridable

WEIGHT_ATTENDANCE: float = 0.35
WEIGHT_PRACTICE:   float = 0.30
WEIGHT_TREND:      float = 0.20
WEIGHT_NOTES:      float = 0.15
```

**Column name constants (all in one file per CLAUDE.md "Code Standards")** (01-RESEARCH.md L350-373):
```python
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

**Why this pattern:** [CITED: CLAUDE.md "Code Standards"] All column names as constants — no hardcoded strings in logic. Every other module imports from `config` — single source of truth.

---

### `src/ingestion.py` (service, batch read + transform)

**Analog:** 01-RESEARCH.md Patterns 2-4 (lines 385-538)

**Locked signature** (STATE.md L93, 01-RESEARCH.md L470):
```python
def ingest(data_paths: dict[str, Path]) -> pd.DataFrame:
```
**This signature is FROZEN** — all downstream phases (2-8) depend on it. Do not return tuples; attach side data to `df.attrs`.

**Imports pattern** (01-RESEARCH.md L386-390 + L433-434):
```python
import pandas as pd
from pathlib import Path
from src import config as cfg
import logging
logger = logging.getLogger(__name__)
```

**Dtype-locked CSV reader (Pattern 2)** (01-RESEARCH.md L392-421):
```python
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
**Pitfall pre-empt:** PITFALL #1 (float promotion) and PITFALL #3 (phone leading zeros) covered by every column in `DTYPE_*` being `"string"` or `"Float64"`.

**Per-row error containment (Pattern 3)** (01-RESEARCH.md L436-459):
```python
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
**Logging convention (Security V7):** Use `student_id` only — never `student_name`, `parent_phone`, or `note_text` in warning messages. Locked in 01-RESEARCH.md "Security Domain" L980.

**Missing module: `_ensure_ids` (D-10 placeholder for missing IDs)** — referenced in Pattern 4 L492-494 but body is implied not shown. Planner must implement: scan `student_id` and `campus_id` for NaN; assign `UNKNOWN_001`, `UNKNOWN_002`, ... auto-incremented; log warning with original row index; append to `warnings` list with `{"type": "missing_id", ...}`.

**Three-CSV merge strategy (Pattern 4)** (01-RESEARCH.md L470-537):
```python
def ingest(data_paths: dict[str, Path]) -> pd.DataFrame:
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

**Docstring template** (01-RESEARCH.md L471-483):
```python
"""
Load 3 CSVs, clean per-row, merge to canonical one-row-per-student DataFrame.

Args:
    data_paths: dict with keys "metrics", "notes", "metadata" mapping to file paths

Returns:
    Single DataFrame, one row per student_id, with columns:
    student_id, student_name, campus_id, parent_phone, facilitator_email,
    session_total_min, practice_total_q, attendance_days,
    latest_note_date, latest_note_text,
    data_quality_warnings (in df.attrs)
"""
```

**Key design rules** (01-RESEARCH.md L540-544):
- Aggregate BEFORE merge to prevent row explosion
- Keep `daily_*_series` lists on the row — Phase 2 trend calc needs them
- `how="left"` on metadata — every metadata row appears even if metrics/notes absent
- Use `df.attrs["data_quality_warnings"]` not tuple return — preserves locked signature

---

### `src/generate_data.py` (utility, standalone CSV writer)

**Analog:** 01-RESEARCH.md Pattern 5 (lines 553-609)

**Module docstring + constants** (01-RESEARCH.md L554-570):
```python
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
```

**Metadata generator template** (01-RESEARCH.md L572-585):
```python
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
```

**Entry-point pattern** (01-RESEARCH.md L598-608):
```python
def main() -> None:
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    metadata = generate_metadata(rng)
    metadata = inject_edge_cases(metadata, rng)
    metadata.to_csv(cfg.DATA_DIR / "student_metadata.csv", index=False)
    # ... metrics, notes
    print(f"Generated synthetic data in {cfg.DATA_DIR}")

if __name__ == "__main__":
    main()
```

**Notes:**
- `print()` is permitted here (01-RESEARCH.md L611) — `generate_data.py` is a dev utility, NOT the pipeline. CLAUDE.md "zero print statements" applies only to production modules.
- Risk distribution tuning per D-04 (15% CRITICAL / 25% HIGH / 40% MEDIUM / 20% LOW) achieved through cohort-based distributions in `generate_metrics()` — research leaves that as `pass` for the planner to design.

---

### `main.py` (orchestrator, pure coordination)

**Analog:** 01-RESEARCH.md Pattern 6 (lines 617-654) + CLAUDE.md "Project Structure" §main.py

**Full skeleton** (01-RESEARCH.md L618-653):
```python
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
**Rule:** Zero business logic (CLAUDE.md "Project Structure"). main.py only loads env, configures logging, and chains the four pipeline functions.

---

### `src/risk_engine.py`, `src/llm_engine.py`, `src/output_generator.py` (Phase 2/3/4 stubs)

**Analog:** STATE.md L93-96 locked signatures + 01-RESEARCH.md L307 stub recommendation

**Stub template** (01-RESEARCH.md L307):
```python
# src/risk_engine.py
import pandas as pd

def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 2: deterministic weighted risk scoring."""
    raise NotImplementedError("Phase 2")
```
```python
# src/llm_engine.py
import pandas as pd

def enrich_with_llm(df: pd.DataFrame, api_key: str) -> pd.DataFrame:
    """Phase 3: campus-batched Claude API enrichment with 3-layer fallback."""
    raise NotImplementedError("Phase 3")
```
```python
# src/output_generator.py
import pandas as pd
from pathlib import Path

def write_outputs(df: pd.DataFrame, output_dir: Path) -> dict[str, Path]:
    """Phase 4: write all 6 output files. Idempotent."""
    raise NotImplementedError("Phase 4")
```
**Rule:** Stubs ONLY if `main.py` needs them for import-time checks. Otherwise leave creation to Phases 2-4. Signatures FROZEN per STATE.md.

---

### `requirements.txt`

**Analog:** 01-RESEARCH.md "Installation" L134-143
```
pandas==2.2.3
openpyxl==3.1.5
python-docx==1.1.2
anthropic==0.103.1
python-dotenv==1.2.2
tenacity==9.1.4
jinja2==3.1.6
```
**Name-confusion warning** (01-RESEARCH.md L192-193): `python-docx` (NOT `docx`); `python-dotenv` (NOT `dotenv`). Both wrong packages exist on PyPI.

---

### `requirements-dev.txt`

**Analog:** 01-RESEARCH.md "Installation (dev)" L146-153
```
pytest==8.3.5
pytest-mock==3.15.1
pytest-cov==7.1.0
respx==0.23.1
freezegun==1.5.5
coverage==7.14.0
```

---

### `.env.example`

**Analog:** 01-RESEARCH.md L740-756
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

---

### `.gitignore`

**Analog:** 01-RESEARCH.md L805-816
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

---

### `Makefile`

**Analog:** 01-RESEARCH.md L760-775
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
**Pitfall pre-empt:** PITFALL #8 (`make` not on Windows). Ship `make.ps1` alongside.

---

### `make.ps1` (Windows PowerShell fallback)

**Analog:** 01-RESEARCH.md L779-801
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

---

### `README.md` (≤30 lines per spec)

**Analog:** 01-RESEARCH.md L820-847
```markdown
# boon-academy-intervention

AI-powered student intervention pipeline. Raises facilitator intervention rates from 30% to 80%+
by scoring student risk and drafting WhatsApp parent messages using Claude.

## Quick Start

` ``bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
make demo      # Unix/macOS
./make.ps1 demo  # Windows
` ``

## What it produces

- `outputs/intervention_priority_list.xlsx` — all students ranked
- `outputs/facilitator_dashboard_*.xlsx` — per-campus dashboards
- `outputs/whatsapp_messages.csv` — pre-drafted parent messages
- `outputs/intervention_report.docx` — full narrative report
- `outputs/facilitator_dashboard.html` — self-contained browser dashboard

## Requirements

Python 3.11+ recommended (3.12, 3.13 also tested).
```

---

### `src/__init__.py` and `tests/__init__.py`

**Analog:** 01-RESEARCH.md L302, L306 + INFRA-09
**Content:** Empty file. Both are package markers. `src/__init__.py` MUST be an empty file (not a stub with content) — conventional and sufficient.

---

## Shared Patterns

### Logging (applied to all .py modules except `generate_data.py`)
**Source:** CLAUDE.md "Code Standards" + 01-RESEARCH.md L433-434, L621-630
```python
import logging
logger = logging.getLogger(__name__)
# ... later in functions:
logger.warning(f"missing {col} for student_id={sid} — filled with 0")
logger.info(f"ingestion complete — {len(df)} students")
```
**Apply to:** `src/config.py`, `src/ingestion.py`, `src/risk_engine.py` (stub), `src/llm_engine.py` (stub), `src/output_generator.py` (stub), `main.py`.
**Forbidden:** `print()` in production code. Exception: `src/generate_data.py` (utility script).

### Type hints + docstrings (INFRA-08, applied to every function)
**Source:** CLAUDE.md "Code Standards" + 01-RESEARCH.md L1004-1005
```python
def ingest(data_paths: dict[str, Path]) -> pd.DataFrame:
    """Brief one-liner.

    Args:
        data_paths: ...

    Returns:
        ...
    """
```
**Apply to:** every function in every .py file. No exceptions.

### Path resolution (INFRA-07, applied everywhere)
**Source:** CLAUDE.md "Code Standards" + 01-RESEARCH.md L664
- Every path derives from `cfg.DATA_DIR`, `cfg.OUTPUT_DIR`, `cfg.DOCS_DIR`.
- Zero hardcoded `"data"`, `"outputs"`, `"docs"` strings outside `src/config.py`.
- Verified by `tests/test_no_hardcoded_paths.py` (Wave 0 grep-based test).

### PII-safe logging convention (Security V7)
**Source:** 01-RESEARCH.md L980
- Log only `student_id`. Never log `student_name`, `parent_phone`, `note_text`.
- Pattern: `logger.warning(f"<issue> for student_id={sid}")`.
**Apply to:** every `logger.*` call in `src/ingestion.py` and `src/generate_data.py` error paths.

### Data quality warnings side channel
**Source:** 01-RESEARCH.md L534-535, L544
- Build `warnings: list[dict]` accumulator inside `ingest()`.
- Each handler appends `{"type": str, "column": str?, "student_id": str?}`.
- Attach via `df.attrs["data_quality_warnings"] = warnings` at end of `ingest()`.
- Phase 4 `output_generator.write_run_log()` reads this attr → `run_log.json["data_quality_warnings"]`.
- A6 caveat: `df.attrs` can be lost on some pandas operations; planner should verify it survives through `risk_engine.score_risk()` in Phase 2 plan.

### Dtype contract (CLAUDE.md Critical Pitfalls #1 — applied to every `read_csv`)
**Source:** CLAUDE.md "Critical Pitfalls" + 01-RESEARCH.md L685-687
- Every `pd.read_csv()` call passes `dtype={...}` dict.
- IDs and phones: `"string"` (never let pandas infer).
- Nullable numerics: `"Float64"` (capital F — pandas nullable type).
- Dates: read as `"string"`, parse to datetime in a separate `_coerce_dates` step with explicit `format="%Y-%m-%d"`.

---

## No Analog Found

None — every file has a documented analog in the planning docs, even if it's a directive rather than full code. The greenfield nature is fully covered because the research phase pre-built canonical patterns.

---

## Metadata

**Analog search scope:** Entire `.planning/` tree (no `src/`, `tests/`, or other source dirs exist yet).
**Files scanned:**
- `.planning/CLAUDE.md` (project root)
- `.planning/STATE.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/research/STACK.md`
- `.planning/research/PITFALLS.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/SUMMARY.md`
- `.planning/research/FEATURES.md`
- `.planning/phases/01-foundation-data-ingestion/01-CONTEXT.md`
- `.planning/phases/01-foundation-data-ingestion/01-RESEARCH.md`

**Pattern extraction date:** 2026-05-22
