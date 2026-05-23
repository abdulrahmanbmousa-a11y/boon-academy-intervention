# Phase 3: Claude API Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 3-Claude API Integration
**Areas discussed:** Fallback templates, Batch overflow, Output column schema

---

## Fallback Templates

### Q1: Where should fallback template content live?

| Option | Description | Selected |
|--------|-------------|----------|
| YAML file (llm_templates.yaml) | Stored at runtime, easy to edit without touching Python code | ✓ |
| Hardcoded in llm_engine.py | Simpler, no file I/O, but mixes content and logic | |
| In config.py as constants | Works for 2-3 variants but unwieldy with many combinations | |

**User's choice:** YAML file (llm_templates.yaml)

---

### Q2: How differentiated should fallback templates be?

| Option | Description | Selected |
|--------|-------------|----------|
| By risk_level only — 2 variants | One set for CRITICAL, one for HIGH. Error type doesn't change what facilitator does | ✓ |
| By risk_level × error type — 6+ variants | Separate templates per error condition × risk level. Complex to maintain | |
| One universal fallback template | Single generic template for all failures | |

**User's choice:** By risk_level only — 2 variants (CRITICAL and HIGH)

---

### Q3: Should fallback templates use student-specific data or be generic?

| Option | Description | Selected |
|--------|-------------|----------|
| Generic text only | No interpolation. Simpler, avoids PII in templates | |
| Inject risk_level + campus_id only | Minimal data, no names or phones | |
| Full interpolation with student data | Templates use scored column values. More personalized | ✓ |

**User's choice:** Full interpolation with student data

---

### Q4: Which student fields available for interpolation?

| Option | Description | Selected |
|--------|-------------|----------|
| student_name + risk_level + attendance_rate + days_since_last_note | Key fields for actionability | |
| All scored columns from score_risk() output | Maximum flexibility | ✓ |
| student_name + risk_level only | Minimal, simple templates | |

**User's choice:** All scored columns from score_risk() output (parent_phone excluded — not a scored column)

---

## Batch Overflow

### Q1: When campus has >10 CRITICAL+HIGH students, how to process?

| Option | Description | Selected |
|--------|-------------|----------|
| Multiple sequential API calls in chunks of 10 | All students get LLM messages; higher cost but complete coverage | ✓ |
| Truncate to top 10 by risk_score | Predictable cost but students #11+ silently downgraded | |
| One call regardless of count | Ignores the configurable MAX_STUDENTS_PER_LLM_CALL limit | |

**User's choice:** Multiple sequential API calls in chunks of MAX_STUDENTS_PER_LLM_CALL

---

### Q2: How should students be ordered within campus before chunking?

| Option | Description | Selected |
|--------|-------------|----------|
| CRITICAL first then HIGH, both by risk_score descending | Most urgent cases in first chunk; later-chunk failures hit lower-priority students | ✓ |
| By risk_score descending only | Same effect in practice since CRITICAL always has higher scores | |

**User's choice:** CRITICAL first, then HIGH, both sorted by risk_score descending

---

## Output Column Schema

### Q1: Which columns does enrich_with_llm() add?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 core columns only | facilitator_summary, whatsapp_message, generated_by | |
| 3 core + error_reason | 4th column tracks failure type for debugging | ✓ |
| 3 core + model_used + batch_id | Full auditability but overkill for v1 | |

**User's choice:** 4 columns — facilitator_summary, whatsapp_message, generated_by, llm_error_reason

---

### Q2: What values for MEDIUM/LOW students (no LLM call)?

| Option | Description | Selected |
|--------|-------------|----------|
| Empty string for all 4 columns | Consistent, no null-handling downstream | |
| None/NaN for message columns, 'skipped' for generated_by | Explicit sentinel for "no generation attempted" | ✓ |

**User's choice:** None/NaN for message columns; then revised in Q3 —

---

### Q3: Allowed values for generated_by?

| Option | Description | Selected |
|--------|-------------|----------|
| 'llm' / 'template' / 'skipped' | Three clear states | |
| 'llm' / 'template' only | MEDIUM/LOW get None/NaN in generated_by too | ✓ |

**User's choice:** 'llm' / 'template' only — MEDIUM/LOW get None/NaN in generated_by (consistent with all 4 columns)

---

## Claude's Discretion

- **Prompt design** — content, tone, and structure of the campus batch prompt not discussed; left to Claude. Constraints: facilitator summary = 2 sentences, WhatsApp = <100 words. Student PII (name, phone) excluded from API prompt.
- **run_log integration pattern** — whether `enrich_with_llm()` accepts `run_log` as mutable parameter or returns counts; planner to decide.
- **Template file load timing** — load once at module import vs. per-call; Claude's call.

## Deferred Ideas

- Arabic/Gulf dialect WhatsApp messages — v2, requires campus-level language config
- Async/concurrent LLM calls for multiple campuses — FUTV2-05, needed at 5,000+ students
- Per-student API calls instead of campus batching — explicitly out of scope (LLM-02)
