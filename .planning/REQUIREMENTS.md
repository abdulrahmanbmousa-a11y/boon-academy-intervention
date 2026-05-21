# Requirements: boon-academy-intervention

**Defined:** 2026-05-21
**Core Value:** A facilitator opens their campus Excel file and immediately knows exactly which students to contact today, with the message already written.

## v1 Requirements

### DATA — Data Ingestion & Synthetic Generation

- [ ] **DATA-01**: System generates realistic synthetic CSV data for all 3 input files (student_daily_metrics.csv, facilitator_notes.csv, student_metadata.csv) covering 14 days, multiple campuses, realistic edge cases
- [ ] **DATA-02**: System reads CSV files using pandas with explicit `dtype=` mapping — no silent type coercion (phone numbers stay strings, IDs stay strings)
- [ ] **DATA-03**: System fills missing `session_attended_min` and `practice_questions` with 0, logs warnings for each fill
- [ ] **DATA-04**: System detects and deduplicates duplicate `student_id` rows, logging each removal
- [ ] **DATA-05**: System handles type mismatches (e.g., string where int expected) without crashing — logs warning, applies safe default
- [ ] **DATA-06**: System merges all 3 CSVs into a single unified student DataFrame with one row per student
- [ ] **DATA-07**: System logs all data quality issues as structured entries in `outputs/run_log.json`
- [ ] **DATA-08**: No single bad record crashes the pipeline — errors are caught per-row, logged, pipeline continues

### RISK — Risk Scoring Engine

- [ ] **RISK-01**: System computes `attendance_rate` = sessions attended / total possible sessions across Days 1–14
- [ ] **RISK-02**: System computes `avg_practice_questions` = average daily practice questions across available days
- [ ] **RISK-03**: System computes `trend_direction` = last 3 days avg vs first 11 days avg; declining = higher risk score component
- [ ] **RISK-04**: System computes `days_since_last_note` from latest facilitator note date; no note = maximum penalty
- [ ] **RISK-05**: System computes `risk_score` (0–100) using weighted formula: attendance_rate 35%, avg_practice 30%, trend 20%, days_since_note 15%
- [ ] **RISK-06**: System assigns `risk_level`: CRITICAL (≥75), HIGH (50–74), MEDIUM (25–49), LOW (<25)
- [ ] **RISK-07**: Output DataFrame includes: risk_score, risk_level, attendance_rate, avg_practice_questions, trend_direction, days_since_last_note
- [ ] **RISK-08**: All column names defined as constants in `src/config.py` — no hardcoded strings in logic

### LLM — Claude API Integration

- [ ] **LLM-01**: System calls Claude `claude-sonnet-4-5` API for CRITICAL and HIGH risk students only
- [ ] **LLM-02**: API calls are batched by campus — one call per campus's at-risk students (not per student)
- [ ] **LLM-03**: Each API call uses tool-use / structured output to return: (a) 2-sentence facilitator action summary, (b) WhatsApp-ready parent message (<100 words)
- [ ] **LLM-04**: System retries failed API calls with exponential backoff (max 3 retries via `anthropic` SDK `max_retries=3`)
- [ ] **LLM-05**: System falls back to rule-based template message on API failure; output is clearly labeled `generated_by: template`
- [ ] **LLM-06**: System logs token usage (input + output tokens) per API call to `run_log.json`
- [ ] **LLM-07**: ANTHROPIC_API_KEY read from environment only — never logged, never hardcoded
- [ ] **LLM-08**: Student names and parent phones are masked in all log output (PII protection)
- [ ] **LLM-09**: MAX_STUDENTS_PER_LLM_CALL configurable via env var (default: 10)

### OUT — Output File Generation

- [ ] **OUT-01**: `outputs/intervention_priority_list.xlsx` — all students ranked by risk_score desc, color-coded rows (red=CRITICAL, orange=HIGH, yellow=MEDIUM, green=LOW), bold headers, frozen top row, auto column widths, Arial font, columns: rank, student_id, student_name, campus_id, facilitator_email, risk_score, risk_level, attendance_rate, avg_practice_questions, trend_direction, days_since_last_note, recommended_action
- [ ] **OUT-02**: `outputs/facilitator_dashboard_{campus_id}.xlsx` — one file per campus, same formatting as OUT-01, filtered to campus, sorted by risk_score desc, summary row at top (total students, critical count, high count, intervention coverage %)
- [ ] **OUT-03**: `outputs/whatsapp_messages.csv` — columns: student_id, student_name, parent_phone, facilitator_email, campus_id, risk_level, message_text, generated_by (llm or template)
- [ ] **OUT-04**: `outputs/intervention_report.docx` — cover page (title, date, campus count, student count), executive summary with risk breakdown table, top 10 most at-risk students table, campus-level summary table, 3–4 student deep-dives (CRITICAL/HIGH/MEDIUM/LOW), data quality notes section, appendix with risk score methodology; opens cleanly in Word and Google Docs
- [ ] **OUT-05**: `outputs/facilitator_dashboard.html` — single self-contained file (all CSS and JS inline), works via file:// with no server, all data embedded as JSON, features: sortable risk table, campus filter, risk level filter buttons, student name search, expandable row with risk breakdown + facilitator summary + WhatsApp message + copy button, summary stats at top
- [ ] **OUT-06**: `outputs/run_log.json` — run timestamp, students processed, API calls made, tokens used, errors encountered, fallbacks triggered, data quality warnings

### DOCS — Documentation Files

- [ ] **DOCS-01**: `analysis.md` — 5-section memo (Diagnosis, What you found in data with real numbers, What you built and why, What you cut and why, What you'd build next); max ~600 words; generated AFTER pipeline runs so it contains real numbers
- [ ] **DOCS-02**: `docs/analysis.docx` — same content as analysis.md, formatted as Word document
- [ ] **DOCS-03**: `docs/architecture.docx` — ASCII pipeline diagram, component descriptions (when each runs, why it exists), where LLM is called and why, technology choices with rationale, why NOT n8n/Zapier, why NOT Airtable
- [ ] **DOCS-04**: `docs/security.docx` — API key management (env vars only, never logged), PII handling (student names and parent phones masked in all logs), data retention recommendation, access control recommendation, what must NOT appear in outputs
- [ ] **DOCS-05**: `docs/engineering_decisions.docx` — risk scoring formula rationale, LLM batching rationale, fallback logic rationale, output format choices, why Claude API, what was left intentionally simple
- [ ] **DOCS-06**: `docs/data_handling.docx` — schema per input file, cleaning steps, missing data imputation strategy, quality issues (warnings vs errors), merge logic, edge cases
- [ ] **DOCS-07**: `docs/scalability.docx` — 20 vs 100 campuses architecture comparison, bottlenecks (LLM rate limits, file I/O), migration path (CSV → SQLite → PostgreSQL), cost projection at $200/month budget
- [ ] **DOCS-08**: `docs/system_design.docx` — AI choices and why, what is NOT done by AI and why, LLM accuracy vs cost vs latency tradeoffs, human review loop recommendation, failure modes and system boundaries
- [ ] **DOCS-09**: `docs/alternatives.docx` — what was NOT built with rationale, alternative risk scoring approaches, alternative delivery methods, what's worth building next

### TEST — Test Suite

- [ ] **TEST-01**: `tests/test_risk_engine.py` — unit tests for each weighted component of risk formula, boundary tests for CRITICAL/HIGH/MEDIUM/LOW thresholds, test for student with all zeros, test for perfect student
- [ ] **TEST-02**: `tests/test_ingestion.py` — missing values test (filled with 0), bad date format test, duplicate student_id test, type mismatch test, empty CSV test
- [ ] **TEST-03**: `tests/test_llm_engine.py` — LLM fallback trigger test (mock API failure with respx, verify template is used and labeled), token logging test (mock successful call, verify tokens logged), batching test (verify campus grouping logic)
- [ ] **TEST-04**: `tests/test_output_generator.py` — assert all 6 output files exist after generation, assert Excel has correct columns and color coding, assert CSV has correct columns, assert HTML contains embedded JSON

### INFRA — Project Infrastructure

- [ ] **INFRA-01**: `main.py` reads like plain English — orchestrates ingestion → risk scoring → LLM → output generation, uses Python `logging` module throughout (no print statements)
- [ ] **INFRA-02**: `src/config.py` — loads all env vars, fails loudly with clear error if required vars missing, defines all column name constants
- [ ] **INFRA-03**: `requirements.txt` — all dependencies pinned to exact versions (pandas==2.2.3, openpyxl==3.1.5, python-docx==1.1.2, anthropic==0.103.1, etc.)
- [ ] **INFRA-04**: `.env.example` — documents all env vars with descriptions and defaults: ANTHROPIC_API_KEY, DATA_DIR, OUTPUT_DIR, DOCS_DIR, LOG_LEVEL, MAX_STUDENTS_PER_LLM_CALL, RISK_THRESHOLD_CRITICAL, RISK_THRESHOLD_HIGH
- [ ] **INFRA-05**: `Makefile` — `make demo` target runs full pipeline, `make test` runs pytest, `make clean` removes outputs/
- [ ] **INFRA-06**: `README.md` — under 30 lines, explains how to run from fresh clone (install deps, set env vars, run main.py)
- [ ] **INFRA-07**: All file paths read from env vars — zero hardcoded paths anywhere in source files
- [ ] **INFRA-08**: Type hints on all functions, docstrings on all public classes and methods
- [ ] **INFRA-09**: `src/__init__.py` exists to make src a proper Python package

## v2 Requirements

### Future Enhancements

- **FUTV2-01**: Real-time dashboard with live data refresh (requires server — not needed for batch use case)
- **FUTV2-02**: WhatsApp Business API integration for direct sending (requires carrier setup + cost)
- **FUTV2-03**: ML risk model trained on labeled quiz outcome data (viable after 6 months of deployment data)
- **FUTV2-04**: SQLite persistence layer replacing CSV files (migration path for 50+ campuses)
- **FUTV2-05**: Async/concurrent LLM calls with rate limit queue (needed at 5,000+ students)
- **FUTV2-06**: Facilitator feedback loop (did they act? did it help?) for model calibration

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time server / live dashboard | Daily batch is sufficient; adds server ops overhead for no facilitator benefit |
| n8n / Zapier automation | Opaque for debugging, hard to version-control; 1 part-time engineer can't maintain visual workflows at 100 campuses |
| Airtable as primary store | Paid dependency, vendor lock-in; CSV → Google Sheets achieves same outcome |
| Docker / Kubernetes | Over-engineered for 20 campuses; adds maintenance burden for 1 part-time engineer |
| SMS gateway (Twilio etc.) | Carrier integration cost; WhatsApp copy-paste achieves same outcome |
| ML risk model (v1) | No labeled training data yet; weighted rules are more auditable and reliable for cold start |
| OAuth / user authentication | Single-user batch pipeline, not a multi-tenant app |
| Student-facing portal | Doubles scope, zero facilitator intervention benefit |
| Auto-sending WhatsApp messages | Removes human judgment; brand risk if message goes to wrong parent |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Pending |
| DATA-06 | Phase 1 | Pending |
| DATA-07 | Phase 1 | Pending |
| DATA-08 | Phase 1 | Pending |
| RISK-01 | Phase 2 | Pending |
| RISK-02 | Phase 2 | Pending |
| RISK-03 | Phase 2 | Pending |
| RISK-04 | Phase 2 | Pending |
| RISK-05 | Phase 2 | Pending |
| RISK-06 | Phase 2 | Pending |
| RISK-07 | Phase 2 | Pending |
| RISK-08 | Phase 2 | Pending |
| LLM-01 | Phase 3 | Pending |
| LLM-02 | Phase 3 | Pending |
| LLM-03 | Phase 3 | Pending |
| LLM-04 | Phase 3 | Pending |
| LLM-05 | Phase 3 | Pending |
| LLM-06 | Phase 3 | Pending |
| LLM-07 | Phase 3 | Pending |
| LLM-08 | Phase 3 | Pending |
| LLM-09 | Phase 3 | Pending |
| OUT-01 | Phase 4 | Pending |
| OUT-02 | Phase 4 | Pending |
| OUT-03 | Phase 4 | Pending |
| OUT-04 | Phase 5 | Pending |
| OUT-05 | Phase 5 | Pending |
| OUT-06 | Phase 4 | Pending |
| DOCS-01 | Phase 6 | Pending |
| DOCS-02 | Phase 6 | Pending |
| DOCS-03 | Phase 6 | Pending |
| DOCS-04 | Phase 6 | Pending |
| DOCS-05 | Phase 6 | Pending |
| DOCS-06 | Phase 6 | Pending |
| DOCS-07 | Phase 6 | Pending |
| DOCS-08 | Phase 6 | Pending |
| DOCS-09 | Phase 6 | Pending |
| TEST-01 | Phase 7 | Pending |
| TEST-02 | Phase 7 | Pending |
| TEST-03 | Phase 7 | Pending |
| TEST-04 | Phase 7 | Pending |
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INFRA-04 | Phase 1 | Pending |
| INFRA-05 | Phase 1 | Pending |
| INFRA-06 | Phase 1 | Pending |
| INFRA-07 | Phase 1 | Pending |
| INFRA-08 | Phase 1 | Pending |
| INFRA-09 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-21*
*Last updated: 2026-05-21 after initial definition*
