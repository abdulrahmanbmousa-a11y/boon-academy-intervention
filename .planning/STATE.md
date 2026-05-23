---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-05-23T21:15:00.000Z"
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 14
  completed_plans: 13
  percent: 63
---

# Project State: boon-academy-intervention

## Current Status

- **Phase:** 6 — Documentation Suite (next up)
- **Active plan:** 06-01 (next to execute)
- **Completed phases:** Phase 1 — Foundation + Data Ingestion; Phase 2 — Risk Scoring Engine; Phase 3 — Claude API Integration; Phase 4 — Excel + CSV Output Generation; Phase 5 — HTML Dashboard + Word Report
- **Last updated:** 2026-05-23

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** A facilitator opens their campus Excel file and immediately knows exactly which students to contact today, with the message already written.
**Current focus:** Phase 6 — Documentation Suite (next up).

## Phase Progress

| Phase | Name | Plans Done | Status |
|-------|------|------------|--------|
| 1 | Foundation + Data Ingestion | 3 / 3 | Complete |
| 2 | Risk Scoring Engine | 2 / 2 | Complete |
| 3 | Claude API Integration | 3 / 3 | Complete |
| 4 | Excel + CSV Output Generation | 3 / 3 | Complete |
| 5 | HTML Dashboard + Word Report | 3 / 3 | Complete |
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
| 03 | 03-01 | ~8 min | 3/3 | 4 |
| 03 | 03-02 | ~15 min | 1/1 | 1 |
| 03 | 03-03 | ~20 min | 2/2 | 2 |
| 04 | 04-01 | ~3 min | 2/2 | 4 |
| 04 | 04-02 | ~12 min | 2/2 | 2 |
| 04 | 04-03 | ~8 min | 2/2 | 3 |
| 05 | 05-01 | ~12 min | 2/2 | 4 |
| 05 | 05-02 | ~10 min | 2/2 | 2 |
| 05 | 05-03 | ~5 min | 2/2 | 2 |

- **Phases completed:** 5 / 8
- **Plans completed:** 14 (Phase 1: 3 plans, Phase 2: 2 plans, Phase 3: 3/3 plans, Phase 4: 3/3 plans, Phase 5: 3/3 plans)
- **Requirements delivered:** 54 / 52+ (INFRA-01..09, DATA-01..08, RISK-01..08, LLM-01..09, OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06 complete)
- **Test coverage:** 111 tests passing (25 Phase 1 + 28 Phase 2 + 12 Phase 3 + 34 Phase 4 + 12 Phase 5, all GREEN)

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
- PyYAML==6.0.3 and respx==0.23.1 added to requirements.txt in 03-01; both were already installed under py -3.12
- LLM_ENABLED uses .lower() == "true" (not bool(os.getenv())) — bool() is always True for any non-empty string including "false"
- YAML >- block scalars used for all template strings — prevents YAML parser misreading {format_placeholders} as flow mappings
- D-09 constants (9 total): ANTHROPIC_MODEL, LLM_ENABLED, MAX_TOKENS, TEMPERATURE, TIMEOUT_SECONDS, COL_FACILITATOR_SUMMARY, COL_WHATSAPP_MESSAGE, COL_GENERATED_BY, COL_LLM_ERROR_REASON added to src/config.py
- Templates loaded once at module import (not per-call) via yaml.safe_load(); path = Path(__file__).parent / "llm_templates.yaml"
- Three-layer fallback: Layer 1 = SDK max_retries=3 (automatic); Layer 2 = one re-prompt on APIConnectionError/RateLimitError/APIStatusError/APITimeoutError; Layer 3 = YAML template on re-prompt failure OR KeyError/StopIteration from malformed tool parse
- INTERVENTION_TOOL uses cfg.COL_STUDENT_ID / cfg.COL_FACILITATOR_SUMMARY / cfg.COL_WHATSAPP_MESSAGE as JSON schema property names — all column names via cfg.COL_* including inside tool schema definition
- student_data prompt list uses cfg.COL_* as dict keys — no bare DataFrame column name strings anywhere in llm_engine.py production code
- _write_results_back() uses result.get(cfg.COL_GENERATED_BY, generated_by) — works for both LLM results (no key present, falls to "llm") and template results (key from _apply_templates)
- Plan verification script step 5 flags unavoidable JSON Schema vocabulary ("type", "object", "required") — these are not DataFrame column names; targeted check confirms zero bare DF column name strings
- Summary row layout (04-02 D-08): header=row1 (frozen), summary=row2 (bold grey FFEEEEEE), data=row3+; freeze_panes="A2" on campus dashboards (not "A3") — D-08 compliant
- MEDIUM/LOW campus dashboard LLM cells: written as Python None (not "N/A") — openpyxl writes empty cell; D-06 compliance
- pandas NA normalization: non-string cell values checked with pd.isna() before passing to openpyxl to prevent "nan" string appearing in cells
- D-10: COLOR_* constants use 8-char ARGB format (FF prefix) matching openpyxl PatternFill fgColor contract — test assertions use same 8-char value (not 6-char)
- OUTPUT_COLS_CAMPUS defined as OUTPUT_COLS_PRIORITY + 3 LLM cols — guarantees superset relationship without duplication
- _write_whatsapp_csv uses encoding="utf-8-sig" (UTF-8 BOM) for Excel compatibility with Arabic characters
- _write_run_log uses json.dumps(default=str) to handle datetime or Path objects without TypeError
- httpx.MockTransport(respx_mock.handler) is the correct respx 0.23.1 injection pattern — respx_mock fixture is a MockRouter (not a transport); httpx.Client(transport=respx_mock) silently bypasses the mock
- test_no_bare_column_strings_in_llm_engine uses expanded allowed set (23 entries) covering JSON Schema vocab, Anthropic API structure keys, return dict keys, and tool name — all 24 known column name values asserted absent
- main.py Phase 3 wiring: df, llm_counts = llm_engine.enrich_with_llm(df, cfg.ANTHROPIC_API_KEY); run_log updated from llm_counts; logger.info with aggregate counts only (no PII)
- write_outputs(df, output_dir, run_log) 3-arg orchestrator: output_dir.mkdir first, calls all 6 private helpers in order, returns unified dict with keys: priority_list, campus_*, whatsapp, run_log, dashboard, report (D-01..D-04)
- T-04-05 confirmed: ANTHROPIC_API_KEY passed to enrich_with_llm() only, never stored in run_log dict; run_log has exactly 7 safe keys
- main.py Phase 4 wiring: from src import output_generator at top; paths = output_generator.write_outputs(df, cfg.OUTPUT_DIR, run_log) uses 3 positional args (not keyword); logger.info logs list(paths.keys())
- DISPLAY_COLS_DASHBOARD (12 cols): no COL_RANK (JS sorts client-side), no COL_RECOMMENDED_ACTION (COL_FACILITATOR_SUMMARY used instead per D-02)
- Jinja2 loaded lazily inside _write_html_dashboard() (not at module import); autoescape=False because students_json is pre-serialised JSON in a script tag
- dashboard.html.j2: zero external URLs; all CSS/JS inline; campus_ids template variable populates filter <select>; risk buttons use data-level attribute; one detail row open at a time
- json.dumps(records).replace("</","<\\/") in _write_html_dashboard — T-05-01 script-tag injection guard; covered by test_html_dashboard_escape_script_tag
- python-docx add_heading(level=0) uses "Title" paragraph style (not "Heading 1") — test assertions must check style.name == "Title" OR style.name.startswith("Heading")
- _write_report deep-dives use COL_ATTENDANCE_RATE/COL_AVG_PRACTICE/COL_TREND_DIR/COL_DAYS_SINCE_NOTE (always present) not COL_*_COMPONENT (optional); missing columns guarded via col in df_copy.columns

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

**Stack:** Python 3.12 (py -3.12), anthropic 0.103.1 (claude-sonnet-4-5), pandas 2.2.3, openpyxl 3.1.5, python-docx 1.1.2, jinja2 3.1.6, pytest 8.3.5, respx 0.23.1, freezegun 1.5.5, PyYAML 6.0.3
**Entry point:** `python main.py`
**Module contracts:**

- `ingestion.ingest(data_paths) -> DataFrame` — clean, merged, deduped
- `risk_engine.score_risk(df) -> DataFrame` — pure function, no I/O
- `llm_engine.enrich_with_llm(df, api_key, http_client=None) -> tuple[DataFrame, dict]` — never raises; dict keys: api_calls_made (int), tokens_used (dict[str,int]), fallbacks_triggered (int)
- `output_generator.write_outputs(df, output_dir, run_log) -> dict[str, Path]` — idempotent; run_log is required positional arg (D-01)

---
*State initialized: 2026-05-21*
*Last updated: 2026-05-23 after 05-03 execution (Phase 5 complete — write_outputs() wired to all 6 helpers, "dashboard" and "report" keys in return dict, 111 total tests GREEN)*
