---
phase: 02-risk-scoring-engine
reviewed: 2026-05-23T09:58:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/config.py
  - src/risk_engine.py
  - tests/test_config.py
  - tests/test_risk_engine.py
  - main.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-23T09:58:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Five files reviewed: the config module, the risk scoring engine, both test suites, and the orchestrator. The risk scoring logic itself is structurally sound — vectorized, pure, and well-guarded against NaN/short-series edge cases. The critical issue is a freezegun/pandas incompatibility that makes `@freeze_time` tests non-deterministic: `pd.Timestamp.now()` is not reliably patched by freezegun, meaning the wall-clock leaks into supposedly deterministic tests. Four warnings cover a stale module-level bins list, a missing entry-point guard, dead code in a test, and a semantic ambiguity in the trend label. Three info items cover bare column strings lacking constants, a misleading comment, and a missing `importlib` import guard.

---

## Critical Issues

### CR-01: `pd.Timestamp.now()` Is Not Frozen by `@freeze_time` — Tests Are Non-Deterministic

**File:** `src/risk_engine.py:152`
**Issue:** `score_risk` computes `today` via `pd.Timestamp.now().normalize()`. Freezegun patches `datetime.datetime.now()` at the CPython level, but `pd.Timestamp.now()` calls into pandas' C extension directly and bypasses that patch in pandas 2.x. As a result, every `@freeze_time`-decorated test that exercises `_days_since_last_note` (RISK-04, `test_notes_component_today_is_zero`, `test_worst_student_is_critical`, `test_perfect_student_is_low`, `test_recommended_action_matches_level`) uses live wall-clock time instead of the frozen date. On 2026-05-23 `test_notes_component_today_is_zero` happens to pass because `latest_note_date` is also hardcoded to `2026-05-23` — but the day after that date the test will silently return `days_since=1` instead of `0`, breaking the assertion. This is a latent time-bomb in CI.

**Fix:** Replace `pd.Timestamp.now()` with `datetime.now()` from the stdlib (which freezegun does patch), or add `today` as an optional parameter to `score_risk` so tests can inject it directly:

```python
# Option A — use stdlib datetime (freezegun patches this)
from datetime import datetime, timezone
today = pd.Timestamp(datetime.now()).normalize()

# Option B — injectable parameter (preferred for testability)
def score_risk(df: pd.DataFrame, today: pd.Timestamp | None = None) -> pd.DataFrame:
    df = df.copy()
    if today is None:
        from datetime import datetime
        today = pd.Timestamp(datetime.now()).normalize()
    ...
```

Tests then become:
```python
@freeze_time("2026-05-23")
def test_notes_component_today_is_zero() -> None:
    # freeze_time now works because datetime.now() is patched
    ...
```

---

## Warnings

### WR-01: Module-Level `_RISK_BINS` Captures Config Values at Import Time — Override Tests Will Silently Use Stale Bins

**File:** `src/risk_engine.py:34`
**Issue:** `_RISK_BINS` is built once at module import:
```python
_RISK_BINS: list = [-np.inf, cfg.RISK_THRESHOLD_MEDIUM, cfg.RISK_THRESHOLD_HIGH, cfg.RISK_THRESHOLD_CRITICAL, np.inf]
```
`RISK_THRESHOLD_CRITICAL` and `RISK_THRESHOLD_HIGH` are env-overridable in `config.py`. Any test (or future code path) that changes those thresholds via `monkeypatch.setenv` and re-imports `config` will have updated threshold values in `cfg.*` — but `_RISK_BINS` will still hold the values from the original import. The `pd.cut` in `score_risk` will silently classify students against the wrong bins. No test currently exercises this, but the env-override feature advertised in `config.py` lines 41-42 is broken for risk_engine's binning.

**Fix:** Move bin construction inside `score_risk` so it is always consistent with current config values:
```python
def score_risk(df: pd.DataFrame, ...) -> pd.DataFrame:
    df = df.copy()
    risk_bins = [-np.inf, cfg.RISK_THRESHOLD_MEDIUM, cfg.RISK_THRESHOLD_HIGH, cfg.RISK_THRESHOLD_CRITICAL, np.inf]
    ...
    df[cfg.COL_RISK_LEVEL] = pd.cut(
        df[cfg.COL_RISK_SCORE],
        bins=risk_bins,
        labels=_RISK_LABELS,
        right=False,
    ).astype(pd.StringDtype())
```

---

### WR-02: `main.py` Has No `__main__` Guard Protecting Pipeline Side-Effects at Import Time

**File:** `main.py:39`
**Issue:** `main()` calls `setup_logging()` which invokes `logging.basicConfig(...)` as a side effect. Any module that imports from `main.py` (e.g., a future integration test doing `from main import main`) will trigger `logging.basicConfig` reconfiguration immediately at import, before any test fixtures set up their own log handlers. Additionally, `from src import config as cfg` at line 11 triggers the `ANTHROPIC_API_KEY` fail-loud check at import time — this is expected — but `setup_logging()` being a bare callable rather than guarded means future importers of `main` get implicit side effects. The `if __name__ == "__main__"` guard at line 87 correctly gates `sys.exit(main())`, but `setup_logging` is not guarded when called from inside `main()`. This is low-severity now but will cause test pollution as the test suite grows.

**Fix:** This is already structured correctly for the current phase (nothing imports from `main`). The warning is forward-looking: ensure that `tests/` never import from `main` directly, or extract `setup_logging` into `src/` so it can be imported without running `main()`.

---

### WR-03: `test_missing_api_key_raises` Contains a Dead Statement

**File:** `tests/test_config.py:29`
**Issue:** Line 29 `importlib.reload(src.config)` is unreachable. The `clean_config_module` fixture removes `src.config` from `sys.modules`, so line 28 `import src.config` always performs a fresh module load. If `ANTHROPIC_API_KEY` is absent (as arranged by `monkeypatch.delenv`), this fresh import raises `KeyError` immediately, and line 29 never executes. If the import somehow succeeded (it cannot with no key), the reload would be a second attempt. The dead statement creates a false impression that the test is verifying reload behavior.

**Fix:**
```python
def test_missing_api_key_raises(self, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(KeyError):
        import src.config  # noqa: F401
    # importlib.reload line removed — unreachable; fresh import via fixture is sufficient
```

---

### WR-04: `_trend_component_and_direction` Returns Ambiguous "stable" Label for Two Structurally Different Cases

**File:** `src/risk_engine.py:71-80`
**Issue:** The `_compute` inner function returns `("stable", 50.0)` for series with fewer than 3 values (insufficient data fallback) and `("stable", 0.0)` for series where `last3 == first11` (genuine data stability). Both cases produce `trend_direction = "stable"` in the output column, but with opposite risk implications: 50 (moderate risk/unknown) vs 0 (no risk). A downstream consumer reading `trend_direction == "stable"` cannot distinguish "we don't know" from "the student is genuinely stable." This breaks the audit-trail promise of the component columns (D-09).

```python
# Current — ambiguous:
if not isinstance(series, list) or len(series) < 3:
    return (_TREND_NEUTRAL, "stable")   # component=50, direction="stable"
...
else:
    return (0.0, "stable")              # component=0,  direction="stable"
```

**Fix:** Use a distinct direction label for the insufficient-data case:
```python
if not isinstance(series, list) or len(series) < 3:
    return (_TREND_NEUTRAL, "insufficient_data")  # or "unknown"
```
Update `_ACTION_BY_LEVEL` is unaffected (it maps risk_level, not trend_direction). Update the test at `test_trend_short_series_is_neutral_50` and `test_trend_nan_series_is_neutral_50` to assert `"insufficient_data"` instead of `"stable"`.

---

## Info

### IN-01: Four Ingestion-Internal Column Names Are Bare Strings with No `cfg.COL_*` Constants

**File:** `src/risk_engine.py:53, 58, 82, 95`
**Issue:** `risk_engine.py` references `"attendance_days"`, `"practice_total_q"`, `"daily_session_series"`, and `"latest_note_date"` as bare string literals. These are added to the allowed set in the RISK-08 test scan (lines 491-498) specifically because no `cfg.COL_*` constants exist for them. This is a tracked technical debt item, but it creates a class of typo that the test suite explicitly cannot catch: a misspelling of `"attendance_days"` in `risk_engine.py` would produce a silent `KeyError` at runtime rather than a `NameError` at import time.

**Fix:** Add constants to `src/config.py` for these four ingestion-output columns and update `risk_engine.py` to use them. Remove from the `allowed` set in `test_no_bare_column_strings_in_risk_engine`:
```python
# In config.py — under "Ingestion output columns" heading
COL_ATTENDANCE_DAYS: str = "attendance_days"
COL_PRACTICE_TOTAL_Q: str = "practice_total_q"
COL_DAILY_SESSION_SERIES: str = "daily_session_series"
COL_LATEST_NOTE_DATE: str = "latest_note_date"
```

---

### IN-02: Misleading Comment in `test_recommended_action_matches_level` MEDIUM Case

**File:** `tests/test_risk_engine.py:385`
**Issue:** The comment on line 385 states `"trend=50: neutral"` for a `session_series=[30.0]*14` input, but a 14-element constant series produces `last3=30.0`, `first11=30.0`, equal — so `_compute` returns `(0.0, "stable")`, not the neutral fallback of 50.0. The actual computed score is `50×0.35 + 0×0.30 + 0×0.20 + 50×0.15 = 25.0` which lands exactly on the MEDIUM boundary (correct), but the comment's arithmetic `"trend=50"` is wrong. The test passes because score=25.0 is in [25, 50) but for the wrong stated reason.

**Fix:** Correct the comment:
```python
elif level == "MEDIUM":
    # attendance=50: 7 days → attendance_component=50
    # practice=0: 210q → practice_component=0
    # trend=0: stable (14 equal values → last3==first11 → component=0)
    # notes=50: 15 days ago → notes_component=50
    # score = 50*0.35 + 0*0.30 + 0*0.20 + 50*0.15 = 17.5 + 0 + 0 + 7.5 = 25.0 → MEDIUM [25,50)
```

---

### IN-03: `importlib` Imported But Only Used in a Dead Statement

**File:** `tests/test_config.py:6`
**Issue:** `import importlib` at line 6 is present solely to support `importlib.reload(src.config)` at line 29, which is the dead statement identified in WR-03. Once that dead statement is removed, `importlib` becomes an unused import, which linters (flake8/ruff F401) will flag.

**Fix:** Remove `import importlib` from `tests/test_config.py` when the dead reload statement is removed.

---

_Reviewed: 2026-05-23T09:58:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
