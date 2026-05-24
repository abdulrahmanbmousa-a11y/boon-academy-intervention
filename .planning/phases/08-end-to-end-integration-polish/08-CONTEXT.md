# Phase 8: End-to-End Integration + Polish - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 8 delivers a fully verified, submission-ready repository: a live `python main.py`
run on fresh synthetic data produces all 14 output/doc types cleanly, all quality gates
pass (tests, code review, UI check), demo outputs are committed, and the repo runs
correctly from a fresh clone.

**This phase verifies the complete system — no new requirement IDs are introduced.**

**Out of scope:** New pipeline features, automated UI testing tools (playwright/selenium),
adding linting tools (mypy/ruff) to the Makefile, web app functionality.

</domain>

<decisions>
## Implementation Decisions

### End-to-End Run (D-01, D-02)
- **D-01:** Run a full live pipeline — `python -m src.generate_data` then `python main.py`
  with a real API key. This satisfies success criterion 1 literally: fresh data in, all
  14 output types produced, pipeline completes without errors. Existing outputs/ contents
  do NOT count as verification — a fresh run is required.
- **D-02:** Commit all demo outputs to the repo after the verified run. The submission
  checklist identifies `outputs/` as a required deliverable. A reviewer must be able to
  open the files without running the pipeline themselves.

### requirements-dev.txt (D-03, D-04)
- **D-03:** Create `requirements-dev.txt` with the minimal test dependency set:
  `pytest`, `pytest-anyio` (async), `respx` (API mocking), `freezegun` (time mocking).
  Exactly what the current test suite already uses — nothing extra.
- **D-04:** Do NOT add linting tools (mypy, ruff) to requirements-dev.txt. That's scope
  creep for this phase. `make install` will work from a fresh clone once D-03 is done.

### print() Rule (D-05)
- **D-05:** Fix `src/generate_data.py:322` — replace `print()` with `logger.info()` or
  equivalent. The "no print statements" success criterion applies to the whole codebase
  including CLI scripts. No carve-outs.

### Submission Polish (D-06, D-07, D-08, D-09, D-10)
- **D-06:** Replace the real API key in `.env.example` with a placeholder:
  `ANTHROPIC_API_KEY=sk-ant-REPLACE-WITH-YOUR-KEY`. The current file has an actual key
  value — this fails the "no hardcoded API keys" code review criterion and is a
  security issue.
- **D-07:** Review README for correctness: Quick Start steps (pip install, .env setup,
  python main.py) must match the actual project structure. Fix any stale instructions.
- **D-08:** Verify `analysis.md` has real pipeline numbers (student counts, risk
  distributions, API call counts, token usage) from the fresh live run. If it has
  placeholder values, update them with real data.
- **D-09:** Verify all 8 `.docx` files exist in `docs/` and open without errors in
  Google Docs. Phase 6 generated them — Phase 8 confirms they are present and not
  corrupted.
- **D-10:** Manual HTML dashboard UI check: open `outputs/facilitator_dashboard.html`
  in Chrome, test campus filter, risk filter, copy button, and layout at 1280px and
  1920px viewport widths. Document the result (pass/fail) in the verification record.

### Claude's Discretion
- Exact package versions to pin in `requirements-dev.txt` — match whatever is already
  installed and working in the current environment.
- Order of tasks within the plan — the live run should happen after all code fixes so
  outputs reflect the final polished code.
- How to handle the 20-campus dashboard count in outputs/ (data generates 20 campuses;
  this is fine as long as all files open correctly).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 8 Requirements and Success Criteria
- `.planning/ROADMAP.md` §Phase 8 — 5 success criteria (the authoritative pass/fail gate)
- `.planning/REQUIREMENTS.md` — full v1 requirement IDs being verified

### Code Standards (apply to all fixes)
- `CLAUDE.md` §Code Standards — type hints on all functions, docstrings on public classes
  and methods, no print statements, all column names as constants, all paths from env vars
- `CLAUDE.md` §Critical Pitfalls — openpyxl color format, HTML JSON injection safety,
  `os.environ` vs `os.getenv`, `dtype` in read_csv

### Source Modules Being Verified
- `main.py` — pipeline orchestrator (ingest → score_risk → enrich_with_llm → write_outputs → write_docs)
- `src/config.py` — all env vars, column constants, color constants
- `src/generate_data.py` — synthetic data generator (has print() to fix at line 322)
- `src/ingestion.py` — CSV ingestion
- `src/risk_engine.py` — deterministic risk scoring
- `src/llm_engine.py` — Claude API integration with three-layer fallback
- `src/output_generator.py` — all 6 output files
- `src/doc_generator.py` — all 8 documentation files

### Infrastructure Files Being Fixed/Created
- `requirements.txt` — pinned prod dependencies (already correct)
- `requirements-dev.txt` — to be CREATED with pytest, pytest-anyio, respx, freezegun
- `Makefile` — `make install`, `make demo`, `make test`, `make clean` targets
- `.env.example` — to be FIXED: replace real API key with placeholder

### Existing Test Infrastructure
- `tests/` — 114 tests passing across test_config.py, test_ingestion.py,
  test_risk_engine.py, test_llm_engine.py, test_output_generator.py,
  test_doc_generator.py, conftest.py

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `output_generator.write_outputs()` — writes all 6 output types to a given dir; already wired in main.py
- `doc_generator.write_docs()` — writes all 8 doc files to DOCS_DIR; already wired in main.py
- `src/generate_data.py main()` — generates all 3 CSVs; invoked via `python -m src.generate_data`
- `Makefile demo` target — already chains generate_data + main.py in the right order

### Established Patterns
- `logging.getLogger(__name__)` throughout — generate_data.py fix must use the same pattern
- All paths derived from `cfg.*_DIR` constants — no hardcoding anywhere in src/
- `os.environ["KEY"]` for required secrets (fail-loud), `os.getenv("KEY", default)` for optional

### Integration Points
- `make demo` = `python -m src.generate_data && python main.py` — this is the fresh-run command
- `make test` = `pytest tests/ -v` — this is the test gate command
- `make install` currently fails on fresh clone because `requirements-dev.txt` doesn't exist

### Known Issues to Fix
1. `src/generate_data.py:322` — `print()` → convert to `logger.info()` or `logger.warning()`
2. `.env.example` — real API key → replace with `sk-ant-REPLACE-WITH-YOUR-KEY`
3. `requirements-dev.txt` — missing → create with test deps
4. `docs/` contents — need verification that all 8 .docx files exist from Phase 6

</code_context>

<specifics>
## Specific Ideas

- **Live run sequence:** Fix code issues first → then run `make demo` → verify 14 output
  types → commit outputs. This ensures demo outputs reflect the polished codebase.
- **requirements-dev.txt format:** Mirror the style of requirements.txt — pinned versions,
  one package per line, brief comment at top.
- **generate_data.py print() fix:** The print() at line 322 is likely in the `main()` function
  reporting completion. Replace with `logger.info("Generated synthetic data: ...")` using the
  module-level `logger = logging.getLogger(__name__)`.
- **Code review scan:** Run `grep -rn "print(" src/ main.py` to confirm zero prints after fix.
  Run `grep -rn "sk-ant\|api_key\s*=" .env.example` to confirm no hardcoded keys.
- **Verification record:** Success criterion 5 (HTML UI check) result should be documented
  — a brief note in the commit message or a VERIFICATION.md is sufficient.

</specifics>

<deferred>
## Deferred Ideas

- Adding mypy + ruff linting to the Makefile — valuable but out of scope for Phase 8
- Automated playwright/selenium UI tests for the HTML dashboard — mentioned and deferred
- Phase 9 web application — noted in ROADMAP post-v1 backlog

</deferred>

---

*Phase: 8-End-to-End Integration + Polish*
*Context gathered: 2026-05-25*
