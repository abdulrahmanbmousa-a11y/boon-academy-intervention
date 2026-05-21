# boon-academy-intervention

## What This Is

An AI-powered student intervention pipeline for Boon Academy (EdTech case study). It ingests 14 days of student attendance, practice, and facilitator note data, scores every student's risk of falling behind, generates a prioritized action list for facilitators, and drafts WhatsApp-ready parent messages using Claude AI. The system runs end-to-end with `python main.py` and produces Excel dashboards, a Word report, a standalone HTML dashboard, and all supporting documentation — designed to raise facilitator intervention rates from 30% to 80%+.

## Core Value

A facilitator opens their campus Excel file and immediately knows exactly which 3–5 students to contact today, with the message already written — no analysis required, no guessing.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Pipeline runs end-to-end with `python main.py` on 3 CSV input files
- [ ] Risk scoring (0–100) per student using weighted formula: attendance 35%, practice consistency 30%, trend 20%, days since last note 15%
- [ ] Risk levels: CRITICAL (≥75), HIGH (50–74), MEDIUM (25–49), LOW (<25)
- [ ] Claude API generates 2-sentence facilitator action summary per CRITICAL/HIGH student
- [ ] Claude API generates WhatsApp-ready parent message (<100 words) per CRITICAL/HIGH student
- [ ] Batching by campus (one API call per campus's at-risk students)
- [ ] Fallback to rule-based template on API failure, clearly labeled
- [ ] `outputs/intervention_priority_list.xlsx` — color-coded, ranked, all students
- [ ] `outputs/facilitator_dashboard_{campus_id}.xlsx` — per-campus, self-contained
- [ ] `outputs/whatsapp_messages.csv` — ready to copy-paste
- [ ] `outputs/intervention_report.docx` — executive summary, student deep-dives
- [ ] `outputs/facilitator_dashboard.html` — sortable, filterable, works via file://
- [ ] `outputs/run_log.json` — tokens, errors, fallbacks, runtime stats
- [ ] `docs/analysis.docx` + `analysis.md` — 5-section memo with real numbers
- [ ] `docs/architecture.docx` — ASCII diagram, component reasoning, why-not n8n/Airtable
- [ ] `docs/security.docx` — API key handling, PII masking, data retention
- [ ] `docs/engineering_decisions.docx` — rationale for every technical choice
- [ ] `docs/data_handling.docx` — schema, cleaning, imputation, edge cases
- [ ] `docs/scalability.docx` — 20 vs 100 campuses, migration path, cost projection
- [ ] `docs/system_design.docx` — AI choices, what's NOT AI, failure modes
- [ ] `docs/alternatives.docx` — what was cut and why, alternative approaches
- [ ] Synthetic data generation for all 3 CSV input files
- [ ] Full test suite: unit tests for risk formula, ingestion edge cases, LLM fallback, output files
- [ ] All paths/secrets from environment variables — zero hardcoded values
- [ ] `requirements.txt` pinned, `.env.example` documented, `Makefile` with demo target

### Out of Scope

- Real-time server / live dashboard — CSV batch is sufficient for 6-day Quiz 2 window
- SMS gateway integration — WhatsApp copy-paste achieves same outcome without carrier cost
- ML risk model — no training data; weighted deterministic rules beat a poorly-trained ML model
- n8n/Zapier automation — opaque for debugging, hard to version-control, 1 part-time engineer can't maintain visual workflows at 100 campuses
- Airtable as primary store — paid dependency, vendor lock-in; CSV → Google Sheets achieves same result
- Docker / Kubernetes — over-engineered for 20 campuses today
- OAuth / user authentication — single-user pipeline, not a multi-tenant app
- Video walkthrough generation — produced by user, not by the pipeline

## Context

**Business context:** Boon Academy (parallel-universe stand-in for Noon Academy, Saudi EdTech) runs hybrid test-prep classrooms. Day 14 of a 20-day cycle. Quiz 2 in 6 days. 18 campuses today, scaling to 100 next year.

**User context:** Facilitators are non-technical — comfortable with WhatsApp and Google Sheets, not dashboards. Every tool they must learn is a tool that won't get used. The system must slot into their existing workflow, not replace it.

**Technical context:** Single engineer will maintain this. Simplicity and debuggability beat elegance. Python + pandas + openpyxl + python-docx + Anthropic SDK is the entire stack — all well-documented, all easily Googled.

**Data context:** 3 CSV files covering 14 days. Data is messy (missing values, type mismatches, duplicates). Pipeline must log warnings and continue, never crash on a single bad record.

**Submission context:** This is an interview case study. The repo, outputs/, analysis files, and a Loom video walkthrough are the four required deliverables. Code must run from a fresh clone. No hardcoded paths or API keys.

## Constraints

- **Budget**: $200/month — Claude API costs must fit; campus-level batching is the cost control
- **Team**: 1 part-time engineer post-launch — no framework requiring specialist knowledge
- **Timeline**: 6 days to Quiz 2 — pipeline must work today, not after a 2-week setup
- **Users**: Non-technical facilitators — Excel + WhatsApp is the delivery interface
- **Scale target**: 100 campuses, 5,000 students in 6 months — architecture must have a clear migration path
- **Tech stack**: Python 3.11+, Anthropic Claude API (`claude-sonnet-4-5`), pandas, openpyxl, python-docx, pytest
- **Security**: API key via env var only, PII masked in all logs, no raw API responses in outputs
- **Code quality**: Type hints on all functions, Python `logging` module (no print), docstrings on all public classes/methods, constants in config.py

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Deterministic risk scoring (not ML) | No training data; weighted rules are auditable, explainable, and don't overfit | — Pending |
| Campus-level LLM batching | Reduces API calls ~10x vs per-student; preserves cohort context in prompt | — Pending |
| Rule-based fallback templates | Reliability at scale requires graceful degradation; labeled clearly so facilitators know | — Pending |
| Excel for facilitator deliverable | Facilitators already use Google Sheets; no new tool to learn | — Pending |
| HTML dashboard (file://) | Shareable without a server; single-file, self-contained; works offline | — Pending |
| python-docx for Word reports | Native .docx generation without Word installed; cross-platform | — Pending |
| Synthetic data generation | No real PII in the repo; reproducible demo; tests against known values | — Pending |
| analysis.md + analysis.docx both | assignment.txt requires .md; user spec requires .docx; both = zero risk | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-21 after initialization*
