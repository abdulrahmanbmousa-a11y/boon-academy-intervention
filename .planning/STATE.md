---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-05-23T09:46:00Z"
progress:
  total_phases: 8
  completed_phases: 1
  total_plans: 6
  completed_plans: 4
  percent: 15
---

# Project State: boon-academy-intervention

## Current Status

- **Phase:** 2 — Risk Scoring Engine (in progress)
- **Active plan:** Phase 2, Plan 02 (02-02) — implement score_risk()
- **Completed phases:** Phase 1 — Foundation + Data Ingestion
- **Last updated:** 2026-05-23

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** A facilitator opens their campus Excel file and immediately knows exactly which students to contact today, with the message already written.
**Current focus:** Phase 2 Plan 01 complete (Wave 0 scaffolding). Next: Plan 02-02 — implement score_risk() to turn RED tests GREEN.

## Phase Progress

| Phase | Name | Plans Done | Status |
|-------|------|------------|--------|
| 1 | Foundation + Data Ingestion | 3 / 3 | Complete |
| 2 | Risk Scoring Engine | 1 / ? | In Progress |
| 3 | Claude API Integration | 0 / ? | Pending |
| 4 | Excel + CSV Output Generation | 0 / ? | Pending |
| 5 | HTML Dashboard + Word Report | 0 / ? | Pending |
| 6 | Documentation Suite | 0 / ? | Pending |
| 7 | Test Suite | 0 / ? | Pending |
| 8 | End-to-End Integration + Polish | 0 / ? | Pending |

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01-01 | ~20 min | 3/3 | 17 |
| 01 | 01-02 | ~15 min | 2/2 | 11 |
| 01 | 01-03 | ~25 min | 3/3 | 2 |
| 02 | 02-01 | ~5 min | 2/2 | 3 |

- **Phases completed:** 1 / 8
- **Plans completed:** 4 (Phase 1: 3 plans, Phase 2: 1 plan)
- **Requirements delivered:** 18 / 52 (INFRA-01 through INFRA-09, DATA-01 through DATA-08, INFRA-08) — RISK-08 scaffold added (test exists, impl pending 02-02)
- **Test coverage:** 25 Phase 1 tests passing + 28 Phase 2 scaffold tests collected (9 GREEN, 19 RED pending 02-02 implementation)

## Accumulated Context

### Key Decisions

- Deterministic risk scoring (not ML) — auditable, explainable, no training data needed
- Campus-level LLM batching — reduces API calls ~10x, preserves cohort context in prompt
- Rule-based fallback templates — labeled `generated_by: template`, pipeline never halts on API failure
- openpyxl over xlsxwriter — read+write+append required for test assertions
- respx (not responses) for mocking — Anthropic SDK uses httpx, not requests
- pandas 2.2.3 (not 3.x) — avoid mandatory Copy-on-Write breaking chained assignment patterns
- python-docx 1.1.2 (not 1.2.0) — 1.2.0 has open OxmlElement + table-border issues
- D-07: All 21 column constants + risk thresholds + weights in src/config.py (17 from Phase 1 + 4 D-09 component columns added in 02-01)
- D-08: Only ANTHROPIC_API_KEY uses os.environ (fail-loud); paths use os.getenv with safe defaults
- D-05/D-06: run_log dict built in-memory throughout run, written once at end via output_generator
- Python 3.12 required for test execution — pandas==2.2.3 has no wheel for Python 3.14 (system default)
- D-02: np.random.default_rng(42) for reproducible synthetic data; sha256 of student_metadata.csv verified identical across two runs
- D-04: _assign_risk_cohort() uses index buckets (15/25/40/20%) — deterministic cohort assignment, not RNG-dependent
- inject_edge_cases() appends 9 dupe rows to metadata, blanks ~210 numeric cells in metrics (5% of 4200), sets ~84 type-mismatch strings
- Numeric columns loaded as "string" dtype in DTYPE_METRICS (not "Float64") — pd.read_csv crashes on type mismatch strings with Float64; string load + pd.to_numeric(errors='coerce') in _fill_numeric_with_zero is the safe pattern
- Post-merge fill (0) added for session_total_min/practice_total_q/attendance_days — students with no metrics get 0 activity, consistent with D-09

### Known Pitfalls (from research)

- pandas reads numeric IDs as float64 — must use `dtype={"student_id": "str"}` explicitly
- Claude may return markdown-wrapped JSON — use tool-use for structured output
- PatternFill requires `fill_type="solid"` or silently produces no color
- `</script>` in embedded JSON breaks HTML — escape with `replace("</", "<\\/")`
- openpyxl test assertions need 8-char hex (e.g., `"00FFCCCC"` not `"FFCCCC"`)
- Phone numbers drop leading zeros without `dtype={"parent_phone": "str"}`
- `os.environ["KEY"]` not `os.getenv("KEY")` — fail loudly at startup if key missing

### Open Questions

- Risk weight calibration — defaults need academic director validation
- Arabic dialect per campus — Modern Standard vs. Gulf dialect
- Expected CRITICAL+HIGH student count in real data (affects cost estimate)
- LibreOffice vs Excel on facilitator PCs

### Todos

- Use `py -3.12` when running pytest/main.py — Python 3.14 (system default) has no pandas==2.2.3 wheel

### Blockers

- (none)

## Session Continuity

**Stack:** Python 3.11+, anthropic 0.103.1 (claude-sonnet-4-5), pandas 2.2.3, openpyxl 3.1.5, python-docx 1.1.2, jinja2 3.1.6, pytest 8.3.5, respx 0.23.1, freezegun 1.5.5
**Entry point:** `python main.py`
**Module contracts:**

- `ingestion.ingest(data_paths) -> DataFrame` — clean, merged, deduped
- `risk_engine.score_risk(df) -> DataFrame` — pure function, no I/O
- `llm_engine.enrich_with_llm(df, api_key) -> DataFrame` — never raises
- `output_generator.write_outputs(df, output_dir) -> dict[str, Path]` — idempotent

---
*State initialized: 2026-05-21*
*Last updated: 2026-05-23 after Plan 02-01 execution (3 files modified/created, 28 tests collected, 9 GREEN, 19 RED pending 02-02)*
*Phase 2 in progress. Next: /gsd:execute-phase 2 (Plan 02-02 — implement score_risk to turn RED tests GREEN)*
