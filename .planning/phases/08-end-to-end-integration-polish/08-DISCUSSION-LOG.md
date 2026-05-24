# Phase 8: End-to-End Integration + Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 08-end-to-end-integration-polish
**Areas discussed:** End-to-end run scope, requirements-dev.txt gap, print() in generate_data.py, Submission polish scope

---

## End-to-End Run Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full live run | Run `python main.py` with real API key, verify all 14 output types produced | ✓ |
| Verify existing outputs only | Trust prior run outputs, skip re-running, no API cost | |
| Live run + fresh data regeneration | Regenerate synthetic data first, then run full pipeline | |

**User's choice:** Full live run (Recommended)

**Follow-up — what to do with outputs:**

| Option | Description | Selected |
|--------|-------------|----------|
| Commit demo outputs to repo | All outputs committed; reviewer can open files without running pipeline | ✓ |
| Leave outputs gitignored | Reviewer must run pipeline locally | |
| Commit a subset only | Only key files, skip 20 campus Excel files | |

**User's choice:** Commit demo outputs to the repo (Recommended)

**Notes:** outputs/ is listed as a required submission deliverable. Committing fresh run outputs satisfies both the technical success criterion and the reviewer UX requirement.

---

## requirements-dev.txt Gap

| Option | Description | Selected |
|--------|-------------|----------|
| Create requirements-dev.txt | Standard Python separation of prod/dev deps; `make install` works on fresh clone | ✓ |
| Move pytest into requirements.txt | Simpler but blurs prod/dev boundary | |
| Remove requirements-dev.txt from Makefile | Minimal; leaves install incomplete | |

**User's choice:** Create requirements-dev.txt (Recommended)

**Follow-up — what packages:**

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal test deps only | pytest, pytest-anyio, respx, freezegun — exactly what the test suite uses | ✓ |
| Test deps + linting | Add mypy and ruff/flake8 | |
| You decide | Claude picks the minimal set | |

**User's choice:** Minimal test deps only (Recommended)

**Notes:** Linting tools noted as deferred — not in scope for Phase 8.

---

## print() in generate_data.py

| Option | Description | Selected |
|--------|-------------|----------|
| Fix it — convert to logging | Replace print() with logger.info(); clean zero-print rule across whole codebase | ✓ |
| Carve out an exception for scripts | Document that no-print rule applies to library modules only | |
| You decide | Claude applies whichever is more defensible | |

**User's choice:** Fix it — convert to logging (Recommended)

**Notes:** The "no print statements" success criterion is explicit and applies codebase-wide. No carve-outs.

---

## Submission Polish Scope

**Multi-select — all selected:**

| Option | Description | Selected |
|--------|-------------|----------|
| .env.example placeholder | Replace real API key with `sk-ant-REPLACE-WITH-YOUR-KEY` | ✓ |
| README review | Verify Quick Start matches actual project structure | ✓ |
| analysis.md real numbers | Confirm real pipeline numbers, not placeholders | ✓ |
| docs/ verification | Confirm all 8 .docx files exist and open without errors | ✓ |

**Follow-up — HTML dashboard UI check:**

| Option | Description | Selected |
|--------|-------------|----------|
| Manual browser check + document result | Open in Chrome, test filters/copy button at 1280/1920px, document result | ✓ |
| Skip — trust existing tests | test_output_generator.py covers dashboard generation | |
| Add automated UI test | playwright/selenium for viewport check | |

**User's choice:** Manual browser check + document result (Recommended)

**Notes:** Automated UI testing noted as deferred (adds complexity and scope).

---

## Claude's Discretion

- Exact package versions for `requirements-dev.txt` — match currently installed working environment
- Order of tasks within the plan — code fixes first, then live run, then commit outputs
- How to handle the 20-campus dashboard count (data generates 20 campuses; this is correct behavior)

## Deferred Ideas

- mypy + ruff linting added to Makefile — deferred, out of Phase 8 scope
- Automated playwright/selenium UI tests — deferred
- Phase 9 web application — noted in ROADMAP post-v1 backlog
