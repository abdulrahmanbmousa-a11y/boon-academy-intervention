# Roadmap: boon-academy-intervention

**Project:** boon-academy-intervention
**Granularity:** Fine (8 phases)
**Coverage:** 52/52 requirements mapped
**Last updated:** 2026-05-24

---

## Phases

- [x] **Phase 1: Foundation + Data Ingestion** - Project scaffold, config, synthetic data, and a clean unified DataFrame — COMPLETE 2026-05-22
- [x] **Phase 2: Risk Scoring Engine** - Deterministic weighted risk formula producing risk_score and risk_level for every student — COMPLETE 2026-05-23
- [x] **Phase 3: Claude API Integration** - Campus-batched LLM calls with three-layer error handling and PII-safe logging — COMPLETE 2026-05-23
- [x] **Phase 4: Excel + CSV Output Generation** - intervention_priority_list.xlsx, per-campus dashboards, whatsapp_messages.csv, run_log.json — COMPLETE 2026-05-23
- [x] **Phase 5: HTML Dashboard + Word Report** - Self-contained HTML dashboard and intervention_report.docx — COMPLETE 2026-05-23
- [x] **Phase 6: Documentation Suite** - All 8 .docx documentation files and analysis.md — COMPLETE 2026-05-24
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
- [x] 04-01-PLAN.md — Config constants + _write_whatsapp_csv + _write_run_log + unit tests (OUT-03, OUT-06) — COMPLETE 2026-05-23
- [x] 04-02-PLAN.md — _write_priority_list + _write_campus_dashboards + Excel format tests (OUT-01, OUT-02) — COMPLETE 2026-05-23
- [x] 04-03-PLAN.md — write_outputs orchestrator + main.py wiring + integration test (OUT-01, OUT-02, OUT-03, OUT-06)
**UI hint**: yes

### Phase 5: HTML Dashboard + Word Report
**Goal:** A single self-contained HTML file lets any facilitator explore all student data offline, and intervention_report.docx opens cleanly in both Word and Google Docs with full narrative and tables.
**Depends on:** Phase 4
**Requirements:** OUT-04, OUT-05
**Success Criteria** (what must be TRUE):
  1. Opening `outputs/facilitator_dashboard.html` directly in a browser via file:// shows the risk table, campus filter, risk-level filter buttons, and name search — all functional with no network requests
  2. Clicking a student row expands to show risk breakdown, facilitator summary, WhatsApp message, and a copy button that copies the message text to clipboard
  3. Opening `outputs/intervention_report.docx` in Word and Google Docs shows: cover page, executive summary with risk breakdown table, top 10 most at-risk students, campus summary table, 3-4 student deep-dives, data quality notes, and methodology appendix — all without rendering errors
**Plans:** 3 plans

**Wave 1** *(parallel)*
- [x] 05-01-PLAN.md — DISPLAY_COLS_DASHBOARD config constant + src/templates/dashboard.html.j2 Jinja2 template + _write_html_dashboard() helper + HTML unit tests (OUT-05) — COMPLETE 2026-05-23
- [x] 05-02-PLAN.md — _write_report() helper: all 7 docx sections programmatically via python-docx + report unit tests (OUT-04) — COMPLETE 2026-05-23

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 05-03-PLAN.md — Extend write_outputs() to call both new helpers + integration test asserting "dashboard" and "report" keys (OUT-04, OUT-05) — COMPLETE 2026-05-23

**Cross-cutting constraints:**
- All column names via cfg.COL_* — no bare string literals in output logic
- json.dumps().replace("</", "<\\/") required before embedding data in script tags
- python-docx: built-in heading levels + 'Table Grid' style only, no OxmlElement
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
**Plans:** 6 plans

**Wave 1** *(parallel)*
- [x] 06-01-PLAN.md — src/templates/docs_content.yaml: full content for all 7 static docs (DOCS-03..09) ✓ commit 2491b8b
- [x] 06-02-PLAN.md — src/doc_generator.py skeleton: write_docs() orchestrator + 9 private helper stubs (DOCS-01..09) ✓ commit f2d2286

**Wave 2** *(parallel, blocked on Wave 1)*
- [x] 06-03-PLAN.md — _write_analysis_md + _write_analysis_docx: run_log-driven, 5-section structure (DOCS-01, DOCS-02) ✓ commit abcfc42
- [x] 06-04-PLAN.md — _write_architecture + _write_data_handling + _write_scalability: hybrid YAML renderer + cost table (DOCS-03, DOCS-06, DOCS-07) ✓ commits e5dc909 e29d4ee
- [x] 06-05-PLAN.md — _write_security + _write_engineering_decisions + _write_system_design + _write_alternatives: narrative YAML renderer (DOCS-04, DOCS-05, DOCS-08, DOCS-09) ✓ commit b26f204

**Wave 3** *(blocked on Wave 2)*
- [x] 06-06-PLAN.md — main.py wiring (D-02) + end-to-end smoke test asserting all 9 keys and all 9 files on disk (DOCS-01..09) ✓ commit b562eed

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
| 4. Excel + CSV Output Generation | 3/3 | Complete | 2026-05-23 |
| 5. HTML Dashboard + Word Report | 3/3 | Complete | 2026-05-23 |
| 6. Documentation Suite | 6/6 | Complete | 2026-05-24 |
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

## Post-v1 Backlog (Future Phases)

These features were requested after v1 scope was locked. Implement after Phase 8 completes.

### Phase 9: Web Application
**Goal:** Replace the file-based workflow with a hosted web app that facilitators can access via browser without running the pipeline locally.
**Key decisions to make in discuss-phase:**
- Framework (Flask / FastAPI / Django)
- Hosting (local network vs. cloud)
- Authentication (single password vs. per-facilitator login)
- Data refresh trigger (manual run button vs. scheduled)

### Phase 10: In-App Report Downloads
**Goal:** Facilitators can download their campus Excel dashboard and the Word intervention report directly from the web app — no shared drive or email needed.
**Depends on:** Phase 9 (Web Application)
**Key decisions to make in discuss-phase:**
- Download scope (own campus only, or admin can download all)
- File freshness indicator (show when last pipeline run completed)
- Whether downloads are pre-generated or generated on-demand

---

*Roadmap created: 2026-05-21*
*Last updated: 2026-05-24 — Phase 6 complete (06-06: main.py wiring + smoke test, commit b562eed); Phase 7 Test Suite next*
