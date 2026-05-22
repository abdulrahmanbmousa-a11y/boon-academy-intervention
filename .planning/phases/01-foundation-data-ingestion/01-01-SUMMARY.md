---
phase: 01-foundation-data-ingestion
plan: "01"
subsystem: scaffold
tags:
  - scaffolding
  - config
  - env-vars
  - python
  - tdd
dependency_graph:
  requires: []
  provides:
    - src.config (env vars, all column/threshold/weight constants)
    - requirements.txt (pinned production deps)
    - requirements-dev.txt (pinned test deps)
    - src/__init__.py (package marker)
    - tests/__init__.py (package marker)
    - Phase 2/3/4 stub signatures (locked interfaces)
    - main.py orchestrator skeleton with D-05 run_log schema
  affects:
    - All downstream plans (all phases import src.config)
    - Plan 01-02 (generate_data.py uses cfg.DATA_DIR and column constants)
    - Plan 01-03 (ingestion.py uses all column constants from config)
tech_stack:
  added:
    - pandas==2.2.3
    - openpyxl==3.1.5
    - python-docx==1.1.2
    - anthropic==0.103.1
    - python-dotenv==1.2.2
    - tenacity==9.1.4
    - jinja2==3.1.6
    - pytest==8.3.5
    - pytest-mock==3.15.1
    - pytest-cov==7.1.0
    - respx==0.23.1
    - freezegun==1.5.5
    - coverage==7.14.0
  patterns:
    - Fail-loud secret loading via os.environ (D-08)
    - Safe-default optional paths via os.getenv (D-08)
    - In-memory run_log dict accumulated throughout run, written once at end (D-06)
    - All column/threshold/weight constants in single config module (D-07)
    - TDD RED/GREEN cycle for config module tests
key_files:
  created:
    - requirements.txt
    - requirements-dev.txt
    - .env.example
    - .gitignore
    - README.md
    - Makefile
    - make.ps1
    - src/__init__.py
    - src/config.py
    - tests/__init__.py
    - tests/test_config.py
    - tests/test_no_hardcoded_paths.py
    - tests/test_package_structure.py
    - src/risk_engine.py
    - src/llm_engine.py
    - src/output_generator.py
    - main.py
  modified: []
decisions:
  - "D-07: All 17 column constants + risk thresholds + weights in src/config.py from day 1 — single source of truth"
  - "D-08: Only ANTHROPIC_API_KEY uses os.environ (fail-loud); DATA_DIR/OUTPUT_DIR/DOCS_DIR use os.getenv with safe defaults"
  - "D-05: Full run_log.json schema (7 keys) scaffolded in main.py from day 1 even though API fields are empty until Phase 3"
  - "D-06: run_log dict built in-memory throughout pipeline run, written once at end via output_generator — no incremental writes"
  - "Python 3.12 used for test execution: pandas==2.2.3 has no binary wheel for Python 3.14 (system default). Code targets 3.11+ per README; 3.12 satisfies this and is present on the machine."
metrics:
  duration: "~20 minutes"
  completed: "2026-05-22"
  tasks_completed: 3
  tasks_total: 3
  files_created: 17
  files_modified: 0
  tests_added: 8
  tests_passing: 8
---

# Phase 1 Plan 01: Foundation Scaffold Summary

**One-liner:** Project scaffold with fail-loud config (D-08), all 17 column constants (D-07), locked Phase 2/3/4 stubs, and in-memory run_log pattern (D-05/D-06) wired from day 1.

## What Was Built

17 new files delivering the complete project scaffold. The primary deliverable is `src/config.py` as the single source of truth for all env vars, paths, column names, risk thresholds, and weight constants. `main.py` is a pure orchestrator skeleton that scaffolds the D-05 run_log schema in memory. Phase 2/3/4 stubs lock the module interfaces. Tests enforce D-07, D-08, and INFRA-07/09.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| Task 1 | Package legitimacy gate | (human approval — no commit) | 13 PyPI URLs verified |
| Task 2 | Requirements, env template, gitignore, README, Makefile, make.ps1 | 39d7605 | 7 files |
| Task 3 | src/config.py + tests (TDD RED/GREEN) | 55192b5 | 6 files |
| Task 4 | Phase 2/3/4 stubs + main.py skeleton | f33470e | 4 files |

## Verification Results

All plan verification checks passed:

- `pytest tests/ -v` — 8/8 tests pass
- Fail-loud check: `import src.config` without `ANTHROPIC_API_KEY` raises `KeyError`
- Fail-loud check: `import src.config` with `ANTHROPIC_API_KEY` set succeeds
- Stub imports: `from src import risk_engine, llm_engine, output_generator` succeeds
- Each stub raises `NotImplementedError("Phase N")` on call
- No hardcoded `"data"`, `"outputs"`, `"docs"` literals in `src/*.py` outside `config.py`
- `README.md` is 26 lines (limit: 30)
- Makefile uses tab-indented recipes (verified via binary check)
- All constants in `src/config.py` are type-annotated

## Deviations from Plan

### Environment Deviation (Rule 3 — Auto-fixed Blocking Issue)

**Found during:** Task 3 (test execution step)
**Issue:** Python 3.14.3 is the system default. `pandas==2.2.3` has no binary wheel for Python 3.14 (earliest available wheel is 2.3.3 for 3.14). Installation via `pip install -r requirements.txt` fails with a Meson/C-compiler error.
**Fix:** Python 3.12.1 is installed on the machine. All test execution and verification was run via `py -3.12` (Python 3.12). The project files (requirements.txt, README.md) already specify "Python 3.11+ recommended" — 3.12 is fully compliant. No project files were changed; only the executor's invocation command was adjusted.
**User action needed:** When running `make demo` or `make test`, use `py -3.12 -m pytest` or ensure `python` on PATH resolves to Python 3.12. Alternatively install Python 3.11 from python.org.
**Files modified:** None (deviation is in the execution environment, not in project files).

## Smoke Test Behavior

`python main.py` (with `ANTHROPIC_API_KEY=dummy`) raises `ModuleNotFoundError: No module named 'src.ingestion'` — this is correct behavior for Plan 01. `src/ingestion.py` is delivered in Plan 03. Config loads cleanly; the failure is at `from src.ingestion import ingest`, proving the import graph is correct up to the ingestion boundary.

## Requirements Addressed

| Requirement | Status | Evidence |
|-------------|--------|---------|
| INFRA-01 | Done | main.py skeleton with logging.basicConfig, zero print() |
| INFRA-02 | Done | src/config.py with fail-loud ANTHROPIC_API_KEY and all constants |
| INFRA-03 | Done | requirements.txt with 7 pinned production packages |
| INFRA-04 | Done | .env.example with all 8 documented env vars |
| INFRA-05 | Done | Makefile (install/demo/test/clean) + make.ps1 PowerShell mirror |
| INFRA-06 | Done | README.md 26 lines with Quick Start and ANTHROPIC_API_KEY |
| INFRA-07 | Done | test_no_hardcoded_paths.py enforces zero hardcoded path literals |
| INFRA-08 | Done | All functions type-hinted; all public methods have docstrings |
| INFRA-09 | Done | src/__init__.py exists; test_package_structure.py verifies it |

## Known Stubs

The following stubs are intentional — they lock the module interfaces for downstream plans:

| Stub | File | Phase | Reason |
|------|------|-------|--------|
| `score_risk(df)` | src/risk_engine.py | Phase 2 | Deterministic risk scoring — Plan 02 |
| `enrich_with_llm(df, api_key)` | src/llm_engine.py | Phase 3 | Claude API integration — Plan 03 |
| `write_outputs(df, output_dir)` | src/output_generator.py | Phase 4 | All output file generation — Plan 04 |
| `ingest(data_paths)` | src/ingestion.py (missing) | Plan 01-03 | CSV ingestion — not yet created |

These stubs are intentional and do not block the plan's goal. Each raises `NotImplementedError("Phase N")`.

## Threat Flags

No new threat surface beyond what was modeled in the plan's `<threat_model>`. All mitigations applied:

- T-01-01: `ANTHROPIC_API_KEY` loaded via `os.environ` only; not logged anywhere
- T-01-02: `.gitignore` includes `.env` on its own line; only `.env.example` committed
- T-01-03: All 13 packages visually verified on PyPI by human (Task 1 checkpoint)
- T-01-05: `logging.basicConfig` with ISO timestamps in main.py
- T-01-06: Logging convention locked — log only `student_id`, never PII

## Self-Check: PASSED

Files verified on disk:
- requirements.txt: FOUND
- requirements-dev.txt: FOUND
- .env.example: FOUND
- .gitignore: FOUND
- README.md: FOUND
- Makefile: FOUND
- make.ps1: FOUND
- src/__init__.py: FOUND
- src/config.py: FOUND
- tests/__init__.py: FOUND
- tests/test_config.py: FOUND
- tests/test_no_hardcoded_paths.py: FOUND
- tests/test_package_structure.py: FOUND
- src/risk_engine.py: FOUND
- src/llm_engine.py: FOUND
- src/output_generator.py: FOUND
- main.py: FOUND

Commits verified:
- 39d7605: feat(01-01): write requirements files, env template, gitignore, README, Makefile, make.ps1
- 55192b5: feat(01-01): write src/config.py with fail-loud env loading and all constants; add tests
- f33470e: feat(01-01): write Phase 2/3/4 stubs and main.py orchestrator skeleton (D-05, D-06)
