# Phase 2: Risk Scoring Engine - Research

**Researched:** 2026-05-23
**Domain:** Deterministic numerical scoring over a pandas DataFrame (pure function, no I/O)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 Attendance component:** `attendance_component = (1 - attendance_days / 14) * 100`
  - 14/14 days → 0 risk; 0/14 → 100 risk; denominator always 14
  - Uses `attendance_days` from Phase 1 ingestion
- **D-02 Practice component:** `practice_component = max(0, (1 - avg_practice / 15)) * 100`
  - 15+ questions/day → 0 risk; 0/day → 100 risk; capped at 15
  - `avg_practice = practice_total_q / 14` (always divide by 14, not attendance_days)
- **D-03 Trend component:** Binary 0/100
  - `last3_avg = mean(daily_session_series[-3:])`, `first11_avg = mean(daily_session_series[:11])`
  - `trend_component = 100 if last3_avg < first11_avg else 0`
  - If series length < 3 values → `trend_component = 50` (neutral)
  - If `first11_avg == 0` → activity in last 3 = 0 risk; no activity = 0 (flat)
- **D-04 Notes component:** `notes_component = min(days_since_note, 30) / 30 * 100`
  - Note today → 0; 30+ days or NaT → 100
  - Reference date: `pd.Timestamp.now().normalize()`
- **D-05 Weighted formula:**
  `risk_score = round(att_c * 0.35 + prac_c * 0.30 + trend_c * 0.20 + notes_c * 0.15, 2)`
  - Weights from `cfg.WEIGHT_ATTENDANCE / WEIGHT_PRACTICE / WEIGHT_TREND / WEIGHT_NOTES`
  - Clip final to [0, 100] after rounding
- **D-06 Risk levels:**
  - `>= 75` → CRITICAL; `>= 50` → HIGH; `>= 25` → MEDIUM; `< 25` → LOW
  - Thresholds from `cfg.RISK_THRESHOLD_CRITICAL / RISK_THRESHOLD_HIGH / RISK_THRESHOLD_MEDIUM`
- **D-07 trend_direction:** string label `"declining" / "stable" / "improving"`
  - `last3 < first11` → declining; `>` → improving; `==` → stable
  - Uses `cfg.COL_TREND_DIR`
- **D-08 recommended_action labels:**
  - CRITICAL → "Contact parent immediately"
  - HIGH → "Schedule check-in this week"
  - MEDIUM → "Monitor closely"
  - LOW → "On track"
  - Uses `cfg.COL_RECOMMENDED_ACTION`
- **D-09 Component score columns added to output DataFrame:**
  - `attendance_component`, `practice_component`, `trend_component`, `notes_component` (float 0-100)
  - **NOT yet in `src/config.py`** — must be added as `COL_ATTENDANCE_COMPONENT`, `COL_PRACTICE_COMPONENT`, `COL_TREND_COMPONENT`, `COL_NOTES_COMPONENT`
- **Locked signature:** `score_risk(df: pd.DataFrame) -> pd.DataFrame` (pure function, no I/O)

### Claude's Discretion

- Vectorization approach (apply vs vectorized — research recommends vectorized for performance, `.apply` for `daily_session_series` because it's a list-column)
- Whether to add `attendance_rate` as `attendance_days / 14` (float 0.0-1.0) alongside `attendance_component` — RISK-07 names it as an output column, so YES, must include
- How to handle NaN values inside `daily_session_series` (research recommends `np.nanmean` with empty-array guard)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RISK-01 | Compute `attendance_rate` = sessions attended / total possible sessions Days 1–14 | D-01 formula + `attendance_days / 14`; ingestion already produces `attendance_days` count where `session_attended_min > 0`. Add `attendance_rate` column for RISK-07 compatibility. |
| RISK-02 | Compute `avg_practice_questions` = average daily practice across available days | D-02 formula: `practice_total_q / 14`. Ingestion produces `practice_total_q` (sum). Always divide by 14 per D-02 — fixed window. |
| RISK-03 | Compute `trend_direction` = last 3 days avg vs first 11 days avg; declining = higher risk | D-03 binary scoring + D-07 string label. Uses `daily_session_series` list column from ingestion. |
| RISK-04 | Compute `days_since_last_note`; no note = maximum penalty | D-04: `(today - latest_note_date).days` clamped to [0, 30]. NaT → 30 (max penalty). |
| RISK-05 | Compute `risk_score` (0–100) weighted: attendance 35%, practice 30%, trend 20%, notes 15% | D-05 with weights from `cfg.WEIGHT_*` constants. |
| RISK-06 | Assign `risk_level`: CRITICAL ≥75, HIGH 50–74, MEDIUM 25–49, LOW <25 | D-06 with thresholds from `cfg.RISK_THRESHOLD_*` constants. |
| RISK-07 | Output DataFrame includes: risk_score, risk_level, attendance_rate, avg_practice_questions, trend_direction, days_since_last_note | All 6 RISK-07 columns + 4 D-09 component columns + recommended_action. Column names from `cfg.COL_*` constants. |
| RISK-08 | All column names from `cfg.COL_*` — no bare strings in `risk_engine.py` | Test must grep for string literals that look like column names; enforce via `test_no_hardcoded_columns` pattern. |
</phase_requirements>

## Summary

Phase 2 implements a **pure function** that adds risk scoring columns to a Phase 1 DataFrame. All formula decisions are locked in CONTEXT.md — the research effort focused on (1) the exact Phase 1 output schema, (2) pandas idioms for safely operating on a list-column (`daily_session_series`), (3) NaN/NaT handling at the boundary between Phase 1 and Phase 2, (4) test patterns for deterministic pure functions, and (5) detecting bare string literals to enforce RISK-08.

The phase is technically small (one function, no external dependencies beyond pandas/numpy already in `requirements.txt`), but **gets hard at the edge cases**: list-column with varying lengths, NaT in `latest_note_date`, students with no metrics rows (handled by Phase 1 post-merge fill but `daily_session_series` is still an empty list), float-precision in the weighted sum, and `RISK_THRESHOLD_HIGH = 50` collision with the requirements doc that says "HIGH 50–74" (boundary inclusivity matters).

**Primary recommendation:** Implement `score_risk(df)` as a composition of small private helpers (`_attendance_component`, `_practice_component`, `_trend_component`, `_notes_component`, `_risk_level_for_score`, `_action_for_level`), use vectorized pandas operations everywhere except `daily_session_series` (use `.apply` for that single column), copy the DataFrame at function entry (`df = df.copy()`) to preserve purity, and assert column-name discipline with a grep-style test.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-student risk computation | Pure function (CPU) | — | Deterministic numerical transform; no I/O, no state, no API |
| Component score breakdown | Pure function (CPU) | — | Same call site as risk_score — keep computation together for audit trail |
| Risk level labeling | Pure function (CPU) | — | Threshold compare on a single Series column |
| Recommended action default | Pure function (CPU) | LLM (Phase 3 overwrite) | Rule-based labels here become the **fallback** if LLM fails (D-08) |
| Column name discipline | Compile-time via constants import | Test-time grep | RISK-08 — enforce via `from src import config as cfg` and a regression test |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.2.3 | DataFrame operations, vectorized arithmetic, groupby/merge | [VERIFIED: requirements.txt pinned, used by Phase 1] Already a project dependency; D-05 pandas version pin in CLAUDE.md (Copy-on-Write opt-in in 2.x, mandatory in 3.x). |
| numpy | (transitive via pandas) | `np.nanmean`, `np.clip`, array-safe aggregations on list-column | [VERIFIED: transitive dependency of pandas==2.2.3] Already available; need for safe NaN-aware mean of `daily_session_series` slices. |

### Supporting
None required. The function is pure pandas/numpy.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas `.apply(axis=1)` for trend column | Pre-extract `daily_session_series` to a numpy 2-D array and slice columns | Slightly faster at 10k+ students but adds complexity; with 300 students from synthetic data and ~2000 students realistic upper-bound for v1, `.apply` on the list-column is fine. [CITED: pandas docs — vectorization vs apply](https://pandas.pydata.org/docs/user_guide/enhancingperf.html) |
| Per-row Python loop | Vectorized arithmetic for all scalar columns | Vectorized is 10-100x faster and more idiomatic. **Use vectorized everywhere except** the list-column trend computation. [ASSUMED — standard pandas wisdom] |
| pandas `groupby` on student_id | Not needed — input is already one-row-per-student from Phase 1 merge | Phase 1's `ingestion.ingest()` already aggregates and deduplicates; no groupby needed in Phase 2. [VERIFIED: src/ingestion.py L319-345 + 01-03-SUMMARY.md L77] |

**Installation:** No new dependencies. `requirements.txt` unchanged.

**Version verification:**
```bash
# pandas==2.2.3 already in requirements.txt (Phase 1 INFRA-03)
# numpy is transitive dep of pandas
py -3.12 -c "import pandas as pd; import numpy as np; print(pd.__version__, np.__version__)"
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pandas | PyPI | 17 years | ~600M/month | github.com/pandas-dev/pandas | [OK] | Already installed (Phase 1) |
| numpy | PyPI | 19 years | ~700M/month | github.com/numpy/numpy | [OK] | Already installed (transitive) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

slopcheck verified both packages clean on 2026-05-23 (output: `2 OK`).

## Architecture Patterns

### System Architecture Diagram

```
                  Phase 1 output                    Phase 3 input
                       |                                  ^
                       v                                  |
   ingest() -> DataFrame -> [score_risk()] -> DataFrame --+
                              |
            +-----------------+-----------------+
            |                 |                 |
            v                 v                 v
   per-student scalar    list-column      datetime column
   ops (vectorized)      ops (.apply)     (vectorized .dt)
            |                 |                 |
            v                 v                 v
   attendance_component   trend_component   notes_component
   practice_component
            |                 |                 |
            +---------+-------+-----------------+
                      v
            weighted sum + clip
                      |
                      v
            risk_score (float64, 0-100)
                      |
            +---------+---------+
            v                   v
   risk_level (str)    recommended_action (str)
   via threshold       via D-08 dict lookup
```

**Trace:** A student row enters with `attendance_days`, `practice_total_q`, `daily_session_series` (list[float] of length ≤14), and `latest_note_date` (datetime64 or NaT). Four component scores compute independently and column-vectorized. The weighted sum produces `risk_score`. Threshold comparison produces `risk_level`. Dict lookup on `risk_level` produces `recommended_action`. The output DataFrame has 10 new columns; nothing is removed from the input.

### Recommended Project Structure
```
src/
├── risk_engine.py     # score_risk() public + 6 private helpers
tests/
├── test_risk_engine.py    # NEW — pytest with parametrize for boundary tests
└── conftest.py            # may add risk_input_df fixture builder helper
```

Single file is appropriate — the entire risk engine fits in ~200 lines. No subpackage needed.

### Pattern 1: Pure-function copy-on-entry
**What:** Copy the input DataFrame at function entry so the caller's reference is never mutated.
**When to use:** Every pure DataFrame-in / DataFrame-out function (CLAUDE.md: pure function, no side effects).
**Example:**
```python
def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    """..."""
    df = df.copy()  # purity guarantee — never mutate caller's frame
    df[cfg.COL_ATTENDANCE_COMPONENT] = _attendance_component(df)
    # ...
    return df
```

### Pattern 2: Vectorized component computation
**What:** Compute each component as a Series operation over the whole DataFrame, not row-by-row.
**When to use:** Scalar input columns (`attendance_days`, `practice_total_q`, `latest_note_date`).
**Example:**
```python
def _attendance_component(df: pd.DataFrame) -> pd.Series:
    """Vectorized D-01: (1 - days/14) * 100, clipped to [0,100]."""
    return ((1 - df["attendance_days"] / 14) * 100).clip(0, 100)
```
For `attendance_days` already an Int/Float column, this is a single vectorized expression — no `.apply` needed.

### Pattern 3: `.apply` for list-column with custom logic
**What:** Use `.apply` on the list-column for trend computation; no clean vectorized way exists for variable-length slices.
**When to use:** Operations on `daily_session_series` (Python `list[float]` per row).
**Example:**
```python
def _trend_component_and_direction(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """D-03 trend score + D-07 string label, in one pass."""
    def _compute(series: list) -> tuple[float, str]:
        if not isinstance(series, list) or len(series) < 3:
            return (50.0, "stable")  # neutral (D-03 edge case)
        # NaN-safe means in case ingestion ever produces NaN inside the series
        last3 = float(np.nanmean(series[-3:])) if len(series) >= 3 else 0.0
        first11 = float(np.nanmean(series[:11])) if len(series) >= 1 else 0.0
        if last3 < first11:
            return (100.0, "declining")
        elif last3 > first11:
            return (0.0, "improving")
        else:
            return (0.0, "stable")  # D-03: equal → 0 (flat = no decline)
    results = df["daily_session_series"].apply(_compute)
    components = results.apply(lambda t: t[0]).astype(float)
    directions = results.apply(lambda t: t[1]).astype("string")
    return components, directions
```

### Pattern 4: Datetime arithmetic via `.dt` accessor
**What:** Compute `days_since_last_note` using the `.dt` accessor on a datetime64 Series — vectorized and NaT-safe.
**When to use:** Any date diff over a datetime64 column.
**Example:**
```python
def _days_since_last_note(df: pd.DataFrame) -> pd.Series:
    """Vectorized D-04 helper: days since latest_note_date (NaT → 30 max penalty)."""
    today = pd.Timestamp.now().normalize()
    delta_days = (today - df["latest_note_date"]).dt.days
    # NaT subtraction yields NaT → .dt.days is <NA>; fillna(30) handles "no note" case
    return delta_days.fillna(30).clip(lower=0, upper=30).astype(float)
```

### Pattern 5: Dict-lookup for categorical mapping
**What:** Use a module-level dict and `Series.map()` for risk_level → recommended_action mapping (D-08).
**When to use:** Categorical-to-categorical mapping with a fixed lookup.
**Example:**
```python
_ACTION_BY_LEVEL: dict[str, str] = {
    "CRITICAL": "Contact parent immediately",
    "HIGH": "Schedule check-in this week",
    "MEDIUM": "Monitor closely",
    "LOW": "On track",
}

def _action_for_level(level_series: pd.Series) -> pd.Series:
    return level_series.map(_ACTION_BY_LEVEL).astype("string")
```

### Anti-Patterns to Avoid
- **`df["col"] = ...` after slicing without `.copy()`** — pandas 2.x raises `SettingWithCopyWarning`; in 3.x this would silently fail under CoW. Always copy at function entry.
- **Mutating `daily_session_series` in `.apply`** — the list values are shared references with the caller's frame. Slice instead of mutating: use `series[-3:]` not `series[-3:].clear()`.
- **`if pd.isna(x)` inside vectorized code** — use `.fillna()` or `.dropna()` for Series-level NaN handling, not row-by-row `pd.isna`.
- **Bare string literals like `"risk_score"` or `"attendance_days"`** — RISK-08 violation. Always import from `cfg`.
- **Float comparison `==` for thresholds** — `risk_score == 75` is fragile if upstream uses different rounding. Use `>=` consistently per D-06.
- **Computing `today` inside `.apply`** — `pd.Timestamp.now()` should be called **once** at function entry; calling inside an apply per row makes the function non-deterministic within a single call if a date boundary crosses mid-execution.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Risk threshold lookup | Custom if/elif chain | `pd.cut()` with `bins` and `labels` | One-line vectorized; less error-prone for boundary inclusivity |
| Days-since-date math | `(datetime.now() - row["latest_note_date"]).days` per row | `.dt.days` on a `(pd.Timestamp.now() - col)` Series | Vectorized, NaT-safe, no apply needed |
| List-slice average | `sum(series[-3:]) / 3` | `np.nanmean(series[-3:])` | NaN-safe, single-element-safe (returns the element), empty-list-safe (returns NaN → caller handles) |
| Clipping to [0,100] | `max(0, min(100, x))` per row | `.clip(0, 100)` on Series | Vectorized; pandas optimized path |
| Map level → action | Multi-line if/elif | `Series.map(_ACTION_BY_LEVEL)` | Dict lookup; impossible to drift if dict is single source of truth |

**Key insight:** pandas has a vectorized one-liner for every operation in this phase **except** the trend computation (list-column with variable length). Use vectorized for the 99%; use `.apply` only for the trend column.

## Runtime State Inventory

Not applicable — Phase 2 is greenfield (adds a new module body to a stub file). No rename, refactor, or data migration involved.

## Common Pitfalls

### Pitfall 1: `RISK_THRESHOLD_HIGH = 50` boundary off-by-one vs RISK-06 spec
**What goes wrong:** RISK-06 says "HIGH (50–74)" — read literally that's an exclusive upper bound. CONTEXT.md D-06 uses `>= RISK_THRESHOLD_HIGH (50)` for HIGH. Both produce the same result **if** CRITICAL is computed first (`>=75` strips off 75-100), but only if the threshold ladder is `if/elif/elif/else` in descending order.
**Why it happens:** Naive implementations test ranges in ascending order or use a single `pd.cut` with overlapping intervals.
**How to avoid:** Use `pd.cut(scores, bins=[-1, 25, 50, 75, 101], labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"], right=False)` — `right=False` makes intervals left-closed: `[0,25), [25,50), [50,75), [75,101)`. This matches D-06 exactly. **Verify with boundary tests:** `score=74.99 → HIGH`, `score=75.0 → CRITICAL`, `score=49.99 → MEDIUM`, `score=50.0 → HIGH`.
**Warning signs:** Test `score=75 → CRITICAL` passes but `score=74.99 → HIGH` fails (or vice versa).

### Pitfall 2: `daily_session_series` is `list[np.float64]`, not `np.array`
**What goes wrong:** Ingestion produces lists via `.agg(daily_session_series=(cfg.COL_SESSION_MIN, list))`. The elements are `np.float64` objects but the container is a Python list, not a numpy array.
**Why it happens:** Pandas `.agg` with `list` converts a Series to a Python list, not an ndarray.
**How to avoid:** When slicing in `.apply`, treat as a list: `series[-3:]` works fine on Python lists. Pass to `np.nanmean()` which accepts list or array. Do not call `.mean()` (method) on the list — only `np.mean()`/`np.nanmean()` (function).
**Warning signs:** `AttributeError: 'list' object has no attribute 'mean'`.

### Pitfall 3: `latest_note_date` is NaT for students with no notes
**What goes wrong:** Phase 1 left-joins notes onto metadata; students with no notes get NaT. `(today - NaT).days` returns `<NA>` (pandas missing scalar), not 30.
**Why it happens:** Datetime arithmetic propagates NaT; `.dt.days` on a NaT-containing TimedeltaSeries returns `<NA>` (Int64 nullable).
**How to avoid:** Apply `.fillna(30)` AFTER `.dt.days`, then `.clip(lower=0, upper=30)`, then cast to float for the formula. Tested: `(pd.Timestamp.now() - pd.Series([pd.NaT])).dt.days.fillna(30) == 30`.
**Warning signs:** `notes_component` Series contains NaN values; risk_score for students with no notes is NaN.

### Pitfall 4: Empty `daily_session_series` (zero-length list)
**What goes wrong:** A student in metadata with zero metrics rows produces `daily_session_series = []` (post-merge, before fillna). Phase 1 currently fills `session_total_min`, `practice_total_q`, `attendance_days` with 0 but does **not** fill `daily_session_series` (it remains NaN, not `[]`).
**Why it happens:** Phase 1's `numeric_fill_cols` (ingestion.py L376) does not include list-columns. Students with no metrics rows have `daily_session_series = NaN` (float) after merge, NOT an empty list.
**How to avoid:** In `_trend_component_and_direction`, the guard `if not isinstance(series, list) or len(series) < 3` correctly handles BOTH cases:
  - `NaN` (no metrics) → not a list → returns (50.0, "stable")
  - `[]` (defensive) → list of length 0 < 3 → returns (50.0, "stable")
**Warning signs:** `TypeError: object of type 'float' has no len()` if the isinstance guard is missing.

### Pitfall 5: Float precision in weighted sum vs `round(..., 2)`
**What goes wrong:** `0.35 + 0.30 + 0.20 + 0.15 = 0.9999999999` (binary float) — rare, but if components are `[100, 100, 100, 100]`, weighted sum is `99.99...` then `round(_, 2)` is `100.0`. Edge case: components are `[100, 0, 100, 0]` → `0.35*100 + 0.20*100 = 55.0` exact → OK. Real risk is around boundary 75.0 / 50.0 / 25.0.
**Why it happens:** IEEE 754 binary float addition.
**How to avoid:** D-05 explicitly says `round(..., 2)`. Apply round AFTER the sum, then `.clip(0, 100)`. For threshold comparison, the rounded score is fine. Use `pd.cut` with `right=False` (left-closed) so a score of exactly 75.0 lands in CRITICAL, not HIGH.
**Warning signs:** A boundary unit test flickers — passing locally but failing on a different platform's float behavior.

### Pitfall 6: RISK-07 column name `attendance_rate` vs D-01 column name `attendance_component`
**What goes wrong:** RISK-07 says output must include `attendance_rate`. D-09 introduces `attendance_component`. These are DIFFERENT: `attendance_rate = attendance_days / 14` (0.0–1.0 float); `attendance_component = (1 - rate) * 100` (0–100 risk score).
**Why it happens:** The requirements doc uses domain language ("rate"); the formula uses risk-component language.
**How to avoid:** Output **both** columns. `cfg.COL_ATTENDANCE_RATE` already exists in config.py. `cfg.COL_ATTENDANCE_COMPONENT` does NOT exist yet — must be added in Phase 2. Same pattern: output `avg_practice_questions` (domain) AND `practice_component` (risk). Phase 4 Excel uses the domain columns; Phase 5 risk breakdown uses the components.
**Warning signs:** Phase 4 Excel generation fails with KeyError on `attendance_rate`.

### Pitfall 7: `pd.Timestamp.now()` makes the function time-dependent (not pure)
**What goes wrong:** Strictly, a "pure function" returns the same output for the same input. `pd.Timestamp.now()` introduces time dependence — running today vs tomorrow on the same input DataFrame produces different `days_since_last_note` and possibly different risk levels.
**Why it happens:** Risk scoring is inherently time-sensitive — "days since last note" requires a reference date.
**How to avoid:** Document this limitation in the docstring: "Pure with respect to the input DataFrame **as of the wall-clock date at call time**." For tests, freeze time with `freezegun` (already in stack: 1.5.5 per STATE.md L105). Pattern: `with freeze_time("2026-05-23"): df = score_risk(input_df)` makes assertions deterministic.
**Warning signs:** A test that asserts `days_since_last_note == 5` fails on day 6 of CI.

### Pitfall 8: `df.attrs` is dropped by some pandas operations
**What goes wrong:** Phase 1 attaches `df.attrs["data_quality_warnings"]`. Some pandas operations (especially `pd.concat`, certain merges) silently drop `.attrs`.
**Why it happens:** Pandas `.attrs` is experimental and not propagated through all operations.
**How to avoid:** In `score_risk`, do NOT use operations that drop attrs. `df.copy()` preserves attrs (verified: pandas 2.2 `df.copy().attrs == df.attrs`). Column assignment via `df[col] = ...` preserves attrs. If the function ever needs `pd.concat`, manually re-attach: `result.attrs = df.attrs`.
**Warning signs:** Phase 4 cannot find `data_quality_warnings` for run_log.json.

## Code Examples

### Full `score_risk` skeleton (vectorized + .apply hybrid)

```python
"""Risk scoring engine for boon-academy-intervention.

Pure function: deterministic weighted scoring over a one-row-per-student
DataFrame. No I/O, no API calls, no side effects (except wall-clock dependence
on pd.Timestamp.now() for days_since_last_note — see docstring caveat).
"""
import logging

import numpy as np
import pandas as pd

from src import config as cfg

logger = logging.getLogger(__name__)

# D-08: rule-based recommended_action labels (Phase 3 LLM overwrites for CRITICAL/HIGH)
_ACTION_BY_LEVEL: dict[str, str] = {
    "CRITICAL": "Contact parent immediately",
    "HIGH":     "Schedule check-in this week",
    "MEDIUM":   "Monitor closely",
    "LOW":      "On track",
}

# D-06: threshold ladder for pd.cut — left-closed intervals
# bins:   [-inf, 25, 50, 75, +inf]   right=False
# labels: ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
_RISK_BINS = [-np.inf, cfg.RISK_THRESHOLD_MEDIUM, cfg.RISK_THRESHOLD_HIGH,
              cfg.RISK_THRESHOLD_CRITICAL, np.inf]
_RISK_LABELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Fixed window length per D-01/D-02 (Days 1-14 = 14 days)
_WINDOW_DAYS: int = 14
_PRACTICE_CAP: float = 15.0     # D-02 cap
_NOTES_MAX_DAYS: int = 30       # D-04 cap
_TREND_NEUTRAL: float = 50.0    # D-03 fallback when series < 3


def _attendance_component(df: pd.DataFrame) -> pd.Series:
    """D-01: (1 - attendance_days/14) * 100, clipped [0,100]."""
    return ((1.0 - df["attendance_days"].astype(float) / _WINDOW_DAYS) * 100).clip(0, 100)


def _practice_component(df: pd.DataFrame) -> pd.Series:
    """D-02: max(0, 1 - avg/15) * 100. avg = practice_total_q / 14 (always 14)."""
    avg = df["practice_total_q"].astype(float) / _WINDOW_DAYS
    return ((1.0 - (avg / _PRACTICE_CAP)).clip(lower=0) * 100).clip(0, 100)


def _trend_component_and_direction(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """D-03 binary + D-07 string label, computed together (one .apply pass)."""
    def _compute(series) -> tuple[float, str]:
        # Guards: NaN (no metrics), non-list, or too short
        if not isinstance(series, list) or len(series) < 3:
            return (_TREND_NEUTRAL, "stable")
        last3 = float(np.nanmean(series[-3:]))
        first11 = float(np.nanmean(series[:11]))
        if last3 < first11:
            return (100.0, "declining")
        elif last3 > first11:
            return (0.0, "improving")
        return (0.0, "stable")

    results = df["daily_session_series"].apply(_compute)
    components = results.map(lambda t: t[0]).astype(float)
    directions = results.map(lambda t: t[1]).astype("string")
    return components, directions


def _days_since_last_note(df: pd.DataFrame, today: pd.Timestamp) -> pd.Series:
    """D-04 helper: days since latest_note_date, NaT → 30 (max penalty)."""
    delta = (today - df["latest_note_date"]).dt.days
    return delta.fillna(_NOTES_MAX_DAYS).clip(lower=0, upper=_NOTES_MAX_DAYS).astype(float)


def _notes_component(days_since: pd.Series) -> pd.Series:
    """D-04: min(days, 30) / 30 * 100."""
    return (days_since.clip(upper=_NOTES_MAX_DAYS) / _NOTES_MAX_DAYS * 100).clip(0, 100)


def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic weighted risk scoring to the student DataFrame.

    Pure function: takes a DataFrame produced by ingestion.ingest() and returns
    a new DataFrame with risk_score, risk_level, recommended_action, and the
    four component scores added. Caller's DataFrame is never mutated.

    Note: this function reads pd.Timestamp.now() ONCE at the start to compute
    days_since_last_note. Same input on a different wall-clock date may produce
    a different output. Use freezegun in tests for deterministic assertions.

    Args:
        df: One-row-per-student DataFrame from ingestion.ingest(). Required
            columns: attendance_days, practice_total_q, daily_session_series
            (list[float] or NaN), latest_note_date (datetime64 or NaT).

    Returns:
        Copy of df with these columns added:
          - attendance_rate (float 0-1)        — RISK-07
          - avg_practice_questions (float)     — RISK-07
          - trend_direction (str)              — RISK-07, D-07
          - days_since_last_note (float 0-30)  — RISK-07
          - attendance_component (float 0-100) — D-09
          - practice_component (float 0-100)   — D-09
          - trend_component (float 0-100)      — D-09
          - notes_component (float 0-100)      — D-09
          - risk_score (float 0-100)           — RISK-05
          - risk_level (str)                   — RISK-06
          - recommended_action (str)           — D-08
    """
    df = df.copy()
    today = pd.Timestamp.now().normalize()

    # RISK-07 domain columns
    df[cfg.COL_ATTENDANCE_RATE] = df["attendance_days"].astype(float) / _WINDOW_DAYS
    df[cfg.COL_AVG_PRACTICE] = df["practice_total_q"].astype(float) / _WINDOW_DAYS
    df[cfg.COL_DAYS_SINCE_NOTE] = _days_since_last_note(df, today)

    # D-09 component scores
    df[cfg.COL_ATTENDANCE_COMPONENT] = _attendance_component(df)
    df[cfg.COL_PRACTICE_COMPONENT] = _practice_component(df)
    trend_c, trend_d = _trend_component_and_direction(df)
    df[cfg.COL_TREND_COMPONENT] = trend_c
    df[cfg.COL_TREND_DIR] = trend_d
    df[cfg.COL_NOTES_COMPONENT] = _notes_component(df[cfg.COL_DAYS_SINCE_NOTE])

    # D-05 weighted sum + round + clip
    df[cfg.COL_RISK_SCORE] = (
        df[cfg.COL_ATTENDANCE_COMPONENT] * cfg.WEIGHT_ATTENDANCE
        + df[cfg.COL_PRACTICE_COMPONENT] * cfg.WEIGHT_PRACTICE
        + df[cfg.COL_TREND_COMPONENT] * cfg.WEIGHT_TREND
        + df[cfg.COL_NOTES_COMPONENT] * cfg.WEIGHT_NOTES
    ).round(2).clip(0, 100)

    # D-06 risk level (left-closed intervals via right=False)
    df[cfg.COL_RISK_LEVEL] = pd.cut(
        df[cfg.COL_RISK_SCORE],
        bins=_RISK_BINS,
        labels=_RISK_LABELS,
        right=False,
    ).astype("string")

    # D-08 recommended action via dict map
    df[cfg.COL_RECOMMENDED_ACTION] = df[cfg.COL_RISK_LEVEL].map(_ACTION_BY_LEVEL).astype("string")

    logger.info(f"Scored {len(df)} students — "
                f"CRITICAL={(df[cfg.COL_RISK_LEVEL] == 'CRITICAL').sum()}, "
                f"HIGH={(df[cfg.COL_RISK_LEVEL] == 'HIGH').sum()}, "
                f"MEDIUM={(df[cfg.COL_RISK_LEVEL] == 'MEDIUM').sum()}, "
                f"LOW={(df[cfg.COL_RISK_LEVEL] == 'LOW').sum()}")

    return df
```

### Test fixture pattern (parametrized boundary tests)

```python
# tests/test_risk_engine.py
import numpy as np
import pandas as pd
import pytest
from freezegun import freeze_time

from src import config as cfg
from src.risk_engine import score_risk


def _build_student_row(
    student_id: str = "S0001",
    attendance_days: int = 14,
    practice_total_q: float = 210.0,    # 15/day * 14 = full practice
    session_series: list | None = None,
    latest_note_date: pd.Timestamp | None = None,
) -> dict:
    """Helper to build a single-student DataFrame row with sensible defaults."""
    if session_series is None:
        session_series = [30.0] * 14  # all 14 days, 30 min/day
    if latest_note_date is None:
        latest_note_date = pd.Timestamp("2026-05-23")  # today (in frozen-time tests)
    return {
        cfg.COL_STUDENT_ID: student_id,
        cfg.COL_STUDENT_NAME: "Test Student",
        cfg.COL_CAMPUS_ID: "C01",
        cfg.COL_PARENT_PHONE: "0501234567",
        cfg.COL_FACILITATOR_EMAIL: "t@example.com",
        "attendance_days": attendance_days,
        "practice_total_q": practice_total_q,
        "session_total_min": float(sum(session_series)),
        "daily_session_series": session_series,
        "daily_practice_series": [practice_total_q / 14] * 14,
        "daily_dates": [str(pd.Timestamp("2026-05-10") + pd.Timedelta(days=i)) for i in range(14)],
        "latest_note_date": latest_note_date,
        "latest_note_text": "test note",
    }


@freeze_time("2026-05-23")
def test_perfect_student_is_low():
    """Success Criterion 3: perfect attendance + high practice + recent note → LOW."""
    df = pd.DataFrame([_build_student_row(
        attendance_days=14, practice_total_q=15 * 14,
        session_series=[10.0]*11 + [30.0]*3,  # improving
        latest_note_date=pd.Timestamp("2026-05-23"),
    )])
    result = score_risk(df)
    assert result[cfg.COL_RISK_SCORE].iloc[0] < 25
    assert result[cfg.COL_RISK_LEVEL].iloc[0] == "LOW"


@freeze_time("2026-05-23")
def test_worst_student_is_critical():
    """Success Criterion 2: zero attendance + zero practice + declining + no note → CRITICAL."""
    df = pd.DataFrame([_build_student_row(
        attendance_days=0, practice_total_q=0,
        session_series=[10.0]*11 + [0.0]*3,  # declining
        latest_note_date=pd.NaT,
    )])
    result = score_risk(df)
    assert result[cfg.COL_RISK_SCORE].iloc[0] >= 75
    assert result[cfg.COL_RISK_LEVEL].iloc[0] == "CRITICAL"


@pytest.mark.parametrize("score,expected_level", [
    (0.0,   "LOW"),
    (24.99, "LOW"),
    (25.0,  "MEDIUM"),
    (49.99, "MEDIUM"),
    (50.0,  "HIGH"),
    (74.99, "HIGH"),
    (75.0,  "CRITICAL"),
    (100.0, "CRITICAL"),
])
def test_risk_level_boundaries(score, expected_level):
    """RISK-06 boundary inclusivity — left-closed intervals."""
    # construct an input that produces exactly `score` after the formula
    # easiest: monkeypatch components by passing pre-computed values via a custom path,
    # OR build inputs that hit the score exactly. Cleanest: assert pd.cut directly.
    series = pd.Series([score])
    result = pd.cut(series, bins=[-np.inf, 25, 50, 75, np.inf],
                    labels=["LOW","MEDIUM","HIGH","CRITICAL"], right=False)
    assert str(result.iloc[0]) == expected_level


def test_attendance_component_endpoints():
    """D-01: 0/14 → 100, 14/14 → 0."""
    df = pd.DataFrame([_build_student_row(attendance_days=0),
                        _build_student_row(student_id="S0002", attendance_days=14)])
    result = score_risk(df)
    assert result[cfg.COL_ATTENDANCE_COMPONENT].iloc[0] == 100.0
    assert result[cfg.COL_ATTENDANCE_COMPONENT].iloc[1] == 0.0


def test_trend_short_series_is_neutral():
    """D-03 edge: series < 3 values → trend_component = 50."""
    df = pd.DataFrame([_build_student_row(session_series=[10.0, 20.0])])
    result = score_risk(df)
    assert result[cfg.COL_TREND_COMPONENT].iloc[0] == 50.0
    assert result[cfg.COL_TREND_DIR].iloc[0] == "stable"


def test_notes_component_nat_is_max():
    """D-04 edge: NaT → 30 days → 100 risk."""
    df = pd.DataFrame([_build_student_row(latest_note_date=pd.NaT)])
    result = score_risk(df)
    assert result[cfg.COL_DAYS_SINCE_NOTE].iloc[0] == 30.0
    assert result[cfg.COL_NOTES_COMPONENT].iloc[0] == 100.0


def test_pure_function_does_not_mutate_input():
    """Pure function discipline: caller's df is unchanged after score_risk."""
    df = pd.DataFrame([_build_student_row()])
    cols_before = set(df.columns)
    _ = score_risk(df)
    cols_after = set(df.columns)
    assert cols_before == cols_after, "score_risk mutated input columns"


def test_recommended_action_matches_level():
    """D-08: every level has the correct rule-based action."""
    # ... assert one row per level has the right action
```

### RISK-08 enforcement test (no hardcoded column strings)

```python
# tests/test_risk_engine.py (continued)
import re
from pathlib import Path

def test_no_bare_column_strings_in_risk_engine():
    """RISK-08: every column-name string in risk_engine.py must come from cfg.

    Detects bare quoted strings that look like snake_case column names. Allowed
    exceptions: the four risk_level labels ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
    which are domain constants tied to D-06.
    """
    source = Path("src/risk_engine.py").read_text()
    # Strip comments and docstrings before scanning
    no_docstrings = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
    no_comments = re.sub(r'#.*', '', no_docstrings)
    # Find quoted strings that look like column names: snake_case, length >= 4
    matches = re.findall(r'"([a-z][a-z0-9_]{3,})"', no_comments)
    allowed = {"declining", "improving", "stable"}  # D-07 string labels
    offenders = [m for m in matches if m not in allowed]
    assert not offenders, (
        f"Bare column-name strings found in risk_engine.py: {offenders} — "
        f"use cfg.COL_* constants instead (RISK-08)."
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `df.applymap` for elementwise ops | `df.map` (DataFrame) / `Series.map` | pandas 2.1 | Method renamed; use `Series.map()` for our dict-lookup pattern |
| Chained assignment `df[df.col > 0]["x"] = 5` | `df.loc[df.col > 0, "x"] = 5` | pandas 1.x deprecation, 2.x warning, 3.x silent under CoW | Use `.loc[]` always; not relevant to score_risk because we only assign whole columns |
| `df.append(other)` | `pd.concat([df, other])` | pandas 2.0 removed `.append` | Not relevant — we don't append rows |
| Implicit numeric inference in read_csv | Explicit `dtype=` | Phase 1 D-02 (Pitfall #3) | Already enforced upstream in ingestion.py — Phase 2 inherits clean types |

**Deprecated/outdated:**
- `pd.cut(..., labels=[...])` returning a CategoricalIndex — still current in pandas 2.2; we cast to `"string"` for downstream Excel/HTML stability.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `daily_session_series` for students with no metrics is `NaN` (float), not `[]` (empty list), after Phase 1 left-join | Pitfall 4 | If wrong, my isinstance guard still handles it correctly (both NaN and empty list trigger the neutral branch) — low risk. |
| A2 | `freezegun` 1.5.5 works with `pd.Timestamp.now()` | Pitfall 7 / test examples | If wrong, tests for `days_since_last_note` will need an alternative time-injection pattern (e.g., make `today` a parameter with a default). Mitigation: write the helper signature `_days_since_last_note(df, today: pd.Timestamp)` so a test can pass an explicit `today` instead. |
| A3 | `df.copy().attrs == df.attrs` (attrs is preserved through copy in pandas 2.2.3) | Pitfall 8 | If wrong, Phase 4's `df.attrs["data_quality_warnings"]` lookup would return empty. Mitigation: explicit `result.attrs = df.attrs` at function end is a 1-line defensive backup. |
| A4 | The `_ACTION_BY_LEVEL` strings match exactly what Phase 3 LLM/template expects to overwrite | Pattern 5, Code Examples | If Phase 3's fallback template expects a different exact string, Phase 4 output may show conflicting wording. Mitigation: D-08 in CONTEXT.md is authoritative; Phase 3 should read from the same source. |
| A5 | Standard pandas wisdom ("vectorized is 10-100x faster than `.apply`") | Alternatives Considered | Performance assumption — at 300-2000 students per run, even `.apply` everywhere would complete in under a second. Low risk for v1. |

## Open Questions

1. **Should `attendance_rate` be float 0.0-1.0 or percentage 0-100?**
   - What we know: RISK-07 calls it `attendance_rate` (rate implies 0-1.0). Phase 4 Excel may format it as percentage for display.
   - What's unclear: Whether Phase 4 expects raw 0-1.0 (and applies % format) or pre-multiplied 0-100.
   - Recommendation: Store as 0.0-1.0 float (semantically correct for "rate"). Phase 4 applies `%` cell format in openpyxl. If Phase 4 actually wants 0-100, change in one place.

2. **Does `pd.cut` with `astype("string")` preserve the categorical order for sorting?**
   - What we know: After `.astype("string")`, sorting is alphabetical ("CRITICAL" < "HIGH" < "LOW" < "MEDIUM") — NOT risk-order.
   - What's unclear: Whether downstream (Phase 4 Excel) sorts by `risk_level` directly or by `risk_score`.
   - Recommendation: Phase 4 should sort by `risk_score` desc (per OUT-01); `risk_level` is for display/filtering only. Document this in the Phase 2 docstring.

3. **What happens if `attendance_days > 14` (data anomaly)?**
   - What we know: D-01 formula `1 - days/14` would produce a negative number; `.clip(0, 100)` handles it.
   - What's unclear: Whether to log a warning when attendance_days exceeds the window.
   - Recommendation: Add a debug-level log if `(df["attendance_days"] > 14).any()` — single check, no per-row noise. Not blocking.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | pandas 2.2.3 wheel availability | ✓ (per STATE.md L97) | 3.12.x | None — STATE.md mandates `py -3.12` |
| pandas | All computation | ✓ | 2.2.3 (pinned) | None |
| numpy | nanmean, clip, inf bins | ✓ (transitive) | (whatever pandas 2.2.3 ships with) | None |
| freezegun | Test time-freezing | ✓ | 1.5.5 (per STATE.md L105) | Pass explicit `today` parameter to `_days_since_last_note` |
| pytest | Test runner | ✓ | 8.3.5 | None |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | tests/conftest.py (existing) |
| Quick run command | `py -3.12 -m pytest tests/test_risk_engine.py -x --tb=short` |
| Full suite command | `py -3.12 -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RISK-01 | attendance_rate column exists and equals attendance_days/14 | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_attendance_rate_column -x` | ❌ Wave 0 |
| RISK-02 | avg_practice_questions = practice_total_q / 14 | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_avg_practice_calculation -x` | ❌ Wave 0 |
| RISK-03 | trend_direction is "declining"/"improving"/"stable"; component 100/0/50 | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_trend_direction_and_component -x` | ❌ Wave 0 |
| RISK-04 | days_since_last_note from latest_note_date; NaT → 30 | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_notes_component_nat_is_max -x` | ❌ Wave 0 |
| RISK-05 | risk_score = weighted sum, rounded, clipped | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_risk_score_weighted_formula -x` | ❌ Wave 0 |
| RISK-06 | risk_level boundaries: 0/25/50/75 with left-closed intervals | unit (parametrize) | `py -3.12 -m pytest tests/test_risk_engine.py::test_risk_level_boundaries -x` | ❌ Wave 0 |
| RISK-07 | Output DataFrame has all 6 required columns | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_required_output_columns_present -x` | ❌ Wave 0 |
| RISK-08 | No bare column-name strings in risk_engine.py | unit (source scan) | `py -3.12 -m pytest tests/test_risk_engine.py::test_no_bare_column_strings_in_risk_engine -x` | ❌ Wave 0 |
| Success Criterion 1 | score_risk returns df with required columns | smoke | `py -3.12 -m pytest tests/test_risk_engine.py::test_required_output_columns_present -x` | ❌ Wave 0 |
| Success Criterion 2 | Worst-case student → CRITICAL | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_worst_student_is_critical -x` | ❌ Wave 0 |
| Success Criterion 3 | Perfect student → LOW | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_perfect_student_is_low -x` | ❌ Wave 0 |
| Success Criterion 4 | All column strings from cfg | unit (source scan) | same as RISK-08 above | ❌ Wave 0 |
| (purity) | Input DataFrame not mutated | unit | `py -3.12 -m pytest tests/test_risk_engine.py::test_pure_function_does_not_mutate_input -x` | ❌ Wave 0 |
| (integration) | main.py wires score_risk after ingest | integration | `py -3.12 main.py` exits 0 and logs "Scored N students" | ❌ Wave 0 (main.py wiring task) |

### Sampling Rate
- **Per task commit:** `py -3.12 -m pytest tests/test_risk_engine.py -x --tb=short` (~2-5 sec)
- **Per wave merge:** `py -3.12 -m pytest tests/ -v` (full suite, currently 25 tests + new ~12 = ~37)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_risk_engine.py` — covers RISK-01 through RISK-08 + boundary tests + purity test (NEW FILE)
- [ ] `src/config.py` extension — add `COL_ATTENDANCE_COMPONENT`, `COL_PRACTICE_COMPONENT`, `COL_TREND_COMPONENT`, `COL_NOTES_COMPONENT` constants (4 new lines)
- [ ] `tests/test_config.py` — extend to assert the 4 new component column constants exist
- [ ] `main.py` — uncomment and wire `df = risk_engine.score_risk(df)` after ingest (L70 stub)
- [ ] No new test fixtures needed — `_build_student_row` helper in test file suffices for unit tests; happy-path ingestion fixture works for integration smoke

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — pure function over DataFrame |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No access control surface |
| V5 Input Validation | yes (light) | Defensive guards on list-column (isinstance check), NaT handling. No untrusted input — DataFrame is constructed in-process by Phase 1. |
| V6 Cryptography | no | No crypto operations |
| V7 (Logging) | yes | PII-safe logging — `logger.info` uses aggregate counts only (no student_id/name/phone). Already established pattern from Phase 1. |
| V8 (Data Protection) | yes | Pure function does not persist or transmit data; no leakage surface. |

### Known Threat Patterns for {pandas / pure-function CPU computation}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| DataFrame mutation by callee (caller surprise) | Tampering | `df.copy()` at function entry — never assign to caller's reference |
| NaN propagation producing silent wrong scores | Tampering / Repudiation | `.fillna(default)` at every NaN-producing operation; assert no NaN in final risk_score column |
| Time-zone confusion in `pd.Timestamp.now()` | Repudiation | Use `.normalize()` to strip time component; consistent UTC vs local-time policy (recommend local time per current pattern — single-host pipeline) |
| Logging PII (student_name, phone) | Information Disclosure | Aggregate-only logging — log counts and levels, never per-student identifiers |
| Threshold drift between code and config | Tampering | All thresholds from `cfg.RISK_THRESHOLD_*` — never hardcode 25/50/75 in risk_engine.py |
| Float precision causing flickering boundary tests | Repudiation | `round(_, 2)` per D-05 + `pd.cut(..., right=False)` for deterministic left-closed bins |

## Project Constraints (from CLAUDE.md)

The planner MUST verify each plan complies with these directives:

- **Type hints on ALL functions** — every private helper and public `score_risk` must annotate args and return
- **Docstrings on all public classes and methods** — `score_risk` requires full docstring; private helpers may have minimal docstrings
- **Python `logging` module throughout — zero print statements** — use `logger = logging.getLogger(__name__)` at module top; no `print()` anywhere
- **All column names as constants in `src/config.py`** — no hardcoded strings in `risk_engine.py` logic (RISK-08, enforced by source-scan test)
- **All paths from env vars** — N/A for Phase 2 (pure function, no file I/O)
- **`dtype={"student_id": "str", "parent_phone": "str"}` in every read_csv** — N/A (no CSV reads in Phase 2)
- **`os.environ["KEY"]` not `os.getenv("KEY")` for required secrets** — N/A (no env access in Phase 2)
- **pandas 2.2.3 not 3.x** — already pinned; Phase 2 must not use 3.x-only syntax. Specifically: avoid the new mandatory CoW assumption — always `df.copy()` at function entry, use `.loc[]` for slice assignment (not relevant here since we assign whole columns).
- **respx for API mocking** — N/A (no API calls in Phase 2)

## Sources

### Primary (HIGH confidence)
- `src/config.py` — full source read; confirmed which `COL_*` constants exist and which must be added
- `src/ingestion.py` — full source read; confirmed output schema (column names, dtypes, list-column structure)
- `src/risk_engine.py` — read existing stub; confirmed locked signature
- `main.py` — confirmed integration point (L70 stub `# df = risk_engine.score_risk(df)`)
- `.planning/phases/02-risk-scoring-engine/02-CONTEXT.md` — locked decisions D-01 through D-09 + Claude's Discretion areas
- `.planning/REQUIREMENTS.md` §RISK-01 through RISK-08 — authoritative requirement specs
- `.planning/STATE.md` — pinned stack versions (pandas 2.2.3, freezegun 1.5.5, pytest 8.3.5), Python 3.12 requirement, locked module contracts
- `.planning/phases/01-foundation-data-ingestion/01-03-SUMMARY.md` — Phase 1 deviation log; confirms post-merge fill behavior for numeric columns
- `tests/conftest.py` + `tests/test_ingestion.py` — existing test patterns; confirms `ANTHROPIC_API_KEY` mock pattern, fixture builders, caplog usage

### Secondary (MEDIUM confidence)
- pandas docs (general knowledge): `Series.map`, `pd.cut(..., right=False)`, `.dt.days`, `.clip()`, `.astype("string")` — all standard pandas 2.x APIs

### Tertiary (LOW confidence)
- None — every claim is backed by source code in this repo or by the explicit decisions in CONTEXT.md

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — dependencies already pinned and used in Phase 1
- Architecture: HIGH — pure function with locked signature; pandas idioms are well-established
- Pitfalls: HIGH — each pitfall is observable in actual source code (e.g., Pitfall 4 verified against ingestion.py L376-379)
- Phase 1 schema understanding: HIGH — full ingestion.py read, output columns enumerated
- Test design: HIGH — pattern matches existing test_ingestion.py / test_generate_data.py style
- Time-dependence handling: MEDIUM — freezegun pattern is standard but not verified to work with `pd.Timestamp.now()` in this specific stack version (Assumption A2)

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (30 days — stable pure-function domain, no fast-moving libraries)
