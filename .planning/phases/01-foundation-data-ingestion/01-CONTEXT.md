# Phase 1: Foundation + Data Ingestion - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the project scaffold and ingestion pipeline. By end of phase:
- Project infrastructure exists (Makefile, requirements.txt, .env.example, README, src/ package)
- Synthetic CSV data is generated (3 files, 300 students, 20 campuses, 14 days)
- `ingestion.ingest(data_paths)` returns a single clean DataFrame with one row per student
- All data quality issues are logged; no single bad record crashes the pipeline
- The canonical DataFrame schema is frozen — all downstream phases (2–8) depend on it

This phase does NOT implement risk scoring, LLM calls, or any output file generation.

</domain>

<decisions>
## Implementation Decisions

### Synthetic Data Profile (src/generate_data.py)
- **D-01:** Generate **20 campuses**, **15 students each** = 300 students total. Covers all 3 CSVs: `data/student_daily_metrics.csv`, `data/facilitator_notes.csv`, `data/student_metadata.csv`
- **D-02:** Use **seeded random** — `numpy.random.seed(42)` at the top of `generate_data.py`. Reproducible across runs; test assertions against specific output values will work reliably
- **D-03:** Edge case density: **~5% missing numeric values**, **~3% duplicate student_id rows**, **~2% type mismatches** (e.g., "abc" in a numeric column). Realistic enough to exercise all DATA-03, DATA-04, DATA-05 code paths without overwhelming the logs
- **D-04:** Risk level distribution baked into synthetic data: approximately **15% CRITICAL**, **25% HIGH**, **40% MEDIUM**, **20% LOW** — achieved by controlling attendance/practice distributions per student cohort

### run_log.json Schema (initialized in Phase 1)
- **D-05:** Initialize the **full run_log.json structure** from Phase 1, even though API fields are empty until Phase 3. Schema:
  ```json
  {
    "run_timestamp": "ISO-8601",
    "students_processed": 0,
    "api_calls_made": 0,
    "tokens_used": {"input": 0, "output": 0},
    "errors_encountered": [],
    "fallbacks_triggered": 0,
    "data_quality_warnings": []
  }
  ```
- **D-06:** Build the log dict **in memory throughout the run**, write it **once at pipeline end** via `output_generator`. Atomic write, no partial files, no file locking needed

### config.py Scope and Validation
- **D-07:** Define **all constants in Phase 1** — both column name constants AND risk threshold constants, even though Phase 2 uses the thresholds. Single source of truth from day 1:
  - Column constants: `COL_STUDENT_ID`, `COL_CAMPUS_ID`, `COL_PARENT_PHONE`, `COL_NOTE_DATE`, `COL_SESSION_MIN`, `COL_PRACTICE_Q`, `COL_RISK_SCORE`, `COL_RISK_LEVEL`, etc.
  - Risk thresholds: `RISK_THRESHOLD_CRITICAL = 75`, `RISK_THRESHOLD_HIGH = 50`, `RISK_THRESHOLD_MEDIUM = 25`
  - Weight constants: `WEIGHT_ATTENDANCE = 0.35`, `WEIGHT_PRACTICE = 0.30`, `WEIGHT_TREND = 0.20`, `WEIGHT_NOTES = 0.15`
- **D-08:** **Only `ANTHROPIC_API_KEY` fails loudly** with `os.environ["ANTHROPIC_API_KEY"]` at import time. `DATA_DIR`, `OUTPUT_DIR`, `DOCS_DIR` use `os.getenv("DATA_DIR", "data")` with safe string defaults — avoids forcing the user to set obvious paths

### Ingestion Error Handling (src/ingestion.py)
- **D-09:** Missing or unparseable **numeric columns** (`session_attended_min`, `practice_questions`) → **fill with 0**, log `WARNING` with student_id and column name. Matches DATA-03 requirement explicitly. 0 = no activity, conservative risk.
- **D-10:** Missing or unparseable **ID columns** (`student_id`, `campus_id`) → **assign placeholder** (`UNKNOWN_001`, `UNKNOWN_002`, etc., auto-incremented), log `WARNING`. Preserves the row for downstream analysis rather than silently discarding it.
- **D-11:** Bad **date format** in `note_date` or `metric_date` → **assign `NaT`** (pandas Not-a-Time), log `WARNING`. Preserves the full student row. Risk engine (Phase 2) treats `NaT` note_date as maximum `days_since_last_note` penalty.

### Claude's Discretion
- Exact column names in each of the 3 CSVs (derive from risk formula requirements in DATA-01/RISK requirements)
- Merge strategy: aggregate `student_daily_metrics` from per-day to per-student before join; `facilitator_notes` → latest note date per student before join; `student_metadata` → base table
- `src/generate_data.py` is a standalone script, not imported by `main.py` — it runs independently to populate `data/`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/REQUIREMENTS.md` §DATA-01 to DATA-08 — exact ingestion requirements
- `.planning/REQUIREMENTS.md` §INFRA-01 to INFRA-09 — exact infrastructure requirements

### Project Decisions and Pitfalls
- `CLAUDE.md` — critical pitfalls (dtype mapping, PatternFill, respx, JSON escaping, os.environ), code standards, and module contracts
- `.planning/STATE.md` §Known Pitfalls — 7 specific pitfalls that MUST be pre-empted in Phase 1 code
- `.planning/STATE.md` §Accumulated Context — locked stack versions and module signatures

### Research
- `.planning/research/STACK.md` — pinned versions and why each library was chosen
- `.planning/research/PITFALLS.md` — extended pitfall list from research phase
- `.planning/research/ARCHITECTURE.md` — module interaction diagram and data flow

### Success Criteria (Phase 1)
- `.planning/ROADMAP.md` §Phase 1 — 5 success criteria that define "done" for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing code to reuse or extend.

### Established Patterns
- Module contracts are pre-defined in STATE.md:
  - `ingestion.ingest(data_paths: dict[str, Path]) -> pd.DataFrame`
  - `risk_engine.score_risk(df: pd.DataFrame) -> pd.DataFrame`
  - `llm_engine.enrich_with_llm(df, api_key) -> pd.DataFrame`
  - `output_generator.write_outputs(df, output_dir) -> dict[str, Path]`
  - These signatures are LOCKED — downstream phases depend on them

### Integration Points
- `main.py` calls `ingestion.ingest()` and passes its return value directly to `risk_engine.score_risk()` in Phase 2 — the DataFrame schema frozen in Phase 1 gates all downstream work

</code_context>

<specifics>
## Specific Ideas

- `src/generate_data.py` is invoked via `make demo` (not `main.py`) to populate `data/` before the pipeline runs
- `make demo` sequence: generate data → run pipeline → print summary. `make test` runs pytest. `make clean` removes `outputs/`
- `README.md` must be ≤30 lines — trim ruthlessly, it's a demo repo

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Foundation + Data Ingestion*
*Context gathered: 2026-05-21*
