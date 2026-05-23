---
phase: 05-html-dashboard-word-report
plan: "02"
subsystem: output_generator
tags: [word-report, python-docx, out-04, docx]
dependency_graph:
  requires: [05-01]
  provides: [OUT-04]
  affects: [src/output_generator.py, tests/test_output_generator.py]
tech_stack:
  added: []
  patterns:
    - python-docx 1.1.2 programmatic Document() builder (no binary template)
    - add_heading/add_paragraph/add_table — no OxmlElement (D-10/D-11/D-12)
    - doc.save(str(path)) — str() required on Windows
    - col in df_copy.columns guard for optional component columns
key_files:
  created: []
  modified:
    - src/output_generator.py
    - tests/test_output_generator.py
decisions:
  - "level=0 heading maps to 'Title' style in python-docx (not 'Heading') — test checks both Title and Heading styles"
  - "Deep-dive uses COL_ATTENDANCE_RATE/COL_AVG_PRACTICE/COL_TREND_DIR/COL_DAYS_SINCE_NOTE (end-user columns always present) not COL_*_COMPONENT (optional internal columns)"
  - "Campus table rows computed via groupby dropna=True — same pattern as _write_campus_dashboards"
metrics:
  duration: ~10 min
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 6
  tests_total: 110
---

# Phase 5 Plan 02: Word Intervention Report Summary

**One-liner:** 7-section python-docx intervention_report.docx builder with cover page, exec summary, top-10 table, campus summary, per-tier deep-dives, data quality notes, and methodology appendix.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement _write_report() in output_generator.py | 4d377e8 | src/output_generator.py |
| 2 | Add _write_report unit tests to test_output_generator.py | 667be77 | tests/test_output_generator.py |

## What Was Built

### Task 1 — `_write_report()` in `src/output_generator.py`

Added `from docx import Document` import and `_write_report(df, run_log, output_dir) -> Path` function positioned after `_write_html_dashboard` and before `_write_priority_list`.

The function builds a 7-section Word document:

1. **Cover page** — title heading (level=0), run date, campus count, students processed
2. **Executive Summary** — narrative paragraph + 5-row risk breakdown table (Table Grid, 3 cols)
3. **Top 10 Most At-Risk Students** — nlargest(10) hard cap (T-05-06), table with rank/name/campus/score/level
4. **Campus Summary** — groupby campus, table with total/critical/high/coverage%
5. **Student Deep-Dives** — up to 4 sections (one per tier); skips empty tiers (D-08); uses end-user-facing columns (COL_ATTENDANCE_RATE etc.) for component scores
6. **Data Quality Notes** — "No data quality issues detected" when warnings empty; bullet list otherwise
7. **Methodology Appendix** — weights table + threshold paragraphs using cfg.WEIGHT_* and cfg.RISK_THRESHOLD_* constants

All constraints satisfied: Table Grid style throughout, no OxmlElement, doc.save(str(path)), all column/weight/threshold references via cfg.* constants.

### Task 2 — 6 unit tests in `tests/test_output_generator.py`

- Added `_write_report` to the import block
- Added `report_path` fixture mirroring `html_dashboard_path`
- 6 test functions in `# _write_report tests (OUT-04)` section

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] python-docx level=0 produces 'Title' style, not 'Heading' style**

- **Found during:** Task 2 test run (test_report_contains_cover_heading failed)
- **Issue:** `doc.add_heading(text, level=0)` uses python-docx "Title" paragraph style. The test checked only `p.style.name.startswith("Heading")`, missing the Title paragraph entirely. Headings list was empty for the cover heading.
- **Fix:** Updated `test_report_contains_cover_heading` to collect paragraphs where `style.name.startswith("Heading") or style.name == "Title"`. Implementation unchanged — level=0 is correct per plan spec.
- **Files modified:** tests/test_output_generator.py
- **Commit:** 667be77

## Verification Results

```
py -3.12 -m pytest tests/test_output_generator.py -k "report" -x -q
6 passed in 0.99s

py -3.12 -m pytest tests/ -x -q
110 passed in 8.33s
```

## Known Stubs

None — _write_report produces a fully populated docx with real data from the DataFrame.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced beyond the local outputs/ directory write (T-05-04 accepted in plan threat model).

## Self-Check: PASSED

- src/output_generator.py contains `def _write_report` — confirmed
- tests/test_output_generator.py contains 6 report test functions — confirmed
- commit 4d377e8 exists — confirmed (feat(05-02))
- commit 667be77 exists — confirmed (test(05-02))
- 110 tests pass, no regressions
