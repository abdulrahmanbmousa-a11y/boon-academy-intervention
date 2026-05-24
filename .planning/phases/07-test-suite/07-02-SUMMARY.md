---
phase: 07-test-suite
plan: "02"
subsystem: test-risk-engine-ingestion
tags: [testing, TEST-01, TEST-02, boundary-tests, ingestion, D-03]

dependency_graph:
  requires:
    - "07-01-BASELINE.md: authoritative failure list — fixed only real failures, not preemptive rewrites"
    - "tests/conftest.py: minimal_enriched_df fixture (Wave 0)"
  provides:
    - "tests/test_risk_engine.py: test_score_75_is_critical and test_score_74_is_high end-to-end boundary tests"
    - "tests/test_ingestion.py: D-03 canonical function names for 5 edge-case tests"
    - "tests/test_config.py: load_dotenv patch so test_missing_api_key_raises correctly observes KeyError"
  affects:
    - "Full test suite: all TEST-01 and TEST-02 requirements now covered"

tech_stack:
  added: []
  patterns:
    - "Construct exact-score inputs via WEIGHTS dict arithmetic (not pd.cut direct) for boundary tests"
    - "monkeypatch.setattr('dotenv.load_dotenv', ...) to isolate env-var contract tests from .env files"
    - "D-03 canonical names — rename-not-rewrite pattern for ingestion edge case tests"

key_files:
  created: []
  modified:
    - "tests/test_risk_engine.py"
    - "tests/test_ingestion.py"
    - "tests/test_config.py"

commits:
  - "13aacac: test(07-02): add test_score_75_is_critical and test_score_74_is_high end-to-end boundary tests"
  - "c0fce79: refactor(07-02): rename ingestion tests to D-03 required names (TEST-02)"
  - "0bcc845: fix(07-02): patch load_dotenv in test_missing_api_key_raises so .env cannot mask KeyError (D-08)"

test_results:
  command: "py -3.12 -m pytest tests/test_risk_engine.py tests/test_ingestion.py tests/test_config.py tests/test_generate_data.py tests/test_package_structure.py tests/test_no_hardcoded_paths.py -v"
  passed: 62
  failed: 0
  status: green

## Self-Check: PASSED

All must-haves verified:

- [x] test_score_75_is_critical defined in test_risk_engine.py — calls score_risk() end-to-end, asserts risk_level == "CRITICAL"
- [x] test_score_74_is_high defined in test_risk_engine.py — calls score_risk() end-to-end, asserts risk_level == "HIGH"
- [x] test_empty_csv_does_not_crash, test_duplicate_student_ids_deduplicated, test_missing_values_filled_with_zero present with D-03 names
- [x] py -3.12 -m pytest tests/test_risk_engine.py tests/test_ingestion.py -v exits 0
- [x] All TEST-01 and TEST-02 BASELINE.md entries are now OK
- [x] test_config.py::TestFailLoudBehavior::test_missing_api_key_raises now PASSES (load_dotenv patched)

## What Was Built

**TEST-01 boundary tests** (`tests/test_risk_engine.py`): Two new end-to-end tests construct input rows using
the WEIGHTS dict so the weighted formula produces exactly 75.0 (CRITICAL boundary) and 74.0 (HIGH boundary).
Both call `score_risk()` end-to-end — not `pd.cut()` directly — closing the confirmed gap from 07-PATTERNS.md.

**TEST-02 D-03 renaming** (`tests/test_ingestion.py`): Five edge-case test functions renamed to the exact
names mandated by D-03: `test_missing_values_filled_with_zero`, `test_duplicate_student_ids_deduplicated`,
`test_empty_csv_does_not_crash`, `test_bad_date_format_safe_default`, `test_type_mismatch_safe_default`.
Existing test logic was preserved; only the function names changed.

**test_config.py fix**: The `test_missing_api_key_raises` test was failing because `load_dotenv()` in
`src/config.py` was re-populating `ANTHROPIC_API_KEY` from a parent-directory `.env` file before the
`os.environ["ANTHROPIC_API_KEY"]` line executed. Fixed by monkeypatching `dotenv.load_dotenv` to a no-op
inside the test, so the KeyError contract is correctly observed.

**Auxiliary tests**: `test_generate_data.py`, `test_package_structure.py`, `test_no_hardcoded_paths.py`
passed without modification — no baseline failures in those files.
