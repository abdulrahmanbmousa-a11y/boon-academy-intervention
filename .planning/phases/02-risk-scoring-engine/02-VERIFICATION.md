---
phase: 02-risk-scoring-engine
verified: 2026-05-23T10:02:00Z
status: passed
score: 13/13 must-haves verified
overrides_applied: 0
---

# Phase 2: Risk Scoring Engine — Verification Report

**Phase Goal:** Every student in the merged DataFrame receives a deterministic risk_score (0–100), a risk_level (CRITICAL/HIGH/MEDIUM/LOW), and all four component scores, computed by a pure function with no I/O.
**Verified:** 2026-05-23T10:02:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `score_risk(df)` returns DataFrame with risk_score, risk_level, attendance_rate, avg_practice_questions, trend_direction, days_since_last_note | ✓ VERIFIED | All 11 columns confirmed present in `test_required_output_columns_present` — 28/28 tests pass |
| 2 | Worst student (0 attendance, 0 practice, declining, no note) → risk_score >= 75, risk_level == "CRITICAL" | ✓ VERIFIED | `test_worst_student_is_critical` passes under `@freeze_time("2026-05-23")`; formula yields 100.0 |
| 3 | Perfect student (full attendance, high practice, improving, recent note) → risk_score < 25, risk_level == "LOW" | ✓ VERIFIED | `test_perfect_student_is_low` passes; formula yields 0.0 |
| 4 | No bare snake_case column-name strings in `src/risk_engine.py` outside the allowed set | ✓ VERIFIED | `test_no_bare_column_strings_in_risk_engine` passes; grep confirms no `raise NotImplementedError`, no `print(`, no `open(` |
| 5 | `score_risk` is a pure function: caller's df columns unchanged, result is a different object | ✓ VERIFIED | `df = df.copy()` at L150; `test_pure_function_does_not_mutate_input` passes |
| 6 | `df.attrs["data_quality_warnings"]` survives score_risk transform | ✓ VERIFIED | `df.copy()` preserves attrs; `test_df_attrs_preserved` passes |
| 7 | `logger.info` from score_risk does not emit student_name or parent_phone | ✓ VERIFIED | Only aggregate log line emitted (L199–205); `test_pii_safe_logging_in_score_risk` passes |
| 8 | D-05 weighted formula uses cfg.WEIGHT_* constants, not hardcoded floats | ✓ VERIFIED | L177–180 use `cfg.WEIGHT_ATTENDANCE`, `cfg.WEIGHT_PRACTICE`, `cfg.WEIGHT_TREND`, `cfg.WEIGHT_NOTES` |
| 9 | D-06 risk_level via pd.cut with right=False; thresholds from cfg.RISK_THRESHOLD_* | ✓ VERIFIED | L186–191; `_RISK_BINS` built from `cfg.RISK_THRESHOLD_MEDIUM/HIGH/CRITICAL` at L35 |
| 10 | D-07 trend_direction column contains string labels "declining"/"stable"/"improving" | ✓ VERIFIED | `_trend_component_and_direction` returns StringDtype Series; all four trend tests pass |
| 11 | D-08 recommended_action from _ACTION_BY_LEVEL dict with exact D-08 strings | ✓ VERIFIED | `_ACTION_BY_LEVEL` at L28–33; `test_recommended_action_matches_level` (4 parametrize cases) passes |
| 12 | main.py wires score_risk(df) after ingest; logs "Scored {N} students" | ✓ VERIFIED | `from src.risk_engine import score_risk` at L13; `df = score_risk(df)` at L71; `logger.info(f"Scored {len(df)} students")` at L72 |
| 13 | All 28 tests in tests/test_risk_engine.py pass; Phase 1's 25 tests still pass | ✓ VERIFIED | Full suite: 53/53 passed (live run confirmed) |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/risk_engine.py` | Pure function score_risk implementing D-01..D-09 + RISK-01..RISK-08; min 120 lines | ✓ VERIFIED | 208 lines (>120); contains `def score_risk(df: pd.DataFrame) -> pd.DataFrame`; `from src import config as cfg`; `import numpy as np`; `df = df.copy()`; `pd.cut(`; `right=False` |
| `src/config.py` | 21 COL_* constants including 4 new D-09 component columns; 4 WEIGHT_* constants; 3 RISK_THRESHOLD_* constants | ✓ VERIFIED | COL_ATTENDANCE_COMPONENT, COL_PRACTICE_COMPONENT, COL_TREND_COMPONENT, COL_NOTES_COMPONENT present at L83–86; all weights and thresholds confirmed at L41–51 |
| `main.py` | score_risk imported and called after ingest | ✓ VERIFIED | L13, L71, L72; stub comment fully removed; Phase 3/4 stubs untouched |
| `tests/test_risk_engine.py` | 28+ tests covering RISK-01..RISK-08, purity, PII logging, source scan | ✓ VERIFIED | 28 collected, 28 passed; all required function names present |
| `tests/test_config.py` | 21-constant assertion (was 17) | ✓ VERIFIED | 6 tests pass; 4 new constants in EXPECTED_COLUMN_CONSTANTS |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/risk_engine.py` | `src.config` (cfg.WEIGHT_*, cfg.RISK_THRESHOLD_*, cfg.COL_*) | `from src import config as cfg` | ✓ WIRED | L19 of risk_engine.py; used throughout for all column and weight references |
| `src/risk_engine.py` | `pd.cut` threshold ladder | `pd.cut(..., right=False)` | ✓ WIRED | L186–191; bins reference `_RISK_BINS` which uses cfg thresholds |
| `main.py` | `src.risk_engine.score_risk` | `from src.risk_engine import score_risk` + `df = score_risk(df)` | ✓ WIRED | L13 import, L71 call site — between ingest and Phase 3 stub |
| `tests/test_risk_engine.py` | `src.risk_engine.score_risk` | `from src.risk_engine import score_risk` | ✓ WIRED | L17 of test file |
| `tests/test_risk_engine.py` | `src.config` | `from src import config as cfg` | ✓ WIRED | L16 of test file |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `score_risk()` — risk_score | `df[cfg.COL_RISK_SCORE]` | Weighted sum of 4 component columns computed from `attendance_days`, `practice_total_q`, `daily_session_series`, `latest_note_date` passed in from ingest | Yes — deterministic formula; tests verify 100.0/0.0 extremes and boundary cases | ✓ FLOWING |
| `score_risk()` — risk_level | `df[cfg.COL_RISK_LEVEL]` | `pd.cut` on risk_score with `_RISK_BINS` / `_RISK_LABELS` | Yes — categorical output verified by 8-case parametrized boundary test | ✓ FLOWING |
| `score_risk()` — recommended_action | `df[cfg.COL_RECOMMENDED_ACTION]` | `.map(_ACTION_BY_LEVEL)` on risk_level | Yes — 4-case parametrized test verifies each level produces the correct D-08 string | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| score_risk signature unchanged | `py -3.12 -c "from src.risk_engine import score_risk; import inspect; print(inspect.signature(score_risk))"` | `(df: pandas.core.frame.DataFrame) -> pandas.core.frame.DataFrame` | ✓ PASS |
| Full test suite (Phase 1 + Phase 2) | `py -3.12 -m pytest tests/ -q` | 53 passed in 1.28s | ✓ PASS |
| Phase 2 tests only | `py -3.12 -m pytest tests/test_risk_engine.py -q` | 28 passed in 0.67s | ✓ PASS |
| Config constants tests | `py -3.12 -m pytest tests/test_config.py -q` | 6 passed in 0.02s | ✓ PASS |
| 28 tests collected in test file | `py -3.12 -m pytest tests/test_risk_engine.py --collect-only -q` | 28 tests collected | ✓ PASS |
| No prohibited patterns in risk_engine.py | grep for `raise NotImplementedError`, `print(`, `open(` | No matches | ✓ PASS |

---

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` files defined for this phase. Test suite is the declared verification gate per both PLAN files.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RISK-01 | 02-02 | attendance_rate = sessions attended / total possible sessions | ✓ SATISFIED | `_attendance_component` + `COL_ATTENDANCE_RATE` column; `test_attendance_rate_column_exists_and_equals_days_over_14` passes |
| RISK-02 | 02-02 | avg_practice_questions = average daily practice questions (÷14) | ✓ SATISFIED | `_practice_component` + `COL_AVG_PRACTICE` column; `test_avg_practice_questions_equals_total_over_14` passes |
| RISK-03 | 02-02 | trend_direction = last 3 days vs first 11 days avg; declining = higher risk | ✓ SATISFIED | `_trend_component_and_direction`; 4 trend tests pass (declining, improving, short series, NaN series) |
| RISK-04 | 02-02 | days_since_last_note; no note = max penalty (30 days) | ✓ SATISFIED | `_days_since_last_note` + `_notes_component`; NaT → 30 and today → 0 tests pass |
| RISK-05 | 02-02 | risk_score (0–100) weighted: attendance 35%, practice 30%, trend 20%, notes 15% | ✓ SATISFIED | L176–181; formula uses cfg.WEIGHT_* constants; `test_risk_score_weighted_formula` passes all 3 cases |
| RISK-06 | 02-02 | risk_level: CRITICAL (≥75), HIGH (50–74), MEDIUM (25–49), LOW (<25) | ✓ SATISFIED | pd.cut with right=False, _RISK_BINS from cfg thresholds; 8-case parametrized boundary test passes |
| RISK-07 | 02-02 | Output includes: risk_score, risk_level, attendance_rate, avg_practice_questions, trend_direction, days_since_last_note | ✓ SATISFIED | All 11 columns verified by `test_required_output_columns_present` |
| RISK-08 | 02-01 | All column names defined as constants in src/config.py — no bare strings in logic | ✓ SATISFIED | `test_no_bare_column_strings_in_risk_engine` passes; allowed set correctly scoped to D-07 labels + Phase 1 input column names |

All 8 requirements assigned to Phase 2 are SATISFIED. No orphaned requirements found — REQUIREMENTS.md traceability table maps RISK-01 through RISK-08 exclusively to Phase 2.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns found |

Scan performed on `src/risk_engine.py`, `main.py`, `tests/test_risk_engine.py`, `src/config.py`:
- No `TBD`, `FIXME`, `XXX` markers found
- No `raise NotImplementedError` found (stub fully replaced)
- No `print(` statements found
- No `return null`, `return {}`, `return []` patterns found
- No hardcoded empty state passed to rendering
- No placeholder comments in implementation code

One notable decision documented in 02-02-SUMMARY.md: `pd.Timestamp(datetime.now()).normalize()` is used instead of `pd.Timestamp.now().normalize()` at L154 of risk_engine.py. This is a legitimate freeze_time compatibility fix (stdlib `datetime.now` is patched by freezegun; the C-extension `pd.Timestamp.now()` is not). This is correct behavior, not an anti-pattern.

---

### Human Verification Required

None. All must-have truths are fully verifiable from the codebase and test results.

---

### Gaps Summary

No gaps. All phase must-haves are verified. All 4 ROADMAP success criteria are satisfied. All 8 RISK-* requirements are satisfied. Full test suite (53 tests) passes with no failures.

---

_Verified: 2026-05-23T10:02:00Z_
_Verifier: Claude (gsd-verifier)_
