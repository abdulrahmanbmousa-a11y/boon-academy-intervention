# Phase 2: Risk Scoring Engine - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 5 (2 new, 3 modified)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/risk_engine.py` (replace stub body) | module / pure function | transform (DataFrame in → DataFrame out) | `src/ingestion.py` | exact (same module shape: locked public function + private helpers, `cfg` import, module logger, `df.copy()` purity) |
| `tests/test_risk_engine.py` (NEW) | pytest unit test file | request-response (build df → call → assert) | `tests/test_ingestion.py` | exact (same `from src import config as cfg` import, requirement-ID docstrings, `df.attrs` assertions, caplog pattern) |
| `src/config.py` (MODIFY) | config constants module | constant declarations | existing `COL_*` constants block (lines 56-80) | exact (extend the same "Derived columns" section with 4 new `COL_*_COMPONENT` constants) |
| `tests/test_config.py` (MODIFY) | pytest config test file | request-response (import → assert) | `TestColumnConstants` class (lines 53-83) | exact (extend `EXPECTED_COLUMN_CONSTANTS` list) |
| `main.py` (MODIFY) | orchestrator wiring | request-response (call sequence) | existing `ingest()` call site (lines 61-67) | exact (uncomment + mirror the import / call / `len(df)` log pattern) |

---

## Pattern Assignments

### `src/risk_engine.py` (module / pure-function transform)

**Analog:** `src/ingestion.py` (locked public signature + private helpers + cfg imports + module logger)

**Module header pattern** (`src/ingestion.py` lines 1-22):
```python
"""Ingestion module for boon-academy-intervention.

Loads the three source CSVs, cleans per-row with full error containment,
and merges into a single canonical one-row-per-student DataFrame.

The locked signature `ingest(data_paths)` is the contract between Phase 1
and all downstream phases (2-8). Do NOT change the signature or the returned
column schema without updating STATE.md and all downstream callers.

Patterns applied (01-RESEARCH.md):
  Pattern 2 — dtype-locked CSV reader (no inferred types)
  Pattern 3 — per-row error containment (errors='coerce', warnings list)
  Pattern 4 — three-CSV merge strategy (aggregate before merge)
"""
import logging
from pathlib import Path

import pandas as pd

from src import config as cfg

logger = logging.getLogger(__name__)
```
**Apply:** Open `risk_engine.py` with the same module docstring shape (purpose + locked-signature note + "Patterns applied" pointer to 02-RESEARCH.md), then `import logging` / `import numpy as np` / `import pandas as pd` / `from src import config as cfg` / `logger = logging.getLogger(__name__)`. The existing stub already imports `logging` and `pandas` and creates the logger — preserve those.

**Module-level constants pattern** (`src/ingestion.py` lines 31-53):
```python
DTYPE_METRICS: dict[str, str] = {
    cfg.COL_STUDENT_ID:  "string",
    cfg.COL_METRIC_DATE: "string",
    cfg.COL_SESSION_MIN: "string",
    cfg.COL_PRACTICE_Q:  "string",
}
_NUMERIC_DTYPE: str = "Float64"
```
**Apply:** Define module-level private constants with type hints — `_ACTION_BY_LEVEL: dict[str, str]`, `_RISK_BINS: list`, `_RISK_LABELS: list[str]`, `_WINDOW_DAYS: int = 14`, `_PRACTICE_CAP: float = 15.0`, `_NOTES_MAX_DAYS: int = 30`, `_TREND_NEUTRAL: float = 50.0`. Use the same leading-underscore convention for "private to module" and explicit type annotations on every constant.

**Private helper pattern** (`src/ingestion.py` lines 63-91 — `_read_csv_safe`):
```python
def _read_csv_safe(path: Path, dtype: dict[str, str]) -> pd.DataFrame:
    """Read a CSV with dtype-locked columns and standard NA handling.

    Catches EmptyDataError (header-only or truly empty files) and returns an
    empty DataFrame with the expected columns rather than raising.

    Args:
        path:  Absolute or relative path to the CSV file.
        dtype: Per-column dtype mapping (values must be pandas dtype strings).

    Returns:
        DataFrame with exactly the columns in dtype, or empty DataFrame on
        EmptyDataError.
    """
    try:
        return pd.read_csv(...)
    except pd.errors.EmptyDataError:
        ...
```
**Apply:** Every private helper (`_attendance_component`, `_practice_component`, `_trend_component_and_direction`, `_days_since_last_note`, `_notes_component`) must have:
- Leading underscore prefix
- Full type hints on args and return
- One-line summary docstring (research example uses "D-01: (1 - attendance_days/14) * 100, clipped [0,100]." — minimal but cites the decision ID)
- Args/Returns sections only if helper is non-trivial (vs. `_ingestion._read_csv_safe` which has both — use longer docstring for `_trend_component_and_direction` since it returns a tuple)

**Defensive `df.copy()` pattern** (`src/ingestion.py` line 169 — applied per-mutation in helpers):
```python
df = df.copy()
df[date_col] = parsed
return df
```
**Apply:** Once at top of `score_risk(df)` body: `df = df.copy()`. This satisfies the "pure function — caller's frame never mutated" requirement (CLAUDE.md + 02-CONTEXT.md). Pattern matches `_coerce_dates` and `_fill_numeric_with_zero` which both copy-then-assign.

**Public function structure** (`src/ingestion.py` lines 254-389 — `ingest`):
```python
def ingest(data_paths: dict[str, Path]) -> pd.DataFrame:
    """Load 3 CSVs, clean per-row, merge to canonical one-row-per-student DataFrame.

    Applies Pattern 2 (dtype-locked read), Pattern 3 (per-row error containment),
    and Pattern 4 (aggregate-then-merge) from 01-RESEARCH.md.

    Args:
        data_paths: dict with keys "metrics", "notes", "metadata" mapping to
                    Path objects for the corresponding CSV files.

    Returns:
        Single DataFrame with one row per student_id containing columns: [...]
        df.attrs["data_quality_warnings"]: list[dict] — cleaning events accumulated
        during ingestion. Each entry has a "type" key with one of: [...]

    Raises:
        FileNotFoundError: if any path in data_paths does not exist on disk.
        KeyError: if data_paths is missing required keys ...
    """
    # body with section comments delimiting phases
```
**Apply:** `score_risk(df)` docstring must (a) cite the decision IDs it implements (D-01 through D-09), (b) enumerate every column it ADDS to the output (10 new columns), (c) document the pd.Timestamp.now() time-dependence caveat (Pitfall 7 in research), and (d) note "Pure function — caller's df is never mutated". Use the same section-comment delimiters in the body:
```python
# ------------------------------------------------------------------
# D-09 component scores
# ------------------------------------------------------------------
```

**Aggregate-only logging pattern** (`src/ingestion.py` line 385-387):
```python
logger.info(
    f"ingestion complete — {len(df)} students, {len(warnings)} warnings"
)
```
**Apply:** At end of `score_risk`, log aggregate counts only (no student_id/name/phone — Security V7 from research):
```python
logger.info(f"Scored {len(df)} students — "
            f"CRITICAL={(df[cfg.COL_RISK_LEVEL] == 'CRITICAL').sum()}, ...")
```

**Column-naming discipline** (`src/ingestion.py` — every column reference uses `cfg.COL_*`):
- Lines 32-36, 49-53, 112-114, 163, 203, 241-246, 321-328 — never a bare string for a known column
**Apply:** Mandatory for RISK-08 compliance. The four NEW constants (`COL_ATTENDANCE_COMPONENT`, `COL_PRACTICE_COMPONENT`, `COL_TREND_COMPONENT`, `COL_NOTES_COMPONENT`) must exist in `src/config.py` BEFORE `risk_engine.py` references them. Within helpers, **input** column names (`"attendance_days"`, `"practice_total_q"`, `"daily_session_series"`, `"latest_note_date"`) — these come from Phase 1's `ingest()` but are not currently in `cfg`. Decision point for planner: either (a) add `COL_ATTENDANCE_DAYS`, `COL_PRACTICE_TOTAL_Q`, `COL_DAILY_SESSION_SERIES`, `COL_LATEST_NOTE_DATE` to `cfg`, OR (b) accept these specific four as RISK-08 exceptions (input column names are arguably an exception per the RISK-08 source-scan test's "allowed" allowlist).

---

### `tests/test_risk_engine.py` (pytest unit test file)

**Analog:** `tests/test_ingestion.py` (requirement-ID docstrings, `cfg` imports, `df.attrs` assertions, caplog usage)

**Test file header pattern** (`tests/test_ingestion.py` lines 1-16):
```python
"""Tests for src/ingestion.py — covers DATA-02 through DATA-08.

Each test maps to one or more DATA-* requirements from REQUIREMENTS.md.
All tests use committed fixture CSVs under tests/fixtures/ (immutable inputs).
"""
import logging
import pathlib

import pandas as pd
import pytest

from src import config as cfg
from src.ingestion import ingest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
```
**Apply:** Mirror exactly:
```python
"""Tests for src/risk_engine.py — covers RISK-01 through RISK-08 + purity discipline.

Each test maps to one or more RISK-* requirements from REQUIREMENTS.md.
All tests build in-memory DataFrames via the _build_student_row helper —
no fixture CSVs needed (risk_engine is a pure function over a DataFrame).
"""
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from freezegun import freeze_time

from src import config as cfg
from src.risk_engine import score_risk
```

**Test function naming + docstring pattern** (`tests/test_ingestion.py` line 22-32):
```python
def test_phone_stays_string(sample_csv_paths: dict) -> None:
    """DATA-02: parent_phone must be loaded as StringDtype, never promoted to int/float."""
    df = ingest(sample_csv_paths)
    assert df[cfg.COL_PARENT_PHONE].dtype == pd.StringDtype(), (
        f"Expected StringDtype for parent_phone, got {df[cfg.COL_PARENT_PHONE].dtype}"
    )
```
**Apply:** Every test docstring starts with `"REQ-ID: <plain-English assertion>"`. Use `cfg.COL_*` constants in assertions (never bare strings). Assertion failure message uses f-string showing actual value (`f"Expected ..., got {actual}"`).

**Section-comment delimiter pattern** (`tests/test_ingestion.py` lines 18-20, 43-45, 68-70):
```python
# ---------------------------------------------------------------------------
# DATA-02: dtype preservation
# ---------------------------------------------------------------------------
```
**Apply:** Group tests under section comments by requirement ID (RISK-01, RISK-02, ..., RISK-08, then "Purity discipline", then "RISK-08 source scan").

**In-memory DataFrame helper pattern** (NEW — no analog in test_ingestion.py, which uses fixture CSVs):
Research file (02-RESEARCH.md lines 501-527) provides the `_build_student_row` helper signature. Place at top of `test_risk_engine.py` (module-level helper, not a fixture, since each test needs different overrides). Pattern:
```python
def _build_student_row(
    student_id: str = "S0001",
    attendance_days: int = 14,
    practice_total_q: float = 210.0,
    session_series: list | None = None,
    latest_note_date: pd.Timestamp | None = None,
) -> dict:
    """Helper to build a single-student DataFrame row with sensible defaults."""
    ...
```
This is OK to introduce as a new test pattern because Phase 2 tests pure-function behavior on synthetic in-memory rows — fixture CSVs (the test_ingestion.py pattern) would force a round-trip through `ingest()`, coupling risk_engine tests to ingestion behavior. Document in test file docstring: "no fixture CSVs needed (risk_engine is a pure function over a DataFrame)".

**Parametrize pattern for boundary tests** (NEW in this file; matches pytest community standard):
Research example (02-RESEARCH.md lines 556-574) uses `@pytest.mark.parametrize` for the 8-case boundary table (LOW/MEDIUM/HIGH/CRITICAL at endpoints). Mirror that exactly.

**caplog pattern** (`tests/test_ingestion.py` lines 205-239 — `test_pii_safe_logging`):
```python
def test_pii_safe_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Security V7: logger.warning/info must include only student_id — never student_name/phone/note_text."""
    ...
    with caplog.at_level(logging.WARNING, logger="src.ingestion"):
        df = ingest(data_paths)

    pii_values = ["Student S0101", "0501234567", "Missed class today", ...]
    all_log_text = " ".join(record.message for record in caplog.records)
    for pii in pii_values:
        assert pii not in all_log_text, ...
```
**Apply:** Add `test_pii_safe_logging` test to `test_risk_engine.py` — assert that `logger.info` aggregate counts log (CRITICAL=N, HIGH=N, ...) does not leak student_name / phone / note_text. Use `caplog.at_level(logging.INFO, logger="src.risk_engine")`. The score_risk logger emits an INFO line (not WARNING), so level differs from ingestion's test.

**RISK-08 source-scan test** (no analog in test_ingestion.py — pattern from 02-RESEARCH.md lines 623-642):
```python
def test_no_bare_column_strings_in_risk_engine():
    """RISK-08: every column-name string in risk_engine.py must come from cfg."""
    source = Path("src/risk_engine.py").read_text()
    no_docstrings = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
    no_comments = re.sub(r'#.*', '', no_docstrings)
    matches = re.findall(r'"([a-z][a-z0-9_]{3,})"', no_comments)
    allowed = {"declining", "improving", "stable"}
    offenders = [m for m in matches if m not in allowed]
    assert not offenders, ...
```
**Apply:** This is a NEW pattern unique to Phase 2 (RISK-08 enforcement). The `allowed` set should include D-07 string labels (`declining`, `improving`, `stable`) and any input column names that planner decided NOT to add to `cfg` (e.g., `attendance_days`, `practice_total_q`, `daily_session_series`, `latest_note_date`).

---

### `src/config.py` (MODIFY — extend constants block)

**Analog:** Existing "Derived columns" block at lines 73-80

**Existing pattern to extend** (`src/config.py` lines 73-80):
```python
# Derived columns (added by ingestion/risk_engine — frozen for Phase 2+)
COL_ATTENDANCE_RATE: str = "attendance_rate"
COL_AVG_PRACTICE: str = "avg_practice_questions"
COL_TREND_DIR: str = "trend_direction"
COL_DAYS_SINCE_NOTE: str = "days_since_last_note"
COL_RISK_SCORE: str = "risk_score"
COL_RISK_LEVEL: str = "risk_level"
COL_RECOMMENDED_ACTION: str = "recommended_action"
```
**Apply:** Append 4 new constants in the SAME block, immediately after `COL_RECOMMENDED_ACTION`. Use snake_case values matching D-09 spec (`attendance_component`, `practice_component`, `trend_component`, `notes_component`):
```python
# D-09 component score columns (Phase 2)
COL_ATTENDANCE_COMPONENT: str = "attendance_component"
COL_PRACTICE_COMPONENT: str = "practice_component"
COL_TREND_COMPONENT: str = "trend_component"
COL_NOTES_COMPONENT: str = "notes_component"
```
Preserve the explicit `: str =` type annotation pattern (every existing COL_* constant uses it).

---

### `tests/test_config.py` (MODIFY — extend EXPECTED_COLUMN_CONSTANTS list)

**Analog:** `TestColumnConstants` class at lines 53-83

**Existing pattern to extend** (`tests/test_config.py` lines 56-74):
```python
EXPECTED_COLUMN_CONSTANTS = [
    "COL_STUDENT_ID",
    "COL_STUDENT_NAME",
    ...
    "COL_RECOMMENDED_ACTION",
]

def test_column_constants_defined(self, monkeypatch):
    """All 17 column name constants exist and are non-empty strings."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    import src.config as cfg
    for name in self.EXPECTED_COLUMN_CONSTANTS:
        value = getattr(cfg, name)
        assert isinstance(value, str), f"{name} must be a str, got {type(value)}"
        assert len(value) > 0, f"{name} must be a non-empty string"
```
**Apply:**
1. Append the 4 new constant names to `EXPECTED_COLUMN_CONSTANTS`:
   ```python
   "COL_ATTENDANCE_COMPONENT",
   "COL_PRACTICE_COMPONENT",
   "COL_TREND_COMPONENT",
   "COL_NOTES_COMPONENT",
   ```
2. Update the docstring count: `"""All 17 column name constants exist..."""` → `"""All 21 column name constants exist..."""`.
3. The `getattr` loop body needs zero changes — it iterates the list dynamically.
4. Preserve the `monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")` pattern at the start of each test (every test method in this file uses it because `clean_config_module` autouse fixture forces reimport).

---

### `main.py` (MODIFY — uncomment risk_engine wiring)

**Analog:** Existing `ingest()` call site at lines 61-67

**Existing pattern to mirror** (`main.py` lines 61-67):
```python
# Phase 1: Ingestion
df = ingest(data_paths)
run_log["students_processed"] = len(df)

# Capture data quality warnings from ingestion (D-06: accumulate into run_log)
run_log["data_quality_warnings"] = df.attrs.get("data_quality_warnings", [])
logger.info(f"Ingested {len(df)} students")
```
**Apply:**
1. Add the import at top with the other src imports (currently line 12: `from src.ingestion import ingest`):
   ```python
   from src.risk_engine import score_risk
   ```
2. Replace the stub comment at line 69-70:
   ```python
   # Phase 2: Risk scoring (wired in plan 02-02)
   # df = risk_engine.score_risk(df)
   ```
   with:
   ```python
   # Phase 2: Risk scoring
   df = score_risk(df)
   logger.info(f"Scored {len(df)} students")
   ```
3. Keep `df.attrs["data_quality_warnings"]` intact — `df.copy()` in score_risk preserves attrs (Pitfall 8 in research; mitigation: assert this in a purity test).
4. Match the existing `logger.info(f"<verb> {len(df)} students")` aggregate-only style.

---

## Shared Patterns

### Module-level logger
**Source:** `src/ingestion.py` line 22 and `src/config.py` line 17
**Apply to:** `src/risk_engine.py` (the existing stub already has this — preserve)
```python
import logging

logger = logging.getLogger(__name__)
```
**Rule:** Zero `print()` statements anywhere (CLAUDE.md). Use `logger.info` for end-of-phase aggregate summary; `logger.warning` is reserved for data quality issues (none expected in pure scoring).

### `from src import config as cfg`
**Source:** `src/ingestion.py` line 20, `tests/test_ingestion.py` line 12, `tests/test_config.py` line 34
**Apply to:** `src/risk_engine.py` and `tests/test_risk_engine.py`
```python
from src import config as cfg
```
**Rule:** ALL column-name references and ALL weight/threshold references go through `cfg.*`. Never `import config` (no `src.` prefix) and never `from src.config import COL_RISK_SCORE` (no individual imports — always `cfg.COL_RISK_SCORE`). This pattern is enforced uniformly across the codebase.

### Type hints + docstrings on every function
**Source:** `src/ingestion.py` every function (lines 63, 93, 139, 174, 225, 254)
**Apply to:** Every public and private function in `src/risk_engine.py`
- Type hints on all args + return type
- Public functions: full docstring with Args/Returns/Raises sections
- Private helpers: minimal docstring is OK if the body is < 5 lines (matches the `_attendance_component` example in research)
**Rule:** CLAUDE.md mandates type hints on ALL functions; INFRA-08 mandates docstrings on public functions.

### `df.copy()` at function entry (purity guarantee)
**Source:** `src/ingestion.py` lines 169, 220 (defensive per-helper copy)
**Apply to:** `src/risk_engine.py` line 1 of `score_risk` body (one copy at top, then all column assignments mutate the local copy)
```python
df = df.copy()
```
**Rule:** Required for pandas 2.2.3 Copy-on-Write semantics (CLAUDE.md). The purity unit test (`test_pure_function_does_not_mutate_input`) asserts caller's df is unchanged.

### `df.attrs` preservation
**Source:** `src/ingestion.py` line 384 — `df.attrs["data_quality_warnings"] = warnings`
**Apply to:** `src/risk_engine.py` — verify (via test) that `df.copy()` preserves attrs in pandas 2.2.3. If a defensive backup is needed: `result.attrs = df.attrs` before return (Pitfall 8 mitigation).
**Rule:** Phase 4 reads `df.attrs["data_quality_warnings"]` for run_log.json. Phase 2 must NOT drop this side-channel.

### Aggregate-only logging (PII discipline)
**Source:** `src/ingestion.py` line 385-387, also enforced by `test_pii_safe_logging` (lines 205-239)
**Apply to:** `src/risk_engine.py` end-of-function log + `tests/test_risk_engine.py` should include a parallel `test_pii_safe_logging_in_score_risk`
**Rule:** Security V7. Log counts and levels — never student_id concatenated with name/phone/note_text. Even though `score_risk` doesn't take notes_text as input, the input DataFrame still contains `student_name`, `parent_phone`, `latest_note_text` columns from Phase 1. The pattern is: only `len(df)` and aggregate counts in logs.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | All Phase 2 files have a direct analog in the existing codebase. |

The only NEW patterns introduced (no codebase analog, source: 02-RESEARCH.md):
1. **`_build_student_row` in-memory helper** — Phase 2 tests synthesize DataFrames inline rather than going through fixture CSVs. This is a deliberate departure because risk_engine is a pure function and coupling its tests to ingestion would hide regressions on either side.
2. **`@pytest.mark.parametrize` for boundary tests** — pytest community standard, but no existing test_*.py in this repo uses it yet. Pattern matches research example exactly.
3. **`@freeze_time("2026-05-23")` decorator** — `freezegun` is pinned in STATE.md (1.5.5) but unused in current tests. Required because `pd.Timestamp.now()` makes `score_risk` wall-clock-dependent (Pitfall 7).
4. **Source-scan regression test (RISK-08 enforcement)** — file-reads `src/risk_engine.py` and regex-greps for bare snake_case strings. Unique to Phase 2; planner may want to generalize to other modules later.

---

## Metadata

**Analog search scope:** `src/` (ingestion, config, risk_engine stub), `tests/` (test_ingestion, test_config, conftest), `main.py`
**Files scanned:** 7 (ingestion.py, config.py, risk_engine.py, main.py, test_ingestion.py, test_config.py, conftest.py)
**Pattern extraction date:** 2026-05-23
**Confidence:** HIGH — every analog is a verbatim source file in this repo with line numbers cited.
