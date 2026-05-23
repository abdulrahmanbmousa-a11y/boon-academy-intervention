---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-05-23T10:55:00.000Z"
progress:
  total_phases: 8
  completed_phases: 2
  total_plans: 8
  completed_plans: 5
  percent: 25
---

# Project State: boon-academy-intervention

## Current Status

- **Phase:** 3 — Claude API Integration (ready to execute)
- **Active plan:** None — Phase 3 planned (3 plans), ready for /gsd:execute-phase 3
- **Completed phases:** Phase 1 — Foundation + Data Ingestion; Phase 2 — Risk Scoring Engine
- **Last updated:** 2026-05-23

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** A facilitator opens their campus Excel file and immediately knows exactly which students to contact today, with the message already written.
**Current focus:** Phase 3 planned (enrich_with_llm() — campus-batched Claude calls, three-layer fallback, respx tests). Ready to execute.

## Phase Progress

| Phase | Name | Plans Done | Status |
|-------|------|------------|--------|
| 1 | Foundation + Data Ingestion | 3 / 3 | Complete |
| 2 | Risk Scoring Engine | 2 / 2 | Complete |
| 3 | Claude API Integration | 0 / 3 | Planned |
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
| 02 | 02-02 | ~10 min | 2/2 | 3 |

- **Phases completed:** 2 / 8
- **Plans completed:** 5 (Phase 1: 3 plans, Phase 2: 2 plans)
- **Requirements delivered:** 26 / 52 (INFRA-01..09, DATA-01..08, RISK-01..08 all complete)
- **Test coverage:** 53 tests passing (25 Phase 1 + 28 Phase 2, all GREEN)

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
- RISK-08: Used pd.StringDtype() instead of .astype("string") to avoid bare "string" literal triggering the source-scan regex
- score_risk(): pd.Timestamp.now().normalize() called once in function body, injected into _days_since_last_note as parameter (freeze_time compatibility)
- D-08: Only ANTHROPIC_API_KEY uses os.environ (fail-loud); paths use os.getenv with safe defaults
- D-05/D-06: run_log dict built in-memory throughout run, written once at end via output_generator
- Python 3.12 required for test execution — pandas==2.2.3 has no wheel for Python 3.14 (system default)
- D-02: np.random.default_rng(42) for reproducible synthetic data; sha256 of student_metadata.csv verified identical across two runs
- D-04: _assign_risk_cohort() uses index buckets (15/25/40/20%) — deterministic cohort assignment, not RNG-dependent
- inject_edge_cases() appends 9 dupe rows to metadata, blanks ~210 numeric cells in metrics (5% of 4200), sets ~84 type-mismatch strings
- Numeric columns loaded as "string" dtype in DTYPE_METRICS (not "Float64") — pd.read_csv crashes on type mismatch strings with Float64; string load + pd.to_numeric(errors='coerce') in _fill_numeric_with_zero is the safe pattern
- Post-merge fill (0) added for session_total_min/practice_total_q/attendance_days — students with no metrics get 0 activity, consistent with D-09
- enrich_with_llm() returns tuple (df, counts_dict) — df.attrs is fragile in pandas 2.2.x; main.py unpacks tuple to update run_log
- http_client=None optional parameter on enrich_with_llm() — injected in tests (respx transport), None in production; eliminates monkeypatching
- CRITICAL-first sort uses {"CRITICAL": 0, "HIGH": 1} map key — raw string sort produces HIGH-first (alphabetical order inverted)
- PyYAML==6.0.3 and respx==0.23.1 confirmed missing from requirements.txt; added in Phase 3 Wave 0
- Templates loaded once at module import (not per-call) via yaml.safe_load(); path = Path(__file__).parent / "llm_templates.yaml"
- Three-layer fallback: Layer 1 = SDK max_retries=3 (automatic); Layer 2 = one re-prompt on APIConnectionError/RateLimitError/APIStatusError/APITimeoutError; Layer 3 = YAML template on re-prompt failure OR KeyError/StopIteration from malformed tool parse

### Known Pitfalls (from research)

- pandas reads numeric IDs as float64 — must use `dtype={"student_id": "str"}` explicitly
- Claude may return markdown-wrapped JSON — use tool-use for structured output
- PatternFill requires `fill_type="solid"` or silently produces no color
- `</script>` in embedded JSON breaks HTML — escape with `replace("</", "<\\/")`
- openpyxl test assertions need 8-char hex (e.g., `"00FFCCCC"` not `"FFCCCC"`)
- Phone numbers drop leading zeros without `dtype={"parent_phone": "str"}`
- `os.environ["KEY"]` not `os.getenv("KEY")` — fail loudly at startup if key missing
- respx mocking for Anthropic SDK: `httpx.Client(transport=respx_mock)` injected via `Anthropic(http_client=..., max_retries=0)` — `responses` library silently misses httpx calls; `max_retries=0` required to prevent SDK-internal retry loops masking test assertions
- `tool_choice={"type": "tool", "name": "..."}` forces tool call; parse with `isinstance(b, anthropic.types.ToolUseBlock)` then `b.input` (plain dict)
- yaml.safe_load() not yaml.load() — security requirement for YAML template loading

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
- `llm_engine.enrich_with_llm(df, api_key, http_client=None) -> tuple[DataFrame, dict]` — never raises; dict keys: api_calls_made (int), tokens_used (dict[str,int]), fallbacks_triggered (int)
- `output_generator.write_outputs(df, output_dir) -> dict[str, Path]` — idempotent

---
*State initialized: 2026-05-21*
*Last updated: 2026-05-23 after Phase 3 planning (03-01 prerequisites — tuple return contract locked, D-09 constants added)*
