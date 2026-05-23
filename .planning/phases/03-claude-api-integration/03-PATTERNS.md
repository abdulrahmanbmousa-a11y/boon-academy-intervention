# Phase 3: Claude API Integration - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 6 (new/modified files for this phase)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/llm_engine.py` | service | request-response + transform | `src/risk_engine.py` | role-match (pure-function discipline, df.copy(), cfg.COL_* constants, logger pattern) |
| `src/config.py` | config | — | `src/config.py` (extend) | exact (add to existing constant blocks, follow os.getenv pattern) |
| `src/llm_templates.yaml` | config | — | none in codebase | no-analog (RESEARCH.md patterns only) |
| `tests/test_llm_engine.py` | test | — | `tests/test_risk_engine.py` | exact (helper builder, parametrize, caplog, source-scan pattern) |
| `requirements.txt` | config | — | `requirements.txt` (extend) | exact (pinned `==` version format) |
| `main.py` | orchestrator | — | `main.py` lines 74-78 (uncomment) | exact (run_log dict already scoped, comments show wiring point) |

---

## Pattern Assignments

### `src/llm_engine.py` (service, request-response + transform)

**Analog:** `src/risk_engine.py`

**Imports pattern** (`src/risk_engine.py` lines 1-21):
```python
"""LLM enrichment engine for boon-academy-intervention.

Implements campus-batched Claude API enrichment with three-layer fallback.
Signature is LOCKED per STATE.md — all downstream phases depend on it.

Patterns applied (03-RESEARCH.md):
- Pattern 1: Anthropic client instantiated inside function (not module-level — Pitfall 3)
- Pattern 2: tool-use structured output (avoid markdown-wrapped JSON — STATE.md pitfall)
- Pattern 3: three-layer fallback (SDK retry → re-prompt → YAML template)
- Pattern 4: df.copy() at function entry (purity + df.attrs preservation, Pitfall 8)
- Pattern 5: YAML templates loaded once at module import (not per-call)
"""
import logging
from pathlib import Path

import anthropic
import pandas as pd
import yaml

from src import config as cfg

logger = logging.getLogger(__name__)
```

**Module-level constants pattern** (`src/risk_engine.py` lines 27-46 — copy this structure):
```python
# Module-level private constants — mirrors _ACTION_BY_LEVEL / _RISK_BINS pattern in risk_engine.py

_TEMPLATES_PATH = Path(__file__).parent / "llm_templates.yaml"

with _TEMPLATES_PATH.open("r", encoding="utf-8") as _f:
    _TEMPLATES: dict = yaml.safe_load(_f)
# Load once at import time — not per enrich_with_llm() call (D-01)

INTERVENTION_TOOL: dict = {
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
                        "student_id": {"type": "string"},
                        "facilitator_summary": {
                            "type": "string",
                            "description": "Exactly 2 sentences. Action-oriented summary for the facilitator.",
                        },
                        "whatsapp_message": {
                            "type": "string",
                            "description": "WhatsApp-ready parent message. Under 100 words. Warm, professional tone.",
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

**Pure function entry + df.copy() pattern** (`src/risk_engine.py` lines 113-154):
```python
def enrich_with_llm(df: pd.DataFrame, api_key: str) -> tuple[pd.DataFrame, dict]:
    """..docstring.."""
    # Purity guarantee — mirrors score_risk() pattern (Pitfall 8 / CLAUDE.md)
    df = df.copy()

    # Local accumulator — returned as second element of tuple (RESEARCH.md Pattern 6)
    api_calls: int = 0
    tokens: dict[str, int] = {"input": 0, "output": 0}
    fallbacks: int = 0
```

**PII-safe aggregate logging pattern** (`src/risk_engine.py` lines 198-205):
```python
# LOG aggregate counts only — never student_name or parent_phone (LLM-08)
logger.info(
    f"enrich_with_llm complete — "
    f"api_calls={api_calls}, tokens_input={tokens['input']}, "
    f"tokens_output={tokens['output']}, fallbacks={fallbacks}"
)
# Per-student log example (mask PII — LLM-08):
#   logger.debug(f"processed student [STUDENT] on campus {campus_id}")
#   NOT: logger.debug(f"processed {row[cfg.COL_STUDENT_NAME]}")
```

**Column assignment pattern** (`src/risk_engine.py` lines 159-196 — all via cfg.COL_*):
```python
# Initialize 4 new columns with None for all rows (D-07: MEDIUM/LOW stay None)
df[cfg.COL_FACILITATOR_SUMMARY] = None
df[cfg.COL_WHATSAPP_MESSAGE] = None
df[cfg.COL_GENERATED_BY] = None
df[cfg.COL_LLM_ERROR_REASON] = None

# Assign back to specific rows via .loc after processing:
df.loc[idx, cfg.COL_FACILITATOR_SUMMARY] = result["facilitator_summary"]
df.loc[idx, cfg.COL_GENERATED_BY] = "llm"  # or "template"
```

**Error handling / fallback pattern** (RESEARCH.md Pattern 3 — no direct codebase analog, closest is `src/ingestion.py` per-row containment):
```python
# Per-chunk fallback — mirrors ingestion.py per-row containment discipline
try:
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
    results = tool_block.input["students"]  # KeyError → Layer 3 (Pitfall 1)
    tokens["input"] += response.usage.input_tokens
    tokens["output"] += response.usage.output_tokens
    api_calls += 1
except (anthropic.APIConnectionError, anthropic.APITimeoutError,
        anthropic.RateLimitError, anthropic.APIStatusError) as exc:
    error_reason = _classify_error(exc)
    logger.warning(f"LLM API error ({error_reason}) for campus {campus_id} chunk — attempting re-prompt")
    try:
        # Layer 2: re-prompt (simplified)
        response2 = client.messages.create(...)
        results = _parse_tool_response(response2)
        api_calls += 1
    except Exception:
        # Layer 3: rule-based template
        results = _apply_templates(chunk, error_reason)
        fallbacks += len(chunk)
except (KeyError, ValueError, StopIteration) as exc:
    # Malformed ToolUseBlock → skip directly to Layer 3 (Pitfall 1)
    logger.warning(f"Malformed LLM response for campus {campus_id} chunk — using template fallback")
    results = _apply_templates(chunk, "malformed_response")
    fallbacks += len(chunk)
```

**Return pattern** (`src/risk_engine.py` line 207 — extend to tuple per RESEARCH.md Pattern 6):
```python
return df, {
    "api_calls_made": api_calls,
    "tokens_used": tokens,
    "fallbacks_triggered": fallbacks,
}
```

---

### `src/config.py` (config — extend existing file)

**Analog:** `src/config.py` (the file itself — add new blocks following existing section structure)

**Existing tunables block to extend** (`src/config.py` lines 34-36):
```python
# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
MAX_STUDENTS_PER_LLM_CALL: int = int(os.getenv("MAX_STUDENTS_PER_LLM_CALL", "10"))
```
Add after line 36, staying in the same section:
```python
# LLM tunables — all env-overridable, safe defaults (D-09)
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "30"))
```
Note: Same `os.getenv(KEY, default)` pattern as `LOG_LEVEL` and `MAX_STUDENTS_PER_LLM_CALL` on lines 35-36. `LLM_ENABLED` uses the `.lower() == "true"` bool-from-string idiom (not `bool(os.getenv(...))` which is always True for any non-empty string).

**Existing column-name block to extend** (`src/config.py` lines 73-86):
```python
# Derived columns (added by ingestion/risk_engine — frozen for Phase 2+)
COL_ATTENDANCE_RATE: str = "attendance_rate"
...
COL_RECOMMENDED_ACTION: str = "recommended_action"

# D-09 component score columns (Phase 2)
COL_ATTENDANCE_COMPONENT: str = "attendance_component"
...
COL_NOTES_COMPONENT: str = "notes_component"
```
Add a new block after line 87:
```python
# LLM output columns (Phase 3 — D-06)
COL_FACILITATOR_SUMMARY: str = "facilitator_summary"
COL_WHATSAPP_MESSAGE: str = "whatsapp_message"
COL_GENERATED_BY: str = "generated_by"
COL_LLM_ERROR_REASON: str = "llm_error_reason"
```
Exact same `COL_NAME: str = "column_name"` pattern as every other column constant in the file.

---

### `src/llm_templates.yaml` (config — new file, no codebase analog)

**No codebase analog.** Use RESEARCH.md Pattern 5 directly.

**Pattern from RESEARCH.md (lines 406-441):**
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
Key constraint: Use `>-` block scalars for all template strings — this prevents the YAML parser from misinterpreting `{` as a flow mapping (Pitfall 5 in RESEARCH.md). Verify after creation with: `assert "{attendance_rate:.0%}" in _TEMPLATES["CRITICAL"]["facilitator_summary"]`.

---

### `tests/test_llm_engine.py` (test — new file)

**Analog:** `tests/test_risk_engine.py`

**File-level header + imports pattern** (`tests/test_risk_engine.py` lines 1-18):
```python
"""Tests for src/llm_engine.py — covers LLM-01 through LLM-09.

Each test maps to one or more LLM-* requirements from REQUIREMENTS.md.
All tests use respx-mocked Anthropic client injected via http_client= parameter.
No real API calls are made.
"""
import logging
import httpx
import respx
import pytest
import anthropic
import pandas as pd

from src import config as cfg
from src.llm_engine import enrich_with_llm
```

**Builder helper pattern** (`tests/test_risk_engine.py` lines 24-59 — mirror exactly):
```python
def _build_student_row(
    student_id: str = "S0001",
    campus_id: str = "C01",
    risk_level: str = "CRITICAL",
    risk_score: float = 85.0,
    attendance_rate: float = 0.3,
    avg_practice_questions: float = 2.0,
    trend_direction: str = "declining",
    days_since_last_note: float = 20.0,
    recommended_action: str = "Contact parent immediately",
) -> dict:
    """Build a single-student dict for pd.DataFrame([_build_student_row(...)]).

    Includes all columns output by score_risk() that enrich_with_llm() consumes.
    """
    return {
        cfg.COL_STUDENT_ID: student_id,
        cfg.COL_STUDENT_NAME: "Test Student",    # present in df but NOT sent to API (LLM-08)
        cfg.COL_CAMPUS_ID: campus_id,
        cfg.COL_PARENT_PHONE: "0501234567",       # present in df but NOT sent to API (LLM-08)
        cfg.COL_FACILITATOR_EMAIL: "t@example.com",
        cfg.COL_RISK_LEVEL: risk_level,
        cfg.COL_RISK_SCORE: risk_score,
        cfg.COL_ATTENDANCE_RATE: attendance_rate,
        cfg.COL_AVG_PRACTICE: avg_practice_questions,
        cfg.COL_TREND_DIR: trend_direction,
        cfg.COL_DAYS_SINCE_NOTE: days_since_last_note,
        cfg.COL_RECOMMENDED_ACTION: recommended_action,
        # component columns (present from score_risk output)
        cfg.COL_ATTENDANCE_COMPONENT: 70.0,
        cfg.COL_PRACTICE_COMPONENT: 87.0,
        cfg.COL_TREND_COMPONENT: 100.0,
        cfg.COL_NOTES_COMPONENT: 67.0,
    }
```

**respx mock client fixture pattern** (RESEARCH.md Pattern 4 — no codebase analog yet):
```python
ANTHROPIC_BASE_URL = "https://api.anthropic.com"

def _make_tool_response(students: list[dict]) -> dict:
    """Build the raw JSON body the Anthropic API would return for a tool-use call."""
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": cfg.ANTHROPIC_MODEL,
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {"input_tokens": 150, "output_tokens": 80},
        "content": [{
            "type": "tool_use",
            "id": "toolu_test",
            "name": "generate_interventions",
            "input": {"students": students},
        }],
    }
```

**Test function structure pattern** (`tests/test_risk_engine.py` lines 66-81 — one assert per requirement, explicit failure message):
```python
def test_medium_low_students_skipped(respx_mock) -> None:
    """LLM-01: MEDIUM and LOW students receive None in all 4 LLM columns — no API call made."""
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", risk_level="MEDIUM"),
        _build_student_row(student_id="S0002", risk_level="LOW"),
    ])
    http_client = httpx.Client(transport=respx_mock)
    result_df, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    assert counts["api_calls_made"] == 0, "MEDIUM/LOW students should produce zero API calls"
    assert result_df[cfg.COL_GENERATED_BY].isna().all(), (
        "MEDIUM/LOW rows must have None/NaN in generated_by (D-07)"
    )
    assert len(respx_mock.calls) == 0, "LLM-01: no HTTP calls should be made for MEDIUM/LOW only cohort"
```

**caplog PII test pattern** (`tests/test_risk_engine.py` lines 445-463 — copy exactly for LLM-08):
```python
def test_pii_not_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    """LLM-08: student_name and parent_phone must never appear in logger emissions."""
    sensitive_name = "Sensitive Student"
    sensitive_phone = "0509991111"
    row = _build_student_row()
    row[cfg.COL_STUDENT_NAME] = sensitive_name
    row[cfg.COL_PARENT_PHONE] = sensitive_phone
    df = pd.DataFrame([row])

    with caplog.at_level(logging.DEBUG, logger="src.llm_engine"):
        # Use LLM_ENABLED=false path to avoid respx setup — still exercises all logging paths
        ...

    for record in caplog.records:
        assert sensitive_name not in record.message, (
            f"PII leak: student_name '{sensitive_name}' found in log: {record.message}"
        )
        assert sensitive_phone not in record.message, (
            f"PII leak: parent_phone '{sensitive_phone}' found in log: {record.message}"
        )
```

**parametrize pattern** (`tests/test_risk_engine.py` lines 241-268):
```python
@pytest.mark.parametrize("risk_level,expected_generated_by", [
    ("CRITICAL", "template"),
    ("HIGH", "template"),
])
def test_llm_disabled_uses_template_for_all(risk_level: str, expected_generated_by: str, monkeypatch) -> None:
    """LLM_ENABLED=false: all CRITICAL/HIGH get generated_by='template', no API calls."""
    monkeypatch.setenv("LLM_ENABLED", "false")
    ...
```

**Source-scan test pattern** (`tests/test_risk_engine.py` lines 470-506 — copy structure for bare-string check):
```python
def test_no_bare_column_strings_in_llm_engine() -> None:
    """LLM-08 / CLAUDE.md: every column-name string in llm_engine.py must come from cfg.COL_*."""
    import re
    source_path = Path(__file__).parent.parent / "src" / "llm_engine.py"
    source = source_path.read_text(encoding="utf-8")
    no_docstrings = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    matches = re.findall(r'"([a-z][a-z0-9_]{3,})"', no_comments)
    allowed: set[str] = {"llm", "template", "llm_disabled", "timeout", "rate_limit",
                         "malformed_response", "max_retries_exceeded", "students",
                         "CRITICAL", "HIGH"}
    offenders = {m for m in matches if m not in allowed}
    assert not offenders, (
        f"Bare column-name strings in src/llm_engine.py: {sorted(offenders)}. "
        f"Use cfg.COL_* constants."
    )
```

---

### `requirements.txt` (config — extend existing file)

**Analog:** `requirements.txt` (the file itself)

**Existing pinned format** (`requirements.txt` lines 1-7):
```
pandas==2.2.3
openpyxl==3.1.5
python-docx==1.1.2
anthropic==0.103.1
python-dotenv==1.2.2
tenacity==9.1.4
jinja2==3.1.6
```

**Addition — append one line** (same `name==version` format, no extras):
```
PyYAML==6.0.3
```
Also add `respx==0.23.1` if not already present (check: not in current file — must add).
```
respx==0.23.1
```

---

### `main.py` (orchestrator — uncomment lines 74-78)

**Analog:** `main.py` itself — lines 74-78 already contain the wiring comment.

**Current state** (`main.py` lines 74-78):
```python
# Phase 3: LLM enrichment (wired in plan 03-01)
# df = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY)
# run_log["api_calls_made"] = ...
# run_log["tokens_used"] = ...
# run_log["fallbacks_triggered"] = ...
```

**Target state** (uncomment + wire tuple return per RESEARCH.md Pattern 6):
```python
# Phase 3: LLM enrichment
from src import llm_engine
df, llm_counts = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY)
run_log["api_calls_made"] = llm_counts["api_calls_made"]
run_log["tokens_used"] = llm_counts["tokens_used"]
run_log["fallbacks_triggered"] = llm_counts["fallbacks_triggered"]
logger.info(
    f"LLM enrichment complete — "
    f"api_calls={llm_counts['api_calls_made']}, "
    f"fallbacks={llm_counts['fallbacks_triggered']}"
)
```
Note: The import `from src import llm_engine` should move to the top-level imports block (lines 11-13) alongside the existing `from src import config as cfg` and `from src.ingestion import ingest` — not inline.

**run_log schema** (`main.py` lines 45-53 — reference for key names):
```python
run_log: dict[str, object] = {
    "run_timestamp": ...,
    "students_processed": 0,
    "api_calls_made": 0,           # ← Phase 3 writes this
    "tokens_used": {"input": 0, "output": 0},   # ← Phase 3 writes this
    "errors_encountered": [],
    "fallbacks_triggered": 0,      # ← Phase 3 writes this
    "data_quality_warnings": [],
}
```

---

## Shared Patterns

### df.copy() at Function Entry (Purity Discipline)
**Source:** `src/risk_engine.py` line 150
**Apply to:** `src/llm_engine.py` — first statement in `enrich_with_llm()`
```python
df = df.copy()  # Purity guarantee — preserves df.attrs in pandas 2.2.3 (Pitfall 8)
```

### logger = logging.getLogger(__name__)
**Source:** `src/risk_engine.py` line 21, `src/ingestion.py` line 22, `src/config.py` line 17
**Apply to:** `src/llm_engine.py` — module level, after imports
```python
logger = logging.getLogger(__name__)
```
Zero print statements anywhere. This is the only logging setup needed per module.

### All Column Names via cfg.COL_*
**Source:** `src/risk_engine.py` lines 159-196 (every df[] access)
**Apply to:** `src/llm_engine.py` — every DataFrame column access
```python
# Correct:
df[cfg.COL_GENERATED_BY] = "llm"
df.loc[idx, cfg.COL_FACILITATOR_SUMMARY] = text

# Wrong — never:
df["generated_by"] = "llm"
```

### os.getenv Pattern for Optional Config
**Source:** `src/config.py` lines 35-36
**Apply to:** New D-09 constants in `src/config.py`
```python
# Boolean from env string — the ONLY correct pattern (not bool(os.getenv(...)))
LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
# int from env
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))
# float from env
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
```

### PII-Safe Logging
**Source:** `src/risk_engine.py` lines 198-205 (aggregate log only)
**Apply to:** All `logger.*` calls in `src/llm_engine.py`
```python
# Correct — aggregate only, no student identifiers:
logger.info(f"Processing campus {campus_id} — {len(chunk)} students in chunk")
logger.debug(f"Student [STUDENT] processed (campus {campus_id})")

# Wrong — never log these:
# logger.debug(f"Processing {row[cfg.COL_STUDENT_NAME]}")
# logger.debug(f"Phone: {row[cfg.COL_PARENT_PHONE]}")
# logger.debug(f"API key: {api_key}")
```

### conftest.py Dummy API Key Guard
**Source:** `tests/conftest.py` line 15
**Apply to:** `tests/test_llm_engine.py` — no action needed, already handled
```python
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")
# This runs before any src.config import in all test files — no per-test setup needed
```

### pytest Fixture Scope
**Source:** `tests/conftest.py` lines 20-45, `tests/test_risk_engine.py` lines 24-59
**Apply to:** `tests/test_llm_engine.py`
- Use module-level `_build_student_row()` helper (not a `@pytest.fixture`) — same pattern as `test_risk_engine.py`
- `respx_mock` is a pytest fixture provided by the `respx` library — no setup needed
- `caplog` is a pytest built-in — use `caplog.at_level(logging.DEBUG, logger="src.llm_engine")`

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/llm_templates.yaml` | config | — | No YAML files exist in codebase — first YAML resource. Use RESEARCH.md Pattern 5 structure directly. Verify with `yaml.safe_load()` smoke test in Wave 0. |

---

## Critical Implementation Notes for Planner

### Signature Contract Conflict (RESEARCH.md Open Question 1 / A6)
The locked `STATE.md` signature is `enrich_with_llm(df, api_key) -> DataFrame`. RESEARCH.md Pattern 6 recommends returning `tuple[pd.DataFrame, dict]` instead. The planner must:
1. Update `STATE.md` module contract to reflect `-> tuple[pd.DataFrame, dict]`
2. Update `main.py` to unpack the tuple (pattern shown above)
3. Note: existing callers that only check `df = enrich_with_llm(...)` will break — there are no such callers yet (stub not wired), so this is safe

### respx Injection Requires Signature Extension (RESEARCH.md Open Question 2 / A3-A4)
To make `enrich_with_llm()` testable without real HTTP calls, the function must accept an injectable `http_client` parameter:
```python
def enrich_with_llm(
    df: pd.DataFrame,
    api_key: str,
    http_client: httpx.Client | None = None,   # None = production default
) -> tuple[pd.DataFrame, dict]:
```
In production: `http_client=None` → `anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=cfg.TIMEOUT_SECONDS)`
In tests: `http_client=httpx.Client(transport=respx_mock)` → `anthropic.Anthropic(api_key="test-key", http_client=http_client, max_retries=0)`

### Sort Order for CRITICAL-First (RESEARCH.md Pitfall 2)
`df.sort_values(by=["risk_level", "risk_score"], ascending=[True, False])` puts HIGH before CRITICAL alphabetically. Use a key mapping:
```python
campus_students = at_risk_df.sort_values(
    by=[cfg.COL_RISK_LEVEL, cfg.COL_RISK_SCORE],
    ascending=[True, False],
    key=lambda col: col.map({"CRITICAL": 0, "HIGH": 1}) if col.name == cfg.COL_RISK_LEVEL else col
)
```

### ToolUseBlock Attribute Verification (RESEARCH.md A1/A2)
Add a Wave 0 task to verify: `py -3.12 -c "import anthropic; print(dir(anthropic.types.ToolUseBlock))"` confirms `.input` is a plain dict, not Pydantic. Guard with `try/except KeyError` regardless.

---

## Metadata

**Analog search scope:** `src/`, `tests/`, `main.py`, `requirements.txt`
**Files scanned:** 7 (`src/config.py`, `src/risk_engine.py`, `src/ingestion.py`, `src/llm_engine.py`, `tests/test_risk_engine.py`, `tests/conftest.py`, `requirements.txt`, `main.py`)
**Pattern extraction date:** 2026-05-23
