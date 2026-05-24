---
phase: 07-test-suite
reviewed: 2026-05-25T00:21:00+03:00
depth: standard
files_reviewed: 6
files_reviewed_list:
  - tests/conftest.py
  - tests/test_risk_engine.py
  - tests/test_ingestion.py
  - tests/test_config.py
  - tests/test_llm_engine.py
  - tests/test_output_generator.py
findings:
  critical: 3
  warning: 6
  info: 3
  total: 12
status: fixed
---

# Phase 7: Code Review Report

**Reviewed:** 2026-05-25T00:21:00+03:00
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed six test files added/modified during Phase 7 (Test Suite). The suite is well-structured overall: fixtures are clean, respx injection is correctly wired, and the PII-safety and boundary tests are thorough. However three critical defects were found — two assertions that will silently pass when the production behaviour is wrong, and one test that hard-codes an assumption about the `multi_campus_df` fixture column set that does not match `OUTPUT_COLS_CAMPUS`. Six warnings cover weaknesses in assertion strength, a fixture shared-state risk, a misleading test name, and an incomplete source-scan for bare strings. Three info items call out minor improvements.

---

## Critical Issues

### CR-01: `test_campus_dashboard_medium_llm_cells_empty` will silently pass even when LLM columns ARE populated for MEDIUM rows

**File:** `tests/test_output_generator.py:432-455`

**Issue:** The `multi_campus_df` fixture used by this test (line 298) does **not** include `cfg.COL_LLM_ERROR_REASON` in its columns. `OUTPUT_COLS_CAMPUS` only contains `COL_FACILITATOR_SUMMARY`, `COL_WHATSAPP_MESSAGE`, and `COL_GENERATED_BY` (the 13th, 14th, and 15th columns). The test asserts `medium_row[12]`, `medium_row[13]`, and `medium_row[14]` are `None`.

However, the `multi_campus_df` fixture omits `cfg.COL_LLM_ERROR_REASON` entirely. When `_write_campus_dashboards` is called, it selects `df_out = campus_df[list(cfg.OUTPUT_COLS_CAMPUS)]` — a 15-column slice. If `COL_LLM_ERROR_REASON` is not in the fixture DataFrame and `OUTPUT_COLS_CAMPUS` does not include it (it does not — verified in `config.py`), the column slice succeeds. But the deeper issue is that the fixture's `COL_GENERATED_BY` column for the MEDIUM row is `None` (line 345), and `COL_WHATSAPP_MESSAGE` is also `None` (line 340), and `COL_FACILITATOR_SUMMARY` is also `None` (line 332) — so **the assertion is true by fixture construction, not by production code behaviour**. If `_write_campus_dashboards` were changed to write `""` instead of `None` for MEDIUM LLM cells, this test would still pass because the fixture value going in is already `None`, and the production code path for LLM-ineligible rows explicitly sets `value = None` (overwriting the fixture value). The test cannot catch a regression where `_write_campus_dashboards` writes the original (non-None) value through for a MEDIUM row that had a non-None LLM column value in the input DataFrame.

**Fix:** Build a fixture variant where the MEDIUM row has a non-None value in the LLM columns going in, then assert they are written as `None` (or empty) in the output:

```python
# In the test body, not from the fixture:
df_with_llm_on_medium = multi_campus_df.copy()
medium_mask = df_with_llm_on_medium[cfg.COL_RISK_LEVEL] == "MEDIUM"
df_with_llm_on_medium.loc[medium_mask, cfg.COL_FACILITATOR_SUMMARY] = "Should be suppressed"
df_with_llm_on_medium.loc[medium_mask, cfg.COL_WHATSAPP_MESSAGE] = "Should be suppressed"
df_with_llm_on_medium.loc[medium_mask, cfg.COL_GENERATED_BY] = "llm"
paths = _write_campus_dashboards(df_with_llm_on_medium, tmp_path)
# ... existing assertions on medium_row[12], [13], [14] ...
```

---

### CR-02: `test_fallback_to_template` mocks `httpx.TimeoutException` but the production fallback path only catches `anthropic.APIError` subtypes — the test assertion on `llm_error_reason='timeout'` can silently pass for the wrong reason

**File:** `tests/test_llm_engine.py:266-298`

**Issue:** In `llm_engine.py`, the Layer 1 try/except catches `anthropic.APIConnectionError`, `anthropic.APITimeoutError`, `anthropic.RateLimitError`, and `anthropic.APIStatusError` — all are `anthropic.APIError` subclasses. The `_classify_error` helper (line 112) maps `anthropic.APITimeoutError` to `"timeout"`.

The test mock raises `httpx.TimeoutException` directly (line 279). This is a **raw httpx exception**, not an `anthropic.APITimeoutError`. It does not match the Layer 1 anthropic exception handlers. It will instead fall through to the second except clause at line 462: `except (KeyError, ValueError, StopIteration)` — which also does not match. With `max_retries=0` and the httpx mock transport, the Anthropic SDK wraps the raw `httpx.TimeoutException` into an `anthropic.APITimeoutError` before it surfaces to user code (the SDK's httpx transport translates transport exceptions). So the test may happen to pass because the SDK does the wrapping.

However, the test asserts `llm_error_reason == "timeout"` but `_classify_error` is only called in the Layer 1 anthropic exception handler — if the SDK wrapping is ever changed or the version changes, this chain can break silently. More critically, the test **does not assert** that `counts["api_calls_made"] == 0` (API did not succeed) which would confirm the fallback actually triggered rather than a spurious no-op. Without that check, if `enrich_with_llm` were changed to produce `generated_by='template'` by default for all rows, this test would still pass.

**Fix:** Add an explicit assertion that the API call was attempted and failed:

```python
assert counts["api_calls_made"] == 0, (
    "LLM-05: fallback path must not count the failed call as a successful api_call"
)
# Also assert the whatsapp_message is non-empty (already present at line 296 — keep it)
# And confirm respx intercepted exactly one call:
assert len(respx_mock.calls) == 1, (
    "LLM-05: exactly one API attempt must have been made before falling back to template"
)
```

---

### CR-03: `test_no_bare_column_strings_in_llm_engine` allowlist includes `"output"` and `"input"` — these are actual DataFrame-adjacent key names that could mask a real column-name leak

**File:** `tests/test_llm_engine.py:583-584`

**Issue:** The `allowed` set at line 557 contains `"input"` and `"output"` (lines 583-584). These are listed as "Anthropic API message structure keys". However, `"input"` and `"output"` are 5-char strings matching the regex `r'"([a-z][a-z0-9_]{3,})"'`. The intent of the scan is to catch any bare column-name string literal that should use a `cfg.COL_*` constant. Neither `"input"` nor `"output"` is a DataFrame column name in this project, so including them in the allowed set is not wrong per se — but `"output"` also appears as the return dict key in the `tokens` accumulator (`tokens["output"]`), which is not a DataFrame column.

The real defect is that the `known_column_values` set at line 599 is **hard-coded** and diverges from the actual column constants in `config.py`. It lists `"session_attended_min"` and `"practice_questions"` directly (lines 601), but if `config.py` ever renames these constants the scan would stop enforcing the rule for those column names. More critically, it does not include `"llm_error_reason"` as a known column value to prohibit — yet `cfg.COL_LLM_ERROR_REASON = "llm_error_reason"` is a real column. `"llm_error_reason"` is 16 chars, matches the regex, and is in the `allowed` set at line 563 (`"malformed_response"` is there but not `"llm_error_reason"` itself). Actually checking: `"llm_error_reason"` is NOT in the allowed set, and it IS in `known_column_values` at line 605 — so it is correctly caught. But `"llm_disabled"` is in the allowed set (line 562) even though `"llm_disabled"` is an error-reason string value, not a column name — which is fine.

The real gap: `"max_tokens"` was added to the allowed set (the context notes a post-merge fix at 12:17a). Verify this landed correctly by checking it is in the allowed set — it is at line 585. That is correct since `max_tokens` is an Anthropic API parameter, not a column name.

The actual critical defect here is different: the `known_column_values` set uses string literals typed by hand. If the test is the guard against bare strings, **the test's own guard list is itself a set of bare strings that could drift from `config.py`**. A developer adding a new `COL_*` constant to `config.py` would need to remember to update both `config.py` and this test's `known_column_values` set — the test does not auto-derive it from `cfg`. This means the test can silently fail to catch a new column name being used as a bare string in `llm_engine.py`.

**Fix:** Derive `known_column_values` from `config.py` constants at test runtime:

```python
known_column_values: set[str] = {
    v for k, v in vars(cfg).items()
    if k.startswith("COL_") and isinstance(v, str)
}
```

This ensures the set is always in sync with `config.py` and new columns are automatically covered.

---

## Warnings

### WR-01: `test_risk_score_weighted_formula` constructs `worst_row` outside the `freeze_time` context manager

**File:** `tests/test_risk_engine.py:194-221`

**Issue:** `worst_row` is constructed at line 195 before the `with freeze_time("2026-05-23"):` block at line 203. The `latest_note_date=pd.NaT` argument means the notes component is always 100.0 (NaT → 30 days → max penalty), so `freeze_time` does not affect that specific row. However, the test comment at line 193 says "NaT latest_note_date" which is fine. The real risk is consistency: `perfect_row` and `partial_row` both depend on `freeze_time` for their `notes_component=0` (note today), but `worst_row` is built outside. If a future maintainer changes `worst_row` to use a specific date instead of NaT, the frozen date context is no longer in effect, making the row construction produce a different `notes_component` than expected. The test is currently correct but fragile.

**Fix:** Move `worst_row` construction inside the `with freeze_time` block for consistency:

```python
with freeze_time("2026-05-23"):
    worst_row = _build_student_row(...)
    perfect_row = _build_student_row(...)
    partial_row = _build_student_row(...)
    df = pd.DataFrame([worst_row, perfect_row, partial_row])
    result = score_risk(df)
```

---

### WR-02: `test_medium_low_students_skipped` does not assert `COL_LLM_ERROR_REASON` is also None/NaN

**File:** `tests/test_llm_engine.py:105-131`

**Issue:** The test asserts `COL_GENERATED_BY`, `COL_FACILITATOR_SUMMARY`, and `COL_WHATSAPP_MESSAGE` are all NaN/None for MEDIUM/LOW rows (lines 120-128). But `enrich_with_llm` initialises four output columns to `None` for all rows: `COL_FACILITATOR_SUMMARY`, `COL_WHATSAPP_MESSAGE`, `COL_GENERATED_BY`, and `COL_LLM_ERROR_REASON`. The fourth column (`COL_LLM_ERROR_REASON`) is not checked. If a future change sets `llm_error_reason='skipped'` for MEDIUM/LOW rows (which the docstring explicitly forbids — D-07 says "None"), the test would not catch it.

**Fix:** Add:
```python
assert result_df[cfg.COL_LLM_ERROR_REASON].isna().all(), (
    "LLM-01: MEDIUM/LOW rows must have None/NaN in llm_error_reason (D-07)"
)
```

---

### WR-03: `test_token_logging` assertion is too weak — `"150" in caplog.text` can pass spuriously

**File:** `tests/test_llm_engine.py:337-340`

**Issue:** The assertion is `"150" in caplog.text or "token" in caplog.text.lower()`. The `or` means the test passes if either condition is true. Since `enrich_with_llm` logs a completion message at INFO level that contains the word `"token"` (line 473 of `llm_engine.py`: `"tokens_input={tokens['input']}"`) regardless of whether any call was made, the `"token" in caplog.text.lower()` branch will always be true after any successful call. The `"150"` branch — which actually checks the specific input token count — is never needed to satisfy the assertion. A regression that logs the wrong token count (e.g., always 0) would still pass this test.

**Fix:** Tighten the assertion to require the actual value:
```python
assert "150" in caplog.text, (
    "TEST-03: input token count '150' must appear in log output after successful API call"
)
assert "80" in caplog.text, (
    "TEST-03: output token count '80' must appear in log output after successful API call"
)
```

---

### WR-04: `minimal_enriched_df` fixture comment describes wrong row distribution — Row 1 (S002) is labelled CRITICAL with risk_score=75.0 but component math yields ~65.0

**File:** `tests/conftest.py:169-179`

**Issue:** The inline comment block at lines 169-172 notes:
```
# Row 1 (S002): 24.5 + 22.5 + 10.0 +  8.0 = 65.0 (risk_score stored as 75.0 — fixture)
```
The fixture stores `risk_score=75.0` and `risk_level="CRITICAL"` for S002 but the components sum to 65.0. This is a deliberately inconsistent fixture — acknowledged with the "fixture" note. However, this creates a latent trap: any test that calls `score_risk()` on this fixture and then checks risk_level will get a different result from the stored values. The fixture is only safe to use with `output_generator` and `llm_engine` tests (which treat risk_score/risk_level as data, not recompute them). The docstring at line 114 does say "for output/LLM tests" but does not warn against passing it to `score_risk()`.

More concretely: `test_all_6_output_files_exist` (line 611 of `test_output_generator.py`) calls `write_outputs(minimal_enriched_df, ...)` — this is correct. But any future test that imports `minimal_enriched_df` and feeds it to `score_risk()` will silently get a different `risk_level` for S002 than the fixture promises.

**Fix:** Add a clear warning to the fixture docstring:
```python
# WARNING: risk_score/risk_level values are NOT recomputable from the component
# columns — S002 stores risk_score=75.0 but components sum to 65.0. This fixture
# is ONLY valid for output_generator and llm_engine tests. Do NOT pass to score_risk().
```

---

### WR-05: `test_chunk_size_limit` parses student IDs from the prompt text using a fragile regex — test can under-count students per chunk

**File:** `tests/test_llm_engine.py:419-436`

**Issue:** The `_make_response_for_call` side-effect function (line 412) determines which students are in each API call chunk by parsing the raw request body with `re.findall(r"S\d{4}", content_text)` (line 421). This is brittle in two ways:

1. `_build_prompt` (in `llm_engine.py` line 164) formats the student data as `str(student_data)` — a Python list-of-dicts `repr`. The student_id format is `f"S{i:04d}"` which for `i` in range 15 gives `S0000` through `S0014`. The regex `S\d{4}` will match these. But if the prompt format ever changes (e.g., JSON serialisation instead of Python repr), the regex may stop matching.

2. The real consequence: if the regex fails to find student IDs (returns an empty list), `student_results` is empty, `_make_tool_response([])` returns a valid response with zero students, `_write_results_back` is called with an empty list (no-op), and the assertion `len(respx_mock.calls) == 2` still passes — but the students never get their results written back. The test only asserts call count, not that all 15 students were enriched.

**Fix:** Assert that all 15 students have non-None `generated_by` after the call:
```python
assert result_df[cfg.COL_GENERATED_BY].notna().sum() == 15, (
    "LLM-09: all 15 students must have generated_by populated after 2 chunks"
)
```

---

### WR-06: `test_no_bare_column_strings_in_risk_engine` strips only `"""` docstrings, not `'''` docstrings, and the stripping is applied sequentially — nested quote styles can defeat the strip

**File:** `tests/test_risk_engine.py:553-554`

**Issue:** Lines 553-554 strip `"""` docstrings first, then `'''` docstrings. The regex `r'""".*?"""'` with `DOTALL` will strip all `"""..."""` blocks. If a `"""` docstring contains `'''`, the outer `'''` strip would find nothing. This is fine for normal code. However, the `re.sub` for `'''` docstrings runs on the output of the `"""` strip — if any `'''` strings remain they are caught. The logic is correct in practice.

The real issue is that the same pattern is used in `test_no_bare_column_strings_in_llm_engine` (lines 546-547 of `test_llm_engine.py`) but only strips `"""` style, not `'''` style. If `llm_engine.py` ever gains a `'''` docstring, those contents would be scanned as code. Currently `llm_engine.py` uses only `"""` docstrings, so this is latent. But `test_risk_engine.py` strips both `"""` and `'''` while `test_llm_engine.py` only strips `"""` — the two tests are inconsistent.

**Fix:** Align `test_no_bare_column_strings_in_llm_engine` to match `test_risk_engine.py` by adding the `'''` strip:
```python
no_docstrings = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
no_docstrings = re.sub(r"'''.*?'''", "", no_docstrings, flags=re.DOTALL)
no_comments = re.sub(r"#.*", "", no_docstrings)
```

---

## Info

### IN-01: `test_config.py` `TestColumnConstants` lists 21 expected constants but the docstring says "17 from Phase 1 + 4 D-09 component columns" — the 4 LLM columns are not tested

**File:** `tests/test_config.py:74-107`

**Issue:** `config.py` defines 25 column constants (5 metadata + 3 metrics + 2 notes + 7 derived risk + 4 component + 4 LLM = 25). `TestColumnConstants.EXPECTED_COLUMN_CONSTANTS` lists 21 — it is missing all four LLM column constants: `COL_FACILITATOR_SUMMARY`, `COL_WHATSAPP_MESSAGE`, `COL_GENERATED_BY`, and `COL_LLM_ERROR_REASON`. The class docstring says "17 from Phase 1 + 4 D-09 component columns" which implies only 21 were expected when this test was written (pre-Phase 3). Phase 3 added the 4 LLM columns to `config.py` but this test was not updated.

**Fix:** Add the four missing LLM constants to `EXPECTED_COLUMN_CONSTANTS`:
```python
"COL_FACILITATOR_SUMMARY",
"COL_WHATSAPP_MESSAGE",
"COL_GENERATED_BY",
"COL_LLM_ERROR_REASON",
```
And update the docstring count from 21 to 25.

---

### IN-02: `test_report_data_quality_no_warnings` asserts the full phrase "No data quality issues" but the production string is "No data quality issues detected."

**File:** `tests/test_output_generator.py:825-833`

**Issue:** `output_generator.py` line 362 writes:
```python
"No data quality issues detected. All student records were complete and valid."
```
The test asserts `"No data quality issues" in all_text` (line 832). This passes because `"No data quality issues"` is a substring of the production string. This is correct and not a bug. However it creates a maintenance risk: if the message is changed to e.g., `"Zero data quality issues detected."`, the test would fail — but with a confusing message since the assertion checks a substring. Consider asserting the full phrase to make intent explicit:

```python
assert "No data quality issues detected." in all_text, ...
```

---

### IN-03: Dead import — `re` is imported in `tests/test_llm_engine.py` at the module level but also imported again inside `_make_response_for_call` as `import re as _re`

**File:** `tests/test_llm_engine.py:9` and `tests/test_llm_engine.py:420`

**Issue:** `re` is imported at the module top (line 9). Inside `_make_response_for_call` (line 420), it is imported again as `import re as _re`. The inner import is redundant and slightly misleading (it suggests the outer `re` is not accessible, which it is). Both `_json` and `_re` shadow module-level names with local aliases inside the nested function.

**Fix:** Remove the local re-import and use the module-level `re` directly:
```python
# Remove: import re as _re
student_ids_in_chunk = re.findall(r"S\d{4}", content_text)
```

---

_Reviewed: 2026-05-25T00:21:00+03:00_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
