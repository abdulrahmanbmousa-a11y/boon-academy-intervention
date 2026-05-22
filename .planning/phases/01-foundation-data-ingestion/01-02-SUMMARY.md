---
phase: 01-foundation-data-ingestion
plan: "02"
subsystem: synthetic-data
tags:
  - synthetic-data
  - csv-generation
  - test-fixtures
  - numpy-rng
  - tdd
dependency_graph:
  requires:
    - src.config (plan 01-01 — column constants, DATA_DIR)
  provides:
    - src/generate_data.py (deterministic CSV generator — make demo entry point)
    - tests/fixtures/ (8 fixture CSVs for plan 01-03 ingestion tests)
    - tests/conftest.py (sample_csv_paths + csv_scenario fixtures)
    - tests/test_generate_data.py (7 generator tests)
    - data/student_metadata.csv (300 students, 20 campuses)
    - data/student_daily_metrics.csv (~4200 rows, 14 days)
    - data/facilitator_notes.csv (~437 notes)
  affects:
    - Plan 01-03 (ingestion.py tests consume tests/fixtures/ + conftest.py)
    - make demo / make.ps1 demo (calls python -m src.generate_data)
    - Phase 7 integration tests (reference same fixture files)
tech_stack:
  added: []
  patterns:
    - "D-02: numpy.random.default_rng(seed) for reproducible synthetic data"
    - "D-03: PCT_MISSING_NUMERIC / PCT_DUPLICATE_ID / PCT_TYPE_MISMATCH edge-case injection"
    - "D-04: Index-bucket cohort assignment for deterministic risk-tier distribution"
    - "TDD RED/GREEN: fixtures + tests committed before generator implemented"
    - "monkeypatch.setattr(cfg, 'DATA_DIR', tmp_path) — T-02-05 test isolation"
key_files:
  created:
    - src/generate_data.py
    - tests/conftest.py
    - tests/test_generate_data.py
    - tests/fixtures/student_metadata_happy.csv
    - tests/fixtures/student_daily_metrics_happy.csv
    - tests/fixtures/facilitator_notes_happy.csv
    - tests/fixtures/student_metadata_with_dupes.csv
    - tests/fixtures/student_daily_metrics_missing_numeric.csv
    - tests/fixtures/student_daily_metrics_bad_dates.csv
    - tests/fixtures/student_metadata_type_mismatch.csv
    - tests/fixtures/empty.csv
  modified: []
decisions:
  - "D-01: 20 campuses x 15 students = 300 base rows; 3 output CSVs written to cfg.DATA_DIR"
  - "D-02: np.random.default_rng(42) — sha256-identical student_metadata.csv across two runs verified"
  - "D-03: inject_edge_cases() appends 9 dupe rows, blanks ~210 numeric cells, sets ~84 type-mismatch strings"
  - "D-04: _assign_risk_cohort() uses index buckets (15/25/40/20%) so cohort counts are deterministic, not RNG-dependent"
  - "Cohort distributions: CRITICAL Poisson(2), HIGH Normal(15,5), MEDIUM Normal(35,8), LOW Normal(50,5)"
  - "print() permitted in generate_data.py — developer utility exception per 01-RESEARCH.md L611"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-22"
  tasks_completed: 2
  tasks_total: 2
  files_created: 11
  files_modified: 0
  tests_added: 7
  tests_passing: 7
---

# Phase 1 Plan 02: Synthetic Data Generator Summary

**One-liner:** Deterministic synthetic CSV generator (seed=42, 300 students x 20 campuses, D-04 cohort distributions) plus 8 fixture CSVs and conftest.py unblocking plan 01-03 ingestion tests.

## What Was Built

11 new files. The primary deliverable is `src/generate_data.py` — a standalone
developer utility that writes 3 deterministic CSV files to `cfg.DATA_DIR` via
`python -m src.generate_data`. All module-level constants (SEED, N_CAMPUSES,
STUDENTS_PER_CAMPUS, N_DAYS, PCT_* edge-case densities) are locked per
D-01 through D-03. Risk-tier cohort assignment is index-based (not RNG-based)
to guarantee D-04 percentages hold exactly on every run. Edge cases are
injected via `inject_edge_cases()`: 9 duplicate rows, ~210 blank numeric
cells, ~84 type-mismatch strings.

8 test fixture CSVs under `tests/fixtures/` cover happy path, duplicate IDs,
missing numeric values, bad dates, type mismatch, and empty file. `tests/conftest.py`
provides `sample_csv_paths` and the parameterized `csv_scenario` fixture consumed
by plan 01-03 ingestion tests.

## TDD Gate Compliance

| Gate | Status |
|------|--------|
| RED: `test(01-02)` commit | `9cada83` — fixtures + tests committed, generator missing |
| GREEN: `feat(01-02)` commit | `bd6af8e` — generator implemented, all 7 tests pass |
| REFACTOR | Not needed — code was clean on first pass |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| Task 1 | Fixture CSVs, conftest.py, test_generate_data.py (RED) | 9cada83 | 10 files |
| Task 2 | src/generate_data.py (GREEN) | bd6af8e | 1 file |

## Verification Results

All plan verification checks passed:

- `pytest tests/test_generate_data.py -x -v` — 7/7 tests pass
- `python -m src.generate_data` exits 0, writes exactly 3 files to `data/`
- sha256 of student_metadata.csv matches across two independent runs (D-02)
- Generated metadata: 309 total rows, 300 unique student_ids, 20 unique campus_ids
- Generated metrics: 4200 rows (300 x 14 days, no missing rows)
- Generated notes: 437 rows (~70% of 300 students with 1-3 notes each)
- Blank session_attended_min cells: 97 (2.3% of 4200) — within 5% D-03 budget
- Duplicate student_ids: 9 IDs duplicated (9 extra rows = exactly 3% of 300)
- All parent_phone values start with '0' (Pitfall #3 preserved)
- Fixture spot checks: empty.csv header-only, with_dupes.csv has duplicate IDs confirmed

## Deviations from Plan

None — plan executed exactly as written. All D-01 through D-04 constraints satisfied.
The blank_session count (97, ~2.3%) is lower than the theoretical 5% maximum because
PCT_MISSING_NUMERIC applies to a shared pool split between session_min and practice_q
columns; approximately half of the ~210 blanks land on each column. The total blank
cell count across both columns is ~210, matching D-03 exactly.

## Requirements Addressed

| Requirement | Status | Evidence |
|-------------|--------|---------|
| DATA-01 | Done | src/generate_data.py produces 3 CSVs per D-01; test_metadata_row_count_300 + test_campus_count pass |

## Known Stubs

None. All functions in generate_data.py are fully implemented.

## Threat Flags

No new threat surface beyond what was modeled in the plan's threat_model.

Mitigations applied:
- T-02-02: All fixture CSVs use synthetic placeholders ("Student S0101", "0501XXXXXX", "facilitator.cNN@boon.academy") — no real PII
- T-02-03: sha256-identical output verified across two runs; test_deterministic_across_runs asserts this
- T-02-05: All 7 tests use monkeypatch.setattr(cfg, 'DATA_DIR', tmp_path) — no writes to real data/

## Self-Check: PASSED

Files verified on disk:
- src/generate_data.py: FOUND
- tests/conftest.py: FOUND
- tests/test_generate_data.py: FOUND
- tests/fixtures/student_metadata_happy.csv: FOUND
- tests/fixtures/student_daily_metrics_happy.csv: FOUND
- tests/fixtures/facilitator_notes_happy.csv: FOUND
- tests/fixtures/student_metadata_with_dupes.csv: FOUND
- tests/fixtures/student_daily_metrics_missing_numeric.csv: FOUND
- tests/fixtures/student_daily_metrics_bad_dates.csv: FOUND
- tests/fixtures/student_metadata_type_mismatch.csv: FOUND
- tests/fixtures/empty.csv: FOUND

Commits verified:
- 9cada83: test(01-02): add fixture CSVs, conftest.py, and test_generate_data.py (RED)
- bd6af8e: feat(01-02): implement src/generate_data.py — deterministic synthetic CSV generator (GREEN)
