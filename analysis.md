# Analysis: boon-academy-intervention

## Diagnosis

Boon Academy runs 20 campuses serving roughly 300 students, and only ~30% of
at-risk students receive any intervention before the next quiz. The root cause
is not indifference — facilitators are overwhelmed managing parallel classrooms
and have no prioritised view of which students to contact or what to say. Without
a tool that surfaces the right student and drafts the outreach, intervention rate
will collapse entirely as the academy scales from 1,000 to 5,000 students.

## What You Found

- **67 students flagged HIGH or CRITICAL** out of 300 at Day 14 — these are the
  students at immediate risk before Quiz 2 on Day 20.
- **9 duplicate student IDs** removed during ingestion; additional records had
  missing session minutes and blank parent phone numbers, all auto-resolved.
- **30 LLM fallbacks triggered** out of 300 students (10%): real run data confirms
  the three-layer fallback is not theoretical — it fired on live inputs.

## What You Built

- **Ingestion layer** — auto-resolves messy operational data (missing values, type
  mismatches, duplicates) so the pipeline never halts on bad input.
- **Deterministic risk scoring** — weighted formula (attendance 35%, practice 30%,
  trend 20%, notes 15%) produces auditable scores with no training data required.
- **LLM enrichment engine** — campus-batched Claude API calls draft WhatsApp
  parent messages and campus action summaries; three-layer fallback ensures output
  is always produced even when the API is unavailable.
- **Output generator** — six files covering every facilitator workflow: ranked
  Excel priority list, per-campus dashboards, WhatsApp CSV, self-contained HTML
  dashboard, and executive Word report.
- **Documentation suite** — nine reference docs (architecture, security,
  scalability, data handling) so the one part-time maintainer can operate the
  system independently after handoff.

## What You Cut

- **No ML model** — deterministic weighted scoring is auditable and needs no
  labelled historical outcome data; adding ML before validating that the data
  even exists would be premature optimisation.
- **No direct WhatsApp API sending** — WhatsApp Business API requires business
  account verification that can take weeks; facilitators copy-pasting from the
  generated CSV is the safe, immediately shippable v1 path.

## What Next

Connect the system to real student data exports and validate the risk weights
with the academic director — until the model runs on live data and its output is
confirmed against known outcomes, every intervention priority is an educated guess.
