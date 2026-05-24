# Phase 7: Test Suite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 7-Test Suite
**Areas discussed:** Audit vs run-first strategy, Output test isolation, respx injection pattern

---

## Audit vs Run-First Strategy

**Q1: How should we establish what's missing?**

| Option | Description | Selected |
|--------|-------------|----------|
| Run pytest first | Run py -3.12 -m pytest tests/ -v and see what fails. Fix only real failures. | ✓ |
| Audit files against spec first | Read each test file against TEST-01..04, list gaps, then implement. | |
| Both — run first, then audit | Run pytest for baseline, then audit for cases that pass vacuously. | |

**User's choice:** Run pytest first
**Notes:** Ground-truth approach — don't pre-emptively rewrite passing tests.

---

**Q2: When pytest reveals failures, what's the priority order?**

| Option | Description | Selected |
|--------|-------------|----------|
| TEST-01..04 gaps first, then anything else | Focus on the 4 required requirement IDs first. | ✓ |
| All failures equally | Every test must pass — no distinction. | |
| You decide | Leave priority to planner. | |

**User's choice:** TEST-01..04 gaps first, then anything else

---

**Q3: Acceptable if behavior matches but function name differs?**

| Option | Description | Selected |
|--------|-------------|----------|
| Behavior matters, not name | Assertion exists = requirement met. | |
| Name it explicitly | Use names like test_score_75_is_critical so requirements are traceable. Rename if needed. | ✓ |

**User's choice:** Name it explicitly

---

## Output Test Isolation

**Q1: How should test_output_generator.py set up its environment?**

| Option | Description | Selected |
|--------|-------------|----------|
| pytest tmp_path | Each test gets a fresh temp dir, automatic cleanup, no env var pollution. | ✓ |
| Shared temp dir in conftest | One temp dir per session; simpler but tests can interfere. | |
| Use real outputs/ dir | Write to actual outputs/ dir; no isolation. | |

**User's choice:** pytest tmp_path

---

**Q2: Where should the test DataFrame come from?**

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal inline fixture in conftest.py | Small DataFrame built inline (5-10 rows, 2 campuses). No file I/O, fast, deterministic. | ✓ |
| Run ingestion + risk engine to build it | Use real pipeline functions. More realistic but slower. | |
| Load from tests/fixtures/ CSV files | Pre-baked CSVs. Portable but another file to maintain. | |

**User's choice:** Minimal inline fixture in conftest.py

---

**Q3: One integration test for all 6 files, or 6 separate tests?**

| Option | Description | Selected |
|--------|-------------|----------|
| One integration-style test for all 6 | Calls write_outputs() end-to-end, asserts all 6 files exist. | ✓ |
| 6 separate unit tests per file | More granular failures but diverges from success criterion wording. | |
| You decide | Let planner choose based on existing test structure. | |

**User's choice:** One integration-style test for all 6

---

## respx Injection Pattern

**Q1: How should enrich_with_llm() accept a testable client?**

| Option | Description | Selected |
|--------|-------------|----------|
| Optional client param: enrich_with_llm(df, client=None) | Tests pass respx client; production passes None, function creates its own. | ✓ |
| Module-level client singleton, patch in tests | Module creates client at import; tests monkeypatch it. Fragile. | |
| You decide | Let researcher check existing test and propose fix. | |

**User's choice:** Optional client param

---

**Q2: What failure scenario for the fallback test?**

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP 500 from Anthropic endpoint | respx returns 500, SDK raises exception, template fallback. Most realistic. | ✓ |
| Network timeout (ConnectionError) | respx raises httpx.ConnectError. Tests network-failure branch. | |
| Malformed/empty tool response | API returns 200 but no tool_use block. Parse-failure branch. | |

**User's choice:** HTTP 500

---

**Q3: What should the batching test assert?**

| Option | Description | Selected |
|--------|-------------|----------|
| One API call per campus | With students across 2 campuses, assert exactly 2 calls via respx_mock.calls length. | ✓ |
| Students grouped by campus in payload | Inspect request body for all students from same campus in one call. | |
| You decide | Let researcher check existing test_campus_batching. | |

**User's choice:** One API call per campus (call count assertion)

---

## Claude's Discretion

- `pytest.fixture` scope (`session` vs `function`) for the shared DataFrame fixture — choose based on mutation safety.
- Env var setup strategy in conftest.py for `src/config.py` import-time `os.environ["KEY"]` calls — use existing pattern already in conftest.

## Deferred Ideas

- `test_doc_generator.py` for Phase 6's `src/doc_generator.py` — noted for potential Phase 8 polish, out of scope for Phase 7.
