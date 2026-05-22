---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-05-22T09:15:00.000Z"
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 3
  completed_plans: 1
  percent: 33
---

# Project State: boon-academy-intervention

## Current Status

- **Phase:** 1 (In Progress)
- **Active phase:** Phase 1 — Foundation + Data Ingestion
- **Completed phases:** None
- **Last updated:** 2026-05-22

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** A facilitator opens their campus Excel file and immediately knows exactly which students to contact today, with the message already written.
**Current focus:** Phase 1 execution — Wave 2 (01-02 data gen + 01-03 ingestion) — Plan 01-01 scaffold complete

## Phase Progress

| Phase | Name | Plans Done | Status |
|-------|------|------------|--------|
| 1 | Foundation + Data Ingestion | 1 / 3 | In Progress |
| 2 | Risk Scoring Engine | 0 / ? | Pending |
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

- **Phases completed:** 0 / 8
- **Plans completed:** 1 / 3 (Phase 1)
- **Requirements delivered:** 9 / 52 (INFRA-01 through INFRA-09)
- **Test coverage:** 8 tests passing (test_config, test_no_hardcoded_paths, test_package_structure)

## Accumulated Context

### Key Decisions

- Deterministic risk scoring (not ML) — auditable, explainable, no training data needed
- Campus-level LLM batching — reduces API calls ~10x, preserves cohort context in prompt
- Rule-based fallback templates — labeled `generated_by: template`, pipeline never halts on API failure
- openpyxl over xlsxwriter — read+write+append required for test assertions
- respx (not responses) for mocking — Anthropic SDK uses httpx, not requests
- pandas 2.2.3 (not 3.x) — avoid mandatory Copy-on-Write breaking chained assignment patterns
- python-docx 1.1.2 (not 1.2.0) — 1.2.0 has open OxmlElement + table-border issues
- D-07: All 17 column constants + risk thresholds + weights in src/config.py from day 1
- D-08: Only ANTHROPIC_API_KEY uses os.environ (fail-loud); paths use os.getenv with safe defaults
- D-05/D-06: run_log dict built in-memory throughout run, written once at end via output_generator
- Python 3.12 required for test execution — pandas==2.2.3 has no wheel for Python 3.14 (system default)

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
*Last updated: 2026-05-22 after Plan 01-01 execution (17 files, 8 tests passing)*
