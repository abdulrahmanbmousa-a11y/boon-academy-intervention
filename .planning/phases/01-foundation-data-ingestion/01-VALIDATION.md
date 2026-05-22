---
phase: 1
slug: foundation-data-ingestion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest==8.3.5 |
| **Config file** | none — Wave 0 installs (`tests/__init__.py` + minimal `pytest.ini`) |
| **Quick run command** | `pytest tests/test_ingestion.py -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ingestion.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite + `python main.py` smoke + `make demo` + `make test` + `make clean` all green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_generate_data.py::test_three_files_created -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DATA-02 | — | dtype-locked reads prevent phone/ID coercion | unit | `pytest tests/test_ingestion.py::test_phone_stays_string -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DATA-03 | — | N/A | unit | `pytest tests/test_ingestion.py::test_missing_numeric_filled_with_zero -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | DATA-04 | — | N/A | unit | `pytest tests/test_ingestion.py::test_duplicate_ids_deduped -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | DATA-05 | — | N/A | unit | `pytest tests/test_ingestion.py::test_type_mismatch_safe_default -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | DATA-06 | — | N/A | unit | `pytest tests/test_ingestion.py::test_merge_one_row_per_student -x` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 1 | DATA-07 | — | N/A | unit | `pytest tests/test_ingestion.py::test_warnings_attached_to_df -x` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 1 | DATA-08 | — | N/A | unit | `pytest tests/test_ingestion.py::test_bad_record_does_not_crash -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | INFRA-01 | — | N/A | smoke | `python main.py` (after data/ populated) | ❌ W0 manual | ⬜ pending |
| 1-02-02 | 02 | 1 | INFRA-02 | API key leak | Key never logged; raises KeyError with var name only | unit | `pytest tests/test_config.py::test_missing_api_key_raises -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | INFRA-03 | — | N/A | smoke | `pip install -r requirements.txt --dry-run` | manual | ⬜ pending |
| 1-02-04 | 02 | 1 | INFRA-04 | .env committed | `.env` gitignored; only `.env.example` committed | manual | review `.gitignore` | manual | ⬜ pending |
| 1-02-05 | 02 | 1 | INFRA-05 | — | N/A | smoke | `make demo && make test && make clean` | manual | ⬜ pending |
| 1-02-06 | 02 | 1 | INFRA-06 | — | N/A | manual | `wc -l README.md` < 30 | manual | ⬜ pending |
| 1-02-07 | 02 | 1 | INFRA-07 | Path hardcoding | No hardcoded paths in src/ | unit | `pytest tests/test_no_hardcoded_paths.py -x` | ❌ W0 | ⬜ pending |
| 1-02-08 | 02 | 1 | INFRA-08 | — | N/A | manual/lint | `mypy src/ --ignore-missing-imports` | manual | ⬜ pending |
| 1-02-09 | 02 | 1 | INFRA-09 | — | N/A | unit | `pytest tests/test_package_structure.py::test_src_is_package -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — empty file so pytest finds the package
- [ ] `tests/conftest.py` — shared fixtures; add a fixture returning path-dict pointing at sample CSVs
- [ ] `tests/fixtures/` — small canned CSVs covering happy path + edge cases (missing num, dup id, bad date, type mismatch, empty file)
- [ ] `tests/test_config.py` — covers INFRA-02 (env var failure raises loudly)
- [ ] `tests/test_ingestion.py` — covers DATA-02 through DATA-08
- [ ] `tests/test_generate_data.py` — covers DATA-01 (assert 3 files, expected row counts, distribution)
- [ ] `tests/test_no_hardcoded_paths.py` — grep `src/*.py` for hardcoded `"data"`, `"outputs"`, `"docs"` outside config.py
- [ ] `tests/test_package_structure.py` — INFRA-09 verification
- [ ] `requirements-dev.txt` — includes `pytest==8.3.5` plus test-only deps
- [ ] `pip install -r requirements-dev.txt` — framework install

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `make demo`, `make test`, `make clean` execute without error | INFRA-05 | `make` not installed by default on Windows; requires Makefile + `make.ps1` fallback | Run `make demo && make test && make clean` from repo root after cloning fresh |
| `.env.example` documents all env vars | INFRA-04 | Content review — no executable check | Confirm `.env.example` lists `ANTHROPIC_API_KEY`, `DATA_DIR`, `OUTPUT_DIR` (and any others from config.py) with placeholder values |
| README.md ≤ 30 lines | INFRA-06 | Line count only | `wc -l README.md` (or `Get-Content README.md \| Measure-Object -Line` on Windows) |
| Type hints on all functions; docstrings on all public classes/methods | INFRA-08 | Full coverage requires human review | Spot-check each `src/*.py`; run `mypy src/ --ignore-missing-imports` as optional lint |
| `pip install -r requirements.txt` clean install | INFRA-03 | Network dependency; package legitimacy ([ASSUMED] per research) | Run in fresh virtualenv; confirm no warnings or version conflicts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
