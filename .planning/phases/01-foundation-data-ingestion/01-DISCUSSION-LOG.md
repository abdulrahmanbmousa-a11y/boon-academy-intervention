# Phase 1: Foundation + Data Ingestion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 1-Foundation + Data Ingestion
**Areas discussed:** Synthetic data profile, run_log.json scope, config.py constants scope, Ingestion error handling detail

---

## Synthetic Data Profile

| Option | Description | Selected |
|--------|-------------|----------|
| 3 campuses, 15 students each (45 total) | Small and fast. Tests run in milliseconds. | |
| 5 campuses, 20 students each (100 total) | Round numbers, still fast. | |
| 18 campuses, ~30 students each (~540 total) | Matches real Boon Academy scale. | |
| 20 campuses, 15 students each (300 total) | User-specified custom profile. | ✓ |

**User's choice:** 20 campuses, 15 students each = 300 students total

| Option | Description | Selected |
|--------|-------------|----------|
| Seeded random (numpy.random.seed(42)) | Reproducible, looks realistic. | ✓ |
| Fully deterministic patterns | Manual rows, exact control. | |
| Unseeded random | Different data each run. | |

**User's choice:** Seeded random — reproducible across runs.

| Option | Description | Selected |
|--------|-------------|----------|
| Realistic sparse (~5% missing, ~3% dups, ~2% type mismatches) | Mirrors real data. | ✓ |
| Heavy edge cases (~15-20% issues) | Very visible in demo. | |
| Minimal edge cases (1-2 per CSV) | Fast to eyeball. | |

**User's choice:** Realistic sparse edge case density.

| Option | Description | Selected |
|--------|-------------|----------|
| Realistic distribution (~15% CRITICAL, ~25% HIGH, ~40% MEDIUM, ~20% LOW) | Matches real intervention scenario. | ✓ |
| Balanced across 4 levels (25% each) | Equal visibility. | |
| You decide | Claude picks distribution. | |

**User's choice:** Realistic distribution.

---

## run_log.json Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full structure from the start | All fields initialized now; Phase 3 fills API fields. | ✓ |
| Data quality events only | Minimal now, grow the schema later. | |

**User's choice:** Full structure from Phase 1 — consistent schema from day 1.

| Option | Description | Selected |
|--------|-------------|----------|
| Once at pipeline end | In-memory dict, atomic write at finish. | ✓ |
| Append incrementally during run | Per-event writes, safer on crash. | |

**User's choice:** Write once at end — simpler, atomic.

---

## config.py Constants Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All constants now (columns + risk thresholds + weights) | Single source of truth from day 1. | ✓ |
| Phase 1 columns only, add thresholds in Phase 2 | Less coupling now. | |

**User's choice:** All constants defined in Phase 1.

| Option | Description | Selected |
|--------|-------------|----------|
| Only ANTHROPIC_API_KEY fails loudly | DATA_DIR/OUTPUT_DIR/DOCS_DIR have safe defaults. | ✓ |
| All required vars fail loudly | Force explicit path configuration. | |
| You decide | Claude picks validation strategy. | |

**User's choice:** Only ANTHROPIC_API_KEY required at startup.

---

## Ingestion Error Handling Detail

| Option | Description | Selected |
|--------|-------------|----------|
| Fill with 0, log warning | DATA-03 explicit requirement. Conservative. | ✓ |
| Fill with column median, log warning | Less extreme, harder to test. | |
| Skip the row entirely, log warning | Loses student from output. | |

**User's choice (numeric columns):** Fill with 0, log warning with student_id + column name.

| Option | Description | Selected |
|--------|-------------|----------|
| Skip the row entirely, log warning | No ID = can't track. | |
| Assign placeholder ID (UNKNOWN_001, etc.), log warning | Preserves row for analysis. | ✓ |

**User's choice (ID columns):** Assign placeholder ID, preserve row.

| Option | Description | Selected |
|--------|-------------|----------|
| Assign NaT, log warning (preserves row) | Safe null for dates; risk engine handles NaT. | ✓ |
| Skip the entire row, log warning | Loses all student data due to one bad date. | |

**User's choice (date columns):** Assign NaT, log warning. Preserve the full student row.

---

## Claude's Discretion

- Exact CSV column names (derived from risk formula requirements)
- Merge/aggregation strategy: daily_metrics → per-student aggregate → join with metadata + notes
- `src/generate_data.py` as standalone script (not called by main.py)

## Deferred Ideas

None — discussion stayed within phase scope.
