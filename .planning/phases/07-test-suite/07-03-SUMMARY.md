---
phase: 07-test-suite
plan: "03"
subsystem: test-llm-output
tags: [testing, TEST-03, TEST-04, respx, LLM, output-generator, D-08, D-09]

dependency_graph:
  requires:
    - "07-01-BASELINE.md: authoritative failure list — fixed only real failures"
    - "tests/conftest.py: minimal_enriched_df fixture (Wave 0)"
  provides:
    - "tests/test_llm_engine.py: fallback, campus-batching (MAX_STUDENTS pin), token-logging tests aligned with D-08/D-09"
    - "tests/test_output_generator.py: test_all_6_output_files_exist end-to-end + PatternFill color assertion"
  affects:
    - "Full test suite: all TEST-03 and TEST-04 requirements now covered"

tech_stack:
  added: []
  patterns:
    - "respx.mock context manager for httpx-level Anthropic API mocking (not `responses` library)"
    - "monkeypatch.setattr on cfg.MAX_STUDENTS_PER_LLM_CALL to pin batch sizing in campus-batching test"
    - "caplog.text assertion for token-count log lines (not just dict key presence)"
    - "tmp_path fixture for write_outputs() end-to-end isolation"

key_files:
  created: []
  modified:
    - "tests/test_llm_engine.py"
    - "tests/test_output_generator.py"

commits:
  - "c9fb9dc: test(07-03): align test_llm_engine.py with D-08/D-09/TEST-03 requirements"
  - "3fff4f0: test(07-03): add test_all_6_output_files_exist to test_output_generator.py"

test_results:
  command: "py -3.12 -m pytest tests/test_llm_engine.py tests/test_output_generator.py -v"
  passed: 52
  failed: 0
  status: green

## Self-Check: PASSED

All must-haves verified:

- [x] test_fallback_to_template uses respx to simulate HTTP error, asserts generated_by == "template" and non-empty whatsapp_message for CRITICAL/HIGH rows
- [x] test_campus_batching asserts len(respx_mock.calls) == 2 for 2 distinct campuses with MAX_STUDENTS_PER_LLM_CALL pinned via monkeypatch
- [x] Token-logging test asserts caplog.text contains actual token numbers (not just dict value presence)
- [x] test_all_6_output_files_exist calls write_outputs() end-to-end with tmp_path and asserts all 6 paths exist
- [x] PatternFill color assertion compares cell.fill.fgColor.rgb to cfg.COLOR_CRITICAL ("FFFFCCCC")
- [x] py -3.12 -m pytest tests/test_llm_engine.py tests/test_output_generator.py -v exits 0

## What Was Built

**TEST-03 LLM tests** (`tests/test_llm_engine.py`): Three tests aligned with D-08/D-09:
- `test_fallback_to_template`: uses `respx` to mock the Anthropic httpx endpoint with HTTP 500,
  asserts every CRITICAL/HIGH row has `generated_by == "template"` and a non-empty `whatsapp_message`.
- `test_campus_batching`: pins `cfg.MAX_STUDENTS_PER_LLM_CALL` via monkeypatch, asserts exactly
  `len(respx_mock.calls) == 2` for 2 distinct campuses — validates per-campus batch architecture.
- Token-logging test: extended to assert `caplog.text` contains the actual numeric token counts,
  not just that the dict has values (gap from 07-PATTERNS.md observation on caplog assertions).

**TEST-04 output tests** (`tests/test_output_generator.py`): `test_all_6_output_files_exist` calls
`write_outputs()` end-to-end with a `tmp_path` isolated output directory and asserts all 6 returned
`Path` objects exist on disk. `test_campus_dashboard_critical_row_color` asserts
`cell.fill.fgColor.rgb == cfg.COLOR_CRITICAL` where `cfg.COLOR_CRITICAL = "FFFFCCCC"`.
