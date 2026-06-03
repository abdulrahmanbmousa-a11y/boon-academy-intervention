# Real-Data Rebuild Plan

## Problem Statement

The project was built against **synthetic generated data** (`src/generate_data.py`) that invented its own CSV column schema. The **real source files** from NOON Academy use a different schema. The three real CSVs are now in `data/` and must drive the pipeline end-to-end — the generator must be retired.

---

## Column Mismatch Audit

### `student_daily_metrics.csv`
| Real Column | Current Config Constant | Config Value | Status |
|---|---|---|---|
| `student_id` | `COL_STUDENT_ID` | `"student_id"` | OK |
| `date` | `COL_METRIC_DATE` | `"metric_date"` | **MISMATCH** |
| `session_attended_min` | `COL_SESSION_MIN` | `"session_attended_min"` | OK |
| `practice_questions` | `COL_PRACTICE_Q` | `"practice_questions"` | OK |
| `last_quiz_score` | *(missing)* | — | **NEW — add to config** |
| `days_until_next_quiz` | *(missing)* | — | **NEW — add to config** |

### `facilitator_notes.csv`
| Real Column | Current Config Constant | Config Value | Status |
|---|---|---|---|
| `note_id` | *(missing)* | — | NEW — read and ignore |
| `student_id` | `COL_STUDENT_ID` | `"student_id"` | OK |
| `facilitator_email` | `COL_FACILITATOR_EMAIL` | `"facilitator_email"` | OK (duplicate of metadata) |
| `date` | `COL_NOTE_DATE` | `"note_date"` | **MISMATCH** |
| `note_text` | `COL_NOTE_TEXT` | `"note_text"` | OK |

### `student_metadata.csv`
| Real Column | Current Config Constant | Config Value | Status |
|---|---|---|---|
| `student_id` | `COL_STUDENT_ID` | `"student_id"` | OK |
| `student_name` | `COL_STUDENT_NAME` | `"student_name"` | OK |
| `campus_id` | `COL_CAMPUS_ID` | `"campus_id"` | OK |
| `facilitator_email` | `COL_FACILITATOR_EMAIL` | `"facilitator_email"` | OK |
| `grade` | *(missing)* | — | **NEW — add to config** |
| `parent_phone` | `COL_PARENT_PHONE` | `"parent_phone"` | OK |
| `target_score` | *(missing)* | — | **NEW — critical for risk** |
| `learning_track` | *(missing)* | — | **NEW — add to config** |

---

## Root Cause

The ingestion module's dtype dictionaries use `cfg.COL_METRIC_DATE` (`"metric_date"`) and `cfg.COL_NOTE_DATE` (`"note_date"`) as keys. When pandas reads the real files (which have `"date"` in both), it **silently ignores** the unmatched dtype keys and falls through to type inference — causing downstream `KeyError` on first column access.

---

## Files That Must Change

### Priority 1 — Core Schema (blocking everything)
1. `src/config.py` — add 5 new column constants, add `COL_QUIZ_GAP` derived column
2. `src/ingestion.py` — fix dtype dicts, add post-read renames, aggregate new columns
3. `tests/fixtures/*.csv` — update ALL fixture CSVs to match real schema

### Priority 2 — Risk Engine
4. `src/risk_engine.py` — add 5th academic component using `quiz_score_gap`; rebalance weights

### Priority 3 — Downstream Consumers
5. `src/llm_engine.py` — update prompt context to include quiz score, target score, learning track, grade
6. `src/output_generator.py` — add new columns to output column lists

### Priority 4 — Tests
7. `tests/conftest.py` — add new columns to `minimal_enriched_df`
8. `tests/test_ingestion.py` — update assertions for new schema
9. `tests/test_risk_engine.py` — update expected values for new 5-component weights

### Priority 5 — Cleanup
10. `src/generate_data.py` — update to emit real schema (for test fixture regeneration only)
11. `CLAUDE.md` — update note that real data drives the pipeline

---

## Detailed Change Specification

### 1. `src/config.py` — New constants to add

```python
# New metadata columns
COL_GRADE: str = "grade"
COL_TARGET_SCORE: str = "target_score"
COL_LEARNING_TRACK: str = "learning_track"

# New metrics columns  
COL_LAST_QUIZ_SCORE: str = "last_quiz_score"
COL_DAYS_UNTIL_QUIZ: str = "days_until_next_quiz"

# Derived column (computed in ingestion)
COL_QUIZ_GAP: str = "quiz_score_gap"   # target_score - last_quiz_score, clipped ≥ 0
```

New component score column:
```python
COL_ACADEMIC_COMPONENT: str = "academic_component"
```

Updated weight constants (must still sum to 1.0):
```python
WEIGHT_ATTENDANCE: float = 0.30   # was 0.35
WEIGHT_PRACTICE:   float = 0.25   # was 0.30
WEIGHT_TREND:      float = 0.15   # was 0.20
WEIGHT_NOTES:      float = 0.10   # was 0.15
WEIGHT_ACADEMIC:   float = 0.20   # NEW
```

Updated output column tuples to include new fields in campus dashboard:
```python
OUTPUT_COLS_CAMPUS: tuple[str, ...] = OUTPUT_COLS_PRIORITY + (
    COL_GRADE, COL_LEARNING_TRACK, COL_TARGET_SCORE, COL_LAST_QUIZ_SCORE,
    COL_FACILITATOR_SUMMARY, COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
)
```

### 2. `src/ingestion.py` — Ingestion layer changes

**DTYPE_METRICS** — key for date changes from `cfg.COL_METRIC_DATE` to `"date"` (raw file column):
```python
DTYPE_METRICS: dict[str, str] = {
    cfg.COL_STUDENT_ID:      "string",
    "date":                  "string",   # raw column name in real file
    cfg.COL_SESSION_MIN:     "string",
    cfg.COL_PRACTICE_Q:      "string",
    cfg.COL_LAST_QUIZ_SCORE: "Float64",  # nullable numeric
    cfg.COL_DAYS_UNTIL_QUIZ: "Float64",  # nullable numeric
}
```

After `_read_csv_safe()` for metrics, add rename:
```python
metrics = metrics.rename(columns={"date": cfg.COL_METRIC_DATE})
```

**DTYPE_NOTES** — key for date changes from `cfg.COL_NOTE_DATE` to `"date"`:
```python
DTYPE_NOTES: dict[str, str] = {
    "note_id":               "string",   # read but not used downstream
    cfg.COL_STUDENT_ID:      "string",
    cfg.COL_FACILITATOR_EMAIL: "string", # present in real file
    "date":                  "string",   # raw column name in real file
    cfg.COL_NOTE_TEXT:       "string",
}
```

After `_read_csv_safe()` for notes, add rename:
```python
notes = notes.rename(columns={"date": cfg.COL_NOTE_DATE})
```

**DTYPE_META** — add new columns:
```python
DTYPE_META: dict[str, str] = {
    cfg.COL_STUDENT_ID:        "string",
    cfg.COL_STUDENT_NAME:      "string",
    cfg.COL_CAMPUS_ID:         "string",
    cfg.COL_FACILITATOR_EMAIL: "string",
    cfg.COL_GRADE:             "string",   # "10" or "11" — keep as string
    cfg.COL_PARENT_PHONE:      "string",
    cfg.COL_TARGET_SCORE:      "Float64",  # nullable numeric
    cfg.COL_LEARNING_TRACK:    "string",   # Standard/Accelerated/Remedial
}
```

**Metrics aggregation** — add `last_quiz_score` aggregation (last non-null value):
```python
metrics_agg = (
    metrics.groupby(cfg.COL_STUDENT_ID)
    .agg(
        session_total_min=...,
        practice_total_q=...,
        attendance_days=...,
        daily_session_series=...,
        daily_practice_series=...,
        daily_dates=...,
        last_quiz_score=(cfg.COL_LAST_QUIZ_SCORE, lambda s: s.dropna().iloc[-1] if s.notna().any() else pd.NA),
        days_until_next_quiz=(cfg.COL_DAYS_UNTIL_QUIZ, lambda s: s.dropna().iloc[-1] if s.notna().any() else pd.NA),
    )
    .reset_index()
)
```

**Post-merge** — compute `quiz_score_gap`:
```python
df[cfg.COL_QUIZ_GAP] = (
    df[cfg.COL_TARGET_SCORE].astype("Float64") - df["last_quiz_score"].astype("Float64")
).clip(lower=0)
```

### 3. `src/risk_engine.py` — 5th academic component

New private helper:
```python
def _academic_component(df: pd.DataFrame) -> pd.Series:
    """D-05: academic risk — 0 (met target) to 100 (far below target).
    
    Uses quiz_score_gap (target_score - last_quiz_score, clipped >= 0).
    Cap gap at 50 points for normalization (50-point gap = 100% penalty).
    Rows with no quiz data get neutral score of 50.0.
    """
    gap = df[cfg.COL_QUIZ_GAP].astype("Float64")
    has_data = gap.notna()
    result = pd.Series(50.0, index=df.index, dtype="Float64")
    result[has_data] = (gap[has_data] / 50.0 * 100).clip(0, 100)
    return result
```

Update `score_risk()` to compute and include `academic_component`:
```python
df[cfg.COL_ACADEMIC_COMPONENT] = _academic_component(df)
df[cfg.COL_RISK_SCORE] = (
    df[cfg.COL_ATTENDANCE_COMPONENT] * cfg.WEIGHT_ATTENDANCE +
    df[cfg.COL_PRACTICE_COMPONENT]   * cfg.WEIGHT_PRACTICE   +
    df[cfg.COL_TREND_COMPONENT]      * cfg.WEIGHT_TREND       +
    df[cfg.COL_NOTES_COMPONENT]      * cfg.WEIGHT_NOTES       +
    df[cfg.COL_ACADEMIC_COMPONENT]   * cfg.WEIGHT_ACADEMIC
).clip(0, 100)
```

### 4. `src/llm_engine.py` — Richer prompt context

In the student data block sent to Claude, add:
- `grade` (10 or 11)
- `learning_track` (Standard/Accelerated/Remedial)
- `target_score` (student's target)
- `last_quiz_score` (most recent quiz result)
- `quiz_score_gap` (gap between target and actual)

### 5. `tests/fixtures/*.csv` — Schema updates

**student_daily_metrics_happy.csv**: rename `metric_date` → `date`, add `last_quiz_score` and `days_until_next_quiz` columns.

**student_daily_metrics_missing_numeric.csv**: same column rename.

**student_daily_metrics_bad_dates.csv**: same column rename.

**facilitator_notes_happy.csv**: rename `note_date` → `date`, add `note_id` and `facilitator_email` columns.

**student_metadata_happy.csv**: add `grade`, `target_score`, `learning_track` columns.

**student_metadata_with_dupes.csv**: same additions.

**student_metadata_type_mismatch.csv**: same additions.

### 6. `tests/conftest.py` — `minimal_enriched_df` additions

Add new columns to the inline DataFrame:
```python
cfg.COL_GRADE: ["10", "11", "10", "11", "10"],
cfg.COL_LEARNING_TRACK: ["Standard", "Accelerated", "Standard", "Remedial", "Standard"],
cfg.COL_TARGET_SCORE: [85.0, 90.0, 80.0, 60.0, 88.0],
"last_quiz_score": [50.0, 70.0, 75.0, 45.0, 85.0],
cfg.COL_QUIZ_GAP: [35.0, 20.0, 5.0, 15.0, 3.0],
cfg.COL_ACADEMIC_COMPONENT: [70.0, 40.0, 10.0, 30.0, 6.0],
```

### 7. `tests/test_risk_engine.py` — Expected value updates

All tests that assert specific component scores or total risk scores must be recalculated using the new 5-component formula:
```
risk_score = attendance*0.30 + practice*0.25 + trend*0.15 + notes*0.10 + academic*0.20
```

---

## Execution Order

```
Step 1  → src/config.py           (add constants, update weights)
Step 2  → tests/fixtures/*.csv    (fix schema — tests run against these)
Step 3  → src/ingestion.py        (fix dtype dicts + renames + new aggregations)
Step 4  → src/risk_engine.py      (add academic component)
Step 5  → src/llm_engine.py       (richer prompt)
Step 6  → src/output_generator.py (updated column lists)
Step 7  → tests/conftest.py       (update minimal_enriched_df)
Step 8  → tests/test_ingestion.py (update assertions for new schema)
Step 9  → tests/test_risk_engine.py (update expected values)
Step 10 → pytest (all 119+ tests must pass)
Step 11 → python main.py (end-to-end pipeline run with real data)
Step 12 → git commit + push
```

---

## What Does NOT Change

- `main.py` — already reads from `cfg.DATA_DIR`; no changes needed
- `src/doc_generator.py` — works on the enriched DataFrame; new columns flow through automatically
- `.env` / `.env.example` — no new env vars needed
- `CLAUDE.md` code standards — all standards still apply
