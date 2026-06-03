# Self-Execution Prompt: Real-Data Schema Migration
# Divided into 7 Phases — Clear Context Between Each

## Before You Start

You are working on the `boon-academy-intervention` project at:
`C:\Users\abdul\Desktop\NOON ACADEMY ASSIGNEMTN`

This is an AI-powered student intervention pipeline (Python, Claude API, pandas, openpyxl).

**The problem:** The project was built against synthetic CSV data with invented column names.
Three real CSV files from NOON Academy have been placed in `data/`. The full mismatch audit
is in `REBUILD_PLAN.md`. Read it before touching any file.

**Rule:** Complete one phase fully, run its verification, then tell the user:
> "Phase X is complete and verified. Please type /clear to reset context, then paste REBUILD_MD_{X+1} to continue."

---

---

# REBUILD_MD_1 — Schema Foundation (`src/config.py`)

## Skills to invoke first
```
Skill("superpowers:writing-plans")
```

## Context for this phase
You are updating `src/config.py` — the single source of truth for all column names,
weights, and output format constants. This phase has zero code logic changes; it only
adds new constants and adjusts weight values. Every other phase depends on this being
correct first.

Read `REBUILD_PLAN.md` and `src/config.py` before making any edit.

## Tasks

### Task 1-A: Add new column constants

In `src/config.py`, add the following in the **Column name constants** section.
Keep the grouping style (one comment block per CSV source):

```python
# New metadata columns (real NOON Academy schema)
COL_GRADE: str = "grade"
COL_TARGET_SCORE: str = "target_score"
COL_LEARNING_TRACK: str = "learning_track"

# New metrics columns (real NOON Academy schema)
COL_LAST_QUIZ_SCORE: str = "last_quiz_score"
COL_DAYS_UNTIL_QUIZ: str = "days_until_next_quiz"

# Derived column — computed in ingestion (target_score - last_quiz_score, clipped >= 0)
COL_QUIZ_GAP: str = "quiz_score_gap"

# 5th component score column (Phase 2 — D-06)
COL_ACADEMIC_COMPONENT: str = "academic_component"
```

### Task 1-B: Update weight constants

Replace the four weight constants with five (all five MUST sum to 1.0):

```python
WEIGHT_ATTENDANCE: float = 0.30   # was 0.35
WEIGHT_PRACTICE:   float = 0.25   # was 0.30
WEIGHT_TREND:      float = 0.15   # was 0.20
WEIGHT_NOTES:      float = 0.10   # was 0.15
WEIGHT_ACADEMIC:   float = 0.20   # NEW — quiz gap component
```

### Task 1-C: Update `OUTPUT_COLS_CAMPUS` tuple

Add new columns (grade, learning_track, target_score, last_quiz_score) so campus
dashboard sheets include real student context. Also add `COL_ACADEMIC_COMPONENT`:

```python
OUTPUT_COLS_CAMPUS: tuple[str, ...] = OUTPUT_COLS_PRIORITY + (
    COL_GRADE, COL_LEARNING_TRACK, COL_TARGET_SCORE, COL_LAST_QUIZ_SCORE,
    COL_FACILITATOR_SUMMARY, COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
)
```

### Task 1-D: Update `DISPLAY_COLS_DASHBOARD` tuple

Add `COL_GRADE`, `COL_LEARNING_TRACK`, `COL_TARGET_SCORE`, `COL_LAST_QUIZ_SCORE`,
`COL_QUIZ_GAP`, and `COL_ACADEMIC_COMPONENT` to the dashboard display columns.

## Verification

After editing, run:
```bash
python -c "from src import config as cfg; assert abs(cfg.WEIGHT_ATTENDANCE + cfg.WEIGHT_PRACTICE + cfg.WEIGHT_TREND + cfg.WEIGHT_NOTES + cfg.WEIGHT_ACADEMIC - 1.0) < 1e-9, 'weights do not sum to 1.0'; print('config OK')"
```

Expected output: `config OK`

Also confirm all new constants are accessible:
```bash
python -c "from src import config as cfg; print(cfg.COL_GRADE, cfg.COL_TARGET_SCORE, cfg.COL_LEARNING_TRACK, cfg.COL_LAST_QUIZ_SCORE, cfg.COL_QUIZ_GAP, cfg.COL_ACADEMIC_COMPONENT)"
```

## Checkpoint

> Phase REBUILD_MD_1 complete. Verify the two commands above pass.
> Tell the user: "REBUILD_MD_1 is done and verified. Please type /clear to reset context,
> then paste REBUILD_MD_2 to continue."

---

---

# REBUILD_MD_2 — Fixture CSVs (Multi-Agent)

## Skills to invoke first
```
Skill("superpowers:dispatching-parallel-agents")
```

## Context for this phase
You are updating 7 test fixture CSV files in `tests/fixtures/` to match the real NOON
Academy column schema. These files are the immutable inputs for all ingestion tests.
They must be updated BEFORE `ingestion.py` changes so tests remain runnable.

Use THREE parallel agents — each handles a group of fixtures simultaneously:
- Agent A: all three metrics fixture CSVs
- Agent B: the notes fixture CSV
- Agent C: all three metadata fixture CSVs

Dispatch all three agents in a single message with one Agent tool call block each.
Wait for all three to complete before doing anything else.

## Agent A — Metrics Fixtures

Agent A must read and rewrite these three files:

**`tests/fixtures/student_daily_metrics_happy.csv`**
New content (rename `metric_date` → `date`, add `last_quiz_score` and `days_until_next_quiz`):
```csv
student_id,date,session_attended_min,practice_questions,last_quiz_score,days_until_next_quiz
S0101,2026-05-01,45,10,,9
S0101,2026-05-02,50,12,,8
S0101,2026-05-03,40,8,,7
S0101,2026-05-04,55,15,72,10
S0101,2026-05-05,48,11,72,7
S0102,2026-05-01,30,5,,9
S0102,2026-05-02,35,7,,8
S0102,2026-05-03,28,4,,7
S0102,2026-05-04,32,6,58,10
S0102,2026-05-05,38,9,58,7
```

**`tests/fixtures/student_daily_metrics_missing_numeric.csv`**
```csv
student_id,date,session_attended_min,practice_questions,last_quiz_score,days_until_next_quiz
S0101,2026-05-01,,10,,9
S0101,2026-05-02,,12,,8
S0101,2026-05-03,40,,,7
S0102,2026-05-01,30,5,,9
S0102,2026-05-02,35,7,,8
S0102,2026-05-03,28,4,,7
```

**`tests/fixtures/student_daily_metrics_bad_dates.csv`**
Read the current file first. Rename `metric_date` → `date`. Add empty `last_quiz_score`
and `days_until_next_quiz` columns. Keep all other rows and values unchanged.

## Agent B — Notes Fixture

Agent B must rewrite this one file:

**`tests/fixtures/facilitator_notes_happy.csv`**
New content (rename `note_date` → `date`, add `note_id` and `facilitator_email`):
```csv
note_id,student_id,facilitator_email,date,note_text
N001,S0101,facilitator.c01@boon.academy,2026-05-03,Missed class today
N002,S0101,facilitator.c01@boon.academy,2026-05-07,Strong performance this week
N003,S0102,facilitator.c01@boon.academy,2026-05-04,Parent meeting scheduled
N004,S0201,facilitator.c02@boon.academy,2026-05-05,Disengaged in group work
N005,S0301,facilitator.c03@boon.academy,2026-05-06,Submitted late assignment
```

## Agent C — Metadata Fixtures

Agent C must read and rewrite these three files:

**`tests/fixtures/student_metadata_happy.csv`**
New content (add `grade`, `target_score`, `learning_track` columns; insert after `facilitator_email`):
```csv
student_id,student_name,campus_id,facilitator_email,grade,parent_phone,target_score,learning_track
S0101,Student S0101,C01,facilitator.c01@boon.academy,10,0501234567,85,Standard
S0102,Student S0102,C01,facilitator.c01@boon.academy,11,0501345678,70,Remedial
S0201,Student S0201,C02,facilitator.c02@boon.academy,10,0501456789,90,Accelerated
S0202,Student S0202,C02,facilitator.c02@boon.academy,11,0501567890,80,Standard
S0301,Student S0301,C03,facilitator.c03@boon.academy,10,0501678901,75,Standard
```

**`tests/fixtures/student_metadata_with_dupes.csv`**
Read this file first. Add `grade` (alternate "10"/"11"), `target_score` (70 for all rows),
and `learning_track` ("Standard" for all rows) after the `facilitator_email` column.
Keep the duplicate rows as-is — they are intentional for the dupe-deduplication test.

**`tests/fixtures/student_metadata_type_mismatch.csv`**
Read this file first. Add `grade`, `target_score`, `learning_track` columns after
`facilitator_email`. Keep the intentional type-mismatch values unchanged.

## Verification (after all three agents complete)

```bash
python -c "
import pandas as pd
m = pd.read_csv('tests/fixtures/student_daily_metrics_happy.csv')
n = pd.read_csv('tests/fixtures/facilitator_notes_happy.csv')
s = pd.read_csv('tests/fixtures/student_metadata_happy.csv')
assert 'date' in m.columns and 'metric_date' not in m.columns, 'metrics date column wrong'
assert 'last_quiz_score' in m.columns, 'missing last_quiz_score'
assert 'date' in n.columns and 'note_date' not in n.columns, 'notes date column wrong'
assert 'note_id' in n.columns, 'missing note_id'
assert 'grade' in s.columns and 'target_score' in s.columns, 'metadata missing new cols'
print('All fixture schemas correct')
"
```

Expected output: `All fixture schemas correct`

## Checkpoint

> Phase REBUILD_MD_2 complete. Verify the command above passes.
> Tell the user: "REBUILD_MD_2 is done and verified. Please type /clear to reset context,
> then paste REBUILD_MD_3 to continue."

---

---

# REBUILD_MD_3 — Ingestion Layer (`src/ingestion.py`)

## Skills to invoke first
```
Skill("superpowers:test-driven-development")
```

## Context for this phase
You are updating `src/ingestion.py` — the ingestion module that reads the three real CSVs,
cleans them, and merges to a one-row-per-student DataFrame. The fixture CSVs were updated
in REBUILD_MD_2 and now have the real schema. You must:
1. Fix dtype dictionaries so they match real column names
2. Add post-read renames (`date` → `metric_date` / `note_date`)
3. Add coercion for new numeric columns
4. Extend the aggregation to capture quiz data per student
5. Compute `quiz_score_gap` after the merge

Read `src/ingestion.py` and `src/config.py` in full before editing.
Minimize diff — do not restructure or reformat code beyond what the task requires.

## Tasks

### Task 3-A: Fix `DTYPE_METRICS`

Replace the current dict with:
```python
DTYPE_METRICS: dict[str, str] = {
    cfg.COL_STUDENT_ID:      "string",
    "date":                  "string",   # real file column; renamed after load
    cfg.COL_SESSION_MIN:     "string",
    cfg.COL_PRACTICE_Q:      "string",
    cfg.COL_LAST_QUIZ_SCORE: "string",   # coerced to Float64 after load
    cfg.COL_DAYS_UNTIL_QUIZ: "string",   # coerced to Float64 after load
}
```

### Task 3-B: Fix `DTYPE_NOTES`

Replace the current dict with:
```python
DTYPE_NOTES: dict[str, str] = {
    "note_id":                 "string",   # present in real file; not used downstream
    cfg.COL_STUDENT_ID:        "string",
    cfg.COL_FACILITATOR_EMAIL: "string",   # present in real file; already in metadata
    "date":                    "string",   # real file column; renamed after load
    cfg.COL_NOTE_TEXT:         "string",
}
```

### Task 3-C: Fix `DTYPE_META`

Replace the current dict with:
```python
DTYPE_META: dict[str, str] = {
    cfg.COL_STUDENT_ID:        "string",
    cfg.COL_STUDENT_NAME:      "string",
    cfg.COL_CAMPUS_ID:         "string",
    cfg.COL_FACILITATOR_EMAIL: "string",
    cfg.COL_GRADE:             "string",   # "10" or "11" — kept as string
    cfg.COL_PARENT_PHONE:      "string",
    cfg.COL_TARGET_SCORE:      "string",   # coerced to Float64 after load
    cfg.COL_LEARNING_TRACK:    "string",   # Standard / Accelerated / Remedial
}
```

### Task 3-D: Add post-read renames in `ingest()`

Directly after the three `_read_csv_safe()` calls and BEFORE `_ensure_ids()`, add:
```python
# Rename raw "date" columns to internal constant names before any downstream access
metrics = metrics.rename(columns={"date": cfg.COL_METRIC_DATE})
notes   = notes.rename(columns={"date": cfg.COL_NOTE_DATE})
```

### Task 3-E: Coerce new numeric columns

After the existing `_fill_numeric_with_zero` calls for `session_attended_min` and
`practice_questions`, add coercion for quiz columns (do NOT fill NaN — NaN means
no quiz has been taken yet, which is valid and different from zero):

```python
# Coerce quiz columns to nullable Float64 — NaN preserved (means no quiz yet)
for _col in [cfg.COL_LAST_QUIZ_SCORE, cfg.COL_DAYS_UNTIL_QUIZ]:
    if _col in metrics.columns:
        metrics = metrics.copy()
        metrics[_col] = pd.to_numeric(metrics[_col], errors="coerce").astype("Float64")

# Coerce target_score in metadata to nullable Float64
if cfg.COL_TARGET_SCORE in metadata.columns:
    metadata = metadata.copy()
    metadata[cfg.COL_TARGET_SCORE] = (
        pd.to_numeric(metadata[cfg.COL_TARGET_SCORE], errors="coerce").astype("Float64")
    )
```

### Task 3-F: Extend metrics aggregation

In the `metrics.groupby().agg()` block, add two new aggregations for quiz data.
The lambda takes the last non-null value (most recent quiz result per student):

```python
last_quiz_score=(
    cfg.COL_LAST_QUIZ_SCORE,
    lambda s: s.dropna().iloc[-1] if s.notna().any() else pd.NA,
),
days_until_next_quiz=(
    cfg.COL_DAYS_UNTIL_QUIZ,
    lambda s: s.dropna().iloc[-1] if s.notna().any() else pd.NA,
),
```

Also update the empty-metrics fallback DataFrame to include these two columns:
```python
metrics_agg = pd.DataFrame(
    columns=[
        cfg.COL_STUDENT_ID,
        "session_total_min", "practice_total_q", "attendance_days",
        "daily_session_series", "daily_practice_series", "daily_dates",
        "last_quiz_score", "days_until_next_quiz",
    ]
)
```

### Task 3-G: Compute `quiz_score_gap` after merge

After the two `.merge()` calls and the `numeric_fill_cols` fill block, add:
```python
# Compute quiz_score_gap: how far student is below target (0 = at or above target)
# NaN in either input column produces NaN gap (handled as neutral 50 by risk engine)
if cfg.COL_TARGET_SCORE in df.columns and "last_quiz_score" in df.columns:
    gap = (
        df[cfg.COL_TARGET_SCORE].astype("Float64") -
        df["last_quiz_score"].astype("Float64")
    )
    df[cfg.COL_QUIZ_GAP] = gap.clip(lower=0)
else:
    df[cfg.COL_QUIZ_GAP] = pd.NA
```

### Task 3-H: Update `ingest()` docstring

Add the new return columns to the Returns section:
```
last_quiz_score (Float64 or NA), days_until_next_quiz (Float64 or NA),
quiz_score_gap (Float64 or NA), grade (string), target_score (Float64),
learning_track (string).
```

## Verification

```bash
pytest tests/test_ingestion.py -v
```

All ingestion tests must pass. If any fail, debug and fix before proceeding.

## Checkpoint

> Phase REBUILD_MD_3 complete. All ingestion tests pass.
> Tell the user: "REBUILD_MD_3 is done and verified. Please type /clear to reset context,
> then paste REBUILD_MD_4 to continue."

---

---

# REBUILD_MD_4 — Risk Engine (`src/risk_engine.py` + `tests/test_risk_engine.py`)

## Skills to invoke first
```
Skill("superpowers:test-driven-development")
```

## Context for this phase
You are adding a 5th risk component — `academic_component` — to `src/risk_engine.py`.
This component measures how far a student's last quiz score falls below their target.
The weight constants were already updated in REBUILD_MD_1.

Read `src/risk_engine.py` and `src/config.py` before editing.

## Tasks

### Task 4-A: Add `_academic_component` private helper

Insert this function after `_notes_component` and before `score_risk()`:

```python
def _academic_component(df: pd.DataFrame) -> pd.Series:
    """D-05: academic risk component — 0 (at/above target) to 100 (far below target).

    Uses quiz_score_gap (target_score - last_quiz_score, clipped >= 0 by ingestion).
    Gap is normalized against a 50-point cap: a 50-point gap produces 100 risk.
    Rows with no quiz data (NaN gap) receive a neutral score of 50.0.
    """
    gap = df[cfg.COL_QUIZ_GAP].astype("Float64")
    has_data = gap.notna()
    result = pd.Series(50.0, index=df.index, dtype=float)
    result[has_data] = (gap[has_data] / 50.0 * 100).clip(0, 100)
    return result.astype(float)
```

### Task 4-B: Compute academic component in `score_risk()`

In `score_risk()`, after the four existing component computations, add:
```python
df[cfg.COL_ACADEMIC_COMPONENT] = _academic_component(df)
```

### Task 4-C: Update weighted sum in `score_risk()`

Replace the four-term weighted sum with five terms:
```python
df[cfg.COL_RISK_SCORE] = (
    df[cfg.COL_ATTENDANCE_COMPONENT] * cfg.WEIGHT_ATTENDANCE +
    df[cfg.COL_PRACTICE_COMPONENT]   * cfg.WEIGHT_PRACTICE   +
    df[cfg.COL_TREND_COMPONENT]      * cfg.WEIGHT_TREND       +
    df[cfg.COL_NOTES_COMPONENT]      * cfg.WEIGHT_NOTES       +
    df[cfg.COL_ACADEMIC_COMPONENT]   * cfg.WEIGHT_ACADEMIC
).clip(0, 100)
```

### Task 4-D: Update `score_risk()` docstring

Update the Returns section to mention `COL_ACADEMIC_COMPONENT` is added, and note
the new 5-component formula with updated weights.

### Task 4-E: Update `tests/test_risk_engine.py`

Read the full test file. For every test that asserts a specific expected risk score,
recompute the expected value using the new formula:
```
score = attendance_comp * 0.30 + practice_comp * 0.25 + trend_comp * 0.15
      + notes_comp * 0.10 + academic_comp * 0.20
```

For test rows where `quiz_score_gap` is not set or is NaN, `academic_component = 50.0`.
You must add `COL_QUIZ_GAP` and `COL_ACADEMIC_COMPONENT` to any DataFrame constructed
inline in the test file, or the risk engine will KeyError.

If the test DataFrame does not include `COL_QUIZ_GAP`, add it with a value of `pd.NA`
for neutral academic component (= 50.0).

## Verification

```bash
pytest tests/test_risk_engine.py -v
pytest tests/test_ingestion.py -v
```

Both test modules must pass. Fix any failures before proceeding.

## Checkpoint

> Phase REBUILD_MD_4 complete. Risk engine tests pass.
> Tell the user: "REBUILD_MD_4 is done and verified. Please type /clear to reset context,
> then paste REBUILD_MD_5 to continue."

---

---

# REBUILD_MD_5 — Downstream Consumers (Multi-Agent, Parallel)

## Skills to invoke first
```
Skill("superpowers:dispatching-parallel-agents")
```

## Context for this phase
Three source files need updating to consume the new schema. They are independent of each
other — dispatch all three as parallel agents in a single message.

- Agent A → `src/llm_engine.py` (richer prompt context)
- Agent B → `src/output_generator.py` (updated column handling for new fields)
- Agent C → `src/generate_data.py` (update synthetic generator to emit real schema)

## Agent A — `src/llm_engine.py`

Read the full file first. Find the code that constructs the student data dict or text
block sent to Claude in the tool-use prompt. Add the following fields to each student's
context object:

```python
"grade":           str(row.get(cfg.COL_GRADE, "unknown")),
"learning_track":  str(row.get(cfg.COL_LEARNING_TRACK, "unknown")),
"target_score":    float(row[cfg.COL_TARGET_SCORE]) if pd.notna(row.get(cfg.COL_TARGET_SCORE)) else None,
"last_quiz_score": float(row["last_quiz_score"]) if pd.notna(row.get("last_quiz_score")) else None,
"quiz_score_gap":  float(row[cfg.COL_QUIZ_GAP]) if pd.notna(row.get(cfg.COL_QUIZ_GAP)) else None,
```

Also update the system prompt or tool description to mention these new fields so Claude
knows how to interpret them (e.g., "quiz_score_gap > 20 means the student is significantly
below their target score and needs academic support messaging").

## Agent B — `src/output_generator.py`

Read the full file first. The column lists (`OUTPUT_COLS_PRIORITY`, `OUTPUT_COLS_CAMPUS`,
`DISPLAY_COLS_DASHBOARD`) are defined in `config.py` and already updated in REBUILD_MD_1.

Check that the output generator does NOT hardcode column names anywhere. Grep for any
literal strings like `"grade"`, `"target_score"`, `"learning_track"`, `"last_quiz_score"`.

If `output_generator.py` selects columns by name (e.g., `df[list(cfg.OUTPUT_COLS_CAMPUS)]`),
the new columns will appear automatically once the constant is updated. Verify this is the case.

If any function has a `try/except KeyError` that silently drops missing columns, extend
the expected column set to include the new ones so they are not silently dropped.

## Agent C — `src/generate_data.py`

Read the full file. Update the synthetic generator to emit CSVs with the real NOON Academy
column schema:

- **Metrics CSV**: emit `date` (not `metric_date`), add `last_quiz_score` (random int 30-95,
  with 10% chance of empty for rows before first quiz), add `days_until_next_quiz` (random int 1-14).

- **Notes CSV**: emit `note_id` (N001, N002, ...), `facilitator_email` (same as student's
  facilitator), `date` (not `note_date`), keep `note_text`.

- **Metadata CSV**: add `grade` (random choice "10" or "11"), `target_score` (random int 60-95),
  `learning_track` (random choice Standard/Accelerated/Remedial) after `facilitator_email`.

This allows `tests/test_generate_data.py` and fixture regeneration to remain valid.

## Verification (after all three agents complete)

```bash
pytest tests/test_llm_engine.py -v
pytest tests/test_output_generator.py -v
pytest tests/test_generate_data.py -v
```

All three test modules must pass. Fix any failures in this phase before proceeding.

## Checkpoint

> Phase REBUILD_MD_5 complete. Downstream consumer tests pass.
> Tell the user: "REBUILD_MD_5 is done and verified. Please type /clear to reset context,
> then paste REBUILD_MD_6 to continue."

---

---

# REBUILD_MD_6 — Test Suite: conftest + remaining test files

## Skills to invoke first
```
Skill("superpowers:systematic-debugging")   # only if tests are failing
```

## Context for this phase
You are updating `tests/conftest.py` (the shared `minimal_enriched_df` fixture)
and fixing any remaining test failures across the full suite. This is a cleanup phase
— all heavy lifting was done in phases 3-5.

Read `tests/conftest.py` in full before editing.

## Tasks

### Task 6-A: Update `minimal_enriched_df` in `tests/conftest.py`

The `minimal_enriched_df` fixture is used by `test_output_generator.py` and
`test_llm_engine.py`. It must include all columns that those modules now expect.

Add these new columns to the inline DataFrame construction:

```python
cfg.COL_GRADE:             pd.array(["10", "11", "10", "11", "10"], dtype="string"),
cfg.COL_LEARNING_TRACK:    pd.array(["Standard", "Accelerated", "Standard", "Remedial", "Standard"], dtype="string"),
cfg.COL_TARGET_SCORE:      pd.array([85.0, 90.0, 80.0, 60.0, 88.0], dtype="Float64"),
"last_quiz_score":         pd.array([50.0, 70.0, 75.0, 45.0, 85.0], dtype="Float64"),
cfg.COL_QUIZ_GAP:          pd.array([35.0, 20.0, 5.0, 15.0, 3.0], dtype="Float64"),
cfg.COL_ACADEMIC_COMPONENT: [70.0, 40.0, 10.0, 30.0, 6.0],
```

Update the docstring to mention the new columns and note that risk_score values
were computed with the 5-component formula:
```
score = attendance*0.30 + practice*0.25 + trend*0.15 + notes*0.10 + academic*0.20
```

### Task 6-B: Run the full test suite and fix any remaining failures

```bash
pytest -v 2>&1 | head -80
```

For every failing test:
1. Read the error carefully
2. Identify whether it is a column name mismatch, missing column, or wrong expected value
3. Fix the root cause — do NOT skip or xfail tests
4. Re-run until all pass

### Task 6-C: Update `tests/test_config.py` if it checks weight values

If `test_config.py` has an assertion like `WEIGHT_ATTENDANCE == 0.35`, update it to
match the new value `0.30`. Same for WEIGHT_PRACTICE (0.25), WEIGHT_TREND (0.15),
WEIGHT_NOTES (0.10). Also add assertion for WEIGHT_ACADEMIC (0.20) and that all five
sum to 1.0.

## Verification

```bash
pytest -v
```

ALL tests must pass (the count was 119+ before this migration; it should remain stable
or increase). Zero failures, zero errors.

## Checkpoint

> Phase REBUILD_MD_6 complete. Full test suite passes.
> Tell the user: "REBUILD_MD_6 is done and verified. Please type /clear to reset context,
> then paste REBUILD_MD_7 to continue."

---

---

# REBUILD_MD_7 — End-to-End Validation + Commit

## Skills to invoke first
```
Skill("superpowers:verification-before-completion")
Skill("superpowers:finishing-a-development-branch")
```

## Context for this phase
You are running the full pipeline against the real NOON Academy data and committing
everything. This is the final phase. Do not skip the verification steps.

## Tasks

### Task 7-A: Run the full test suite one final time

```bash
pytest -v
```

Zero failures required. If any exist, fix them before proceeding.

### Task 7-B: Run the pipeline end-to-end

```bash
python main.py
```

Watch for and fix:
- Any `KeyError` (column missing from DataFrame)
- Any `FileNotFoundError` (wrong path)
- Any `ValueError` from dtype coercion
- LLM API errors are OK — they use the three-layer fallback and should not crash the pipeline

The pipeline must complete with output in `outputs/` and `docs/`.

### Task 7-C: Verify output quality

After the pipeline runs, check:
```bash
python -c "
import pandas as pd
df = pd.read_csv('outputs/whatsapp_messages.csv')
print('Students in output:', len(df))
print('Columns:', list(df.columns))
print(df.head(3))
"
```

Confirm:
- 200 students processed (matching real data)
- No entirely empty `whatsapp_message` column (some NaN from fallback is OK)

### Task 7-D: Update `CLAUDE.md`

Add a note in the **Key Technical Decisions** section:
```
- **Real NOON Academy data** — pipeline reads from three real CSVs in data/ (200 students,
  5 campuses). Synthetic generator in src/generate_data.py is retained for test fixture
  regeneration only.
- **5-component risk scoring** — attendance(0.30) + practice(0.25) + trend(0.15) +
  notes(0.10) + academic(0.20). Academic component uses quiz_score_gap (target - actual).
```

### Task 7-E: Commit all changes

Stage only source and fixture changes — NOT generated outputs:
```bash
git add src/ tests/ CLAUDE.md REBUILD_PLAN.md REBUILD_PROMPT.md
git status
```

Review what is staged. Then commit:
```
git commit -m "$(cat <<'EOF'
feat: migrate pipeline from synthetic to real NOON Academy data

- Fix column mismatch: real CSVs use 'date'; internal names preserved
  via post-read rename (date -> metric_date / note_date)
- Add grade, target_score, learning_track from real metadata schema
- Add last_quiz_score, days_until_next_quiz from real metrics schema
- Compute quiz_score_gap (target - actual, clipped >= 0) in ingestion
- Add 5th academic risk component using quiz_score_gap
- Rebalance weights: attendance=0.30, practice=0.25, trend=0.15,
  notes=0.10, academic=0.20 (sum = 1.0)
- Update all 7 fixture CSVs to match real schema
- Update LLM prompt with grade, learning_track, target_score, quiz data
- Update generate_data.py to emit real schema for fixture regeneration

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task 7-F: Push to remote

```bash
git push
```

## Final Verification Checklist (from `superpowers:verification-before-completion`)

Before claiming success, confirm all of the following:
- [ ] `pytest -v` — all tests pass
- [ ] `python main.py` — exits with code 0
- [ ] `outputs/whatsapp_messages.csv` exists with 200 rows
- [ ] `outputs/intervention_priority_list.xlsx` exists
- [ ] At least one campus dashboard `.xlsx` exists in `outputs/`
- [ ] `git log --oneline -3` shows the new commit at the top
- [ ] `git status` is clean (no uncommitted changes)

## Checkpoint

> Phase REBUILD_MD_7 complete. Migration is done.
> Tell the user:
> "All 7 phases are complete. The pipeline now reads from the real NOON Academy data
> (200 students, real Arabic facilitator notes, real quiz scores). All tests pass and
> the end-to-end run is clean. The commit has been pushed."
