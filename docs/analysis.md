# Analysis: boon-academy-intervention

## Diagnosis

Boon Academy runs 20 campuses serving roughly 300 students. Facilitator
intervention rate is currently ~30% against an 80%+ target. The gap exists
because facilitators lack a fast, prioritised view of which students to contact
and what to say. This pipeline closes that gap by scoring every student daily,
ranking them by risk, and generating draft WhatsApp messages that facilitators
send in one click.

## What You Found

Student intake: 300 students processed in this run.
Risk distribution at runtime:

- CRITICAL: 1
- HIGH: 79
- MEDIUM: 173
- LOW: 47

Duplicate student IDs removed during ingestion: 9. All data quality
issues (missing metrics, type-mismatch strings, blank notes) were auto-resolved
by the ingestion layer — no manual cleanup required.

## What You Built

A five-stage pipeline: ingest → score → LLM enrich → outputs → docs.

LLM usage this run: 7 API calls, 17558 tokens total
(11258 input + 6300 output). Fallbacks triggered: 43.

Output files produced per run:

- intervention_priority_list.xlsx — ranked student list, colour-coded by risk
- campus_dashboard_<id>.xlsx — one tab per campus with LLM summaries
- whatsapp_messages.csv — ready-to-send parent messages (UTF-8 BOM for Arabic)
- dashboard.html — self-contained, filterable HTML dashboard (no server needed)
- intervention_report.pdf — executive summary with per-campus tables
- docs/ — nine technical reference documents (this suite)

## What You Cut

- No ML model — would require labeled historical outcome data; deterministic
  weighted scoring is auditable and needs no training data.
- No real-time server — on-demand script run fits current facilitator workflow;
  scheduled trigger can be added later with cron or Task Scheduler.
- No OAuth or SSO — out of scope for v1; outputs are file-based, not a web app.
- No Docker or Kubernetes — single-machine Python script; no orchestration layer needed.
- No direct WhatsApp API sending — WhatsApp Business API requires business
  verification; facilitators copy-paste from CSV as the safe v1 path.

## What Next

1. Hook up real student data — replace synthetic CSVs with live exports.
2. Validate risk weights with the academic director — defaults (attendance 35%,
   practice 30%, trend 20%, notes 15%) are reasonable starting points only.
3. Confirm Arabic dialect per campus — Modern Standard vs. Gulf dialect affects
   message naturalness; update the LLM prompt system message accordingly.
4. Test outputs on LibreOffice — facilitator PCs may not have Excel; verify
   .xlsx colour-coding and column widths render correctly.
5. Consider a scheduled daily trigger — a cron job or Windows Task Scheduler
   entry replaces the manual `python main.py` step.
