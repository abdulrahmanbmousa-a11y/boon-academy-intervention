# Phase 3: Claude API Integration - Research

**Researched:** 2026-05-23
**Domain:** Anthropic Python SDK (anthropic==0.103.1), tool_use structured output, respx mocking, PyYAML, campus-batched LLM enrichment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (Template storage):** Rule-based fallback templates stored in `src/llm_templates.yaml`, loaded at runtime by `llm_engine.py` using `Path(__file__).parent / "llm_templates.yaml"`. No env-var path needed.
- **D-02 (Template differentiation):** 2 variants by `risk_level` only — CRITICAL and HIGH. Each variant has `facilitator_summary` and `whatsapp_message` sub-keys.
- **D-03 (Template interpolation):** Full Python `.format_map()` using all scored columns from `score_risk()` output. `parent_phone` excluded.
- **D-04 (Batch overflow):** Multiple sequential API calls in chunks of `MAX_STUDENTS_PER_LLM_CALL` (default 10). All CRITICAL/HIGH students receive output — no truncation.
- **D-05 (Chunk ordering):** Within campus: CRITICAL first sorted by `risk_score` descending, then HIGH sorted by `risk_score` descending.
- **D-06 (New columns):** 4 new columns: `facilitator_summary`, `whatsapp_message`, `generated_by`, `llm_error_reason`.
- **D-07 (MEDIUM/LOW values):** All 4 columns set to `None`/`NaN` for MEDIUM and LOW students.
- **D-08 (generated_by values):** Exactly `"llm"` or `"template"` for CRITICAL/HIGH; `None`/`NaN` for MEDIUM/LOW.
- **D-09 (Config constants):** 9 new constants added to `src/config.py`: `ANTHROPIC_MODEL`, `LLM_ENABLED`, `MAX_TOKENS`, `TEMPERATURE`, `TIMEOUT_SECONDS`, `COL_FACILITATOR_SUMMARY`, `COL_WHATSAPP_MESSAGE`, `COL_GENERATED_BY`, `COL_LLM_ERROR_REASON`.

### Claude's Discretion

- Prompt content, tone, and structure left to implementation.
- Hard constraints: facilitator summary = exactly 2 sentences; WhatsApp message = <100 words.
- Student fields in prompt: `risk_level`, `risk_score`, `attendance_rate`, `avg_practice_questions`, `trend_direction`, `days_since_last_note`, `recommended_action`. Do NOT include `parent_phone` or `student_name`.
- Use `student_id` as per-student identifier within batch prompt.
- Run-log return pattern (tuple vs df.attrs vs mutable dict) is planner's decision.

### Deferred Ideas (OUT OF SCOPE)

- Arabic/Gulf dialect WhatsApp messages (FUTV2)
- Async/concurrent LLM calls for multiple campuses (FUTV2-05)
- Per-student API calls instead of campus batching
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | System calls Claude `claude-sonnet-4-5` API for CRITICAL and HIGH risk students only | SDK client.messages.create() with model=cfg.ANTHROPIC_MODEL; filter df by risk_level |
| LLM-02 | API calls are batched by campus — one call per campus's at-risk students (not per student) | groupby(campus_id), chunk loop per D-04; one client.messages.create() per chunk |
| LLM-03 | Each API call uses tool-use / structured output to return 2-sentence facilitator summary + WhatsApp message (<100 words) | tool_choice={"type":"tool","name":"..."} forces structured JSON; parse response.content ToolUseBlock |
| LLM-04 | System retries failed API calls with exponential backoff (max 3 retries via SDK max_retries=3) | Anthropic(max_retries=3) — SDK handles retries internally before raising |
| LLM-05 | System falls back to rule-based template on API failure; labeled generated_by="template" | Three-layer: SDK retry (automatic) → re-prompt attempt → template from llm_templates.yaml |
| LLM-06 | System logs token usage (input + output tokens) per API call to run_log | response.usage.input_tokens / response.usage.output_tokens after each successful call |
| LLM-07 | ANTHROPIC_API_KEY read from environment only — never logged, never hardcoded | cfg.ANTHROPIC_API_KEY uses os.environ["ANTHROPIC_API_KEY"] (already implemented, fail-loud) |
| LLM-08 | Student names and parent phones masked in all log output | Mask student_name as [STUDENT], parent_phone as [PHONE] in all logger.* calls |
| LLM-09 | MAX_STUDENTS_PER_LLM_CALL configurable via env var (default: 10) | cfg.MAX_STUDENTS_PER_LLM_CALL already defined in config.py |
</phase_requirements>

---

## Summary

Phase 3 fills in `src/llm_engine.py` — the single function `enrich_with_llm(df, api_key) -> DataFrame`. The function groups CRITICAL/HIGH students by campus, sorts them (CRITICAL first, then HIGH, both descending by risk_score), chunks them into batches of at most `MAX_STUDENTS_PER_LLM_CALL`, and calls the Anthropic API once per chunk using tool-use structured output to return per-student `facilitator_summary` and `whatsapp_message` fields. A three-layer fallback ensures the pipeline never halts: the SDK's built-in `max_retries=3` exponential backoff handles transient HTTP errors automatically; if retries are exhausted (or the response is malformed), a single re-prompt attempt is made with a simplified prompt; if that also fails, rule-based templates loaded from `src/llm_templates.yaml` are applied with `generated_by="template"`. Token usage per call is accumulated into the `run_log` dict in `main.py`.

The tool-use pattern is the correct approach for this phase: forcing `tool_choice={"type": "tool", "name": "generate_interventions"}` guarantees Claude returns a structured JSON array with one object per student instead of free-text or markdown-wrapped JSON. The response is parsed from `response.content` by finding the `ToolUseBlock` and accessing its `.input` dict. Testing uses `respx` to mock the underlying httpx transport layer that the Anthropic SDK uses, with a custom `httpx.Client` injected via `http_client=` on the `Anthropic()` constructor.

The `LLM_ENABLED=false` path bypasses all API calls, applies templates for all CRITICAL/HIGH students, and sets `llm_error_reason="llm_disabled"` — this is the fast path for testing output generation without a real API key.

**Primary recommendation:** Implement enrich_with_llm() as a single-pass campus loop with the tool-use batch pattern; inject `httpx.Client(transport=respx_mock_transport)` for testing rather than patching at the module level.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM API calls | API/Backend (`llm_engine.py`) | — | Pure in-memory transformation; no I/O side effects except HTTP |
| Template loading | API/Backend (`llm_engine.py` module import) | — | Package resource co-located with engine; loaded once at module import |
| Token accumulation | API/Backend (`llm_engine.py` return value) | Orchestrator (`main.py`) | enrich_with_llm() returns counts; main.py writes to run_log |
| PII masking | API/Backend (log statements only) | — | Actual data in DataFrame is not masked; only logger.* output |
| Config constants | Config layer (`src/config.py`) | — | All 9 new constants follow existing D-07/D-08 pattern |
| Test mocking | Test layer (`tests/test_llm_engine.py`) | — | respx mock transport injected via Anthropic(http_client=...) |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | 0.103.1 (pinned) | Anthropic Python SDK — client, tool-use, retries, exceptions | Official SDK; handles max_retries, timeout, httpx transport internally |
| `PyYAML` | 6.0.3 (latest) | Load `src/llm_templates.yaml` at module import | Standard Python YAML library; safe_load prevents code execution from YAML |
| `respx` | 0.23.1 (pinned) | Mock httpx transport in pytest | The Anthropic SDK uses httpx; `responses` library does not intercept httpx calls — respx does |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | (transitively from anthropic) | Custom transport injection for tests | Pass `httpx.Client(transport=respx_router)` to `Anthropic(http_client=...)` |
| `pandas` | 2.2.3 (pinned) | DataFrame manipulation — groupby, sort, iloc chunking | Already in stack; all column access via `cfg.COL_*` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML `safe_load` | `tomllib` (stdlib 3.11+) | TOML is safer but YAML chosen (D-01 locked) |
| Tool-use structured output | Free-text parsing with regex | Tool-use guarantees schema; free-text risks markdown-wrapped JSON (STATE.md pitfall) |
| `Anthropic(max_retries=3)` | `tenacity` retry wrapper | SDK max_retries=3 is LLM-04's exact wording; tenacity already in requirements.txt but not needed for LLM retry |

**Installation — new package only (PyYAML not yet in requirements.txt):**
```bash
pip install PyYAML==6.0.3
```
All other Phase 3 packages (`anthropic`, `respx`, `httpx`) are already in `requirements.txt` or transitively available.

---

## Package Legitimacy Audit

> slopcheck binary failed to run (CLI interface mismatch). All packages verified via PyPI registry and official sources.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `anthropic` | PyPI | 3+ yrs | Very high | github.com/anthropics/anthropic-sdk-python | [ASSUMED — slopcheck unavailable] | Approved — official Anthropic SDK |
| `PyYAML` | PyPI | 15+ yrs | 200M+/wk | github.com/yaml/pyyaml | [ASSUMED — slopcheck unavailable] | Approved — canonical Python YAML library |
| `respx` | PyPI | 5+ yrs | Moderate | github.com/lundberg/respx | [ASSUMED — slopcheck unavailable] | Approved — established httpx mock library |
| `httpx` | PyPI | 5+ yrs | Very high | github.com/encode/httpx | [ASSUMED — slopcheck unavailable] | Approved — transitive dep of anthropic |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time (CLI invocation failed). All packages above tagged `[ASSUMED]`. All are well-established packages verified on PyPI registry and cross-referenced to official GitHub repositories — risk is negligible, but the tag stands per protocol.*

---

## Architecture Patterns

### System Architecture Diagram

```
main.py
  │
  ├── df = score_risk(df)         ← Phase 2 output: risk_level, risk_score, etc.
  │
  └── df = enrich_with_llm(df, api_key)
          │
          ├── [LLM_ENABLED=false?] → apply_templates(all CRITICAL/HIGH, "llm_disabled")
          │
          ├── filter: risk_level in {CRITICAL, HIGH}
          │
          ├── for campus_id in df.groupby(COL_CAMPUS_ID):
          │       │
          │       ├── sort: CRITICAL first, then HIGH; both desc by risk_score
          │       │
          │       └── for chunk in range(0, len, MAX_STUDENTS_PER_LLM_CALL):
          │               │
          │               ├── [Layer 1] client.messages.create(max_retries=3)
          │               │       ↓ success → parse ToolUseBlock.input → "llm"
          │               │       ↓ exception after retries exhausted
          │               │
          │               ├── [Layer 2] re-prompt: simplified single-student prompt
          │               │       ↓ success → parse → "llm"
          │               │       ↓ exception or malformed
          │               │
          │               └── [Layer 3] apply_templates(chunk students) → "template"
          │
          └── merge results back into df copy
                  4 new columns: facilitator_summary, whatsapp_message,
                                 generated_by, llm_error_reason
```

### Recommended Project Structure

```
src/
├── llm_engine.py        # enrich_with_llm() — fills in stub
└── llm_templates.yaml   # CRITICAL/HIGH fallback templates (co-located)
tests/
└── test_llm_engine.py   # respx-mocked tests for LLM-01..09
```

### Pattern 1: Anthropic Client Instantiation with max_retries and timeout

**What:** Instantiate the SDK client once (not per call) with retry and timeout config from `cfg`.
**When to use:** At the top of `enrich_with_llm()` before the campus loop, or as a module-level singleton.

```python
# Source: github.com/anthropics/anthropic-sdk-python _client.py
import anthropic
from src import config as cfg

client = anthropic.Anthropic(
    api_key=api_key,
    max_retries=3,           # LLM-04: SDK retries with exponential backoff
    timeout=cfg.TIMEOUT_SECONDS,   # float seconds
)
```

**Note:** `max_retries=3` means the SDK will attempt the call up to 4 times total (1 original + 3 retries) before raising. After exhaustion it raises `anthropic.APIConnectionError`, `anthropic.APITimeoutError`, or `anthropic.APIStatusError` depending on failure mode.

### Pattern 2: Tool-Use Structured Output (Batch — One Tool Call Returns Array)

**What:** Define a single tool whose `input_schema` accepts an array of per-student objects. Use `tool_choice={"type": "tool", "name": "..."}` to force the call. Parse `.input["students"]` from the `ToolUseBlock`.
**When to use:** Every campus chunk API call.

```python
# Source: platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
INTERVENTION_TOOL = {
    "name": "generate_interventions",
    "description": (
        "Generate facilitator intervention summaries and WhatsApp parent messages "
        "for a list of at-risk students. Return one result object per student_id provided."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "students": {
                "type": "array",
                "description": "One result per student in the request, in the same order.",
                "items": {
                    "type": "object",
                    "properties": {
                        "student_id": {
                            "type": "string",
                            "description": "The student_id from the request."
                        },
                        "facilitator_summary": {
                            "type": "string",
                            "description": (
                                "Exactly 2 sentences. Action-oriented summary for "
                                "the facilitator describing what to do and why."
                            ),
                        },
                        "whatsapp_message": {
                            "type": "string",
                            "description": (
                                "WhatsApp-ready parent message. Under 100 words. "
                                "Warm, professional tone. Does not mention risk scores."
                            ),
                        },
                    },
                    "required": ["student_id", "facilitator_summary", "whatsapp_message"],
                },
            }
        },
        "required": ["students"],
    },
}
```

**API call:**
```python
response = client.messages.create(
    model=cfg.ANTHROPIC_MODEL,
    max_tokens=cfg.MAX_TOKENS,
    temperature=cfg.TEMPERATURE,
    tools=[INTERVENTION_TOOL],
    tool_choice={"type": "tool", "name": "generate_interventions"},
    messages=[{"role": "user", "content": prompt}],
)
```

**Response parsing:**
```python
# Source: platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
import anthropic

tool_block = next(
    b for b in response.content
    if isinstance(b, anthropic.types.ToolUseBlock)
)
results: list[dict] = tool_block.input["students"]
# results[i] = {"student_id": "...", "facilitator_summary": "...", "whatsapp_message": "..."}
```

**Token logging:**
```python
run_log["tokens_used"]["input"] += response.usage.input_tokens
run_log["tokens_used"]["output"] += response.usage.output_tokens
run_log["api_calls_made"] += 1
```

### Pattern 3: Exception Handling — Three-Layer Fallback

**What:** Catch SDK exceptions after max_retries exhausted, attempt re-prompt, fall to templates.
**When to use:** Wrapping every `client.messages.create()` call.

```python
# Source: github.com/anthropics/anthropic-sdk-python _exceptions.py
import anthropic

# Layer 1 (automatic — SDK handles internally with max_retries=3):
# anthropic.APITimeoutError      → timeout after TIMEOUT_SECONDS
# anthropic.APIConnectionError   → network failure
# anthropic.RateLimitError       → HTTP 429
# anthropic.APIStatusError       → any other 4xx/5xx after retries

try:
    response = client.messages.create(...)
    results = _parse_tool_response(response)  # may raise if malformed
except (anthropic.APIConnectionError, anthropic.APITimeoutError,
        anthropic.RateLimitError, anthropic.APIStatusError) as exc:
    error_reason = _classify_error(exc)  # "timeout" | "max_retries_exceeded" | "api_error"
    try:
        # Layer 2: single re-prompt with simplified prompt
        response2 = client.messages.create(...)   # no max_retries here (already fresh attempt)
        results = _parse_tool_response(response2)
    except Exception:
        # Layer 3: rule-based template
        results = _apply_templates(chunk, error_reason)
        run_log["fallbacks_triggered"] += len(chunk)
except (KeyError, ValueError, StopIteration) as exc:
    # Malformed tool response — skip directly to Layer 3
    results = _apply_templates(chunk, "malformed_response")
    run_log["fallbacks_triggered"] += len(chunk)
```

**Error reason classification:**
```python
def _classify_error(exc: anthropic.APIError) -> str:
    if isinstance(exc, anthropic.APITimeoutError):
        return "timeout"
    if isinstance(exc, anthropic.RateLimitError):
        return "rate_limit"
    return "max_retries_exceeded"
```

### Pattern 4: respx Mocking for Anthropic SDK Tests

**What:** Inject a custom httpx client with a respx mock transport into the `Anthropic()` constructor.
**When to use:** All tests in `tests/test_llm_engine.py`.

```python
# Source: lundberg.github.io/respx/guide/ + github.com/anthropics/anthropic-sdk-python tests/test_client.py
import httpx
import respx
import pytest
import anthropic

ANTHROPIC_BASE_URL = "https://api.anthropic.com"

@pytest.fixture()
def mock_anthropic_client(respx_mock):
    """Return an Anthropic client whose HTTP layer is fully mocked by respx."""
    http_client = httpx.Client(transport=respx_mock)  # respx_mock is a MockTransport
    return anthropic.Anthropic(
        api_key="test-key",
        http_client=http_client,
        max_retries=0,   # disable SDK retries in tests — test each layer explicitly
    )
```

**Mocking a successful tool-use response:**
```python
def _make_tool_response(students: list[dict]) -> dict:
    """Build the raw JSON body that the Anthropic API would return."""
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-4-5",
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {"input_tokens": 150, "output_tokens": 80},
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_test",
                "name": "generate_interventions",
                "input": {"students": students},
            }
        ],
    }

def test_successful_llm_call(respx_mock):
    respx_mock.post(f"{ANTHROPIC_BASE_URL}/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json=_make_tool_response([
                {"student_id": "S0001", "facilitator_summary": "Two sentences here. Done.", "whatsapp_message": "Short message."}
            ])
        )
    )
    # ... call enrich_with_llm() with injected client
```

**Mocking a timeout (after retries exhausted):**
```python
def test_timeout_falls_to_template(respx_mock):
    respx_mock.post(f"{ANTHROPIC_BASE_URL}/v1/messages").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    # SDK raises anthropic.APITimeoutError after retries → expect template fallback
```

**Mocking a 429 rate limit:**
```python
def test_rate_limit_falls_to_template(respx_mock):
    respx_mock.post(f"{ANTHROPIC_BASE_URL}/v1/messages").mock(
        return_value=httpx.Response(429, json={"type": "error", "error": {"type": "rate_limit_error", "message": "Rate limited"}})
    )
```

### Pattern 5: YAML Template Loading (Once at Module Import)

**What:** Load `llm_templates.yaml` once at module level using `Path(__file__).parent`.
**When to use:** `llm_engine.py` module level, not inside the function.

```python
import yaml
from pathlib import Path

_TEMPLATES_PATH = Path(__file__).parent / "llm_templates.yaml"

with _TEMPLATES_PATH.open("r", encoding="utf-8") as _f:
    _TEMPLATES: dict = yaml.safe_load(_f)

# Usage:
tmpl = _TEMPLATES[risk_level]  # "CRITICAL" or "HIGH"
facilitator_summary = tmpl["facilitator_summary"].format_map(row_dict)
whatsapp_message = tmpl["whatsapp_message"].format_map(row_dict)
```

**YAML structure (D-02):**
```yaml
CRITICAL:
  facilitator_summary: >-
    {student_id} has a risk score of {risk_score} (attendance {attendance_rate:.0%},
    {avg_practice_questions:.1f} questions/day, trend {trend_direction}).
    {recommended_action} — last facilitator note was {days_since_last_note:.0f} days ago.
  whatsapp_message: >-
    Dear parent, we want to check in about your child's recent progress.
    We've noticed some areas where additional support may help, and we'd like to
    schedule a brief conversation. Please reply to arrange a time. Thank you.
HIGH:
  facilitator_summary: >-
    {student_id} has an elevated risk score of {risk_score} with {trend_direction} trend
    and {attendance_rate:.0%} attendance.
    {recommended_action} this week.
  whatsapp_message: >-
    Dear parent, we're reaching out to share a quick update on your child's
    learning journey. We'd love to connect briefly — please reply when convenient.
    Thank you for your continued support.
```

### Pattern 6: run_log Return — Recommended Pattern

**What:** Return `(df, counts_dict)` tuple from `enrich_with_llm()`. This avoids adding `run_log` as a parameter (which would violate the pure-function discipline) and avoids `df.attrs` (which can be lost on some pandas operations).
**When to use:** Unwrap in `main.py` at lines 74-78.

```python
# In llm_engine.py:
def enrich_with_llm(df: pd.DataFrame, api_key: str) -> tuple[pd.DataFrame, dict]:
    ...
    return df, {
        "api_calls_made": api_calls,
        "tokens_used": tokens,
        "fallbacks_triggered": fallbacks,
    }

# In main.py (lines 74-78):
from src import llm_engine
df, llm_counts = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY)
run_log["api_calls_made"] = llm_counts["api_calls_made"]
run_log["tokens_used"] = llm_counts["tokens_used"]
run_log["fallbacks_triggered"] = llm_counts["fallbacks_triggered"]
```

**NOTE for planner:** The locked signature in STATE.md says `enrich_with_llm(df, api_key) -> DataFrame`. Changing the return type to a tuple is a backwards-compatible extension (existing callers that only do `df = enrich_with_llm(...)` still work if they ignore the second element). However, the planner must decide whether to update the STATE.md contract or use an alternative pattern. The `df.attrs` alternative is: store counts in `df.attrs["llm_counts"]` before returning — but `df.attrs` is not preserved by all pandas operations and is fragile. The tuple pattern is the most explicit and testable.

### Pattern 7: Chunk Loop

**What:** Slice a campus's sorted CRITICAL/HIGH students into chunks.
**When to use:** Inside the per-campus loop.

```python
# Source: CONTEXT.md §Specific Ideas
campus_students = (
    df_campus[df_campus[cfg.COL_RISK_LEVEL].isin(["CRITICAL", "HIGH"])]
    .sort_values(
        by=[cfg.COL_RISK_LEVEL, cfg.COL_RISK_SCORE],
        ascending=[True, False],  # CRITICAL < HIGH alphabetically → use categorical or map
        key=lambda col: col.map({"CRITICAL": 0, "HIGH": 1}) if col.name == cfg.COL_RISK_LEVEL else col
    )
)

for i in range(0, len(campus_students), cfg.MAX_STUDENTS_PER_LLM_CALL):
    chunk = campus_students.iloc[i : i + cfg.MAX_STUDENTS_PER_LLM_CALL]
    # ... call API for chunk
```

**Sort note:** `sort_values` with `ascending=[True, False]` on `[risk_level, risk_score]` does not produce CRITICAL-first with alphabetical strings since "CRITICAL" > "HIGH" alphabetically. Use a key function or categorical ordering to get CRITICAL first.

### Anti-Patterns to Avoid

- **Free-text response parsing:** Never parse Claude's text with regex or `json.loads()` on raw text. Use `tool_choice={"type": "tool", ...}` to force a `ToolUseBlock`. Free-text risks markdown-wrapped JSON (STATE.md known pitfall).
- **Per-student API calls:** LLM-02 locks campus batching. Never call `client.messages.create()` once per student.
- **`responses` library for mocking:** The `responses` library intercepts `requests` library calls, not `httpx`. The Anthropic SDK uses `httpx`. Use `respx` only.
- **Module-level `Anthropic()` singleton initialized at import time:** This causes the API key check to run at import time in tests (even with `dummy-key-for-tests` in conftest). Instantiate the client inside `enrich_with_llm()` or accept it as an injected parameter for testability.
- **Bare `str` dict access on tool response:** `tool_block.input["students"]` can raise `KeyError` if Claude returns a malformed tool input. Guard with `try/except (KeyError, TypeError)` to route to re-prompt layer.
- **`yaml.load()` without Loader:** Always use `yaml.safe_load()`. `yaml.load()` without an explicit Loader executes arbitrary Python.
- **Logging student_name or parent_phone:** Any `logger.*` call referencing student identifiers must mask them: `f"student [STUDENT] processed"` not `f"student {row['student_name']} processed"`. This is LLM-08.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with exponential backoff | Custom retry loop with `time.sleep()` | `Anthropic(max_retries=3)` | SDK implements jitter, respects Retry-After headers, handles connection resets |
| Structured JSON output from Claude | Parse free-text with regex | Tool-use with `tool_choice={"type":"tool"}` | Eliminates markdown-wrapped JSON; schema-validated by SDK |
| YAML loading | Custom file parser | `yaml.safe_load()` (PyYAML) | Handles multi-line strings, escaping, encoding edge cases |
| httpx request mocking in tests | `unittest.mock.patch` on SDK internals | `respx` with `httpx.Client(transport=...)` | Patches at the transport layer — survives SDK version changes; `responses` library silently misses httpx calls |

**Key insight:** The Anthropic SDK's internal retry logic (max_retries=3 with exponential backoff) eliminates the need for an outer retry wrapper entirely. The `tenacity` library already in `requirements.txt` is not needed for LLM retry — only the SDK parameter is required for LLM-04 compliance.

---

## Common Pitfalls

### Pitfall 1: Malformed Tool Response — Missing `students` Key

**What goes wrong:** Claude returns a `ToolUseBlock` but its `.input` dict has a different top-level key name (e.g., `"interventions"` instead of `"students"`) or omits the array entirely.
**Why it happens:** Tool descriptions that use multiple terms for the same concept. Claude may use a synonym from the description text as the key name.
**How to avoid:** Use the exact field name from `input_schema.properties` in the description text too. Guard `tool_block.input["students"]` with `try/except KeyError` → re-prompt layer.
**Warning signs:** `KeyError: 'students'` in test logs even with a successful HTTP 200 response.

### Pitfall 2: Sort Order for CRITICAL-First

**What goes wrong:** `df.sort_values(by=["risk_level", "risk_score"], ascending=[True, False])` sorts "CRITICAL" after "HIGH" because "C" < "H" alphabetically, producing HIGH-first order — the exact opposite of D-05.
**Why it happens:** String comparison sorts alphabetically; CRITICAL/HIGH are not inherently ordered.
**How to avoid:** Map risk_level to an integer priority before sorting: `{"CRITICAL": 0, "HIGH": 1}`, sort ascending on the integer column, then drop it. Or use `pd.Categorical` with ordered levels.
**Warning signs:** The first chunk contains HIGH students when CRITICAL students exist in the campus.

### Pitfall 3: SDK Client Instantiated at Module Import

**What goes wrong:** `client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)` at module level causes the API key to be read when `llm_engine` is imported. In tests, `conftest.py` sets `ANTHROPIC_API_KEY=dummy-key-for-tests` via `os.environ.setdefault()`, but if `src.config` is imported before `conftest.py` runs (e.g., via `import src.llm_engine` at top of test file), the key may already be loaded correctly — but the client object is real and will attempt HTTP calls unless mocked.
**Why it happens:** Module-level singletons are initialized at import time, not at test-fixture time.
**How to avoid:** Instantiate `anthropic.Anthropic()` inside `enrich_with_llm()` using the `api_key` parameter, or accept an injectable client parameter. This allows tests to pass a pre-mocked client.
**Warning signs:** Tests make real HTTP calls during CI when `ANTHROPIC_API_KEY` is a real key in the environment.

### Pitfall 4: `df.attrs` Lost After pandas Operations

**What goes wrong:** If return counts are stored in `df.attrs["llm_counts"]` before returning, downstream pandas operations like `.merge()`, `.copy()`, or column assignment may silently drop `df.attrs`.
**Why it happens:** `df.attrs` is not preserved by all DataFrame operations in pandas 2.2.x.
**How to avoid:** Return a `(df, counts_dict)` tuple instead of using `df.attrs` for cross-function metadata. Update STATE.md contract accordingly.
**Warning signs:** `run_log["tokens_used"]` stays at 0 even after successful API calls.

### Pitfall 5: `yaml.safe_load()` on YAML with Python float format strings

**What goes wrong:** YAML scalars containing `{attendance_rate:.0%}` may be misinterpreted by the YAML parser if not quoted.
**Why it happens:** Curly braces in YAML flow mappings have special meaning. An unquoted `{...}` in a block scalar value can parse incorrectly.
**How to avoid:** Use YAML block scalars (`>-` or `|-` notation) for template strings. Block scalars treat `{` as literal text. Always test YAML loading with `assert "{attendance_rate:.0%}" in _TEMPLATES["CRITICAL"]["facilitator_summary"]` in Wave 0.
**Warning signs:** `KeyError` or `ScannerError` when loading templates; `.format_map()` fails because format keys are missing.

### Pitfall 6: respx Not Intercepting Anthropic SDK Calls

**What goes wrong:** Using `@respx.mock` decorator or `respx_mock` fixture alone does NOT intercept Anthropic SDK calls unless the SDK's underlying httpx client is the one being mocked.
**Why it happens:** `respx.mock` patches the global httpx transports, but the Anthropic SDK creates its own private httpx client. The SDK client bypasses the global mock unless you inject a custom transport.
**How to avoid:** Use `httpx.Client(transport=respx_mock)` and pass it as `Anthropic(http_client=..., max_retries=0)`. Set `max_retries=0` in tests to prevent the SDK from retrying mocked failures before the test can assert on them.
**Warning signs:** Test completes with no `respx_mock.calls` recorded; test makes real HTTP requests.

---

## Code Examples

### Complete Tool Definition + Call + Parse Cycle

```python
# Source: platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
#         platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls

import anthropic
from src import config as cfg

def _call_llm_for_chunk(
    client: anthropic.Anthropic,
    chunk_rows: list[dict],
) -> list[dict] | None:
    """Call Claude API for one chunk. Returns list of result dicts or None on failure."""
    student_data = [
        {
            "student_id": r[cfg.COL_STUDENT_ID],
            "risk_level": r[cfg.COL_RISK_LEVEL],
            "risk_score": r[cfg.COL_RISK_SCORE],
            "attendance_rate": r[cfg.COL_ATTENDANCE_RATE],
            "avg_practice_questions": r[cfg.COL_AVG_PRACTICE],
            "trend_direction": r[cfg.COL_TREND_DIR],
            "days_since_last_note": r[cfg.COL_DAYS_SINCE_NOTE],
            "recommended_action": r[cfg.COL_RECOMMENDED_ACTION],
        }
        for r in chunk_rows
    ]
    prompt = (
        f"Generate intervention content for {len(student_data)} at-risk students. "
        f"Student data:\n{student_data}\n"
        f"For each student: facilitator_summary must be exactly 2 sentences. "
        f"whatsapp_message must be under 100 words, warm and professional."
    )
    response = client.messages.create(
        model=cfg.ANTHROPIC_MODEL,
        max_tokens=cfg.MAX_TOKENS,
        temperature=cfg.TEMPERATURE,
        tools=[INTERVENTION_TOOL],
        tool_choice={"type": "tool", "name": "generate_interventions"},
        messages=[{"role": "user", "content": prompt}],
    )
    tool_block = next(
        b for b in response.content
        if isinstance(b, anthropic.types.ToolUseBlock)
    )
    return tool_block.input["students"]
```

### respx Test: Successful Call + Token Assertion

```python
# Source: lundberg.github.io/respx/guide/
import httpx, respx, pytest, anthropic, pandas as pd
from src import config as cfg
from src.llm_engine import enrich_with_llm

def test_llm_tokens_logged(respx_mock):
    respx_mock.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant",
            "model": cfg.ANTHROPIC_MODEL, "stop_reason": "tool_use",
            "stop_sequence": None,
            "usage": {"input_tokens": 200, "output_tokens": 100},
            "content": [{
                "type": "tool_use", "id": "toolu_01", "name": "generate_interventions",
                "input": {"students": [
                    {"student_id": "S0001",
                     "facilitator_summary": "Sentence one. Sentence two.",
                     "whatsapp_message": "Dear parent, brief update needed."}
                ]}
            }]
        })
    )
    # build minimal df with one CRITICAL student...
    df, counts = enrich_with_llm(df_with_critical, cfg.ANTHROPIC_API_KEY,
                                  http_client=httpx.Client(transport=respx_mock))
    assert counts["tokens_used"]["input"] == 200
    assert counts["tokens_used"]["output"] == 100
    assert df.loc[df[cfg.COL_STUDENT_ID] == "S0001", cfg.COL_GENERATED_BY].iloc[0] == "llm"
```

### Prompt Structure (PII-Safe Batch)

```python
# Student fields included in API prompt — NO student_name, NO parent_phone (LLM-08)
student_data = [
    {
        "student_id": row[cfg.COL_STUDENT_ID],        # identifier only, not PII
        "risk_level": row[cfg.COL_RISK_LEVEL],
        "risk_score": float(row[cfg.COL_RISK_SCORE]),
        "attendance_rate": float(row[cfg.COL_ATTENDANCE_RATE]),
        "avg_practice_questions": float(row[cfg.COL_AVG_PRACTICE]),
        "trend_direction": row[cfg.COL_TREND_DIR],
        "days_since_last_note": float(row[cfg.COL_DAYS_SINCE_NOTE]),
        "recommended_action": row[cfg.COL_RECOMMENDED_ACTION],
    }
    for _, row in chunk.iterrows()
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parse JSON from Claude's text response | Tool-use with `tool_choice={"type":"tool"}` | ~2023 (tool-use GA) | Eliminates markdown-wrapped JSON entirely |
| `responses` library for httpx mocking | `respx` library | 2020 (httpx adoption) | `responses` silently misses httpx calls |
| Per-message retry with `tenacity` | `Anthropic(max_retries=3)` | ~2023 (SDK feature) | SDK handles jitter, Retry-After headers |

**Deprecated/outdated:**
- `anthropic.completion()` API: Replaced by `client.messages.create()`. Do not use.
- `yaml.load()` without Loader argument: Deprecated since PyYAML 5.1; always use `yaml.safe_load()`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `anthropic.types.ToolUseBlock` is the correct class name for checking `isinstance(b, ...)` in response.content parsing | Code Examples | Parse fails; need to check actual type name from SDK source |
| A2 | `tool_block.input` is a plain `dict` (not a Pydantic model) accessible with `["students"]` | Code Examples / Pattern 2 | KeyError or AttributeError; may need `.model_dump()` or `.get()` |
| A3 | Setting `max_retries=0` on the test client prevents all SDK internal retries | Pattern 4 / Pitfall 6 | Tests may be slow or flaky if SDK retries despite max_retries=0 |
| A4 | `httpx.Client(transport=respx_mock)` (using the respx_mock fixture directly as transport) is valid | Pattern 4 | May need `respx.MockTransport(respx_mock)` wrapper instead |
| A5 | PyYAML block scalars (`>-`) preserve curly-brace format strings as literal text | Pitfall 5 | Template interpolation silently broken; all fallback messages malformed |
| A6 | The tuple return `(df, counts_dict)` is acceptable as a contract extension over the locked `-> DataFrame` signature | Pattern 6 | STATE.md contract conflict; planner must decide and update STATE.md |

**Verification for A1/A2:** Run `py -3.12 -c "import anthropic; help(anthropic.types.ToolUseBlock)"` after implementing to confirm attribute names.

---

## Open Questions

1. **Return type contract (A6)**
   - What we know: STATE.md locks `enrich_with_llm(df, api_key) -> DataFrame`; main.py comment at line 76-78 implies counts need to flow back somehow
   - What's unclear: Whether to update the STATE.md contract for a tuple return, or use a mutable `run_log` parameter
   - Recommendation: Planner should choose tuple return, update STATE.md, and update main.py lines 74-78 in the same plan

2. **respx mock transport injection API (A3/A4)**
   - What we know: `Anthropic(http_client=httpx.Client(...))` is documented; `respx_mock` fixture provides a mock router
   - What's unclear: Whether `httpx.Client(transport=respx_mock)` requires wrapping in `respx.MockTransport()` or can use the router directly
   - Recommendation: Wave 0 should include a minimal smoke test to confirm the injection pattern works before writing all tests

3. **ToolUseBlock attribute names (A1/A2)**
   - What we know: Official docs show `.input` field contains the dict; SDK source confirms `ToolUseBlock` class exists
   - What's unclear: Whether `.input` is a plain dict or a Pydantic model needing `.model_dump()`
   - Recommendation: Add a `# VERIFY: isinstance check` comment in implementation; check in Wave 0 task

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | pandas 2.2.3 wheel | ✓ | 3.12 (via `py -3.12`) | — |
| `anthropic` SDK | LLM-01..07 | ✓ | 0.103.1 | — |
| `respx` | TEST-03 | ✓ | 0.23.1 | — |
| `PyYAML` | D-01 template loading | ✗ under py3.12 | Not installed in py3.12 env | Must add to requirements.txt and install |
| `httpx` | respx transport | ✓ (transitive) | (via anthropic) | — |
| ANTHROPIC_API_KEY | LLM-01 | ✓ (test dummy) | dummy-key-for-tests | `LLM_ENABLED=false` for local dev |

**Missing dependencies with no fallback:**
- `PyYAML` not installed under Python 3.12 environment — must add `PyYAML==6.0.3` to `requirements.txt` and run `py -3.12 -m pip install PyYAML==6.0.3`. This is a Wave 0 task.

**Missing dependencies with fallback:**
- None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | `pytest.ini` or implicit (no config file detected — follows project convention) |
| Quick run command | `py -3.12 -m pytest tests/test_llm_engine.py -x -q` |
| Full suite command | `py -3.12 -m pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-01 | Only CRITICAL/HIGH students get API calls | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_medium_low_skipped -x` | ❌ Wave 0 |
| LLM-02 | Campus batching — one call per campus chunk | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_campus_batching -x` | ❌ Wave 0 |
| LLM-03 | Tool-use returns facilitator_summary + whatsapp_message | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_tool_use_structured_output -x` | ❌ Wave 0 |
| LLM-04 | max_retries=3 passed to SDK client | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_max_retries_config -x` | ❌ Wave 0 |
| LLM-05 | Template fallback on API failure; generated_by="template" | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_fallback_to_template -x` | ❌ Wave 0 |
| LLM-06 | Token usage logged per call | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_token_logging -x` | ❌ Wave 0 |
| LLM-07 | API key not in any log output | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_api_key_not_logged -x` | ❌ Wave 0 |
| LLM-08 | student_name + parent_phone masked in logs | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_pii_masking_in_logs -x` | ❌ Wave 0 |
| LLM-09 | MAX_STUDENTS_PER_LLM_CALL chunks correctly at 10 | unit | `py -3.12 -m pytest tests/test_llm_engine.py::test_chunk_size_limit -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `py -3.12 -m pytest tests/test_llm_engine.py -x -q`
- **Per wave merge:** `py -3.12 -m pytest tests/ -q`
- **Phase gate:** Full suite green (53 existing + all new LLM tests) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_llm_engine.py` — create file; covers LLM-01 through LLM-09
- [ ] `src/llm_templates.yaml` — create file; Wave 0 must verify YAML loads and format_map works
- [ ] Verify `PyYAML==6.0.3` in `requirements.txt` and installed: `py -3.12 -m pip install PyYAML==6.0.3`
- [ ] Smoke-test respx transport injection: confirm `httpx.Client(transport=respx_mock)` + `Anthropic(http_client=...)` intercepts calls correctly
- [ ] Verify `anthropic.types.ToolUseBlock` attribute names: `py -3.12 -c "import anthropic; print(dir(anthropic.types.ToolUseBlock))"`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `os.environ["ANTHROPIC_API_KEY"]` — fail-loud; already implemented in config.py |
| V3 Session Management | no | Stateless API calls; no session |
| V4 Access Control | no | Single-user batch pipeline |
| V5 Input Validation | yes | Tool-use `input_schema` validates Claude's output; `.format_map()` safe with known keys |
| V6 Cryptography | no | HTTPS enforced by SDK; no custom crypto |
| V7 Error Handling / PII | yes | LLM-08: mask student_name as [STUDENT], parent_phone as [PHONE] in all log output |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in logs | Information Disclosure | `os.environ["ANTHROPIC_API_KEY"]` — never log `api_key` variable; conftest.py already sets dummy key |
| PII (student name, phone) in logs | Information Disclosure | Mask in all `logger.*` calls: `[STUDENT]` / `[PHONE]` literals |
| Prompt injection via student data | Tampering | Student data fields are numeric/categorical — no free-text from untrusted users in the prompt path |
| Malformed LLM output executed | Tampering | `.format_map()` with known keys only; tool-use schema validation; no `eval()` ever |

---

## Sources

### Primary (HIGH confidence)

- `github.com/anthropics/anthropic-sdk-python` — `_exceptions.py` (exception hierarchy, status codes), `_client.py` (constructor signature with max_retries, timeout, http_client) [VERIFIED via WebFetch]
- `platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools` — tool schema syntax, `tool_choice` parameter, `input_schema` structure [VERIFIED via WebFetch]
- `platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls` — `ToolUseBlock` parsing, `response.usage` token fields, `stop_reason` [VERIFIED via WebFetch]
- `lundberg.github.io/respx/guide/` — respx fixture patterns, mock POST, timeout side_effect, call history [VERIFIED via WebFetch]
- Existing codebase: `src/config.py`, `src/llm_engine.py`, `main.py`, `tests/conftest.py` — established patterns, run_log schema, dummy key setup [VERIFIED via Read]

### Secondary (MEDIUM confidence)

- PyPI registry: `anthropic` 0.103.1, `PyYAML` 6.0.3, `respx` 0.23.1 confirmed present on registry [VERIFIED via pip index versions]
- `github.com/anthropics/anthropic-sdk-python tests/test_client.py` — `@pytest.mark.respx(base_url=...)` and `respx_mock.post("/v1/messages")` pattern [VERIFIED via WebFetch]

### Tertiary (LOW confidence)

- A1-A6 in Assumptions Log — inferred from docs and SDK source but not runtime-verified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on PyPI; SDK version confirmed installed
- Architecture: HIGH — patterns derived from official Anthropic docs and existing project code
- Pitfalls: HIGH — 4 of 6 pitfalls are directly from STATE.md or confirmed via SDK source; A1/A4 are LOW individually
- Test patterns: MEDIUM — respx injection pattern confirmed from SDK test file; ToolUseBlock attribute names not runtime-verified (A1/A2)

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (anthropic SDK releases frequently — verify `pip index versions anthropic` before executing if >2 weeks pass)
