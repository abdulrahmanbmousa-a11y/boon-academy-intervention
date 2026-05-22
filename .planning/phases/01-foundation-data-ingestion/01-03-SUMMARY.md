---
phase: 01-foundation-data-ingestion
plan: "03"
subsystem: ingestion
tags:
  - ingestion
  - pandas
  - csv-cleaning
  - per-row-error-containment
  - tdd
dependency_graph:
  requires:
    - 01-01 (src/config.py — column constants, DATA_DIR)
    - 01-02 (tests/fixtures/*.csv, tests/conftest.py)
  provides:
    - src.ingestion.ingest(data_paths) -> pd.DataFrame (locked contract)
    - df.attrs["data_quality_warnings"] side-channel
    - Canonical DataFrame schema (frozen for Phases 2-8)
  affects:
    - All downstream phases (2-8) depend on the locked ingest() signature
    - Phase 2 risk_engine.score_risk() consumes the DataFrame schema produced here
    - Phase 4 output_generator reads df.attrs["data_quality_warnings"] for run_log.json
tech_stack:
  added: []
  patterns:
    - Pattern 2 — dtype-locked CSV reader (all columns as "string" or explicit numeric)
    - Pattern 3 — per-row error containment (errors='coerce', warnings accumulator)
    - Pattern 4 — three-CSV aggregate-before-merge strategy
    - Numeric columns loaded as "string" dtype to survive type mismatches; pd.to_numeric(errors='coerce') applied in _fill_numeric_with_zero
    - Post-merge numeric fill (0) for students with no metrics rows
    - PII-safe logging — student_id only, never student_name/parent_phone/note_text (Security V7)
key_files:
  created:
    - src/ingestion.py
    - tests/test_ingestion.py
  modified: []
decisions:
  - "Numeric columns (session_attended_min, practice_questions) loaded as string dtype rather than Float64 in DTYPE_METRICS — prevents read_csv crashing on type mismatch strings like 'many'/'abc'. pd.to_numeric(errors='coerce') in _fill_numeric_with_zero does the actual type conversion."
  - "Post-merge numeric fill added for session_total_min, practice_total_q, attendance_days — students with no metrics entries get 0 rather than NaN after the left join."
  - "Module-level _unknown_counter reset at the start of each ingest() call — ensures UNKNOWN_NNN placeholders are deterministic and start at 001 per pipeline run."
metrics:
  duration: "~25 minutes"
  completed: "2026-05-22"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 0
  tests_added: 10
  tests_passing: 25
---

# Phase 1 Plan 03: Ingestion Module Summary

**One-liner:** dtype-locked three-CSV ingestion with per-row error containment, UNKNOWN placeholder IDs, NaT date coercion, and PII-safe logging — 10 tests green, 300 students ingested, 303 warnings captured.

## What Was Built

Two files delivering the canonical ingestion contract for all downstream phases:

- `src/ingestion.py` — 389-line implementation of Pattern 2 (dtype-locked reader), Pattern 3 (per-row error containment), and Pattern 4 (aggregate-before-merge) from 01-RESEARCH.md. Public function `ingest(data_paths)` is the locked Phase 1→2 boundary.
- `tests/test_ingestion.py` — 10 tests covering DATA-02 through DATA-08 plus Security V7 (PII-safe logging via caplog).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| Task 1 | Write tests/test_ingestion.py (RED) | 3a94020 | tests/test_ingestion.py |
| Task 2 | Implement src/ingestion.py (GREEN) | 6e22e21 | src/ingestion.py |
| Task 3 | End-to-end smoke — generate_data + main.py | (no commit — verification only) | — |

## Verification Results

All plan verification checks passed:

- `pytest tests/test_ingestion.py -v` — 10/10 tests pass
- `pytest tests/ -v` — 25/25 tests pass (config:6 + generate_data:7 + ingestion:10 + no_hardcoded_paths:1 + package_structure:1)
- Locked signature verified: `ingest(data_paths)` — single parameter
- All functions have return type annotations and docstrings (INFRA-08)
- No hardcoded path literals in src/ingestion.py
- `pd.read_csv` always uses `dtype=` argument
- `py -3.12 -m src.generate_data` exits 0 — generates 309 rows (300 base + ~3% dupes = 9 extra)
- `py -3.12 main.py` exits 0 — logs "Ingested 300 students"
- Second run produces identical output (idempotent)
- `df.attrs["data_quality_warnings"]` populated with 303 entries after synthetic data ingestion

## Actual Run Metrics (synthetic data, seed=42)

| Metric | Value |
|--------|-------|
| Students ingested | 300 |
| Total warnings | 303 |
| missing_numeric warnings | 210 |
| type_mismatch warnings | 84 |
| duplicate_id warnings | 9 |
| bad_date warnings | 0 |
| missing_id warnings | 0 |

Notes: The 0 bad_date count is expected — generate_data.py injects type mismatches in numeric columns but not in date columns. The 9 duplicate_id warnings match the ~3% duplicate injection rate (300 × 3% = 9).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Numeric columns loaded as string instead of Float64 in DTYPE_METRICS**

- **Found during:** Task 2 Task 3 smoke run
- **Issue:** `dtype="Float64"` in `pd.read_csv` causes a hard `ValueError: Unable to parse string "many"` crash when the generated data contains type mismatches in `practice_questions`. Pattern 3's `errors='coerce'` protection only works AFTER loading — read_csv with Float64 dtype validates during parse.
- **Fix:** Changed `COL_SESSION_MIN` and `COL_PRACTICE_Q` dtype in DTYPE_METRICS from `"Float64"` to `"string"`. Added `_NUMERIC_DTYPE = "Float64"` constant. `_fill_numeric_with_zero` now calls `pd.to_numeric(errors='coerce')` then `.astype(_NUMERIC_DTYPE)` — the final column dtype in the DataFrame is still Float64 as intended.
- **Files modified:** src/ingestion.py
- **Commit:** 6e22e21

**2. [Rule 1 - Bug] Post-merge NaN fill for students with no metrics rows**

- **Found during:** Task 2 first test run (`test_missing_numeric_filled_with_zero` failure)
- **Issue:** The happy fixture has 5 metadata students but only 2 students with metrics rows. After a left merge, `session_total_min` and `practice_total_q` are NaN for the 3 students with no metrics — even though individual rows were fill-imputed. The test assertion `df["session_total_min"].notna().all()` failed because the NaN arose from the merge, not from individual row parsing.
- **Fix:** Added post-merge fill loop for `["session_total_min", "practice_total_q", "attendance_days"]` columns to fill NaN with 0 for students with no metrics entries. This is consistent with D-09 (0 = no activity, conservative risk).
- **Files modified:** src/ingestion.py
- **Commit:** 6e22e21

## Requirements Addressed

| Requirement | Status | Evidence |
|-------------|--------|---------|
| DATA-02 | Done | test_phone_stays_string + test_student_id_is_string — dtype=StringDtype preserved |
| DATA-03 | Done | test_missing_numeric_filled_with_zero — NaN → 0 with warning |
| DATA-04 | Done | test_duplicate_ids_deduped — keep=last dedup with duplicate_id warning |
| DATA-05 | Done | test_type_mismatch_safe_default — abc/many coerced to 0, row preserved |
| DATA-06 | Done | test_merge_one_row_per_student — exactly one row per metadata student |
| DATA-07 | Done | test_warnings_attached_to_df — df.attrs['data_quality_warnings'] is list[dict] |
| DATA-08 | Done | test_bad_record_does_not_crash + test_empty_csv_handled — no raise on bad/empty input |
| INFRA-01 | Done | main.py wires ingest() correctly — pipeline runs end-to-end |
| INFRA-08 | Done | All 6 functions have return type annotations and docstrings |

## Known Stubs

None — src/ingestion.py is fully implemented. Downstream stubs (risk_engine, llm_engine, output_generator) are intentional and unchanged.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`. All mitigations applied:

- T-03-01: PII-safe logging enforced — test_pii_safe_logging via caplog confirms no student_name/phone/note_text in log output
- T-03-03: Per-row error containment verified — test_bad_record_does_not_crash and test_empty_csv_handled
- T-03-04: Locked signature preserved — `ingest(data_paths: dict[str, Path]) -> pd.DataFrame`
- T-03-06: Type mismatch safe default — pd.to_numeric(errors='coerce') in _fill_numeric_with_zero
- T-03-07: Date ambiguity prevention — explicit format="%Y-%m-%d" in _coerce_dates

## Self-Check: PASSED

Files verified on disk:
- src/ingestion.py: FOUND
- tests/test_ingestion.py: FOUND

Commits verified:
- 3a94020: test(01-03): add failing tests for ingestion module (RED)
- 6e22e21: feat(01-03): implement src/ingestion.py — dtype-locked CSV ingestion with per-row error containment (GREEN)
