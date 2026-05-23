---
phase: 03-claude-api-integration
plan: "02"
subsystem: api
tags: [anthropic, llm, tool-use, fallback, yaml, batching, pii-safe]

requires:
  - phase: 03-claude-api-integration
    plan: "01"
    provides: 9 D-09 constants in config.py + src/llm_templates.yaml + tuple return contract in STATE.md

provides:
  - Full enrich_with_llm() implementation in src/llm_engine.py
  - Campus-batched Claude API calls via tool-use structured output
  - Three-layer fallback (SDK retry -> re-prompt -> YAML template)
  - LLM_ENABLED=false bypass path for testing without API key
  - INTERVENTION_TOOL module-level constant with generate_interventions schema
  - Tuple return (DataFrame, counts_dict) with api_calls_made, tokens_used, fallbacks_triggered

affects:
  - 03-03 (main.py wiring — unpacks tuple return from enrich_with_llm)
  - tests/test_llm_engine.py (Phase 3 test plan — all LLM-01..09 behaviors now testable)

tech-stack:
  added: []
  patterns:
    - Anthropic client instantiated inside enrich_with_llm() (never at module level — Pitfall 3)
    - tool_choice={'type':'tool','name':'generate_interventions'} forces structured output
    - ToolUseBlock parsing via isinstance(b, anthropic.types.ToolUseBlock) + b.input['students']
    - CRITICAL-first sort using key=lambda col: col.map({'CRITICAL':0,'HIGH':1}) (Pitfall 2)
    - Chunk loop: range(0, len(campus_students), cfg.MAX_STUDENTS_PER_LLM_CALL)
    - _apply_templates() uses cfg.COL_* constants as dict keys throughout
    - _write_results_back() uses cfg.COL_* for all result dict key access

key-files:
  created: []
  modified: [src/llm_engine.py]

key-decisions:
  - "Client instantiation inside function with http_client=None param — injects mock transport in tests (Pitfall 3, Pattern 1)"
  - "INTERVENTION_TOOL uses cfg.COL_STUDENT_ID / cfg.COL_FACILITATOR_SUMMARY / cfg.COL_WHATSAPP_MESSAGE as schema property names — all column names via cfg.COL_*"
  - "student_data prompt list uses cfg.COL_* as dict keys — no bare string column names anywhere in production code"
  - "Layer 2 re-prompt uses same prompt + same tool — simplified in that it is a fresh attempt (not a different prompt structure)"
  - "KeyError/StopIteration from malformed tool response caught at outer except level (after Layer 1 exception handling) — routes directly to Layer 3"
  - "Plan verification script flags JSON Schema vocabulary ('type', 'object', 'required') as bare strings — these are unavoidable in tool schema definition; confirmed zero bare DataFrame column name strings via targeted check"

metrics:
  duration: ~15min
  completed: 2026-05-23
  tasks: 1/1
  files_modified: 1
---

# Phase 3 Plan 02: LLM Engine Implementation Summary

**Full campus-batched enrich_with_llm() implemented with tool-use structured output, three-layer fallback (SDK retry -> re-prompt -> YAML template), PII-safe logging, LLM_ENABLED bypass, and tuple return — replacing the NotImplementedError stub**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-23T11:10:00Z
- **Completed:** 2026-05-23T11:25:00Z
- **Tasks:** 1 / 1
- **Files modified:** 1

## Accomplishments

- Replaced 32-line `NotImplementedError` stub with full 456-line implementation
- `INTERVENTION_TOOL` dict defined at module level with `generate_interventions` tool schema using `cfg.COL_*` constants as property names
- `_TEMPLATES` loaded once at module import via `yaml.safe_load()` (Pattern 5, D-01)
- `_classify_error()` helper: maps `APITimeoutError` -> `"timeout"`, `RateLimitError` -> `"rate_limit"`, others -> `"max_retries_exceeded"`
- `_apply_templates()` helper: uses `cfg.COL_*` as dict keys throughout; `format_map(row.to_dict())` for template interpolation; never logs PII
- `_write_results_back()` helper: uses `df.loc[idx, cfg.COL_*]` for safe row-level assignment; `cfg.COL_*` for result dict key access
- `enrich_with_llm(df, api_key, http_client=None)` public function:
  - `df.copy()` at entry (purity guarantee, mirrors `score_risk()`)
  - Initializes 4 output columns to `None` for all rows (D-07)
  - `LLM_ENABLED=false` early-exit path: applies templates for all CRITICAL/HIGH, 0 API calls
  - Production client: `Anthropic(api_key=api_key, max_retries=3, timeout=cfg.TIMEOUT_SECONDS)`
  - Test client: `Anthropic(api_key=api_key, http_client=http_client, max_retries=0)`
  - CRITICAL-first sort via `map({"CRITICAL":0,"HIGH":1})` key (Pitfall 2, D-05)
  - Campus chunk loop with three-layer fallback per chunk (D-04)
  - Returns `tuple[DataFrame, dict]` with `api_calls_made`, `tokens_used`, `fallbacks_triggered`
- 53 existing tests remain GREEN — zero regressions

## Task Commits

1. **Task 1: Implement src/llm_engine.py — full campus-batched enrichment** - `ed27c76` (feat)

## Files Created/Modified

- `src/llm_engine.py` - Full replacement of 32-line stub with 456-line implementation

## Decisions Made

- `INTERVENTION_TOOL` uses `cfg.COL_STUDENT_ID`, `cfg.COL_FACILITATOR_SUMMARY`, `cfg.COL_WHATSAPP_MESSAGE` as JSON Schema property names — eliminates bare column string literals from the tool schema definition
- `student_data` list passed to the API prompt uses `cfg.COL_*` constants as dict keys — confirmed zero bare DataFrame column name strings via targeted regex check
- Plan's verification script (step 5) flags unavoidable JSON Schema vocabulary (`"type"`, `"object"`, `"required"`, `"description"`, `"items"`, `"array"`, `"string"`) and Anthropic API message structure keys (`"role"`, `"user"`, `"content"`) as bare strings — these cannot be replaced with cfg constants. The targeted check confirms all **DataFrame column names** use `cfg.COL_*` only.
- `_write_results_back()` extracts `result.get(cfg.COL_GENERATED_BY, generated_by)` — works for both LLM results (which have no generated_by key, falling to default `"llm"`) and template results (which carry the key from `_apply_templates`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Extended cfg.COL_* usage to INTERVENTION_TOOL schema and student_data prompt dict**

- **Found during:** Task 1 verification (bare-string check)
- **Issue:** CLAUDE.md mandates "all column names as constants in src/config.py — no hardcoded strings in logic." The initial implementation used bare column name strings as dict keys inside `INTERVENTION_TOOL.input_schema.properties`, `_apply_templates()` result dicts, `_write_results_back()` result dict accesses, and `student_data` prompt dict keys.
- **Fix:** Replaced all bare column name strings with `cfg.COL_*` constants throughout all four locations. The JSON Schema vocabulary strings (`"type"`, `"object"`, `"required"`, `"description"`) are unavoidable structural constants — not column names — and were left as literals.
- **Files modified:** `src/llm_engine.py`
- **Verification:** Targeted regex confirmed zero bare DataFrame column name strings remain.
- **Committed in:** `ed27c76` (same task commit — fixed during implementation before commit)

## Issues Encountered

- Plan's verification script step 5 uses a broad regex that catches all lowercase quoted strings (4+ chars), including JSON Schema vocabulary and Anthropic API message structure strings that are not DataFrame column names. The script's allowed set (`{'llm','template','llm_disabled',...}`) does not include these structural strings. The relevant check (no bare DataFrame column names) passes — confirmed via targeted check against the known set of 24 column name values from config.py.

## Threat Surface Scan

No new network endpoints introduced beyond the Anthropic API call already in the plan's threat model. All mitigations from T-03-03 through T-03-07 are implemented:
- T-03-03: All log statements use aggregate counts only; `student_name`, `parent_phone`, and `api_key` never appear in any logger call
- T-03-04: `student_data` list explicitly excludes `cfg.COL_STUDENT_NAME` and `cfg.COL_PARENT_PHONE`; only non-PII fields sent to API
- T-03-05: `KeyError`/`StopIteration` from `tool_block.input["students"]` caught and routed to Layer 3
- T-03-06: `_apply_templates()` uses `row.to_dict()` (known keys only); no eval(); yaml.safe_load() already in place
- T-03-07: Three-layer fallback ensures pipeline always completes; function never raises

## Known Stubs

None — `enrich_with_llm()` is fully implemented. All CRITICAL/HIGH students receive either LLM-generated or template-generated content. MEDIUM/LOW rows correctly have `None` in all four output columns.

## Self-Check

- [x] `src/llm_engine.py` — imports cleanly: `from src import llm_engine; print('import OK')`
- [x] Signature: `(df: DataFrame, api_key: str, http_client: Optional[httpx.Client] = None) -> tuple[DataFrame, dict]`
- [x] `_TEMPLATES` loaded: `'CRITICAL' in _TEMPLATES and 'HIGH' in _TEMPLATES`
- [x] `INTERVENTION_TOOL['name'] == 'generate_interventions'`
- [x] 53 tests GREEN — `py -3.12 -m pytest tests/ -q` passes
- [x] Zero bare DataFrame column name strings — targeted regex check confirms
- [x] Commit `ed27c76` exists in git log
- [x] `min_lines: 120` requirement met — file is 456 lines

## Self-Check: PASSED

---
*Phase: 03-claude-api-integration*
*Completed: 2026-05-23*
