# Roadmap: boon-academy-intervention

**Project:** boon-academy-intervention
**Granularity:** Fine (8 phases)
**Coverage:** 52/52 requirements mapped
**Last updated:** 2026-05-23

---

## Phases

- [x] **Phase 1: Foundation + Data Ingestion** - Project scaffold, config, synthetic data, and a clean unified DataFrame — COMPLETE 2026-05-22
- [x] **Phase 2: Risk Scoring Engine** - Deterministic weighted risk formula producing risk_score and risk_level for every student — COMPLETE 2026-05-23
- [x] **Phase 3: Claude API Integration** - Campus-batched LLM calls with three-layer error handling and PII-safe logging — COMPLETE 2026-05-23
- [ ] **Phase 4: Excel + CSV Output Generation** - intervention_priority_list.xlsx, per-campus dashboards, whatsapp_messages.csv, run_log.json
- [ ] **Phase 5: HTML Dashboard + Word Report** - Self-contained HTML dashboard and intervention_report.docx
- [ ] **Phase 6: Documentation Suite** - All 8 .docx documentation files and analysis.md
- [ ] **Phase 7: Test Suite** - Full pytest suite covering risk engine, ingestion edge cases, LLM fallback, and output assertions
- [ ] **Phase 8: End-to-End Integration + Polish** - Full pipeline verified on synthetic data with all quality gates passing

---

## Phase Details

### Phase 1: Foundation + Data Ingestion
**Goal:** Project infrastructure is in place and the pipeline can ingest 3 CSV files into a single clean student DataFrame with schema frozen and all quality issues logged.
**Depends on:** None
**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08, INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, INFRA-09
**Success Criteria** (what must be TRUE):
  1. `python main.py` runs without error on the generated synthetic CSV files and produces a single merged DataFrame with one row per student_id
  2. Running ingestion on a CSV with duplicate student_ids, missing numeric values, and type mismatches produces logged warnings and continues without raising an exception
  3. `src/config.py` fails loudly with a clear error message when ANTHROPIC_API_KEY is absent from the environment
  4. `make demo`, `make test`, and `make clean` all execute without error from a fresh clone
  5. No hardcoded file paths or API key strings appear anywhere in the source files
**Plans:** 3 plans
- [x] 01-01-PLAN.md - Project scaffold + src/config.py (env vars, constants) + Phase 2/3/4 stubs + main.py orchestrator (INFRA-01..09) — COMPLETE 2026-05-22
- [x] 01-02-PLAN.md - src/generate_data.py synthetic CSV generator + tests/fixtures/ inventory + conftest (DATA-01) — COMPLETE 2026-05-22
- [x] 01-03-PLAN.md - src/ingestion.py CSV-to-DataFrame pipeline + test_ingestion.py + end-to-end smoke (DATA-02..08) — COMPLETE 2026-05-22

### Phase 2: Risk Scoring Engine
**Goal:** Every student in the merged DataFrame receives a deterministic risk_score (0-100), a risk_level (CRITICAL/HIGH/MEDIUM/LOW), and all four component scores, computed by a pure function with no I/O.
**Depends on:** Phase 1
**Requirements:** RISK-01, RISK-02, RISK-03, RISK-04, RISK-05, RISK-06, RISK-07, RISK-08
**Success Criteria** (what must be TRUE):
  1. Calling `score_risk(df)` on the merged DataFrame returns a DataFrame with columns: risk_score, risk_level, attendance_rate, avg_practice_questions, trend_direction, days_since_last_note
  2. A student with 0 attendance, 0 practice, declining trend, and no facilitator note receives risk_score >= 75 and risk_level == "CRITICAL"
  3. A student with perfect attendance, high practice volume, improving trend, and a recent note receives risk_score < 25 and risk_level == "LOW"
  4. All column name strings used in the scoring logic are imported from constants defined in `src/config.py` — no bare string literals appear in `risk_engine.py`
**Plans:** 2 plans
- [x] 02-01-PLAN.md - Wave 0: src/config.py +4 D-09 component constants + tests/test_config.py extension + tests/test_risk_engine.py failing-test scaffold (RISK-08 scaffolding) — COMPLETE 2026-05-23
- [x] 02-02-PLAN.md - Wave 1: src/risk_engine.py pure function (D-01..D-09) + main.py wiring (RISK-01..RISK-08) — COMPLETE 2026-05-23

### Phase 3: Claude API Integration
**Goal:** CRITICAL and HIGH risk students receive AI-generated facilitator summaries and WhatsApp messages via campus-batched API calls, with automatic fallback to labeled rule-based templates on any failure.
**Depends on:** Phase 2
**Requirements:** LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08, LLM-09
**Success Criteria** (what must be TRUE):
  1. After `enrich_with_llm(df, api_key)` runs, every CRITICAL and HIGH student row has a non-empty facilitator action summary (2 sentences) and a WhatsApp message under 100 words
  2. When the API returns an error on all retries, affected students receive a rule-based template message and their `generated_by` field is set to `"template"` — the pipeline does not raise or halt
  3. `outputs/run_log.json` contains input_tokens and output_tokens for each API call made
  4. Student names and parent phone numbers do not appear in any log output at INFO or DEBUG level
  5. Medium and Low risk students have no LLM fields populated — only one API call per campus is made, not one per student
**Plans:** 3 plans
- [x] 03-01-PLAN.md - Wave 1: requirements.txt +PyYAML+respx, src/config.py D-09 constants, src/llm_templates.yaml, STATE.md contract update (LLM-04, LLM-07, LLM-09) — COMPLETE 2026-05-23
- [x] 03-02-PLAN.md - Wave 2: src/llm_engine.py full implementation — campus batching, tool-use, three-layer fallback, PII masking (LLM-01..LLM-08) — COMPLETE 2026-05-23
- [x] 03-03-PLAN.md - Wave 3: main.py wiring + tests/test_llm_engine.py full suite (LLM-01..LLM-09) — COMPLETE 2026-05-23

### Phase 4: Excel + CSV Output Generation
**Goal:** The pipeline writes intervention_priority_list.xlsx, one facilitator_dashboard_{campus_id}.xlsx per campus, whatsapp_messages.csv, and run_log.json — all correctly formatted and ready to open.
**Depends on:** Phase 3
**Requirements:** OUT-01, OUT-02, OUT-03, OUT-06
**Success Criteria** (what must be TRUE):
  1. Opening `outputs/intervention_priority_list.xlsx` shows all students ranked by risk_score descending, with CRITICAL rows in red, HIGH in orange, MEDIUM in yellow, LOW in green, bold headers, and frozen top row
  2. Each campus Excel file contains only its own students, sorted by risk_score descending, and includes a summary row at top showing total students, critical count, high count, and intervention coverage percentage
  3. `outputs/whatsapp_messages.csv` contains columns student_id, student_name, parent_phone, facilitator_email, campus_id, risk_level, message_text, generated_by — and every CRITICAL/HIGH student has a row
  4. `outputs/run_log.json` exists and contains run_timestamp, students_processed, api_calls_made, tokens_used, errors_encountered, fallbacks_triggered, and data_quality_warnings
**Plans:** 3 plans
- [ ] 04-01-PLAN.md � Config constants + _write_whatsapp_csv + _write_run_log + unit tests (OUT-03, OUT-06)
- [ ] 04-02-PLAN.md � _write_priority_list + _write_campus_dashboards + Excel format tests (OUT-01, OUT-02)
- [ ] 04-03-PLAN.md � write_outputs orchestrator + main.py wiring + integration test (OUT-01, OUT-02, OUT-03, OUT-06)
**UI hint**: yes

### Phase 5: HTML Dashboard + Word Report
**Goal:** A single self-contained HTML file lets any facilitator explore all student data offline, and intervention_report.docx opens cleanly in both Word and Google Docs with full narrative and tables.
**Depends on:** Phase 4
**Requirements:** OUT-04, OUT-05
**Success Criteria** (what must be TRUE):
  1. Opening `outputs/facilitator_dashboard.html` directly in a browser via file:// shows the risk table, campus filter, risk-level filter buttons, and name search — all functional with no network requests
  2. Clicking a student row expands to show risk breakdown, facilitator summary, WhatsApp message, and a copy button that copies the message text to clipboard
  3. Opening `outputs/intervention_report.docx` in Word and Google Docs shows: cover page, executive summary with risk breakdown table, top 10 most at-risk students, campus summary table, 3-4 student deep-dives, data quality notes, and methodology appendix — all without rendering errors
**Plans:** TBD
**UI hint**: yes

### Phase 6: Documentation Suite
**Goal:** All 8 .docx documentation files and analysis.md exist in their correct directories, contain real pipeline run numbers, and are readable in Word and Google Docs.
**Depends on:** Phase 4
**Requirements:** DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07, DOCS-08, DOCS-09
**Success Criteria** (what must be TRUE):
  1. `docs/` contains all 8 .docx files: analysis.docx, architecture.docx, security.docx, engineering_decisions.docx, data_handling.docx, scalability.docx, system_design.docx, alternatives.docx — each opening without errors in Word or Google Docs
  2. `analysis.md` exists at the repo root, contains all 5 required sections (Diagnosis, What you found, What you built, What you cut, What next), stays under 600 words, and includes real numbers from the pipeline run
  3. `docs/security.docx` describes env-var-only API key handling, PII masking in logs, and data retention recommendation without exposing any real API key or student data
  4. `docs/scalability.docx` includes a cost projection at $200/month and a migration path from CSV to SQLite to PostgreSQL
**Plans:** TBD

### Phase 7: Test Suite
**Goal:** A pytest suite passes with zero failures, covering risk formula components, ingestion edge cases, LLM fallback behavior, and output file assertions.
**Depends on:** Phase 5
**Requirements:** TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. `make test` (or `pytest tests/`) completes with 0 failures and 0 errors on a fresh install
  2. `tests/test_risk_engine.py` includes boundary tests confirming that a student at exactly risk_score == 75 receives CRITICAL and a student at exactly 74 receives HIGH
  3. `tests/test_ingestion.py` includes tests that verify: missing numeric values are filled with 0, duplicate student_id rows are deduplicated, and an empty CSV does not crash the pipeline
  4. `tests/test_llm_engine.py` uses respx to mock a failed API call and asserts that the student row has `generated_by == "template"` and a non-empty message_text
  5. `tests/test_output_generator.py` asserts all 6 output files exist after a full generation run and that the Excel file contains the correct color-coded PatternFill values (8-character hex)
**Plans:** TBD

### Phase 8: End-to-End Integration + Polish
**Goal:** A single `python main.py` run on fresh synthetic data produces all 6 output files and all 8 documentation files, all quality gates pass, and the repository runs cleanly from a fresh clone.
**Depends on:** Phase 7
**Requirements:** (Integration verification of all v1 requirements — no new requirement IDs; this phase verifies the complete system)
**Success Criteria** (what must be TRUE):
  1. Running `python main.py` from a fresh clone (after `pip install -r requirements.txt` and `.env` setup) completes without errors and produces all 14 files: 6 in `outputs/` and 8 in `docs/`
  2. All output files open without errors in their target applications (Excel in Google Sheets, .docx in Google Docs, .html in Chrome via file://)
  3. `make test` passes with 0 failures after the integration run
  4. Code review confirms: type hints on all functions, docstrings on all public classes and methods, no print statements, no hardcoded paths or API keys
  5. HTML dashboard quality check confirms: campus filter works, risk filter works, copy button works, no layout breaks at 1280px and 1920px viewport widths
**Plans:** TBD
**UI hint**: yes

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + Data Ingestion | 3/3 | Complete | 2026-05-22 |
| 2. Risk Scoring Engine | 2/2 | Complete | 2026-05-23 |
| 3. Claude API Integration | 3/3 | Complete | 2026-05-23 |
| 4. Excel + CSV Output Generation | 0/? | Not started | - |
| 5. HTML Dashboard + Word Report | 0/? | Not started | - |
| 6. Documentation Suite | 0/? | Not started | - |
| 7. Test Suite | 0/? | Not started | - |
| 8. End-to-End Integration + Polish | 0/? | Not started | - |

---

## Coverage

**v1 requirements mapped:** 52/52
**Orphaned requirements:** 0

| Requirement Group | Count | Phase |
|-------------------|-------|-------|
| DATA-01 to DATA-08 | 8 | Phase 1 |
| INFRA-01 to INFRA-09 | 9 | Phase 1 |
| RISK-01 to RISK-08 | 8 | Phase 2 |
| LLM-01 to LLM-09 | 9 | Phase 3 |
| OUT-01, OUT-02, OUT-03, OUT-06 | 4 | Phase 4 |
| OUT-04, OUT-05 | 2 | Phase 5 |
| DOCS-01 to DOCS-09 | 9 | Phase 6 |
| TEST-01 to TEST-04 | 4 | Phase 7 |
| Integration verification | - | Phase 8 |

---

*Roadmap created: 2026-05-21*
*Last updated: 2026-05-23 after 03-03 execution (Phase 3 complete — main.py wired, 12-test LLM suite passing, 65 total tests GREEN)*
