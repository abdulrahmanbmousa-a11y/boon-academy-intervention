# Phase 2: Risk Scoring Engine - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `src/risk_engine.py` — a pure function `score_risk(df: pd.DataFrame) -> pd.DataFrame` that adds risk scores and labels to the student DataFrame. By end of phase:
- Every student row has `risk_score` (0-100), `risk_level` (CRITICAL/HIGH/MEDIUM/LOW), and 4 component columns
- The 4 intermediate component scores are also included for audit/debugging
- `recommended_action` is populated with rule-based labels as a fallback for Phase 3
- All computation is deterministic — same input always produces same output
- No I/O, no API calls, no side effects — pure function only

This phase does NOT call the Claude API, write files, or produce any output artifacts.

</domain>

<decisions>
## Implementation Decisions

### Score Normalization (D-01 through D-04)

- **D-01 (Attendance component):** `attendance_component = (1 - attendance_days / 14) × 100`
  - 14/14 days attended → 0 risk. 0/14 days → 100 risk. Denominator is always 14 (the full window).
  - Uses `attendance_days` from ingestion (count of days where session_attended_min > 0).

- **D-02 (Practice component):** `practice_component = max(0, (1 - avg_practice / 15)) × 100`
  - 15+ questions/day → 0 risk. 0 questions/day → 100 risk. Cap at 15/day.
  - `avg_practice` = `practice_total_q / 14` (always divide by 14, not attendance_days).

- **D-03 (Trend component):** Binary scoring.
  - Compute: `last3_avg` = mean of `daily_session_series[-3:]`, `first11_avg` = mean of `daily_session_series[:11]`.
  - `trend_component = 100 if last3_avg < first11_avg else 0`
  - If `first11_avg == 0`: compare against 0, so any activity in last 3 days = improving (0), no activity = flat (0).
  - Edge case: fewer than 14 data points → use whatever series length is available; if series < 3 values, trend_component = 50 (neutral).

- **D-04 (Notes component):** `notes_component = min(days_since_note, 30) / 30 × 100`
  - Note today → 0 risk. Note 30+ days ago (or no note ever) → 100 risk.
  - No note in data (`latest_note_date` is NaT) → treat as 30 days = max penalty.
  - Reference date for "today": use `pd.Timestamp.now().normalize()` (date only, no time component).

### Weighted Formula (D-05)

- **D-05:** `risk_score = round(attendance_component × 0.35 + practice_component × 0.30 + trend_component × 0.20 + notes_component × 0.15, 2)`
  - All weights from `src/config.py` constants (WEIGHT_ATTENDANCE, WEIGHT_PRACTICE, WEIGHT_TREND, WEIGHT_NOTES).
  - Clip final score to [0, 100] after rounding.

### Risk Level Assignment (D-06)

- **D-06:** Thresholds from `src/config.py`:
  - `risk_score >= RISK_THRESHOLD_CRITICAL (75)` → "CRITICAL"
  - `risk_score >= RISK_THRESHOLD_HIGH (50)` → "HIGH"
  - `risk_score >= RISK_THRESHOLD_MEDIUM (25)` → "MEDIUM"
  - `risk_score < RISK_THRESHOLD_MEDIUM` → "LOW"

### Trend Direction Column (D-07)

- **D-07:** `trend_direction` stores a **string label**: `"declining"` / `"stable"` / `"improving"`
  - Uses `COL_TREND_DIR` constant from `src/config.py`.
  - Mapping: `last3_avg < first11_avg` → "declining"; `last3_avg > first11_avg` → "improving"; equal → "stable".
  - This is the value in the output DataFrame — human-readable for Phase 4 Excel and Phase 5 reports.

### Recommended Action Column (D-08)

- **D-08:** `risk_engine` populates `recommended_action` with rule-based labels:
  - CRITICAL → "Contact parent immediately"
  - HIGH → "Schedule check-in this week"
  - MEDIUM → "Monitor closely"
  - LOW → "On track"
  - Uses `COL_RECOMMENDED_ACTION` constant. Phase 3 LLM overwrites for CRITICAL/HIGH; rule-based serves as fallback if LLM fails.

### Component Score Columns (D-09)

- **D-09:** Include the 4 intermediate component scores in the output DataFrame:
  - `attendance_component`, `practice_component`, `trend_component`, `notes_component` (each 0-100 float)
  - These are NOT in RISK-07 but added for audit trail and Phase 5 risk breakdown display.
  - Column names defined as constants in `src/config.py` (add if not present: `COL_ATTENDANCE_COMPONENT`, `COL_PRACTICE_COMPONENT`, `COL_TREND_COMPONENT`, `COL_NOTES_COMPONENT`).

### Claude's Discretion

- Exact pandas vectorization approach (apply vs vectorized operations — use vectorized for performance)
- Whether to add `attendance_rate` as `attendance_days / 14` (float 0.0-1.0) to the DataFrame alongside `attendance_component`
- How to handle edge cases in daily_session_series (e.g., NaN values in series from filled-zero rows)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 Requirements
- `.planning/REQUIREMENTS.md` §RISK-01 to RISK-08 — exact risk scoring requirements and output column spec

### Locked Constants (all in src/config.py)
- `src/config.py` — WEIGHT_ATTENDANCE (0.35), WEIGHT_PRACTICE (0.30), WEIGHT_TREND (0.20), WEIGHT_NOTES (0.15); RISK_THRESHOLD_CRITICAL (75), RISK_THRESHOLD_HIGH (50), RISK_THRESHOLD_MEDIUM (25); all COL_* column name constants
- `.planning/STATE.md` §Module contracts — locked signature `score_risk(df: pd.DataFrame) -> pd.DataFrame`

### Input DataFrame Schema (from Phase 1)
- `src/ingestion.py` — `ingest()` return value schema: columns available to risk_engine including `attendance_days` (Float64), `session_total_min` (Float64), `practice_total_q` (Float64), `daily_session_series` (list[float], 14 values), `daily_practice_series` (list[float]), `latest_note_date` (datetime64[ns] or NaT)
- `.planning/phases/01-foundation-data-ingestion/01-03-SUMMARY.md` — actual column names and dtypes confirmed

### Prior Phase Decisions
- `.planning/phases/01-foundation-data-ingestion/01-CONTEXT.md` — D-07 (all constants in config.py from day 1), D-11 (NaT for bad dates)
- `CLAUDE.md` — code standards: type hints on all functions, zero print statements, logging module only

### Success Criteria
- `.planning/ROADMAP.md` §Phase 2 — 4 success criteria defining "done"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py` — all weight constants and threshold constants already defined; all COL_* column name constants already defined. Import everything from here — no hardcoded strings or numbers.
- `src/ingestion.py` — `ingest()` return value is the direct input to `score_risk()`. The `daily_session_series` column contains Python lists of np.float64 values (verified live: `[np.float64(2.0), np.float64(2.0), ...]`).

### Established Patterns
- Zero print statements — use `logging.getLogger(__name__)` throughout (CLAUDE.md)
- Type hints on every function signature (INFRA-08)
- Docstring on every public function (INFRA-08)
- All column names via cfg constants — no bare string literals (RISK-08)
- Pure function: no file I/O, no API calls, no global state mutations

### Integration Points
- `main.py` calls `risk_engine.score_risk(df)` immediately after `ingestion.ingest()` — Phase 2 replaces the `raise NotImplementedError("Phase 2")` stub in `src/risk_engine.py`
- The enriched DataFrame flows from `score_risk()` directly into `llm_engine.enrich_with_llm()` in Phase 3

</code_context>

<specifics>
## Specific Ideas

- The `daily_session_series` values are Python lists (not numpy arrays) — use `pd.Series(row)` or direct list slicing for last3/first11 computation
- Trend uses session minutes (not practice questions) as the activity signal — session engagement is the primary leading indicator
- Component scores (D-09) give facilitators visibility into WHY a student is at risk, not just THAT they are

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Risk Scoring Engine*
*Context gathered: 2026-05-23*
