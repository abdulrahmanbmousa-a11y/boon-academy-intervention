---
phase: 04-excel-csv-output-generation
plan: "02"
subsystem: output-generation
tags: [openpyxl, excel, formatting, tdd]
dependency_graph:
  requires: [04-01]
  provides: [_write_priority_list, _write_campus_dashboards]
  affects: [src/output_generator.py, tests/test_output_generator.py]
tech_stack:
  added: []
  patterns:
    - openpyxl PatternFill with fill_type="solid" (mandatory — omitting silently drops color)
    - save-to-disk then load_workbook round-trip for openpyxl test assertions
    - fill_map built once before loop, not per-cell
    - dropna=True in groupby to exclude NaN campus_id rows
    - None guard in auto-width comprehension (str(None)=="None" underestimates)
key_files:
  created: []
  modified:
    - src/output_generator.py
    - tests/test_output_generator.py
decisions:
  - "Option B summary row layout: header=row1, summary=row2, data=row3; freeze_panes='A2' (D-08 compliant)"
  - "LLM columns for MEDIUM/LOW written as None (not 'N/A') per D-06"
  - "fill_map dict created once per helper before the data-row loop — not per cell"
  - "pandas NA normalized to Python None before passing to openpyxl cell value"
metrics:
  duration: "~12 min"
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 4 Plan 02: Excel Writers (Priority List + Campus Dashboards) Summary

**One-liner:** openpyxl priority list and per-campus dashboards with navy headers, risk-level row colors, frozen panes, summary row, and MEDIUM/LOW LLM cell blanking.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for _write_priority_list + _write_campus_dashboards | 68f0af5 | tests/test_output_generator.py |
| 1+2 (GREEN) | Implement _write_priority_list and _write_campus_dashboards | db830db | src/output_generator.py |

## What Was Built

### `_write_priority_list(df, output_dir) -> Path`

Writes `intervention_priority_list.xlsx` — all students sorted by `risk_score` descending with a 1-based `rank` column prepended. 12 columns per `OUTPUT_COLS_PRIORITY`.

- Row 1: navy header (`COLOR_HEADER = FF1F4E79`), white bold font (`FONT_WHITE = FFFFFFFF`)
- Rows 2+: data rows color-coded by `risk_level` (CRITICAL=FFFFCCCC, HIGH=FFFFE5CC, MEDIUM=FFFFFFCC, LOW=FFCCFFCC)
- `freeze_panes = "A2"` — header always visible when scrolling
- Auto column widths: `min(max_content_len, 60) + 2` with `None` guard

### `_write_campus_dashboards(df, output_dir) -> dict[str, Path]`

Writes one `facilitator_dashboard_{campus_id}.xlsx` per unique non-NaN campus. 15 columns per `OUTPUT_COLS_CAMPUS` (12 standard + 3 LLM).

- Row 1: navy header (identical styling to priority list)
- Row 2: summary stats row — "Summary" in A2, bold, light grey fill (`FFEEEEEE`). Stats: total students, CRITICAL count, HIGH count, coverage %
- Rows 3+: student data rows color-coded by risk_level; data sorted by `risk_score` desc with rank column
- MEDIUM and LOW rows: columns 13/14/15 (facilitator_summary, whatsapp_message, generated_by) written as `None` — D-06 compliance
- `groupby(dropna=True)` — NaN campus_id rows silently excluded; no `facilitator_dashboard_nan.xlsx` produced
- `freeze_panes = "A2"` (D-08)

## Test Results

| Test Group | Tests | Result |
|------------|-------|--------|
| test_priority_list_* (8 tests) | file_exists, header_color, header_font, freeze_panes, critical_row_color, sorted_desc, rank_column, column_count | 8/8 PASS |
| test_campus_dashboard_* (9 tests) | files_created, header_row, freeze_panes, column_count, summary_row, data_starts_row3, critical_row_color, medium_llm_cells_empty, excludes_nan_campus | 9/9 PASS |
| Pre-existing suite (79 tests) | All prior tests | 79/79 PASS |
| **Full suite** | **96 total** | **96/96 PASS** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pandas NA normalization before openpyxl cell write**
- **Found during:** Task 2 implementation review
- **Issue:** When a DataFrame cell contains `pd.NA` or `float("nan")` (from the NaN campus_id row or None LLM columns in multi_campus_df), passing it directly to `ws.cell(value=...)` can write unexpected string representations
- **Fix:** Added explicit `None` normalization in the data-row write loop for non-string values using `pd.isna()` before assigning to cell value
- **Files modified:** `src/output_generator.py`
- **Commit:** db830db (included in GREEN phase commit)

### No Other Deviations

Plan executed as specified. The summary row layout (Option B: header=row1, summary=row2) was already decided in 04-RESEARCH.md and implemented exactly as documented.

## Known Stubs

None — both helpers are fully implemented and tested.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced beyond what was planned. `campus_id` used as a filename component is validated implicitly by `dropna=True` (NaN excluded) and the fact that campus_id values come from ingestion (not user input), satisfying T-04-04.

## Self-Check: PASSED

- [x] `src/output_generator.py` — modified, contains `_write_priority_list` and `_write_campus_dashboards`
- [x] `tests/test_output_generator.py` — modified, contains 17 new test functions
- [x] Commit 68f0af5 exists (RED: failing tests)
- [x] Commit db830db exists (GREEN: implementation)
- [x] 96/96 tests pass (`py -3.12 -m pytest tests/ -v`)
- [x] Zero bare string column literals in output_generator.py (all `cfg.COL_*`)
- [x] All `PatternFill` calls include `fill_type="solid"`
- [x] openpyxl color test assertions use 8-char ARGB hex (`cfg.COLOR_*` constants)
- [x] All color assertions use save-to-disk + `load_workbook` round-trip pattern
