# Phase 7: Test Suite - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 delivers a passing pytest suite with 0 failures and 0 errors: four test files
(`test_risk_engine.py`, `test_ingestion.py`, `test_llm_engine.py`, `test_output_generator.py`)
satisfy TEST-01..TEST-04 requirements. Existing test files are extended and fixed — not
rewritten from scratch. `pytest --collect-only` already shows 50+ collected tests; this phase
fills gaps and repairs failures.

**Out of scope:** `test_doc_generator.py` (Phase 6 code) — not in TEST-01..04.
`test_config.py`, `test_generate_data.py`, `test_package_structure.py`, `test_no_hardcoded_paths.py`
may be fixed if they fail, but are not primary targets.

</domain>

<decisions>
## Implementation Decisions

### Audit and Run Strategy (D-01..D-03)

- **D-01:** Run `py -3.12 -m pytest tests/ -v` first to establish a baseline failure list before
  touching any code. Fix only real failures; do not pre-emptively rewrite passing tests.
- **D-02:** Fix priority: TEST-01..TEST-04 requirement gaps first. All other test failures
  (test_config, test_generate_data, etc.) are fixed second.
- **D-03:** Test function names must be explicit and traceable to requirements. Use names like
  `test_score_75_is_critical`, `test_score_74_is_high`, `test_empty_csv_does_not_crash`,
  `test_duplicate_student_ids_deduplicated`. Rename vaguely named functions if they cover these cases.

### Output Test Isolation (D-04..D-06)

- **D-04:** All `test_output_generator.py` tests that write files use pytest's `tmp_path` fixture.
  Each test gets a fresh temp directory; files are cleaned up automatically. Never write to `outputs/`
  in tests.
- **D-05:** Shared minimal DataFrame fixture in `conftest.py` — built inline (no file I/O), 5-10 rows,
  2 campuses, all required columns present (student_id, name, campus, risk_score, risk_level,
  message_text, generated_by, parent_phone, recommended_action, etc.). This fixture is used by both
  output_generator and llm_engine tests.
- **D-06:** One integration-style test (`test_all_6_output_files_exist`) calls `write_outputs()` end-to-end
  and asserts all 6 file paths exist in `tmp_path`. This is the primary TEST-04 assertion. Separate
  per-column and per-color tests may already exist and are retained.

### respx Injection Pattern (D-07..D-09)

- **D-07:** Add optional `client=None` parameter to `enrich_with_llm(df, client=None)`. When `client`
  is `None`, the function creates `Anthropic()` internally as before. Tests pass a pre-built respx
  client: `Anthropic(http_client=respx_mock, max_retries=0)`. No production code path changes.
- **D-08:** Fallback test (`test_fallback_to_template`) simulates an HTTP 500 from the Anthropic
  endpoint via respx. SDK raises an exception → three-layer fallback uses template → assert
  `generated_by == "template"` and `message_text` is non-empty for every CRITICAL/HIGH row.
  `max_retries=0` on the client is required to prevent SDK retry loops masking the assertion.
- **D-09:** Batching test (`test_campus_batching`) asserts call count: given CRITICAL/HIGH students
  across 2 distinct campuses, exactly 2 API calls are made (one per campus, not per student).
  Verify via `respx_mock.calls` length.

### Claude's Discretion

- Whether to use `@pytest.fixture(scope="session")` vs `scope="function"` for the shared DataFrame
  fixture — choose based on what's safest given the tests' mutation behavior.
- How to handle env var setup in tests that import `src/config.py` (which calls `os.environ["KEY"]`
  at import time) — use `monkeypatch.setenv` or `os.environ` patching in conftest, whichever is
  already established in the existing conftest.py.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 7 Requirements and Success Criteria
- `.planning/REQUIREMENTS.md` §TEST-01 through TEST-04 — exact test cases required per file
- `.planning/ROADMAP.md` §Phase 7 — 5 success criteria with exact assertions (score==75/74, 8-char hex, etc.)

### Source Modules Under Test
- `src/risk_engine.py` — formula weights, threshold logic, `score_risk()` function
- `src/ingestion.py` — `load_data()` merge/dedup/fillna logic
- `src/llm_engine.py` — `enrich_with_llm()` function signature (to add `client=None` param)
- `src/output_generator.py` — `write_outputs()` orchestrator and all 6 file writers
- `src/config.py` — `RISK_THRESHOLD_CRITICAL`, `RISK_THRESHOLD_HIGH` constants; env var loading

### Existing Test Infrastructure
- `tests/conftest.py` — existing fixtures; extend here for the shared DataFrame fixture (D-05)
- `tests/fixtures/` — existing fixture files; check before adding new ones

### Critical Pitfalls
- `CLAUDE.md` §Critical Pitfalls — respx pattern (`Anthropic(http_client=..., max_retries=0)`),
  openpyxl 8-char hex (`"00FFCCCC"` not `"FFCCCC"`), `py -3.12` required
- `.planning/STATE.md` §Known Pitfalls — `respx` not `responses`; `tool_choice` parse pattern;
  `yaml.safe_load()` not `yaml.load()`

### Code Standards
- `CLAUDE.md` §Code Standards — type hints on all functions, docstrings on public methods,
  no print statements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py`: Already has shared fixtures — extend it with the minimal DataFrame fixture
  rather than creating per-file fixtures.
- `tests/fixtures/`: Existing fixture directory — check for pre-baked CSVs before adding new ones.
- All 4 primary test files already exist with 50+ collected tests — run baseline before touching.

### Established Patterns
- `py -3.12` invocation: pandas 2.2.3 has no wheel for Python 3.14 (system default). All pytest
  runs must use `py -3.12 -m pytest` or `python3.12 -m pytest`.
- respx mocking: `httpx.Client(transport=respx_mock)` injected via `Anthropic(http_client=..., max_retries=0)`.
  The `responses` library silently misses httpx calls — never use it here.
- openpyxl color assertions: `cell.fill.fgColor.rgb` returns 8-char hex with alpha prefix
  (e.g., `"00FFCCCC"`). Assert the full 8-char string.

### Integration Points
- `enrich_with_llm()` in `src/llm_engine.py` needs `client=None` param added (D-07) — this is
  the only production source change Phase 7 makes.
- `write_outputs()` in `src/output_generator.py` accepts `output_dir` param — pass `tmp_path`
  from pytest fixture to isolate file writes (D-04).

</code_context>

<specifics>
## Specific Ideas

### Exact Boundary Values (from ROADMAP success criteria)
- `score == 75` → `risk_level == "CRITICAL"` (test name: `test_score_75_is_critical`)
- `score == 74` → `risk_level == "HIGH"` (test name: `test_score_74_is_high`)
- These exact values must be asserted, not approximated.

### TEST-02 Required Cases
- Missing numeric values filled with 0 (not NaN, not dropped)
- Duplicate `student_id` rows → deduplicated to 1 row
- Empty CSV → does not crash, returns valid (possibly empty) DataFrame
- Bad date format → safe default applied (not exception)
- Type mismatch → coerced or safe default (not exception)

### TEST-03 Token Logging
- Mock a successful API call (200 response with valid tool_use block)
- Assert that token counts appear in log output (use `caplog` pytest fixture)

### TEST-04 Excel Color
- Assert `PatternFill` `fgColor.rgb` == `"00FFCCCC"` for CRITICAL rows (8-char hex with alpha)
- This assertion is already established in prior phases as the canonical color check format.

</specifics>

<deferred>
## Deferred Ideas

- `test_doc_generator.py` — tests for Phase 6's `src/doc_generator.py`. Out of scope for Phase 7
  (not in TEST-01..04). Could be added in Phase 8 polish if needed.

</deferred>

---

*Phase: 7-Test Suite*
*Context gathered: 2026-05-24*
