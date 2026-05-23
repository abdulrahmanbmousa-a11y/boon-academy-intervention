---
phase: 02-risk-scoring-engine
plan: "01"
subsystem: risk-engine
tags: [config, test-scaffold, tdd, wave-0]
dependency_graph:
  requires: [01-03]
  provides: [02-02]
  affects: [src/config.py, tests/test_config.py, tests/test_risk_engine.py]
tech_stack:
  added: []
  patterns: [tdd-red-scaffold, module-level-helper, freeze_time, pd-cut-boundary-lock, source-scan-test]
key_files:
  created: [tests/test_risk_engine.py]
  modified: [src/config.py, tests/test_config.py]
decisions:
  - "RISK-08 allowed set is exactly: declining, improving, stable, attendance_days, practice_total_q, daily_session_series, latest_note_date — Phase 1 bare input column names are exempt from cfg requirement"
  - "test_risk_level_boundaries calls pd.cut directly (not score_risk) so it is GREEN immediately and locks the threshold contract independently"
  - "test_recommended_action_matches_level uses parametrize over 4 levels — each level has a dedicated input construction path"
  - "28 tests collected (14 unique logical test functions, 8 parametrize expansions from test_risk_level_boundaries, 4 from test_recommended_action_matches_level)"
metrics:
  duration: "~5 min"
  completed: "2026-05-23"
  tasks: 2/2
  files: 3
---

# Phase 2 Plan 01: Wave 0 Config Constants + Test Scaffold Summary

Wave 0 scaffolding for Phase 2 risk scoring engine — four D-09 component-column constants added to config.py, test_config.py extended to assert all 21 constants, and a 28-test failing scaffold created in test_risk_engine.py covering RISK-01 through RISK-08 with the threshold-contract test GREEN immediately.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add D-09 component-column constants + extend test_config.py | e552224 | src/config.py, tests/test_config.py |
| 2 | Create failing test scaffold (tests/test_risk_engine.py) | cb391ef | tests/test_risk_engine.py |

## What Was Built

### Task 1: Four new COL_* constants in src/config.py

Added immediately after `COL_RECOMMENDED_ACTION` under a `# D-09 component score columns (Phase 2)` comment:

| Constant | Value |
|---|---|
| `COL_ATTENDANCE_COMPONENT` | `"attendance_component"` |
| `COL_PRACTICE_COMPONENT` | `"practice_component"` |
| `COL_TREND_COMPONENT` | `"trend_component"` |
| `COL_NOTES_COMPONENT` | `"notes_component"` |

`tests/test_config.py` extended: EXPECTED_COLUMN_CONSTANTS from 17 to 21 entries; both class docstring and method docstring updated from "17" to "21 (17 from Phase 1 + 4 D-09 component columns from Phase 2)". No changes to the getattr loop.

### Task 2: tests/test_risk_engine.py — 28 tests collected

**Module-level helper:** `_build_student_row(student_id, attendance_days, practice_total_q, session_series, latest_note_date) -> dict` — full Phase 1 schema, sensible "perfect student" defaults, per-call fresh list to avoid shared mutable reference (T-02-01 mitigation).

**Test functions and their GREEN/RED state:**

| Test Function | Maps To | State | Reason |
|---|---|---|---|
| `test_attendance_rate_column_exists_and_equals_days_over_14` | RISK-01 | RED | Calls score_risk → NotImplementedError |
| `test_avg_practice_questions_equals_total_over_14` | RISK-02 | RED | Calls score_risk → NotImplementedError |
| `test_trend_declining_is_100_component_and_declining_label` | RISK-03 + D-07 | RED | Calls score_risk → NotImplementedError |
| `test_trend_improving_is_0_component_and_improving_label` | RISK-03 + D-07 | RED | Calls score_risk → NotImplementedError |
| `test_trend_short_series_is_neutral_50` | RISK-03 edge | RED | Calls score_risk → NotImplementedError |
| `test_trend_nan_series_is_neutral_50` | RISK-03 + Pitfall 4 | RED | Calls score_risk → NotImplementedError |
| `test_notes_component_nat_is_max_30` | RISK-04 | RED | Calls score_risk → NotImplementedError |
| `test_notes_component_today_is_zero` | RISK-04 + freeze_time | RED | Calls score_risk → NotImplementedError |
| `test_risk_score_weighted_formula` | RISK-05 | RED | Calls score_risk → NotImplementedError |
| `test_risk_level_boundaries[*]` (8 cases) | RISK-06 | **GREEN** | Calls pd.cut directly — no score_risk dependency |
| `test_required_output_columns_present` | RISK-07 | RED | Calls score_risk → NotImplementedError |
| `test_worst_student_is_critical` | Success Criterion 2 | RED | Calls score_risk → NotImplementedError |
| `test_perfect_student_is_low` | Success Criterion 3 | RED | Calls score_risk → NotImplementedError |
| `test_recommended_action_matches_level[*]` (4 cases) | D-08 | RED | Calls score_risk → NotImplementedError |
| `test_pure_function_does_not_mutate_input` | Purity | RED | Calls score_risk → NotImplementedError |
| `test_df_attrs_preserved` | Pitfall 8 / Purity | RED | Calls score_risk → NotImplementedError |
| `test_pii_safe_logging_in_score_risk` | Security V7 | RED | Calls score_risk → NotImplementedError |
| `test_no_bare_column_strings_in_risk_engine` | RISK-08 | **GREEN** | Reads src/risk_engine.py — stub has no bare column strings |

**Total: 28 collected. 9 GREEN (8 boundary parametrize + 1 source-scan). 19 RED (NotImplementedError — intended Wave 0 state).**

## Verification Results

| Check | Result |
|---|---|
| `py -3.12 -m pytest tests/test_config.py -x -q` | 6 passed |
| `py -3.12 -m pytest tests/test_risk_engine.py --collect-only -q` | 28 tests collected |
| `py -3.12 -m pytest tests/test_risk_engine.py::test_risk_level_boundaries -q` | 8 passed (GREEN) |
| `py -3.12 -m pytest tests/test_risk_engine.py::test_worst_student_is_critical -q` | 1 failed — NotImplementedError: Phase 2 (RED — intended) |
| `py -3.12 -m pytest tests/ -q --ignore=tests/test_risk_engine.py` | 25 passed (Phase 1 no regression) |

## Deviations from Plan

None — plan executed exactly as written.

- The plan specified "at least 14 test functions" — 28 were collected (parametrize expansions for test_risk_level_boundaries x8 and test_recommended_action_matches_level x4 account for the higher count).
- `test_no_bare_column_strings_in_risk_engine` is also GREEN immediately (stub has no bare column strings). The plan flagged this as a risk_engine-calling test, but it only reads the source file — so it passes against the current stub too. This is correct behavior and aligns with RISK-08's intent.

## Known Stubs

None — this plan is pure scaffolding. `src/risk_engine.py` intentionally raises `NotImplementedError("Phase 2")`. Plan 02-02 will implement the function and turn all RED tests GREEN.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. The RISK-08 source-scan test reads `src/risk_engine.py` from disk (local-only, no network) as documented in T-02-03.

## Self-Check: PASSED

- `src/config.py` — verified contains `COL_ATTENDANCE_COMPONENT: str = "attendance_component"` and all 4 new constants
- `tests/test_config.py` — verified contains `"COL_ATTENDANCE_COMPONENT"` in list and "21 column" in docstrings
- `tests/test_risk_engine.py` — verified exists, 28 tests collected, all required function names present
- Commits `e552224` and `cb391ef` verified in git log
