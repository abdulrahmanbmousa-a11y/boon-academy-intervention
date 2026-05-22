# Phase 2: Risk Scoring Engine — Discussion Log

**Date:** 2026-05-23
**Areas discussed:** Score normalization, Trend direction format, recommended_action column

---

## Area 1: Score Normalization

**Question:** Attendance component — what rate is "perfect" (0 risk)?
**Options presented:** 100% = 0 risk; ≥80% = 0 risk; You decide
**Selected:** 100% attendance = 0 risk
**Formula locked:** `attendance_component = (1 - attendance_days / 14) × 100`

**Question:** Practice component — what avg daily practice = 0 risk?
**Options presented:** 15/day cap; 20/day cap; You decide
**Selected:** 15 questions/day cap
**Formula locked:** `practice_component = max(0, 1 - avg_practice/15) × 100`

**Question:** Notes component — maximum penalty threshold?
**Options presented:** 30 days; 14 days; You decide
**Selected:** 30 days = full penalty
**Formula locked:** `notes_component = min(days_since_note, 30) / 30 × 100`; NaT = 30 days

**Question:** Trend component — how does "last 3 vs first 11" map to 0-100?
**Options presented:** Binary (declining=100, flat/improving=0); Graded proportional; Three-level (declining/flat/improving)
**Selected:** Binary: declining=100, flat/improving=0

---

## Area 2: Trend Direction Format

**Question:** What value does the trend_direction column contain?
**Options presented:** String label ('declining'/'stable'/'improving'); Numeric (-1/0/+1); Float delta
**Selected:** String label: 'declining' / 'stable' / 'improving'

**Question:** Column name for trend_direction?
**Options presented:** COL_TREND_DIR (already in config.py); You decide
**Selected:** COL_TREND_DIR = 'trend_direction' (already in config.py)

---

## Area 3: recommended_action Column

**Question:** Does risk_engine populate recommended_action?
**Options presented:** Phase 2 sets rule-based labels; Leave empty for Phase 3; You decide
**Selected:** Phase 2 sets simple rule-based labels
**Labels locked:** CRITICAL→"Contact parent immediately", HIGH→"Schedule check-in this week", MEDIUM→"Monitor closely", LOW→"On track"

**Question:** Include intermediate component scores in output DataFrame?
**Options presented:** RISK-07 columns only; Include component scores too
**Selected:** Include component scores too (attendance_component, practice_component, trend_component, notes_component)

---

## Deferred Ideas

None.
