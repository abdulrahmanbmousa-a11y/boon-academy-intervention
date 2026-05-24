# Phase 7: Test Suite - Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 6 (4 test files extended + 1 conftest extended + 1 source modified)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tests/test_risk_engine.py` | test | request-response (pure function) | `tests/test_risk_engine.py` itself (lines 241-268) | exact — extend existing parametrize block |
| `tests/test_ingestion.py` | test | CRUD / file-I/O | `tests/test_ingestion.py` itself (lines 187-198) | exact — same fixture-path pattern already used |
| `tests/test_llm_engine.py` | test | event-driven / request-response | `tests/test_llm_engine.py` itself (lines 134-178, 257-285) | exact — respx pattern already established |
| `tests/test_output_generator.py` | test | file-I/O | `tests/test_output_generator.py` itself (lines 571-622) | exact — tmp_path + write_outputs pattern already used |
| `tests/conftest.py` | test config | shared fixtures | `tests/conftest.py` lines 26-45 (`sample_csv_paths`) | exact — same fixture style |
| `src/llm_engine.py` | service | request-response | `src/llm_engine.py` lines 221-225 | exact — `http_client` param already present |

---

## Pattern Assignments

### `tests/test_risk_engine.py` — add boundary tests

**What to add:** `test_score_75_is_critical` and `test_score_74_is_high` (D-03, CONTEXT.md §Specifics).

**Analog:** existing `test_risk_level_boundaries` parametrize block (lines 241-268) — but that test calls `pd.cut` directly and does NOT call `score_risk()`. The new boundary tests must call `score_risk()` end-to-end and assert on the result. Use the RISK-05 weighted formula test (lines 190-235) as the pattern for constructing rows that produce exact scores.

**Imports pattern** (lines 1-18 — already present, copy as-is):
```python
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

**Helper pattern** — use `_build_student_row()` (lines 24-59). The boundary tests need rows whose `score_risk()` output lands exactly at 75 and 74. Use the `test_risk_score_weighted_formula` approach (lines 190-235): construct rows analytically so the weighted sum equals the target score, then assert `cfg.COL_RISK_SCORE` and `cfg.COL_RISK_LEVEL`.

**Core pattern to copy** (lines 241-268 + lines 302-345):
```python
@pytest.mark.parametrize("score,expected_level", [
    (75.0,  "CRITICAL"),
    (74.99, "HIGH"),
])
def test_risk_level_boundaries(score: float, expected_level: str) -> None:
    # existing pattern: pd.cut directly (does NOT call score_risk)
    ...

# NEW pattern — end-to-end via score_risk():
@freeze_time("2026-05-23")
def test_score_75_is_critical() -> None:
    """TEST-01 / ROADMAP SC-1: score_risk() output risk_score==75 → risk_level=='CRITICAL'."""
    # Construct a row where weighted formula yields exactly 75.0:
    # attendance_component=100 (0 days) → 100*0.35 = 35.0
    # practice_component=100 (0 q)     → 100*0.30 = 30.0
    # trend_component=0   (improving)  → 0*0.20   =  0.0
    # notes_component=0   (note today) → 0*0.15   =  0.0
    # total = 65.0 — insufficient; adjust practice_component to reach 75.
    # Use partial construction: attendance=100, practice=100, trend=50, notes=0
    # → 35 + 30 + 10 + 0 = 75.0 exactly
    df = pd.DataFrame([_build_student_row(
        attendance_days=0,
        practice_total_q=0.0,
        session_series=[10.0, 20.0],           # < 3 values → trend_component=50
        latest_note_date=pd.Timestamp("2026-05-23"),  # today → notes_component=0
    )])
    result = score_risk(df)
    assert result[cfg.COL_RISK_SCORE].iloc[0] == pytest.approx(75.0, abs=0.01), (...)
    assert result[cfg.COL_RISK_LEVEL].iloc[0] == "CRITICAL", (...)
```

**Assertion style** (lines 76-81): always use `pytest.approx(value, abs=0.01)` for float scores; use `==` for string labels. Always include a descriptive failure message string.

**Score 74 pattern:** mirror `test_score_75_is_critical` but construct a row landing at 74.0:
- attendance_component=100 (0 days) → 35.0
- practice_component=100 (0 q) → 30.0
- trend_component=45 (tunable) → 9.0 → total = 74.0
- Or: attendance=100, practice=100, trend=50, notes=0 → 75; drop notes from 0 to slightly negative is impossible — instead set trend_component to 45: use session_series that yields trend slightly below 50. Simpler: set attendance=100, practice=93.33% (tune practice_total_q so practice_component gives exact partial), or use the `pd.cut` test as unit test and add a separate `test_score_74_is_high` that constructs from components.

**Recommended approach:** Derive analytically: attendance=100, practice=100, trend=40, notes=0 → 35+30+8+0=73; attendance=100, practice=100, trend=45, notes=0 → 35+30+9+0=74. Need trend_component=45. Check `score_risk()` trend formula to confirm what input produces trend_component=45.

---

### `tests/test_ingestion.py` — add edge case tests

**What to add:** Tests named per D-03: `test_missing_values_filled_with_zero`, `test_duplicate_student_ids_deduplicated`, `test_empty_csv_does_not_crash`, `test_bad_date_format_safe_default`, `test_type_mismatch_safe_default`. Check existing tests first — most are already present (lines 47-199). Add only what is missing.

**Existing coverage audit:**
- `test_missing_numeric_filled_with_zero` → lines 47-65 — ALREADY EXISTS as `test_missing_numeric_filled_with_zero`
- `test_duplicate_ids_deduped` → lines 72-90 — ALREADY EXISTS
- `test_empty_csv_handled` → lines 187-198 — ALREADY EXISTS
- `test_bad_record_does_not_crash` → lines 168-183 — ALREADY EXISTS (bad dates)
- `test_type_mismatch_safe_default` → lines 97-113 — ALREADY EXISTS

**Action:** Run baseline first (D-01). If existing tests are failing rather than missing, fix the underlying source not the test. If tests are passing but named differently from D-03 spec, rename to match D-03 names (`test_duplicate_student_ids_deduplicated`, `test_empty_csv_does_not_crash`, `test_bad_date_format_safe_default`).

**Fixture path pattern** (lines 49-54 — used throughout):
```python
data_paths = {
    "metadata": FIXTURES_DIR / "student_metadata_happy.csv",
    "metrics":  FIXTURES_DIR / "student_daily_metrics_missing_numeric.csv",
    "notes":    FIXTURES_DIR / "facilitator_notes_happy.csv",
}
df = ingest(data_paths)
```

**Assertion style** (lines 57-65):
```python
assert df["session_total_min"].notna().all(), "session_total_min has NaN after imputation"
warnings = df.attrs.get("data_quality_warnings", [])
missing_types = [w["type"] for w in warnings]
assert "missing_numeric" in missing_types, (
    "Expected at least one 'missing_numeric' warning in df.attrs['data_quality_warnings']"
)
```

**Empty CSV pattern** (lines 187-198):
```python
def test_empty_csv_does_not_crash() -> None:
    """DATA-08 / TEST-02: All-empty inputs (header only) must return 0-row DataFrame."""
    data_paths = {
        "metadata": FIXTURES_DIR / "empty.csv",
        "metrics":  FIXTURES_DIR / "empty.csv",
        "notes":    FIXTURES_DIR / "empty.csv",
    }
    df = ingest(data_paths)
    assert isinstance(df, pd.DataFrame), "ingest did not return a DataFrame"
    assert len(df) == 0, f"Expected 0 rows for all-empty input, got {len(df)}"
```

---

### `tests/test_llm_engine.py` — add/verify respx-based tests

**What to add:** Verify `test_fallback_to_template` (D-08) and `test_campus_batching` (D-09) exist and match the spec. Both ALREADY EXIST (lines 134-178, 257-285).

**Action:** Run baseline. These tests reference `enrich_with_llm(df, "test-key", http_client=http_client)` — the `http_client` parameter is already present in `src/llm_engine.py` (line 224). If failing, fix the source behavior or the mock setup, not the test structure.

**Token logging test** — `test_token_logging` ALREADY EXISTS (lines 288-319). It asserts `counts["tokens_used"]["input"] == 150` from the mock response's `"usage": {"input_tokens": 150, "output_tokens": 80}`. CONTEXT.md §TEST-03 asks for a `caplog` assertion too — the existing test does NOT use `caplog`. Add `caplog` check inline:

**Token logging pattern to add** (extend lines 288-319):
```python
def test_token_logging(respx_mock, caplog) -> None:
    """LLM-06 / TEST-03: Token counts appear in counts dict AND in log output."""
    ...
    with caplog.at_level(logging.INFO, logger="src.llm_engine"):
        _, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    assert counts["tokens_used"]["input"] == 150, (...)
    assert counts["tokens_used"]["output"] == 80, (...)
    # TEST-03: token counts must appear in log output
    assert "150" in caplog.text or "token" in caplog.text.lower(), (
        "TEST-03: token counts must be logged after successful API call"
    )
```

**respx injection pattern** (lines 112-115 — used throughout):
```python
http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
result_df, counts = enrich_with_llm(df, "test-key", http_client=http_client)
```

**Fallback test pattern** (lines 257-285):
```python
def test_fallback_to_template(respx_mock) -> None:
    """LLM-05 / D-08: HTTP 500 / timeout → generated_by='template', message_text non-empty."""
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
    ])
    respx_mock.post(ANTHROPIC_API_URL).mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    result_df, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    row = result_df[result_df[cfg.COL_STUDENT_ID] == "S0001"].iloc[0]
    assert row[cfg.COL_GENERATED_BY] == "template", (...)
    assert row[cfg.COL_LLM_ERROR_REASON] == "timeout", (...)
    assert counts["fallbacks_triggered"] >= 1, (...)
    # D-08 addition: whatsapp_message must be non-empty for CRITICAL row
    assert row[cfg.COL_WHATSAPP_MESSAGE] and len(str(row[cfg.COL_WHATSAPP_MESSAGE])) > 0, (
        "D-08: template fallback must produce non-empty message_text for CRITICAL row"
    )
```

**Campus batching pattern** (lines 134-178):
```python
def test_campus_batching(respx_mock) -> None:
    """D-09 / LLM-02: 2 campuses → exactly 2 API calls (one per campus)."""
    ...
    assert len(respx_mock.calls) == 2, (
        f"LLM-02: expected exactly 2 API calls, got {len(respx_mock.calls)}"
    )
```

---

### `tests/test_output_generator.py` — add integration test

**What to add:** `test_all_6_output_files_exist` (D-06) — integration test calling `write_outputs()` end-to-end and asserting all 6 file paths exist in `tmp_path`.

**Analog:** `test_write_outputs_all_paths_exist` (lines 599-608) — ALREADY EXISTS and covers this. Also `test_write_outputs_returns_all_keys` (lines 571-596) asserts keys include `priority_list`, `campus_*`, `whatsapp`, `run_log`, `dashboard`, `report`.

**Action:** Check if a test named exactly `test_all_6_output_files_exist` is required by TEST-04. If the existing `test_write_outputs_all_paths_exist` satisfies TEST-04, no addition is needed. Otherwise add:

**Integration test pattern** (based on lines 571-622):
```python
def test_all_6_output_files_exist(
    full_sample_df: pd.DataFrame,
    sample_run_log_full: dict,
    tmp_path: Path,
) -> None:
    """TEST-04 / D-06: write_outputs() produces all 6 output files in tmp_path."""
    result = write_outputs(full_sample_df, tmp_path, sample_run_log_full)
    # 6 output files: priority_list, campus_ALPHA, campus_BETA, whatsapp, run_log,
    # dashboard, report — at minimum priority_list + whatsapp + run_log + dashboard + report
    for key, path in result.items():
        assert isinstance(path, Path), f"Expected Path for key {key!r}, got {type(path)}"
        assert path.exists(), f"TEST-04: file missing for key {key!r}: {path}"
    # Assert the 5 non-campus keys are all present
    for required_key in ("priority_list", "whatsapp", "run_log", "dashboard", "report"):
        assert required_key in result, f"TEST-04: missing key {required_key!r} in result"
```

**Excel color assertion pattern** (lines 241-248 — TEST-04 color check):
```python
def test_priority_list_critical_row_color(priority_list_path: Path) -> None:
    wb = load_workbook(priority_list_path)
    ws = wb.active
    assert ws["A2"].fill.fgColor.rgb == cfg.COLOR_CRITICAL, (
        f"Expected CRITICAL fill {cfg.COLOR_CRITICAL} at A2, got {ws['A2'].fill.fgColor.rgb}"
    )
```
Note: `cfg.COLOR_CRITICAL` must equal `"00FFCCCC"` (8-char hex with alpha prefix per CLAUDE.md pitfall). This test is ALREADY PRESENT — verify `cfg.COLOR_CRITICAL` is defined with the correct 8-char value.

**tmp_path isolation pattern** (lines 98-141 — used for every file-writing test):
```python
def test_whatsapp_csv_only_critical_high(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    path = _write_whatsapp_csv(sample_df, tmp_path)
    result = pd.read_csv(path, dtype=str)
    ...
```
Every test that writes a file takes `tmp_path: Path` as a pytest fixture parameter. Never write to `outputs/`.

---

### `tests/conftest.py` — add shared minimal DataFrame fixture

**What to add:** A `minimal_enriched_df` fixture (D-05) — 5-10 rows, 2 campuses, all required columns, built inline with no file I/O. Used by `test_output_generator.py` and `test_llm_engine.py`.

**Analog:** `sample_csv_paths` fixture (lines 20-45) and the local `sample_df` fixture in `test_output_generator.py` (lines 26-76).

**Scope decision (Claude's Discretion):** Use `scope="function"` (not `scope="session"`) because `test_output_generator.py` tests add columns like `risk_score` and mutate DataFrames via `write_outputs`. Function scope gives each test a fresh copy.

**Env var pattern** (lines 14-15 — already present):
```python
# Ensure ANTHROPIC_API_KEY is set before any src.config import occurs.
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")
```
This is already established. Do not duplicate — conftest.py already handles env var patching at module level.

**Fixture pattern to add** (after line 104, following `csv_scenario`):
```python
@pytest.fixture()
def minimal_enriched_df() -> pd.DataFrame:
    """Minimal enriched DataFrame with 5 rows across 2 campuses for output/LLM tests.

    Built inline — no file I/O. Covers all 4 risk levels plus one extra CRITICAL row.
    Includes all columns produced by score_risk() and enrich_with_llm():
    student_id, student_name, campus_id, parent_phone, facilitator_email,
    risk_score, risk_level, attendance_rate, avg_practice_questions,
    trend_direction, days_since_last_note, recommended_action,
    facilitator_summary, whatsapp_message, generated_by, llm_error_reason,
    attendance_component, practice_component, trend_component, notes_component.
    """
    return pd.DataFrame({
        cfg.COL_STUDENT_ID:   ["S001", "S002", "S003", "S004", "S005"],
        cfg.COL_STUDENT_NAME: ["Alice", "Bob", "Carol", "Dave", "Eve"],
        cfg.COL_CAMPUS_ID:    ["C01", "C01", "C01", "C02", "C02"],
        cfg.COL_PARENT_PHONE: ["0501111111", "0502222222", "0503333333",
                               "0504444444", "0505555555"],
        cfg.COL_FACILITATOR_EMAIL: ["f@c01.sa"] * 3 + ["f@c02.sa"] * 2,
        cfg.COL_RISK_SCORE:   [90.0, 75.0, 40.0, 80.0, 15.0],
        cfg.COL_RISK_LEVEL:   ["CRITICAL", "CRITICAL", "MEDIUM", "CRITICAL", "LOW"],
        cfg.COL_ATTENDANCE_RATE:    [0.1, 0.3, 0.7, 0.2, 0.95],
        cfg.COL_AVG_PRACTICE:       [1.0, 2.0, 5.0, 1.5, 9.0],
        cfg.COL_TREND_DIR:          ["declining", "stable", "stable", "declining", "improving"],
        cfg.COL_DAYS_SINCE_NOTE:    [25, 15, 5, 20, 1],
        cfg.COL_RECOMMENDED_ACTION: [
            "Contact parent immediately",
            "Contact parent immediately",
            "Monitor progress",
            "Contact parent immediately",
            "Acknowledge progress",
        ],
        cfg.COL_FACILITATOR_SUMMARY: [
            "Alice is critical.", "Bob is critical.", None, "Dave is critical.", None,
        ],
        cfg.COL_WHATSAPP_MESSAGE: [
            "Message Alice.", "Message Bob.", None, "Message Dave.", None,
        ],
        cfg.COL_GENERATED_BY:      ["llm", "template", None, "llm", None],
        cfg.COL_LLM_ERROR_REASON:  [None, None, None, None, None],
        cfg.COL_ATTENDANCE_COMPONENT: [31.5, 24.5, 7.0, 28.0, 1.5],
        cfg.COL_PRACTICE_COMPONENT:   [27.0, 22.5, 12.0, 24.0, 3.0],
        cfg.COL_TREND_COMPONENT:      [20.0, 10.0, 10.0, 20.0, 0.0],
        cfg.COL_NOTES_COMPONENT:      [11.5, 8.0, 3.0, 10.5, 0.5],
    })
```

**Import to add at top of conftest.py** (after existing imports):
```python
from src import config as cfg
```

---

### `src/llm_engine.py` — verify `client=None` parameter

**Status: ALREADY IMPLEMENTED.** The function signature at line 221-225 is:
```python
def enrich_with_llm(
    df: pd.DataFrame,
    api_key: str,
    http_client: Optional[httpx.Client] = None,
) -> tuple[pd.DataFrame, dict]:
```

The `http_client=None` parameter is present. D-07 requires no code change to `src/llm_engine.py`. The existing tests already use `enrich_with_llm(df, "test-key", http_client=http_client)` (e.g., line 115).

**No modification needed.** If tests are failing due to this signature, the issue is in the test's call site or mock setup, not the parameter.

---

## Shared Patterns

### Environment Variable Setup
**Source:** `tests/conftest.py` lines 14-15
**Apply to:** All test files that import `src.config`
```python
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")
```
Already set at conftest module level — runs before any test file imports `src.config`. Do not duplicate in individual test files.

### caplog PII-Safe Log Assertion
**Source:** `tests/test_risk_engine.py` lines 445-463 + `tests/test_ingestion.py` lines 205-239
**Apply to:** Any new test asserting log safety
```python
with caplog.at_level(logging.INFO, logger="src.<module>"):
    <call under test>

for record in caplog.records:
    assert sensitive_value not in record.message, (
        f"PII leak: '{sensitive_value}' found in log: {record.message}"
    )
```

### respx Mock Injection
**Source:** `tests/test_llm_engine.py` lines 112-115
**Apply to:** All LLM tests requiring API mocking
```python
http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
result_df, counts = enrich_with_llm(df, "test-key", http_client=http_client)
```
`max_retries=0` is only needed when building an `Anthropic()` client directly (not used here — `http_client` injection bypasses the Anthropic constructor in tests).

### openpyxl Color Assertion
**Source:** `tests/test_output_generator.py` lines 241-248
**Apply to:** All Excel color tests
```python
assert ws["A2"].fill.fgColor.rgb == cfg.COLOR_CRITICAL
# cfg.COLOR_CRITICAL must equal "00FFCCCC" (8-char hex with alpha prefix)
# NOT "FFCCCC" — openpyxl always returns 8-char hex
```

### pytest.approx for Float Scores
**Source:** `tests/test_risk_engine.py` lines 76-81
**Apply to:** All risk_score assertions
```python
assert result[cfg.COL_RISK_SCORE].iloc[0] == pytest.approx(75.0, abs=0.01)
```

### tmp_path Isolation for File Writes
**Source:** `tests/test_output_generator.py` lines 98-105
**Apply to:** Every test that calls any `_write_*` or `write_outputs` function
```python
def test_something(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    path = _write_whatsapp_csv(sample_df, tmp_path)
    ...
```
Never pass `cfg.OUTPUT_DIR` or a real directory — always `tmp_path`.

### Module-level Helper Function (not a fixture)
**Source:** `tests/test_risk_engine.py` lines 24-59 + `tests/test_llm_engine.py` lines 29-65
**Apply to:** Any test file needing per-test row construction with overridable defaults
```python
def _build_student_row(
    student_id: str = "S0001",
    ...
) -> dict:
    """Build a minimal student row dict for pd.DataFrame([_build_student_row(...)])."""
    return { cfg.COL_STUDENT_ID: student_id, ... }
```
Use a module-level function (prefixed `_`) rather than a fixture when each test needs different override combinations. Use a fixture only for a single canonical shared DataFrame.

---

## No Analog Found

None. All 6 files have direct analogs in the existing codebase.

---

## Key Observations for Planner

1. **`enrich_with_llm` already has `http_client=None`** — D-07 (the only source change) is already done. Phase 7 is test-only work for this function.

2. **Most required tests already exist** — `test_ingestion.py` covers all 5 TEST-02 cases; `test_llm_engine.py` covers fallback and batching. The baseline run (D-01) is the critical first step to distinguish "test exists but failing" from "test genuinely missing."

3. **Boundary test `test_score_75_is_critical` is the key gap** — the existing parametrized `test_risk_level_boundaries` test calls `pd.cut` directly, not `score_risk()`. The new tests must go through `score_risk()` end-to-end. The planner must derive correct input values from the weighted formula (0.35*att + 0.30*prac + 0.20*trend + 0.15*notes = 75).

4. **conftest.py needs `from src import config as cfg`** — the new `minimal_enriched_df` fixture uses `cfg.COL_*` constants; this import is not currently in conftest.py (lines 1-17 only import `os`, `shutil`, `pathlib.Path`, `pytest`).

5. **D-06 integration test** — `test_write_outputs_all_paths_exist` (lines 599-608) already iterates all result values and asserts `path.exists()`. If TEST-04 requires a test named exactly `test_all_6_output_files_exist`, add it as a thin alias calling the same fixture + assertion with the explicit 6-file check.

---

## Metadata

**Analog search scope:** `tests/`, `src/`
**Files scanned:** 10 test files, 2 source modules (`src/llm_engine.py`, `src/config.py`)
**Pattern extraction date:** 2026-05-24
