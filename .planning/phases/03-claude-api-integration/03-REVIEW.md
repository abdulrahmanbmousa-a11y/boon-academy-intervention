---
phase: "03"
status: has_critical
reviewed_files:
  - requirements.txt
  - src/config.py
  - src/llm_templates.yaml
  - src/llm_engine.py
  - main.py
  - tests/test_llm_engine.py
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-23T11:29:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** has_critical

---

## Summary

Phase 3 delivers the Claude API integration layer: prerequisites (config constants, YAML
templates), the full `enrich_with_llm()` implementation in `llm_engine.py`, main.py wiring,
and a 12-test suite. The structural decisions — campus batching, three-layer fallback,
`http_client` injection for mocking, PII exclusion from prompts and logs — are sound.

Two critical bugs are present. First, `test_fallback_to_template` relies on
`httpx.TimeoutException` propagating through the Anthropic SDK as `anthropic.APITimeoutError`,
but with `max_retries=0` and a mock transport the SDK wraps network exceptions differently
than production, making this test unable to reach the inner `except anthropic.APITimeoutError`
branch it claims to exercise; the test passes by coincidence (both layers time out and Layer 3
fires) but does not verify the error-reason classification path it documents. Second, the
`_apply_templates()` function uses `str.format_map(row.to_dict())` against YAML templates that
contain format specifiers (e.g. `{attendance_rate:.0%}`), but `row.to_dict()` values for
numeric columns are raw Python/numpy floats — the format spec works for native Python floats but
will raise `ValueError` for `numpy.float64` values when the format string contains a
presentation type (e.g. `:.0%`) if the value comes from a pandas column that retains the numpy
dtype. This is a runtime crash path that is untested. Several warnings and info items round out
the review.

---

## Critical Issues

### CR-01: Template `format_map` crashes on `numpy.float64` with format specifiers

**File:** `src/llm_engine.py:147-148` (and `src/llm_templates.yaml:4-5, 18-19`)

**Issue:** `_apply_templates()` calls `tmpl[cfg.COL_FACILITATOR_SUMMARY].format_map(row_dict)`
where `row_dict = row.to_dict()`. Pandas stores numeric columns as `numpy.float64` by default.
The YAML templates contain format specifiers `{attendance_rate:.0%}`,
`{avg_practice_questions:.1f}`, and `{days_since_last_note:.0f}`. Python's `str.format_map`
applies `.__format__()` on each value object. `numpy.float64.__format__` does NOT support the
`%` presentation type — calling `"{:.0%}".format(numpy.float64(0.3))` raises:

```
ValueError: Unknown format code '%' for object of type 'float'
```

This is a crash in the template fallback path — the exact path that must never fail (Layer 3
guarantee). Any student whose `attendance_rate` column holds a `numpy.float64` (which is every
student coming from a real pipeline run) will cause `_apply_templates()` to raise, then
`_write_results_back()` is never called, and those students silently receive `None` in all four
output columns rather than template content. Because `_apply_templates()` is called from within
the `except` handlers in `enrich_with_llm()`, the raised `ValueError` propagates outward and is
not caught anywhere — this causes `enrich_with_llm()` itself to raise, breaking the
"never raises" guarantee stated in the docstring and violated LLM-05.

**Fix:** Convert values to native Python scalars before calling `format_map`. Replace the
two lines in `_apply_templates()`:

```python
# Before (line 145-148)
row_dict = row.to_dict()
tmpl = _TEMPLATES[risk_level]
facilitator_summary = tmpl[cfg.COL_FACILITATOR_SUMMARY].format_map(row_dict)
whatsapp_message = tmpl[cfg.COL_WHATSAPP_MESSAGE].format_map(row_dict)

# After — convert numpy scalars to native Python types
row_dict = {
    k: (float(v) if hasattr(v, "item") else v)
    for k, v in row.to_dict().items()
}
tmpl = _TEMPLATES[risk_level]
facilitator_summary = tmpl[cfg.COL_FACILITATOR_SUMMARY].format_map(row_dict)
whatsapp_message = tmpl[cfg.COL_WHATSAPP_MESSAGE].format_map(row_dict)
```

Alternatively use `row_dict = {k: v.item() if hasattr(v, 'item') else v for k, v in row.to_dict().items()}` which calls numpy's `.item()` to extract the native scalar.

Add a test that constructs a DataFrame from `pd.read_csv`-like numeric columns (i.e., with
`numpy.float64` dtypes) and asserts `_apply_templates()` does not raise.

---

### CR-02: `test_fallback_to_template` does not actually verify error-reason classification; Layer 2 exception type mismatch makes the test unreliable

**File:** `tests/test_llm_engine.py:257-285`

**Issue:** The test mocks `httpx.TimeoutException` at the transport layer and expects the
engine to classify the error as `"timeout"` via `_classify_error()`. However, the classification
check `isinstance(exc, anthropic.APITimeoutError)` in `_classify_error` (line 119 of
`llm_engine.py`) is only reached when the caught exception in the outer `except` block at
line 408 is `anthropic.APITimeoutError`. With `max_retries=0`, the Anthropic SDK may wrap
`httpx.TimeoutException` as `anthropic.APITimeoutError` in some SDK versions, but the test
passes even if classification never fires because:

1. The mock raises `httpx.TimeoutException` on every call, including the Layer 2 re-prompt.
2. The Layer 2 `except Exception` at line 443 catches the re-prompt failure and falls through to
   Layer 3 regardless of the error type.
3. The test only checks `generated_by == 'template'` and `llm_error_reason is not None` — it
   does NOT assert that `llm_error_reason == 'timeout'`.

This means the test would pass even if `_classify_error()` were deleted entirely and the
error_reason were always `"max_retries_exceeded"`. The `error_reason` variable set at line 415
is from `_classify_error(exc)` and is used in the Layer 3 template call at line 449, but the
test never asserts its value. The test therefore provides no coverage of the classification path
it documents (LLM-05 error-reason assignment).

**Fix:** Add an explicit assertion on the error reason value, and confirm the SDK exception type
wrapping works as expected with `max_retries=0`:

```python
# Add to test_fallback_to_template after existing asserts:
assert row[cfg.COL_LLM_ERROR_REASON] in {"timeout", "max_retries_exceeded"}, (
    "LLM-05: error reason must be a classified value, not None or empty"
)
# To pin the exact timeout classification:
assert row[cfg.COL_LLM_ERROR_REASON] == "timeout", (
    "LLM-05: httpx.TimeoutException must classify as 'timeout'"
)
```

If the SDK does not wrap `httpx.TimeoutException` as `anthropic.APITimeoutError` at
`max_retries=0`, then `_classify_error` returns `"max_retries_exceeded"` (the default), and the
classification logic for `timeout` and `rate_limit` is never tested by any test in the suite.
In that case a separate test should inject an `anthropic.APITimeoutError` directly using
`monkeypatch` to exercise `_classify_error()` in isolation.

---

## Warnings

### WR-01: `config.py` imported at module level causes `KeyError` at import in any test that does not set `ANTHROPIC_API_KEY`

**File:** `src/config.py:22`

**Issue:** `ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]` executes at module
import time. Any test file that does `from src import config as cfg` (or transitively imports
any `src` module) will raise `KeyError: 'ANTHROPIC_API_KEY'` unless the env var is set before
the test process starts. The tests currently work because `conftest.py` uses
`os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")` (per 03-03-SUMMARY.md). However, this
`conftest.py` setdefault pattern is fragile:

- If `conftest.py` is not on the pytest path (e.g., a test run from a subdirectory), the guard
  is skipped and all tests fail with a confusing `KeyError` that looks like a missing env var
  rather than a test infrastructure problem.
- The `config.py` module is also imported by `llm_engine.py` at module level, meaning any
  import of `llm_engine` outside pytest (e.g., `python -c "from src import llm_engine"`) fails
  if `ANTHROPIC_API_KEY` is not set — even though the caller may only need `_TEMPLATES` or
  `INTERVENTION_TOOL` and never calls `enrich_with_llm`.

**Fix:** Either (a) confirm `conftest.py` is in the repo root `tests/` directory and document
the requirement explicitly, or (b) defer the `KeyError` to the first call of
`enrich_with_llm()` by reading the key lazily rather than at module import:

```python
# config.py — lazy pattern for secrets used only at runtime
def get_anthropic_api_key() -> str:
    """Return API key, raising KeyError at call time (not import time)."""
    return os.environ["ANTHROPIC_API_KEY"]

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
# Empty string is falsy; callers that need the key call get_anthropic_api_key()
```

Note: CLAUDE.md explicitly states to use `os.environ["KEY"]` for required secrets (fail at
startup). If the startup-fail behavior is intentional (and the conftest guard is confirmed
present), this is acceptable but the fragility should be acknowledged.

---

### WR-02: Layer 2 re-prompt is identical to Layer 1 — provides no additional resilience for permanent errors

**File:** `src/llm_engine.py:420-441`

**Issue:** Layer 2 sends the exact same prompt, model, `max_tokens`, `temperature`, `tools`,
and `tool_choice` to the same endpoint. For the error cases it's supposed to handle
(`RateLimitError`, `APIStatusError`), retrying with the same payload immediately will almost
always fail again with the same error:

- `RateLimitError`: Rate limit is still active seconds later; a re-prompt with no back-off
  simply burns another API call.
- `APIStatusError` (e.g., 400 Bad Request): A payload that triggers a 400 will always trigger
  a 400; an identical re-prompt never recovers.
- `APIConnectionError`: May recover on transient network blip, but max_retries=3 at Layer 1
  already handles this.

The docstring states "simplified re-prompt (same structure)" which acknowledges this, but the
practical effect is that Layer 2 wastes one API call and one timeout-worth of latency before
falling to Layer 3. For a permanent error (invalid model name, quota exhausted, bad auth), Layer
2 doubles the student wait time with no benefit. `RateLimitError` in particular should either
apply a back-off delay or skip Layer 2 entirely and go directly to Layer 3.

**Fix:** At minimum, skip the re-prompt for `RateLimitError` and `APIStatusError` where a
second identical call cannot succeed:

```python
# In the Layer 1 except block, before attempting Layer 2:
if isinstance(exc, (anthropic.RateLimitError, anthropic.APIStatusError)):
    logger.warning(
        f"Campus {campus_id}: permanent API error ({error_reason}) — "
        f"skipping re-prompt, applying template fallback directly"
    )
    template_results = _apply_templates(chunk, error_reason)
    _write_results_back(df, template_results, generated_by="template")
    fallbacks += len(chunk)
    continue  # skip to next chunk
# Otherwise attempt Layer 2 re-prompt for transient errors
```

---

### WR-03: `test_max_retries_config` — `_FakeClient` constructor patches `anthropic.Anthropic` globally but does not restore it; interaction risk with other tests in the same process

**File:** `tests/test_llm_engine.py:219-254`

**Issue:** The test uses `monkeypatch.setattr(_anthropic_module, "Anthropic", _FakeClient)`.
`_FakeClient` is a local class with a nested `messages` class attribute that raises
`RuntimeError("should not be called in this test")` on any `.create()` call. If test ordering
causes `test_max_retries_config` to run before a test that uses a real `enrich_with_llm` path
with `http_client=None` and the monkeypatch is somehow not torn down (e.g., a test failure
before teardown), subsequent tests would receive `RuntimeError` from the fake. While
`monkeypatch` should restore the original in pytest's teardown, the `messages` attribute is a
class (not an instance), and `_FakeClient.messages.create` is a `@staticmethod` — any
reference held before teardown would still point to the fake. This is a low-probability issue
but the test comment "should not be called in this test" is misleading when `_FakeClient` is
used with a MEDIUM-only df where no `.create()` is ever invoked; the `RuntimeError` guard is
therefore dead code in the test.

Additionally: `_FakeClient.__init__` accepts only `**kwargs` but the production branch passes
`api_key`, `max_retries`, and `timeout` as keyword arguments. The test correctly captures them
in `captured_kwargs`. However, the timeout argument value (`float(cfg.TIMEOUT_SECONDS)`) is
never asserted — only `max_retries` is checked. This means a regression that removes `timeout`
from the production client would not be caught by this test.

**Fix:** Add an assertion for `timeout`:

```python
assert captured_kwargs.get("timeout") == float(cfg.TIMEOUT_SECONDS), (
    f"LLM-04: production Anthropic client must pass timeout={cfg.TIMEOUT_SECONDS}, "
    f"got timeout={captured_kwargs.get('timeout')}"
)
```

---

### WR-04: `_apply_templates` does not guard against missing YAML key for a risk level

**File:** `src/llm_engine.py:146`

**Issue:** `tmpl = _TEMPLATES[risk_level]` performs a raw dictionary lookup with no
`KeyError` handling. `_TEMPLATES` is loaded from `llm_templates.yaml` which defines only
`CRITICAL` and `HIGH`. The function docstring states the `chunk` contains only CRITICAL or HIGH
rows, and the caller (`enrich_with_llm`) only passes at-risk students filtered by
`.isin(["CRITICAL", "HIGH"])`. However, if the filter is ever relaxed (e.g., a future change
adds MEDIUM to the intervention scope) or if the YAML file is edited to remove a key, the
`KeyError` from line 146 propagates out of `_apply_templates` and is not caught in the
calling `except` blocks in `enrich_with_llm`, because `_apply_templates` is called from within
the `except` handler chain. A `KeyError` from `_apply_templates` would surface as an uncaught
exception, breaking the "never raises" guarantee.

**Fix:** Add a guard with a safe fallback:

```python
tmpl = _TEMPLATES.get(risk_level)
if tmpl is None:
    logger.error(
        f"No template found for risk_level={risk_level!r} — "
        f"using CRITICAL template as fallback"
    )
    tmpl = _TEMPLATES.get("CRITICAL", {})
```

---

### WR-05: `requirements.txt` is missing `httpx` as an explicit dependency

**File:** `requirements.txt`

**Issue:** `httpx` is used directly in `src/llm_engine.py` (type annotation `Optional[httpx.Client]`)
and throughout `tests/test_llm_engine.py` (`import httpx`, `httpx.Client(...)`,
`httpx.MockTransport(...)`, `httpx.Response(...)`, `httpx.TimeoutException`). It is not listed
in `requirements.txt`. It is currently available as a transitive dependency of `anthropic`
(the Anthropic SDK depends on `httpx`), but transitive dependencies are not guaranteed to be
stable across SDK minor versions. If Anthropic SDK ever changes its transport layer or pins
`httpx` to a different version, the implicit dependency could break.

**Fix:** Add `httpx` at the version currently installed (check with `pip show httpx`) to
`requirements.txt`:

```
httpx==0.27.2   # or whatever version is installed — check with: pip show httpx
```

---

## Info

### IN-01: YAML template `facilitator_summary` contains risk score (`{risk_score}/100`) — contradicts LLM-03 spec for WhatsApp message but not for facilitator summary; document the intentional distinction

**File:** `src/llm_templates.yaml:4, 18`

**Issue:** The YAML `facilitator_summary` template includes `Risk score: {risk_score}/100`.
The `whatsapp_message` template correctly omits risk scores (per LLM-03: "Does not mention risk
scores"). This is correct behavior — risk scores are appropriate in the internal facilitator
summary but not in the parent-facing WhatsApp message. However, the prohibition language in
the `INTERVENTION_TOOL` schema description at line 91 of `llm_engine.py`
(`"Does not mention risk scores"`) applies only to `whatsapp_message`. There is no
corresponding note for `facilitator_summary`. Future YAML edits could accidentally add a risk
score to `whatsapp_message` without any automated guard.

**Fix:** Add a test assertion that verifies the WhatsApp template output does not contain
numeric risk-score patterns (e.g., `re.search(r'\d+/100', whatsapp_message)` is None). This
is low priority but would catch accidental YAML edits.

---

### IN-02: `test_chunk_size_limit` imports `json` and `re` inside a nested function — minor style inconsistency

**File:** `tests/test_llm_engine.py:393-399`

**Issue:** `import json as _json` and `import re as _re` are placed inside the
`_make_response_for_call` inner function. `re` is already imported at the top of the test
module (line 8). Using `re` inside the nested function is fine, but importing it again as `_re`
creates a shadow alias. The `json` import inside a function is also a minor style inconsistency
with the module-level import convention used elsewhere in the file.

**Fix:** Move `import json` to the module-level imports at the top of the test file and
use `re` directly (already imported) in `_make_response_for_call`:

```python
# At top of test file, add:
import json

# Inside _make_response_for_call:
body = json.loads(request.content)
student_ids_in_chunk = re.findall(r"S\d{4}", content_text)
```

---

### IN-03: `main.py` Phase 4 `write_outputs` call is commented out — pipeline produces no output files in current state

**File:** `main.py:87`

**Issue:** The line `# write_outputs(df, cfg.OUTPUT_DIR, run_log=run_log)` is intentionally
stubbed pending Phase 4. This means running `python main.py` today produces no output files
despite processing students through ingestion, scoring, and LLM enrichment. A developer running
the pipeline for the first time would see only log output with no artifacts, which may appear
as a silent failure.

**Fix:** Add a `logger.info` note at that point in the pipeline:

```python
# Phase 4: Output generation — stub pending Phase 4 implementation
logger.info("Phase 4 (output generation) not yet implemented — outputs will be written in Phase 4")
```

---

### IN-04: `test_no_bare_column_strings_in_llm_engine` — regex strips only `"""..."""` docstrings; `'''...'''` docstrings would survive

**File:** `tests/test_llm_engine.py:525`

**Issue:** `re.sub(r'""".*?"""', "", source, flags=re.DOTALL)` strips triple-double-quoted
docstrings only. If any future function in `llm_engine.py` uses `'''...'''` (triple-single-
quote) docstrings, those would not be stripped and any bare column-name strings inside them
would trigger false positives. Currently `llm_engine.py` uses only `"""..."""`, so this is
not a current defect, but it is a fragility in the test's logic.

**Fix:** Add a second strip for triple-single-quoted strings:

```python
no_docstrings = re.sub(r"'''.*?'''", "", no_docstrings, flags=re.DOTALL)
```

---

### IN-05: `_build_prompt` formats `student_data` list via `f"{student_data}"` — sends raw Python repr to Claude API

**File:** `src/llm_engine.py:174`

**Issue:** The prompt is built as:
```python
f"Student data:\n{student_data}"
```
`student_data` is a `list[dict]`. Python's default `__repr__` for a list of dicts is not
JSON — it uses single quotes, `True`/`False` for booleans, and Python-style number
representations. This is human-readable but not machine-parseable JSON. If Claude attempts
to echo back student IDs from a repr-formatted list, there could be subtle parsing differences.
This is a quality issue rather than a crash, but using `json.dumps(student_data, indent=2)`
would produce cleaner, unambiguous output.

**Fix:**

```python
import json
...
f"Student data:\n{json.dumps(student_data, indent=2)}"
```

---

_Reviewed: 2026-05-23T11:29:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
