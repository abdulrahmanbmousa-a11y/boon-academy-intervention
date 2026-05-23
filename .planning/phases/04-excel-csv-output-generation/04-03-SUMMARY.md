---
phase: 04-excel-csv-output-generation
plan: "03"
subsystem: output-generation
tags: [output, orchestrator, integration-test, main-wiring, phase-complete]
dependency_graph:
  requires:
    - 04-01  # _write_whatsapp_csv, _write_run_log
    - 04-02  # _write_priority_list, _write_campus_dashboards
  provides:
    - write_outputs orchestrator (3-arg, D-01..D-04)
    - main.py Phase 4 wiring
    - integration test suite for write_outputs
  affects:
    - main.py (Phase 4 call now active)
    - src/output_generator.py (stub replaced)
    - tests/test_output_generator.py (3 integration tests added)
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN for orchestrator integration
    - Orchestrator delegates to 4 private helpers, merges dict results
    - output_dir.mkdir(parents=True, exist_ok=True) idempotent directory creation
key_files:
  created: []
  modified:
    - src/output_generator.py
    - main.py
    - tests/test_output_generator.py
    - .planning/STATE.md
    - .planning/ROADMAP.md
decisions:
  - write_outputs import placed at top of main.py (with other src imports) rather than inline at call site — consistent with project import style
  - 3 positional args used in main.py call (not keyword run_log=run_log) — D-01 requirement
  - T-04-05: ANTHROPIC_API_KEY confirmed absent from run_log dict before shipping
metrics:
  duration: ~8 min
  completed_date: "2026-05-23"
  tasks_completed: 2/2
  files_modified: 5
---

# Phase 4 Plan 3: write_outputs Orchestrator + main.py Wiring Summary

**One-liner:** 3-arg write_outputs orchestrator wires all 4 Phase 4 helpers into main.py, completing the pipeline output loop with 99 tests GREEN.

## What Was Built

### Task 1: write_outputs Orchestrator (TDD RED → GREEN)

Replaced the 2-arg `NotImplementedError` stub in `src/output_generator.py` with the full 3-arg orchestrator:

- Signature: `write_outputs(df: pd.DataFrame, output_dir: Path, run_log: dict) -> dict[str, Path]`
- First statement: `output_dir.mkdir(parents=True, exist_ok=True)` (D-03, idempotent)
- Calls all 4 private helpers in order: `_write_priority_list`, `_write_campus_dashboards`, `_write_whatsapp_csv`, `_write_run_log` (D-04)
- Returns unified dict: `priority_list`, `campus_{campus_id}` keys per campus, `whatsapp`, `run_log` (D-02)
- Docstring references D-01, D-02, D-03, D-04, D-09
- Updated STATE.md module contract from 2-arg to 3-arg signature

### Task 2: main.py Wiring + Integration Tests

- Added `from src import output_generator` to main.py top-level imports
- Replaced commented Phase 4 block with active call: `paths = output_generator.write_outputs(df, cfg.OUTPUT_DIR, run_log)`
- Call uses 3 positional args (D-01 — not keyword form `run_log=run_log`)
- Added `logger.info("Outputs written: %s", list(paths.keys()))` after call

Integration tests added to `tests/test_output_generator.py`:
- `full_sample_df` fixture: 6 students, 2 campuses (ALPHA/BETA), all 4 risk levels, str dtype for student_id and parent_phone
- `sample_run_log_full` fixture: complete 7-key D-06 schema
- `test_write_outputs_returns_all_keys`: asserts `priority_list`, at least one `campus_*` key, `whatsapp`, `run_log` present
- `test_write_outputs_all_paths_exist`: asserts every returned `Path` value points to an existing file
- `test_write_outputs_creates_output_dir`: asserts `mkdir(parents=True, exist_ok=True)` handles non-existent nested directory

## Verification Results

All Phase 4 verification checks passed:

1. Full test suite: **99 tests GREEN** (96 pre-existing + 3 new integration tests)
2. Signature check: `params == ['df', 'output_dir', 'run_log']` — OK
3. Config constants: `OUTPUT_COLS_PRIORITY==12`, `OUTPUT_COLS_CAMPUS==15`, colors correct — OK
4. main.py imports clean: `import main` exits 0 — OK
5. No bare column strings: `student_id`, `risk_level`, etc. absent from output_generator.py AST — OK

## Threat Model Verification (T-04-05)

Confirmed: `ANTHROPIC_API_KEY` is passed to `enrich_with_llm()` (line 76) and never stored in the `run_log` dict. The run_log dict has exactly 7 safe keys: `run_timestamp`, `students_processed`, `api_calls_made`, `tokens_used`, `errors_encountered`, `fallbacks_triggered`, `data_quality_warnings`. No secrets in `run_log.json`.

## Deviations from Plan

**1. [Rule 2 - Style] Import placed at module top rather than inline at call site**
- **Found during:** Task 2
- **Issue:** Plan's action block showed `from src import output_generator` inline at the Phase 4 call site. CLAUDE.md mandates clean module-level imports; inline imports inside function bodies are a code smell.
- **Fix:** Added `from src import output_generator` with the other `from src import ...` lines at the top of main.py. The call site uses `output_generator.write_outputs(...)` as specified.
- **Files modified:** main.py
- No behavioral impact — functionally identical.

## Known Stubs

None. All 4 output helpers are fully implemented and the orchestrator wires them end-to-end.

## Phase 4 Complete

All 4 requirements delivered:
- OUT-01: `intervention_priority_list.xlsx` — all students, ranked desc, color-coded, bold headers, frozen A2
- OUT-02: `facilitator_dashboard_{campus}.xlsx` — campus-only students, summary row, risk_score sorted
- OUT-03: `whatsapp_messages.csv` — 8 columns, CRITICAL/HIGH only, UTF-8 BOM
- OUT-06: `run_log.json` — 7 required keys present

## Self-Check: PASSED

- [x] `src/output_generator.py` — write_outputs orchestrator confirmed present
- [x] `main.py` — Phase 4 call active, import at top
- [x] `tests/test_output_generator.py` — 3 integration tests present
- [x] `.planning/STATE.md` — 3-arg contract, Phase 4 complete, metrics updated
- [x] `.planning/ROADMAP.md` — Phase 4 checked complete, 04-03 checked
- [x] Commits exist: fe31025 (RED), 7541c43 (GREEN), 870c0e1 (main.py wiring)
- [x] 99 tests GREEN — confirmed by pytest run
