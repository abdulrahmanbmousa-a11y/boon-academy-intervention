---
phase: 03-claude-api-integration
plan: "03"
subsystem: api
tags: [main, wiring, test, respx, llm, fallback, batching, pii-safe]

requires:
  - phase: 03-claude-api-integration
    plan: "01"
    provides: 9 D-09 constants in config.py + src/llm_templates.yaml + tuple return contract
  - phase: 03-claude-api-integration
    plan: "02"
    provides: Full enrich_with_llm() implementation in src/llm_engine.py

provides:
  - main.py with enrich_with_llm() wired at Phase 3 section; from src import llm_engine import added
  - run_log["api_calls_made"], run_log["tokens_used"], run_log["fallbacks_triggered"] populated from llm_counts
  - tests/test_llm_engine.py: 12 tests covering all 9 LLM requirements (LLM-01 through LLM-09)
  - Confirmed httpx.MockTransport(respx_mock.handler) as the correct respx 0.23.1 injection pattern

affects:
  - Phase 4 (Excel + CSV Output Generation) — main.py pipeline now complete through Phase 3
  - tests/ — full suite is now 65 tests (53 + 12 new)

tech-stack:
  added: []
  patterns:
    - httpx.MockTransport(respx_mock.handler) — correct respx 0.23.1 transport injection (NOT httpx.Client(transport=respx_mock) which fails since MockRouter is not a transport)
    - monkeypatch.setattr(cfg, "LLM_ENABLED", False) — patches module attribute directly for LLM_ENABLED bypass test
    - monkeypatch.setattr(anthropic_module, "Anthropic", FakeClass) — captures constructor kwargs for max_retries assertion
    - respx_mock.post(URL).mock(side_effect=[R1, R2]) — sequential response list for multi-campus test
    - respx_mock.post(URL).mock(side_effect=callable) — dynamic response generation for chunk-size test

key-files:
  created: [tests/test_llm_engine.py]
  modified: [main.py]

key-decisions:
  - "httpx.MockTransport(respx_mock.handler) not httpx.Client(transport=respx_mock) — respx_mock is a MockRouter (not a transport); RESEARCH.md Pattern 4 was incorrect for respx 0.23.1; deprecated MockTransport(router=) also works but emits DeprecationWarning"
  - "test_no_bare_column_strings_in_llm_engine uses expanded allowed set — unavoidable JSON Schema vocabulary, Anthropic message structure keys, and return dict keys are all present in llm_engine.py post-stripping; allowed set explicitly excludes all 24 known column name values from config.py"
  - "test_chunk_size_limit uses callable side_effect — parses student_ids from prompt text to build per-chunk responses dynamically, avoiding hardcoded list of 15 student responses"
  - "from src import llm_engine placed in top-level imports block — not inline at Phase 3 section, per CLAUDE.md/PATTERNS.md guidance"

metrics:
  duration: ~20min
  completed: 2026-05-23
  tasks: 2/2
  files_modified: 2
---

# Phase 3 Plan 03: main.py Wiring + LLM Test Suite Summary

**main.py wired with enrich_with_llm() tuple unpack and run_log population; 12-test suite in tests/test_llm_engine.py covers all LLM-01 through LLM-09 requirements using the correct respx 0.23.1 MockTransport injection pattern**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-23T11:25:00Z
- **Completed:** 2026-05-23T11:45:00Z
- **Tasks:** 2 / 2
- **Files modified:** 2 (main.py created/modified; tests/test_llm_engine.py created)

## Accomplishments

- Added `from src import llm_engine` to main.py top-level imports block (after `from src.risk_engine import score_risk`)
- Replaced 5-line Phase 3 comment stub in main.py with live wiring:
  - `df, llm_counts = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY)`
  - `run_log["api_calls_made"] = llm_counts["api_calls_made"]`
  - `run_log["tokens_used"] = llm_counts["tokens_used"]`
  - `run_log["fallbacks_triggered"] = llm_counts["fallbacks_triggered"]`
  - `logger.info(...)` with aggregate counts only (no PII, T-03-08)
- Created tests/test_llm_engine.py (597 lines) with 12 test functions:
  - `test_medium_low_students_skipped` — LLM-01: MEDIUM/LOW get None in all 4 output columns, 0 API calls
  - `test_campus_batching` — LLM-02: two-campus cohort produces exactly 2 API calls
  - `test_tool_use_structured_output` — LLM-03: success path sets generated_by='llm' with content
  - `test_max_retries_config` — LLM-04: production Anthropic client has max_retries=3
  - `test_fallback_to_template` — LLM-05: timeout causes generated_by='template' with error reason
  - `test_token_logging` — LLM-06: input_tokens=150, output_tokens=80 accumulated in counts dict
  - `test_api_key_not_in_logs` — LLM-07: "SUPERSECRETKEY123" absent from all caplog records
  - `test_pii_not_in_logs` — LLM-08: student_name and parent_phone absent from all logs
  - `test_chunk_size_limit` — LLM-09: 15 students on one campus produces exactly 2 API calls
  - `test_llm_disabled_uses_templates` — D-09: LLM_ENABLED=False path uses templates, 0 API calls
  - `test_malformed_tool_response` — LLM-05: wrong_key in tool input triggers malformed_response fallback
  - `test_no_bare_column_strings_in_llm_engine` — CLAUDE.md: source scan confirms cfg.COL_* usage throughout
- Full test suite: 65 tests passing (53 existing + 12 new), 0 failures

## Task Commits

1. **Task 1: Wire enrich_with_llm into main.py** — `97305ed` (feat)
2. **Task 2: Write tests/test_llm_engine.py — 12 tests** — `9d4e86c` (feat)

## Files Created/Modified

- `main.py` — 5-line comment stub replaced with 9-line live wiring; import added
- `tests/test_llm_engine.py` — new file, 597 lines, 12 test functions

## Decisions Made

- `httpx.MockTransport(respx_mock.handler)` is the correct respx 0.23.1 injection pattern. `respx_mock` (the pytest fixture) is a `MockRouter` object, not an httpx transport — passing it directly to `httpx.Client(transport=...)` silently fails (mock is set up but never called). `MockTransport(router=respx_mock)` also works but emits `DeprecationWarning`. The canonical form per respx 0.23.1 deprecation message is `httpx.MockTransport(respx_mock.handler)`.
- `test_no_bare_column_strings_in_llm_engine` uses an expanded allowed set (23 entries vs the plan's 11). The additional entries cover unavoidable JSON Schema vocabulary (`"type"`, `"object"`, `"array"`, `"string"`, `"description"`, `"required"`, `"properties"`, `"items"`, `"input_schema"`), Anthropic API message structure keys (`"role"`, `"user"`, `"content"`, `"input"`, `"output"`), the tool name (`"generate_interventions"`), and return dict keys (`"api_calls_made"`, `"tokens_used"`, `"fallbacks_triggered"`). These were already documented as unavoidable in 03-02-SUMMARY.md. The test explicitly lists all 24 known column name values and asserts none appear — this is the correct check.
- `test_chunk_size_limit` uses a callable `side_effect` that parses student IDs from the request body to build per-chunk responses dynamically, rather than a static list of 2 pre-built responses. This avoids hardcoding the exact prompt format.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RESEARCH.md Pattern 4 respx injection pattern incorrect for respx 0.23.1**

- **Found during:** Task 2 — test_campus_batching failed with `len(respx_mock.calls) == 0` despite mock being set up
- **Issue:** `httpx.Client(transport=respx_mock)` passes a `MockRouter` object as the transport. `MockRouter` does not implement `httpx.BaseTransport` (it lacks `handle_request()`), so httpx bypasses it silently. The Anthropic SDK's internal httpx client never routes through the mock, causing all Layer 1 calls to fail with `APIStatusError` (SDK retries exhausted) rather than the mocked responses.
- **Fix:** Changed `httpx.Client(transport=respx_mock)` to `httpx.Client(transport=httpx.MockTransport(respx_mock.handler))` throughout test_llm_engine.py (8 test functions). Removed `from respx.transports import MockTransport` import (deprecated form) in favour of `httpx.MockTransport` (canonical form).
- **Files modified:** `tests/test_llm_engine.py`
- **Verification:** `py -3.12 -m pytest tests/test_llm_engine.py -x -q` → 12 passed, 0 warnings
- **Committed in:** `9d4e86c`

**2. [Rule 2 - Missing Critical Functionality] Extended test_no_bare_column_strings_in_llm_engine allowed set to match actual llm_engine.py content**

- **Found during:** Task 2 — source scan test would have failed with the plan-spec allowed set of 11 entries because llm_engine.py legitimately contains JSON Schema vocabulary and Anthropic API structure strings
- **Issue:** Plan spec allowed set: `{"llm","template","llm_disabled","timeout","rate_limit","malformed_response","max_retries_exceeded","students","tool","name","utf"}`. Actual llm_engine.py post-strip contains 27 unique lowercase quoted strings, including `"generate_interventions"`, `"api_calls_made"`, `"tokens_used"`, `"type"`, `"object"`, etc. — none of which are column names.
- **Fix:** Expanded allowed set to 23 entries; added explicit `known_column_values` set (all 24 column name values from config.py) and asserted separately that none of those appear. This makes the test both accurate and descriptive.
- **Files modified:** `tests/test_llm_engine.py`
- **Committed in:** `9d4e86c`

## Known Stubs

None — main.py Phase 3 section is fully wired. Phase 4 section (`write_outputs` commented line) is an intentional stub pending Phase 4 implementation.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced beyond what the plan's threat model documents:
- T-03-08: `logger.info` in main.py Phase 3 section logs only aggregate counts (`api_calls_made`, `fallbacks_triggered`) — no key, no student identifiers. Mitigated.
- T-03-09: conftest.py `setdefault` pattern preserves real key if already set; tests use `respx_mock` transport so "test-key" is never transmitted. Accepted.

## Self-Check

- [x] `main.py` parses: `py -3.12 -c "import ast, pathlib; ast.parse(pathlib.Path('main.py').read_text()); print('syntax OK')"` → syntax OK
- [x] `from src import llm_engine` present in main.py top-level imports
- [x] `llm_engine.enrich_with_llm` present in main.py Phase 3 section
- [x] `llm_counts["api_calls_made"]` wired into run_log
- [x] `llm_counts["tokens_used"]` wired into run_log
- [x] `llm_counts["fallbacks_triggered"]` wired into run_log
- [x] `tests/test_llm_engine.py` exists with 12 test functions
- [x] `py -3.12 -m pytest tests/test_llm_engine.py -x -q` → 12 passed, 0 failures
- [x] `py -3.12 -m pytest tests/ -q` → 65 passed, 0 failures
- [x] Commit `97305ed` exists (Task 1 — main.py)
- [x] Commit `9d4e86c` exists (Task 2 — test_llm_engine.py)
- [x] All 9 LLM-* requirements have at least one passing test

## Self-Check: PASSED

---
*Phase: 03-claude-api-integration*
*Completed: 2026-05-23*
