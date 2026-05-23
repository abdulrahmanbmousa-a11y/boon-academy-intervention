# Phase 4: Excel + CSV Output Generation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 4-Excel-CSV-Output-Generation
**Areas discussed:** Signature extension, Campus dashboard columns, Color palette, Phase 4 scope boundary

---

## Signature Extension

| Option | Description | Selected |
|--------|-------------|----------|
| Add run_log as 3rd kwarg | `write_outputs(df, output_dir, run_log: dict)` — matches main.py comment exactly, explicit contract | ✓ |
| Keep 2-arg signature | write_outputs() builds a minimal run_log from observations; main.py patches in api/token counts after | |
| Pass via df.attrs | Store run_log in df.attrs before calling; avoids signature change but df.attrs is fragile in pandas 2.2.x | |

**User's choice:** Add run_log as 3rd kwarg (required, no default)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Required — no default | Forces callers to always pass run_log; fail loudly if omitted | ✓ |
| Optional with default None | write_outputs(df, output_dir, run_log=None); adds if-branch for skipping run_log.json | |

**User's choice:** Required — no default

---

| Option | Description | Selected |
|--------|-------------|----------|
| Dict of all output paths | `{'priority_list': Path(...), 'campus_X': Path(...), ...}` — semantic keys, safe for test assertions | ✓ |
| List of Path objects | Simpler but index-based assertions; fragile if order changes | |
| None | No return value; callers reconstruct paths themselves | |

**User's choice:** Dict of all output paths

---

## Campus Dashboard Columns

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include LLM cols for CRITICAL/HIGH | Campus Excels show facilitator_summary + whatsapp_message + generated_by alongside 12 standard cols | ✓ |
| No — strictly same 12 cols as OUT-01 | Campus Excels match OUT-01 column-for-column; facilitator cross-references whatsapp CSV separately | |
| You decide | Claude picks the most useful layout for facilitators | |

**User's choice:** Yes — include LLM columns (facilitator_summary, whatsapp_message, generated_by). All students shown; MEDIUM/LOW have empty cells in LLM columns.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Empty cells | Blank for MEDIUM/LOW in LLM columns | ✓ |
| N/A or dash text | Write "N/A" or "-" — more explicit but adds noise | |
| Omit those rows | Campus dashboard shows only CRITICAL/HIGH students | |

**User's choice:** Empty cells

---

## Color Palette

| Option | Description | Selected |
|--------|-------------|----------|
| Soft pastel palette | CRITICAL: FFCCCC, HIGH: FFE5CC, MEDIUM: FFFFCC, LOW: CCFFCC — readable on all backgrounds | ✓ |
| Bold/saturated palette | CRITICAL: FF0000, HIGH: FFA500, MEDIUM: FFFF00, LOW: 00FF00 — high contrast but harsh | |
| You decide | Claude picks most legible palette for a working spreadsheet | |

**User's choice:** Soft pastel palette

---

| Option | Description | Selected |
|--------|-------------|----------|
| Dark blue/navy header | #1F4E79 fill, white bold text — standard professional look | ✓ |
| Medium grey header | #D9D9D9 fill, black bold text — subtle, neutral | |
| White with bold only | No background fill; relies purely on bold for distinction | |

**User's choice:** Dark blue/navy header (#1F4E79)

---

## Phase 4 Scope Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 4 writes 4 files; Phase 5 extends same function | Phase 5 adds _write_report() and _write_html_dashboard() helpers to same write_outputs() | ✓ |
| Phase 4 adds NotImplementedError stubs for Phase 5 | Explicit forward declaration but adds dead code to Phase 4 | |
| Phase 5 uses separate write_phase5_outputs() function | Two public entry points; main.py calls both; clean separation but two points to coordinate | |

**User's choice:** Phase 4 writes 4 files only; Phase 5 extends the same function with additional private helpers.

---

| Option | Description | Selected |
|--------|-------------|----------|
| mkdir(parents=True, exist_ok=True) at entry | write_outputs() always ensures output_dir exists — idempotent | ✓ |
| Caller is responsible | main.py calls mkdir() before write_outputs() | |

**User's choice:** mkdir at entry (idempotent)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Private helper per output file | _write_priority_list(), _write_campus_dashboards(), _write_whatsapp_csv(), _write_run_log() | ✓ |
| Single function body | All logic inline; simpler but 250+ lines in one function | |

**User's choice:** Private helper per output file

---

## Claude's Discretion

- Auto column width calculation: `max(len(str(v)) for v in col_values)` capped at 60
- whatsapp_messages.csv encoding: UTF-8 with BOM (`utf-8-sig`) for Excel compatibility with Arabic characters
- Campus dashboard summary row layout: Claude to decide cleanest positioning relative to header row and frozen panes

## Deferred Ideas

- `intervention_report.docx` (OUT-04) — Phase 5
- `facilitator_dashboard.html` (OUT-05) — Phase 5
- Per-campus color theming — out of scope for v1
- Excel charts/sparklines — FUTV2, adds xlsxwriter dependency conflict
