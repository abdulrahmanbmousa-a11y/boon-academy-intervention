# Phase 3: Claude API Integration - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `src/llm_engine.py` — `enrich_with_llm(df: pd.DataFrame, api_key: str) -> pd.DataFrame` that adds AI-generated facilitator summaries and WhatsApp messages to every CRITICAL and HIGH risk student via campus-batched Claude API calls. Three-layer fallback: HTTP retry (SDK max_retries=3) → re-prompt → rule-based template from YAML. Function **never raises** — pipeline always completes.

- MEDIUM and LOW students are skipped entirely (no API call, no template — None/NaN in all 4 new columns)
- One API call per campus chunk (at most MAX_STUDENTS_PER_LLM_CALL students per call)
- Token usage logged per call into the in-memory run_log dict
- All student names and parent phones masked in log output (PII discipline)
- All constants in `src/config.py`; all column names via `cfg.COL_*`

This phase does NOT write files, does NOT generate Excel/CSV/HTML — it only enriches the in-memory DataFrame.

</domain>

<decisions>
## Implementation Decisions

### Fallback Templates (D-01 through D-03)

- **D-01 (Template storage):** Rule-based fallback templates stored in `src/llm_templates.yaml`, loaded at runtime by `llm_engine.py` using `Path(__file__).parent / "llm_templates.yaml"`. Co-located with the engine that uses it. No env-var path needed — it's a package resource, not user data.

- **D-02 (Template differentiation):** 2 variants by `risk_level` only — one for CRITICAL, one for HIGH. Error type (timeout vs malformed vs max-retries-exceeded) does NOT produce separate variants. Each variant has two sub-keys: `facilitator_summary` and `whatsapp_message`. YAML structure:
  ```yaml
  CRITICAL:
    facilitator_summary: "..."
    whatsapp_message: "..."
  HIGH:
    facilitator_summary: "..."
    whatsapp_message: "..."
  ```

- **D-03 (Template interpolation):** Full Python `.format_map()` interpolation using all scored columns from `score_risk()` output. Available fields: `student_name`, `campus_id`, `facilitator_email`, `risk_score`, `risk_level`, `recommended_action`, `attendance_rate`, `avg_practice_questions`, `trend_direction`, `days_since_last_note`, `attendance_component`, `practice_component`, `trend_component`, `notes_component`. Note: `parent_phone` is intentionally excluded from template interpolation (it is not a scored column and PII discipline applies to log output — but the WhatsApp message text itself goes into the output CSV, which is the intended delivery channel).

### Batch Processing (D-04 through D-05)

- **D-04 (Batch overflow):** When a campus has more than `MAX_STUDENTS_PER_LLM_CALL` (default 10) CRITICAL+HIGH students, make multiple sequential API calls in chunks. Each chunk is an independent API call. Example: 15 students → 2 calls (10 + 5). All CRITICAL/HIGH students receive LLM-generated messages (no truncation).

- **D-05 (Chunk ordering):** Within a campus, sort before chunking: CRITICAL students first (sorted by `risk_score` descending), then HIGH students (sorted by `risk_score` descending). This ensures the most urgent cases land in the first chunk — if later chunks fail, fallback applies only to lower-priority students.

### Output Column Schema (D-06 through D-08)

- **D-06 (New columns):** `enrich_with_llm()` adds exactly 4 new columns:
  - `COL_FACILITATOR_SUMMARY` (`"facilitator_summary"`) — 2-sentence action summary for the facilitator
  - `COL_WHATSAPP_MESSAGE` (`"whatsapp_message"`) — WhatsApp-ready parent message (<100 words)
  - `COL_GENERATED_BY` (`"generated_by"`) — source label: `"llm"` (API succeeded) or `"template"` (fallback used)
  - `COL_LLM_ERROR_REASON` (`"llm_error_reason"`) — error type string for fallback rows (e.g., `"timeout"`, `"malformed_response"`, `"max_retries_exceeded"`); empty string or NaN for successful LLM rows

- **D-07 (MEDIUM/LOW values):** MEDIUM and LOW students: all 4 columns set to `None`/`NaN` (not empty string, not `"skipped"`). Downstream phases null-check `generated_by` to determine whether to display message content.

- **D-08 (generated_by values):** Exactly 2 non-null values: `"llm"` and `"template"`. `None`/`NaN` for MEDIUM/LOW only.

### New Config Constants (D-09)

Add to `src/config.py` (following existing D-07/D-08 patterns):

```python
# LLM tunables — all env-overridable, safe defaults
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "30"))

# New output columns (Phase 3)
COL_FACILITATOR_SUMMARY: str = "facilitator_summary"
COL_WHATSAPP_MESSAGE: str = "whatsapp_message"
COL_GENERATED_BY: str = "generated_by"
COL_LLM_ERROR_REASON: str = "llm_error_reason"
```

`LLM_ENABLED=false` → skip API entirely, use templates for all CRITICAL/HIGH (no API calls, `generated_by: "template"`, `llm_error_reason: "llm_disabled"`).

### Prompt Design (Claude's Discretion)

- Prompt content, tone, and structure left to Claude during implementation
- Hard constraints from requirements: facilitator summary = exactly 2 sentences; WhatsApp message = <100 words
- Student data to include per student in batch prompt: risk_level, risk_score, attendance_rate, avg_practice_questions, trend_direction, days_since_last_note, recommended_action
- Use tool-use / structured output to avoid markdown-wrapped JSON (STATE.md pitfall — "Claude may return markdown-wrapped JSON")
- Do NOT include parent_phone or student_name in the API prompt (PII protection for API transmission)
- Use student_id as identifier within the prompt if individual reference is needed

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 3 Requirements
- `.planning/REQUIREMENTS.md` §LLM-01 to LLM-09 — exact LLM requirements: model, batching, output format, retry, fallback, token logging, PII, configurability

### Locked Module Contract
- `.planning/STATE.md` §Module contracts — `enrich_with_llm(df, api_key) -> DataFrame` never raises; `main.py` integration point at lines 74-78
- `.planning/STATE.md` §Key Decisions — respx (not responses) for mocking, three-layer fallback, campus-level batching rationale

### Input Schema (from Phase 2)
- `.planning/phases/02-risk-scoring-engine/02-CONTEXT.md` — D-08: `recommended_action` column serves as Phase 3 fallback label; full output column list from `score_risk()`
- `src/risk_engine.py` — 11 scored columns added by `score_risk()`, all available as `enrich_with_llm()` input

### Existing Code to Extend
- `src/config.py` — all existing constants; add D-09 constants for Phase 3 before implementing llm_engine.py
- `src/llm_engine.py` — existing stub with locked signature; Phase 3 replaces `raise NotImplementedError("Phase 3")`
- `main.py` — in-memory `run_log` dict initialized at lines 45-53; Phase 3 updates `api_calls_made`, `tokens_used`, `fallbacks_triggered`

### Code Standards
- `CLAUDE.md` — type hints on all functions, docstrings on all public methods, no print statements, all column names as constants, all paths from env vars
- `CLAUDE.md` §Critical Pitfalls — respx for mocking, tool-use to avoid markdown JSON

### Success Criteria
- `.planning/ROADMAP.md` §Phase 3 — 5 success criteria defining "done"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py:22` — `ANTHROPIC_API_KEY` already loaded fail-loud; `MAX_STUDENTS_PER_LLM_CALL` already defined at line 36
- `src/risk_engine.py:113` — `score_risk()` return value is direct input; all 11 scored columns confirmed present
- `src/llm_engine.py` — stub with locked signature and docstring describing intended implementation; replace `raise NotImplementedError("Phase 3")`
- `main.py:45-53` — `run_log` dict schema: `api_calls_made` (int), `tokens_used` (dict with `input`/`output` int keys), `fallbacks_triggered` (int)

### Established Patterns
- `df.copy()` at function entry — purity guarantee, preserves `df.attrs` (Pitfall 8 in CLAUDE.md)
- `logging.getLogger(__name__)` throughout — zero print statements
- All column names via `cfg.COL_*` constants — no bare string literals in logic
- Pure function for `score_risk()` — `enrich_with_llm()` follows same discipline (no I/O, no global state) except for the API call itself
- `pd.StringDtype()` for string columns (not bare `"string"`)

### Integration Points
- `main.py:74-78` — Phase 3 wiring: uncomment `df = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY)` and wire `api_calls_made`, `tokens_used`, `fallbacks_triggered` back into `run_log`
- `run_log` in `main.py` is passed by reference — Phase 3 must update it; return updated counts from `enrich_with_llm()` or accept `run_log` as a mutable parameter (planner to decide)

</code_context>

<specifics>
## Specific Ideas

- Template YAML structure: top-level keys must match `risk_level` values exactly (`CRITICAL`, `HIGH`). Each sub-key: `facilitator_summary` and `whatsapp_message`. Load once at module import, not per-call.
- `LLM_ENABLED=false` flow: set `generated_by="template"`, `llm_error_reason="llm_disabled"`, interpolate templates, skip all API calls. Useful for testing output generation without real API.
- Token accumulation pattern: `run_log["tokens_used"]["input"] += response.usage.input_tokens` after each successful API call.
- PII masking: mask `student_name` as `[STUDENT]` and `parent_phone` as `[PHONE]` in all log statements. Actual student data in DataFrame and output files is NOT masked — only log output is.
- Chunk loop pattern: `for i in range(0, len(campus_students), cfg.MAX_STUDENTS_PER_LLM_CALL): chunk = campus_students.iloc[i:i+MAX_STUDENTS_PER_LLM_CALL]`

</specifics>

<deferred>
## Deferred Ideas

- Arabic/Gulf dialect WhatsApp messages — FUTV2, requires campus-level language config
- Async/concurrent LLM calls for multiple campuses — FUTV2-05, needed only at 5,000+ students
- Per-student API calls instead of campus batching — explicitly out of scope (LLM-02 locks campus batching)

</deferred>

---

*Phase: 3-Claude API Integration*
*Context gathered: 2026-05-23*
