# Phase 7 — Baseline Pytest Run

**Captured:** 2026-05-24
**Executor:** Agent aaa7d326fe641eec5 (07-01 Wave 0)

---

## Baseline Command

```
py -3.12 -m pytest tests/ -v --tb=short
```

Python version: 3.12.1
pytest version: 8.3.5
Platform: win32
Plugins: anyio-4.13.0, cov-7.1.0, mock-3.15.1, respx-0.23.1

---

## Summary Line

```
1 failed, 110 passed in 7.31s
```

Total collected: 111 items

---

## Failures By Test File

### `tests/test_config.py`

| Test | Failure Synopsis |
|------|-----------------|
| `TestFailLoudBehavior::test_missing_api_key_raises` | `Failed: DID NOT RAISE <class 'KeyError'>` — `os.environ["ANTHROPIC_API_KEY"]` evaluated successfully even with the key absent (conftest sets `ANTHROPIC_API_KEY=dummy-key-for-tests` before src.config is imported, so config never gets a chance to raise) |

---

## TEST-01..TEST-04 Gap Analysis

### TEST-01 — `tests/test_risk_engine.py` (boundary + formula + all-zeros + perfect student)

| Required Case | Test Function | Status |
|---------------|---------------|--------|
| boundary: score == 75 → CRITICAL (via `score_risk()` end-to-end) | `test_score_75_is_critical` | MISSING |
| boundary: score == 74 → HIGH (via `score_risk()` end-to-end) | `test_score_74_is_high` | MISSING |
| boundary tests via `pd.cut` (75.0-CRITICAL, 74.99-HIGH, etc.) | `test_risk_level_boundaries[...]` | OK (passes but calls pd.cut directly, not score_risk) |
| all-zeros student → CRITICAL (worst case) | `test_worst_student_is_critical` | OK |
| perfect student → LOW | `test_perfect_student_is_low` | OK |
| weighted formula (attendance 35%, practice 30%, trend 20%, notes 15%) | `test_risk_score_weighted_formula` | OK |
| each component column exists | `test_required_output_columns_present` | OK |

**Gap summary:** 2 MISSING — `test_score_75_is_critical` and `test_score_74_is_high` that exercise `score_risk()` end-to-end at exact boundary values.

---

### TEST-02 — `tests/test_ingestion.py` (edge case handling)

| Required Case | Test Function | Status |
|---------------|---------------|--------|
| Missing numeric values filled with 0 | `test_missing_numeric_filled_with_zero` | OK |
| Duplicate student_id rows → deduplicated | `test_duplicate_ids_deduped` | OK |
| Empty CSV → does not crash, valid DataFrame | `test_empty_csv_handled` | OK |
| Bad date format → safe default (no exception) | `test_bad_record_does_not_crash` | OK |
| Type mismatch → coerced or safe default | `test_type_mismatch_safe_default` | OK |

**Gap summary:** 0 MISSING, 0 FAIL — all 5 TEST-02 cases present and passing.

Note: Test function names differ from D-03 spec (e.g., `test_duplicate_ids_deduped` vs `test_duplicate_student_ids_deduplicated`). These are passing tests — renaming is a Wave 1 discretionary item per D-01 (fix only real failures).

---

### TEST-03 — `tests/test_llm_engine.py` (fallback, token logging, batching)

| Required Case | Test Function | Status |
|---------------|---------------|--------|
| LLM fallback trigger (mock API failure, verify template used and labeled) | `test_fallback_to_template` | OK |
| Token logging test (mock success, verify tokens logged) | `test_token_logging` | OK |
| Batching test (verify campus grouping — 2 campuses → 2 API calls) | `test_campus_batching` | OK |

**Gap summary:** 0 MISSING, 0 FAIL — all 3 TEST-03 cases present and passing.

---

### TEST-04 — `tests/test_output_generator.py` (output files, colors, columns, HTML JSON)

| Required Case | Test Function | Status |
|---------------|---------------|--------|
| All 6 output files exist after generation | `test_write_outputs_all_paths_exist` | OK |
| Excel has correct columns | `test_priority_list_file_exists`, `test_campus_dashboard_column_count` | OK |
| Excel has correct color coding (CRITICAL row = FFFFCCCC) | `test_priority_list_critical_row_color`, `test_campus_dashboard_critical_row_color` | OK |
| CSV has correct columns | `test_whatsapp_csv_columns` | OK |
| HTML contains embedded JSON | `test_write_outputs_html_contains_embedded_json` | OK |

**Gap summary:** 0 MISSING, 0 FAIL — all TEST-04 cases present and passing.

---

## Priority Order Per D-02

Ordered per decision D-02: TEST-01..TEST-04 gaps first, then all other failures.

### Priority 1 — TEST-01..TEST-04 MISSING and FAIL items

1. **TEST-01 MISSING:** `test_score_75_is_critical` — add to `tests/test_risk_engine.py`; must call `score_risk()` end-to-end and assert `risk_score==75.0` → `risk_level=="CRITICAL"`. Target file: **07-02-PLAN.md**
2. **TEST-01 MISSING:** `test_score_74_is_high` — add to `tests/test_risk_engine.py`; must call `score_risk()` end-to-end and assert `risk_score==74.0` → `risk_level=="HIGH"`. Target file: **07-02-PLAN.md**

### Priority 2 — Other failures (non-TEST-01..TEST-04)

3. **FAIL:** `tests/test_config.py::TestFailLoudBehavior::test_missing_api_key_raises` — the test expects `os.environ["ANTHROPIC_API_KEY"]` to raise `KeyError` when the key is absent. It does not raise because `conftest.py` calls `os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")` at module scope before any test runs, so the key is always set. Fix options: (a) change the test to temporarily delete the env var using `monkeypatch.delenv` + import isolation, or (b) accept that this is a test isolation design issue and document it. This is in `test_config.py` (not in TEST-01..04 scope). Target file: **07-03-PLAN.md** or deferred.

---

## Notes

- All `test_generate_data.py` tests PASS (7/7)
- All `test_no_hardcoded_paths.py` tests PASS (1/1)
- All `test_package_structure.py` tests PASS (1/1)
- All `test_ingestion.py` tests PASS (10/10)
- All `test_llm_engine.py` tests PASS (12/12)
- All `test_output_generator.py` tests PASS (34/34)
- `test_risk_engine.py` tests PASS (20/20) — but 2 test functions required by TEST-01 are MISSING (not failing, simply absent)
- `test_config.py` has 1 FAIL out of 12 tests

Wave 1 plans (07-02 and 07-03) MUST fix only the items listed in this baseline document per D-01.
