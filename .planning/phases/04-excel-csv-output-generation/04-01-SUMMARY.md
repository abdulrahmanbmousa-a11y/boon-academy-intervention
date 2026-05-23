---
phase: 04-excel-csv-output-generation
plan: "01"
subsystem: output-generation
tags:
  - config-constants
  - csv-writer
  - json-writer
  - tdd
dependency_graph:
  requires:
    - "03-03: main.py Phase 3 wiring complete; enrich_with_llm() returns enriched DataFrame"
  provides:
    - "cfg.COLOR_*, cfg.FONT_WHITE, cfg.COL_RANK, cfg.OUTPUT_COLS_PRIORITY (12), cfg.OUTPUT_COLS_CAMPUS (15)"
    - "_write_whatsapp_csv(df, output_dir) -> Path"
    - "_write_run_log(run_log, output_dir) -> Path"
  affects:
    - "04-02: Excel writers consume COLOR_* and OUTPUT_COLS_* from config"
    - "04-03: write_outputs() orchestrator calls _write_whatsapp_csv and _write_run_log"
tech_stack:
  added: []
  patterns:
    - "8-char openpyxl ARGB hex format (FF prefix) for all color constants"
    - "encoding='utf-8-sig' for BOM CSV — Excel compatibility without garbled Arabic"
    - "json.dumps(default=str) — datetime-safe JSON serialization"
    - "df.copy() at function entry — pure function discipline, no caller mutation"
key_files:
  created:
    - tests/test_output_generator.py
  modified:
    - src/config.py
    - tests/test_config.py
decisions:
  - "COLOR_* constants use 8-char ARGB format (FF prefix) matching openpyxl PatternFill fgColor contract — test assertions use same 8-char value (not 6-char)"
  - "OUTPUT_COLS_CAMPUS defined as OUTPUT_COLS_PRIORITY + 3 LLM cols — guarantees superset relationship without duplication"
  - "write_outputs() stub kept with NotImplementedError — Plan 04-02 and 04-03 complete it; no dead placeholder code added per D-09"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 14
  tests_total: 79
---

# Phase 4 Plan 1: Phase 4 Constants + CSV/JSON Helpers Summary

**One-liner:** Added 9 openpyxl formatting constants to config.py and implemented `_write_whatsapp_csv` (UTF-8 BOM, CRITICAL/HIGH filter) and `_write_run_log` (JSON with `default=str`) with 14 new tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Phase 4 constants to src/config.py and extend test_config.py | 33fc285 | src/config.py, tests/test_config.py |
| 2 | Implement _write_whatsapp_csv and _write_run_log in output_generator.py | 392800f | src/output_generator.py, tests/test_output_generator.py |

## What Was Built

### Task 1: Phase 4 Config Constants (33fc285)

Added 9 new constants to `src/config.py` after `COL_LLM_ERROR_REASON`:

- `COLOR_CRITICAL = "FFFFCCCC"` — light red, 8-char openpyxl ARGB
- `COLOR_HIGH = "FFFFE5CC"` — light orange
- `COLOR_MEDIUM = "FFFFFFCC"` — light yellow
- `COLOR_LOW = "FFCCFFCC"` — light green
- `COLOR_HEADER = "FF1F4E79"` — dark navy for header row
- `FONT_WHITE = "FFFFFFFF"` — white for header row text
- `COL_RANK = "rank"` — derived rank column added by write_outputs()
- `OUTPUT_COLS_PRIORITY` — 12-element list for intervention_priority_list.xlsx
- `OUTPUT_COLS_CAMPUS` — 15-element list (standard 12 + 3 LLM cols) for campus dashboards

Added `TestPhase4FormattingConstants` class with 7 test functions to `tests/test_config.py`.

### Task 2: _write_whatsapp_csv and _write_run_log (392800f)

Implemented two private helpers in `src/output_generator.py`:

**`_write_whatsapp_csv(df, output_dir) -> Path`:**
- Filters to CRITICAL and HIGH `risk_level` rows only (MEDIUM/LOW excluded)
- Selects 8 columns in exact OUT-03 order: student_id, student_name, parent_phone, facilitator_email, campus_id, risk_level, whatsapp_message, generated_by
- Writes UTF-8 BOM CSV (`encoding="utf-8-sig"`) for Excel compatibility with Arabic characters
- All column references via `cfg.COL_*` — zero bare string literals

**`_write_run_log(run_log, output_dir) -> Path`:**
- Serializes the run_log dict as indented JSON (`indent=2`)
- `default=str` handles datetime or Path objects without TypeError
- Pure write — no transformation of the in-memory dict

Created `tests/test_output_generator.py` with 7 test functions covering both helpers.

## Verification

```
py -3.12 -m pytest tests/test_config.py tests/test_output_generator.py -v
# 20 passed

py -3.12 -m pytest tests/ -v --tb=short
# 79 passed (65 pre-existing + 7 config + 7 output_generator)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

- `write_outputs()` still raises `NotImplementedError("Phase 4")` — intentional per D-09. Plans 04-02 and 04-03 will replace it. The two private helpers implemented here (`_write_whatsapp_csv`, `_write_run_log`) are wired in Plan 04-03.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundary crossings introduced. The `run_log.json` writer uses a fixed-schema dict (keys verified by test_run_log_keys) — no mechanism for ANTHROPIC_API_KEY to enter the dict (T-04-02 mitigation: key schema is enforced by main.py's dict literal, not dynamic).

## Self-Check: PASSED

- [x] src/config.py exists and contains COLOR_CRITICAL = "FFFFCCCC"
- [x] tests/test_config.py contains TestPhase4FormattingConstants with 7 test functions
- [x] src/output_generator.py contains _write_whatsapp_csv and _write_run_log
- [x] tests/test_output_generator.py created with 7 test functions
- [x] Commit 33fc285 exists (Task 1)
- [x] Commit 392800f exists (Task 2)
- [x] 79 tests pass (zero regressions against pre-existing 65)
