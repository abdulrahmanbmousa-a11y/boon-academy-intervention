---
phase: 07-test-suite
plan: "01"
subsystem: test-infrastructure
tags: [testing, baseline, fixtures, documentation]

dependency_graph:
  requires: []
  provides:
    - "07-01-BASELINE.md: authoritative baseline failure inventory for Wave 1 plans"
    - "tests/conftest.py: minimal_enriched_df fixture (5 rows, 2 campuses, 20 COL_* columns)"
    - "CLAUDE.md: corrected openpyxl color pitfall example (FFFFCCCC)"
  affects:
    - "07-02-PLAN.md: consumes BASELINE.md priority order for risk engine boundary test additions"
    - "07-03-PLAN.md: consumes BASELINE.md failure list for test_config and other non-TEST-01..04 fixes"
    - "tests/test_output_generator.py: can use minimal_enriched_df fixture"
    - "tests/test_llm_engine.py: can use minimal_enriched_df fixture"

tech_stack:
  added: []
  patterns:
    - "conftest.py module-scope cfg import after env var setdefault (D-08 compliance)"
    - "function-scoped inline DataFrame fixture (no file I/O, fresh copy per test)"
    - "cfg.COL_* constants as dict keys in fixture body (zero bare string column names)"

key_files:
  created:
    - ".planning/phases/07-test-suite/07-01-BASELINE.md"
    - ".planning/phases/07-test-suite/07-01-SUMMARY.md"
  modified:
    - "tests/conftest.py"
    - "CLAUDE.md"

decisions:
  - "Function scope chosen for minimal_enriched_df (not session) — output_generator tests mutate DataFrames"
  - "cfg import placed after os.environ.setdefault to satisfy D-08 (fail-loud import order)"
  - "BASELINE.md documents 2 MISSING (test_score_75_is_critical, test_score_74_is_high) + 1 FAIL (test_missing_api_key_raises)"

metrics:
  duration: "~3 minutes"
  completed_date: "2026-05-24"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 2
---

# Phase 7 Plan 01: Baseline + Fixture Setup Summary

**One-liner:** Baseline run captured (1 fail, 2 missing TEST-01 boundary tests), shared `minimal_enriched_df` fixture added to conftest.py, and CLAUDE.md openpyxl color example corrected from `00FFCCCC` to `FFFFCCCC`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Capture baseline pytest run | `419db79` | `.planning/phases/07-test-suite/07-01-BASELINE.md` |
| 2 | Extend conftest.py with fixture | `92e4495` | `tests/conftest.py` |
| 3 | Correct CLAUDE.md color pitfall | `9f37002` | `CLAUDE.md` |

## What Was Built

**Task 1 — Baseline capture:**
- Ran `py -3.12 -m pytest tests/ -v --tb=short` (111 collected)
- Result: **1 failed, 110 passed**
- 1 FAIL: `test_config::TestFailLoudBehavior::test_missing_api_key_raises` — conftest sets the env var before any test, so KeyError never raised
- 2 MISSING (TEST-01): `test_score_75_is_critical` and `test_score_74_is_high` — required boundary tests that exercise `score_risk()` end-to-end at exact threshold values do not yet exist
- All TEST-02, TEST-03, TEST-04 requirements already satisfied by passing tests
- Priority order per D-02 documented for Wave 1 plans

**Task 2 — conftest.py extension:**
- Added `import pandas as pd`
- Added `from src import config as cfg` (after env var setdefault, per D-08 order)
- Added `minimal_enriched_df` fixture: function-scoped, 5 rows, 2 campuses (C01: 3 rows, C02: 2 rows), risk levels `[CRITICAL, CRITICAL, MEDIUM, CRITICAL, LOW]` (1+ CRITICAL per campus)
- All 20 `cfg.COL_*` constants used as dict keys — zero bare string column names
- Saudi-format phone strings (`05xxxxxxxx`), non-None summaries/messages for CRITICAL rows
- `generated_by`: `["llm", "template", None, "llm", None]`
- Runtime check confirmed: `FIXTURE_OK` (>=5 rows, >=2 campuses, all 20 columns present)

**Task 3 — CLAUDE.md correction:**
- Changed `"00FFCCCC"` → `"FFFFCCCC"` in the openpyxl pitfall bullet
- Added note referencing the FF**CCCC pattern in `src/config.py`
- `COLOR_CRITICAL = "FFFFCCCC"` in src/config.py uses FF (opaque) alpha prefix, not 00 (transparent)

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed without deviation.

## Verification Results

- `07-01-BASELINE.md` exists, non-empty, contains all 5 required sections including explicit MISSING entries for `test_score_75_is_critical` and `test_score_74_is_high`
- `py -3.12 -m pytest tests/ --collect-only -q` returns same 111 tests (no new collection errors)
- FIXTURE_OK — runtime check confirmed 5 rows, 2 campuses, all 20 COL_* columns
- CLAUDE_MD_OK — `FFFFCCCC` present, `00FFCCCC` absent, `8-char hex with alpha prefix` text preserved
- `git diff --name-only src/` returns empty (zero production source changes)

## Known Stubs

None.

## Threat Flags

None. This plan made no changes to network endpoints, auth paths, file access patterns, or schema. Only documentation and test infrastructure were modified.

## Self-Check: PASSED

- [x] `.planning/phases/07-test-suite/07-01-BASELINE.md` exists: FOUND
- [x] `tests/conftest.py` modified: FOUND (`from src import config as cfg`, `minimal_enriched_df`)
- [x] `CLAUDE.md` modified: FOUND (`FFFFCCCC` present, `00FFCCCC` absent)
- [x] Task 1 commit `419db79`: FOUND
- [x] Task 2 commit `92e4495`: FOUND
- [x] Task 3 commit `9f37002`: FOUND
- [x] No src/ modifications: CONFIRMED
- [x] 111 tests collected, same as baseline: CONFIRMED
