---
phase: "06-documentation-suite"
plan: "01"
subsystem: "content-library"
tags: [yaml, documentation, content-authoring]
dependency_graph:
  requires: []
  provides: ["src/templates/docs_content.yaml"]
  affects: ["src/doc_generator.py"]
tech_stack:
  added: ["PyYAML 6.0.3 (already installed)"]
  patterns:
    - "YAML >- block scalars for all text values containing special characters"
    - "Hybrid pattern (architecture/data_handling/scalability): paragraph opener + bullets"
    - "Narrative pattern (security/engineering_decisions/system_design/alternatives): 2-4 paragraphs per section"
key_files:
  created:
    - src/templates/docs_content.yaml
  modified: []
decisions:
  - "Single YAML file for all 7 static docs — loaded once at doc_generator.py import (D-04)"
  - "D-14 content depth rules applied: hybrid docs scan-friendly (bullets), narrative docs argumentative (paragraphs)"
  - "Real D-13 numbers embedded: 300 students, 14 API calls, 31,771 tokens, 106 tokens/student"
  - "Cost projection in scalability: 63,600 tokens/run at 100 campuses, ~$11.45/month vs $200/month budget"
metrics:
  duration: "~8 min"
  completed: "2026-05-24"
  tasks_completed: 2
  files_created: 1
---

# Phase 6 Plan 01: YAML Content Library Summary

## One-liner

YAML content library with 7 static documentation blocks — hybrid (paragraph+bullets) for architecture/data_handling/scalability and narrative (2-4 paragraphs) for security/engineering_decisions/system_design/alternatives.

## What Was Built

`src/templates/docs_content.yaml` — 988 lines of structured YAML containing the full authored content for all 7 static documentation files that `doc_generator.py` will render into .docx format. The file follows the D-06 schema (`title`, `sections` with `heading` and `body`, body items with `type: paragraph | bullet` and `text`) and applies the D-14 content depth rules throughout.

### Document Inventory

| Doc Key | Title | Sections | Pattern | Requirements |
|---------|-------|----------|---------|--------------|
| architecture | System Architecture | 4 | Hybrid | DOCS-03 |
| data_handling | Data Handling | 5 | Hybrid | DOCS-06 |
| scalability | Scalability Analysis | 4 | Hybrid | DOCS-07 |
| security | Security Design | 4 | Narrative | DOCS-04 |
| engineering_decisions | Engineering Decisions | 5 | Narrative | DOCS-05 |
| system_design | System Design and AI Integration | 5 | Narrative | DOCS-08 |
| alternatives | Alternatives Considered | 4 | Narrative | DOCS-09 |

### Key Content Highlights

**architecture:** 5-stage pipeline flow (ingestion → risk_engine → llm_engine → output_generator → doc_generator), ASCII diagram, per-module descriptions (when/why it runs), technology choice rationale (pandas 2.2.3, openpyxl, python-docx 1.1.2, PyYAML, anthropic 0.103.1, respx), and explicit comparison against n8n/Zapier/Airtable alternatives.

**data_handling:** Input schema with dtype override explanation, 4-step cleaning pipeline (type coercion → dedup → missing fill → derived columns), conservative missing-data strategy (fill with 0 = maximum risk), edge case inventory (9 dupe IDs, ~84 type-mismatch cells, ~210 blank cells), and 2-step merge logic (metadata LEFT JOIN metrics LEFT JOIN notes).

**scalability:** Current scale baseline (300 students / 20 campuses / 14 API calls / 31,771 tokens), bottleneck analysis at 100 campuses (API call count, sequential xlsx writes, memory), CSV → SQLite → PostgreSQL migration path with per-phase guidance, and cost projection: 63,600 tokens/run → ~$11.45/month at 100 campuses vs $200/month budget (17x headroom).

**security:** env-var-only API key via `os.environ["ANTHROPIC_API_KEY"]` (fail-loud, never logged, never in outputs, audited run_log with exactly 7 safe keys), PII masking (names/phones never in logs, API receives only anonymised engagement metrics at campus-cohort level), data retention recommendation (delete outputs/ same day, no intermediate persistence), and access control guidance (OS-level file permissions, single-machine model).

**engineering_decisions:** Deterministic risk formula rationale (no ML — no outcome labels yet, weights are unvalidated assumptions needing academic director review), LLM batching strategy (14 vs ~120 API calls, cohort context, MAX_STUDENTS_PER_LLM_CALL=10 bound), three-layer fallback (SDK retry → re-prompt → template, generated_by:template tagging), output format choices (openpyxl read+write for tests, utf-8-sig for Arabic CSV, self-contained HTML), and intentional simplicity (no Docker/auth server/message queue at current scale).

**system_design:** AI role scoped to text generation only (not scoring, not sending, not data access), boundaries enforced by pipeline architecture, claude-sonnet-4-5 selection rationale, cost/accuracy/latency tradeoffs (batching = 9x cost reduction), human review loop (facilitator reviews before sending, generated_by column makes provenance explicit), and three failure modes (API down → template fallback, malformed CSV → conservative fill, empty campus → skip gracefully).

**alternatives:** Risk scoring alternatives (ML deferred — no outcome labels yet, rule-only loses personalisation), delivery alternatives (n8n/Zapier: no version control or unit tests; WhatsApp Business API: carrier approval + per-message cost + persistent server), infrastructure alternatives (Docker deferred, cloud scheduler deferred, SQLite documented as next migration step), and prioritised "what to build next" (real data → weight calibration → dialect selection → scheduled trigger).

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 | Author all 7 doc blocks (hybrid + narrative) | 2491b8b | src/templates/docs_content.yaml |

Note: Both tasks were executed together as a single atomic authoring session. The YAML file was created whole with all 7 keys, then both Task 1 and Task 2 verification scripts confirmed correctness before the single commit.

## Deviations from Plan

None — plan executed exactly as written. Tasks 1 and 2 were committed together since the YAML file is a single artefact; both verification scripts passed before commit.

## Known Stubs

None. The YAML file contains complete, substantive prose — no placeholder text, no TODO markers, no "coming soon" entries.

## Threat Flags

None. The YAML file is a static content file with no secrets, no user input, no network endpoints, and no executable code. yaml.safe_load() is the only load path (yaml.load() is never used anywhere in the file or in the loading pattern). T-06-01 and T-06-SC from the plan's threat register are both satisfied.

## Self-Check

Files exist:
- [x] src/templates/docs_content.yaml — confirmed (988 lines, 1 file added in commit 2491b8b)

Commits exist:
- [x] 2491b8b — confirmed via `git rev-parse --short HEAD`

Verification scripts:
- [x] Task 1 automated check: `hybrid docs OK`
- [x] Task 2 automated check: `ALL 7 docs validated OK`
- [x] Content requirements: scalability $200/month + CSV->SQLite->PostgreSQL confirmed
- [x] Content requirements: security env-var + PII masking + data retention confirmed
- [x] Pattern compliance: hybrid docs have paragraph opener in every section
- [x] Pattern compliance: narrative docs have 2+ paragraphs in every section
- [x] Final plan verification: all 7 keys printed by `yaml.safe_load()` check

## Self-Check: PASSED
