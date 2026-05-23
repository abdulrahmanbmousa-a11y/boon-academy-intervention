# Phase 4: Excel + CSV Output Generation - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `src/output_generator.py` — `write_outputs(df, output_dir, run_log)` that writes 4 output files from the fully-enriched one-row-per-student DataFrame:

1. `outputs/intervention_priority_list.xlsx` — all students ranked by risk_score desc, color-coded rows, bold navy header, frozen top row, auto column widths (OUT-01)
2. `outputs/facilitator_dashboard_{campus_id}.xlsx` — one file per campus, same Excel formatting, plus LLM columns for CRITICAL/HIGH students, summary row at top (OUT-02)
3. `outputs/whatsapp_messages.csv` — all CRITICAL/HIGH students with message_text and generated_by (OUT-03)
4. `outputs/run_log.json` — pipeline run metadata dict flushed once at pipeline end (OUT-06)

Phase 4 does NOT implement `intervention_report.docx` (Phase 5 / OUT-04) or `facilitator_dashboard.html` (Phase 5 / OUT-05). Phase 5 will extend `write_outputs()` with additional private helpers.

</domain>

<decisions>
## Implementation Decisions

### Function Signature (D-01 through D-03)

- **D-01 (Signature):** `write_outputs(df: pd.DataFrame, output_dir: Path, run_log: dict) -> dict[str, Path]`
  — `run_log` is a **required** positional parameter (no default). Fails loudly if omitted. Updates STATE.md contract from the 2-arg stub.
  — `main.py` wiring: `paths = output_generator.write_outputs(df, cfg.OUTPUT_DIR, run_log)` (matches the comment already on line 87).

- **D-02 (Return value):** Returns a dict mapping semantic keys to resolved `Path` objects. Example:
  ```python
  {
      "priority_list": Path("outputs/intervention_priority_list.xlsx"),
      "campus_ALPHA": Path("outputs/facilitator_dashboard_ALPHA.xlsx"),
      "campus_BETA": Path("outputs/facilitator_dashboard_BETA.xlsx"),
      "whatsapp": Path("outputs/whatsapp_messages.csv"),
      "run_log": Path("outputs/run_log.json"),
  }
  ```
  Campus files use `f"campus_{campus_id}"` as the dict key.

- **D-03 (Directory creation):** `write_outputs()` calls `output_dir.mkdir(parents=True, exist_ok=True)` at entry — idempotent, no caller setup required.

### Internal Structure (D-04)

- **D-04 (Private helpers):** One private helper per output type:
  - `_write_priority_list(df, output_dir) -> Path`
  - `_write_campus_dashboards(df, output_dir) -> dict[str, Path]`
  - `_write_whatsapp_csv(df, output_dir) -> Path`
  - `_write_run_log(run_log, output_dir) -> Path`
  
  `write_outputs()` orchestrates the four helpers and merges their results into the return dict. Each helper is independently testable.

### Campus Dashboard Columns (D-05 through D-06)

- **D-05 (Column scope):** Per-campus Excel files include the standard 12 OUT-01 columns **plus** 3 LLM columns: `facilitator_summary`, `whatsapp_message`, `generated_by`. Total: 15 columns per campus file.
  — Facilitators get the full picture in one file without cross-referencing the CSV.

- **D-06 (MEDIUM/LOW LLM cells):** MEDIUM and LOW students appear in campus dashboards with **empty cells** in the 3 LLM columns. No "N/A" text — just blank. Downstream display logic null-checks `generated_by`.

### Color Palette (D-07 through D-08)

- **D-07 (Row fill colors — soft pastel):**
  | Risk Level | Hex (6-char) | openpyxl (8-char, FF prefix) |
  |------------|-------------|------------------------------|
  | CRITICAL   | `FFCCCC`    | `FFFFCCCC` → assert `"00FFCCCC"` NO — use `"FFFFCCCC"` |
  | HIGH       | `FFE5CC`    | `FFFFE5CC`                   |
  | MEDIUM     | `FFFFCC`    | `FFFFFFCC`                   |
  | LOW        | `CCFFCC`    | `FFCCFFCC`                   |

  **openpyxl PatternFill pattern:** `PatternFill(fill_type="solid", fgColor="FFFFCCCC")` — always include `fill_type="solid"` or no color renders (CLAUDE.md pitfall).
  **Test assertion:** `assert cell.fill.fgColor.rgb == "FFFFCCCC"` — 8-char hex with `FF` alpha prefix (not 6-char).

- **D-08 (Header row):** Row 1 (column headers): `fgColor="FF1F4E79"` (dark navy fill), white bold text (`Font(bold=True, color="FFFFFFFF")`). Clearly distinct from data rows.
  — Header row is also frozen: `ws.freeze_panes = "A2"` (freeze row 1, scroll from row 2).

### Phase 4 Scope Boundary (D-09)

- **D-09 (Phase 5 extension):** Phase 5 adds `_write_report()` and `_write_html_dashboard()` as private helpers in the same `output_generator.py` and calls them from `write_outputs()`. Phase 4 does NOT add stub/NotImplementedError placeholders for Phase 5 outputs — no dead code in Phase 4.
  — Phase 5 will also update the return dict to include `"report"` and `"dashboard"` keys.

### Formatting Constants (D-10)

- **D-10 (New config constants needed):** Add to `src/config.py` before implementing `output_generator.py`:
  ```python
  # Phase 4 output formatting constants
  COLOR_CRITICAL: str = "FFFFCCCC"   # light red (8-char openpyxl format)
  COLOR_HIGH: str = "FFFFE5CC"        # light orange
  COLOR_MEDIUM: str = "FFFFFFCC"      # light yellow
  COLOR_LOW: str = "FFCCFFCC"         # light green
  COLOR_HEADER: str = "FF1F4E79"      # dark navy
  FONT_WHITE: str = "FFFFFFFF"        # white (for header text)
  
  # OUT-01 column order (12 cols) — must match REQUIREMENTS.md OUT-01 spec exactly
  OUTPUT_COLS_PRIORITY: list[str] = [
      COL_RANK, COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
      COL_FACILITATOR_EMAIL, COL_RISK_SCORE, COL_RISK_LEVEL,
      COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
      COL_DAYS_SINCE_NOTE, COL_RECOMMENDED_ACTION,
  ]
  # COL_RANK is a new derived column added by write_outputs() (not from risk_engine)
  
  # OUT-02 campus dashboard: standard 12 + 3 LLM cols
  OUTPUT_COLS_CAMPUS: list[str] = OUTPUT_COLS_PRIORITY + [
      COL_FACILITATOR_SUMMARY, COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
  ]
  ```
  — `COL_RANK` must also be added to the column constants section.

### Claude's Discretion

- Auto column width calculation: use `max(len(str(v)) for v in col_values)` capped at a reasonable max (e.g., 60). Standard openpyxl pattern — no user preference specified.
- whatsapp_messages.csv encoding: UTF-8 with BOM (`encoding="utf-8-sig"`) for Excel compatibility when facilitators open the CSV directly.
- Campus dashboard summary row format: row 1 of campus file contains summary stats (total students, CRITICAL count, HIGH count, intervention coverage %), styled distinctly (bold, light grey fill). Data rows start at row 2, headers at row... actually this conflicts with frozen panes — Claude to decide the cleanest layout (summary above header, or summary below header row).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 4 Requirements
- `.planning/REQUIREMENTS.md` §OUT-01 to OUT-03, OUT-06 — exact column lists, sort order, color spec, summary row spec, JSON schema for run_log

### Locked Module Contract
- `.planning/STATE.md` §Module contracts — `write_outputs()` signature (Phase 4 updates this to 3 args); `main.py` wiring point at line 87
- `.planning/STATE.md` §Key Decisions — openpyxl rationale, D-05/D-06 run_log in-memory pattern, pitfall list

### Input Schema (from Phase 3)
- `.planning/phases/03-claude-api-integration/03-CONTEXT.md` — D-06: 4 LLM columns added by enrich_with_llm(); D-07/D-08: MEDIUM/LOW have None/NaN in LLM cols; generated_by values: "llm" or "template"
- `src/config.py` — all existing COL_* constants; Phase 4 adds COLOR_* and OUTPUT_COLS_* constants before implementing

### Existing Code to Extend
- `src/output_generator.py` — existing stub with locked signature; Phase 4 replaces `raise NotImplementedError("Phase 4")`
- `main.py:87` — commented-out wiring: `# write_outputs(df, cfg.OUTPUT_DIR, run_log=run_log)`; Phase 4 uncomments and corrects to positional arg

### Known Pitfalls
- `CLAUDE.md` §Critical Pitfalls — PatternFill(fill_type="solid") required, 8-char hex in test assertions
- `.planning/STATE.md` §Known Pitfalls — openpyxl color format, df.attrs fragility in pandas 2.2.x

### Code Standards
- `CLAUDE.md` — type hints on all functions, docstrings on all public methods, no print statements, all column names as constants, all paths from env vars

### Success Criteria
- `.planning/ROADMAP.md` §Phase 4 — 4 success criteria defining "done"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py:28-29` — `OUTPUT_DIR` already defined; `Path(os.getenv("OUTPUT_DIR", "outputs"))` — write_outputs() uses this directly
- `src/config.py:65-99` — All COL_* constants available for column ordering; Phase 4 adds COLOR_* and OUTPUT_COLS_* constants
- `main.py:46-54` — run_log dict schema already defined: `run_timestamp`, `students_processed`, `api_calls_made`, `tokens_used`, `errors_encountered`, `fallbacks_triggered`, `data_quality_warnings`
- `main.py:87` — commented wiring ready to uncomment: `# write_outputs(df, cfg.OUTPUT_DIR, run_log=run_log)`
- `src/llm_engine.py` pattern — `df.copy()` at function entry for purity; `logging.getLogger(__name__)` for zero print statements

### Established Patterns
- All column names via `cfg.COL_*` — no bare string literals in output logic
- `logging.getLogger(__name__)` throughout — zero print statements in module
- Pure function discipline: `df.copy()` at entry, no mutation of caller's DataFrame
- `pd.StringDtype()` for string columns (not bare `"string"`)
- `dtype={"student_id": "str", "parent_phone": "str"}` in every read_csv (not relevant for writes, but establishes type discipline)

### Integration Points
- `main.py:87` — Phase 4 wiring: `paths = output_generator.write_outputs(df, cfg.OUTPUT_DIR, run_log)` then `logger.info(f"Outputs written: {list(paths.keys())}")`
- `src/config.py` — Phase 4 adds COLOR_* and OUTPUT_COLS_* constants before implementing output_generator.py (same pattern as Phase 3 adding D-09 constants in Plan 03-01 before implementing llm_engine.py in 03-02)

</code_context>

<specifics>
## Specific Ideas

- **openpyxl PatternFill exact pattern** (from CLAUDE.md pitfall):
  ```python
  PatternFill(fill_type="solid", fgColor=cfg.COLOR_CRITICAL)
  ```
  Never omit `fill_type="solid"` — silently produces no color.

- **Test assertion pattern** (from CLAUDE.md pitfall):
  ```python
  assert ws["A2"].fill.fgColor.rgb == cfg.COLOR_CRITICAL  # "FFFFCCCC" not "FFCCCC"
  ```

- **run_log.json write pattern** (D-06 from prior phases):
  ```python
  import json
  path = output_dir / "run_log.json"
  path.write_text(json.dumps(run_log, indent=2, default=str), encoding="utf-8")
  ```
  `default=str` handles any datetime or Path objects that slipped into run_log.

- **whatsapp_messages.csv encoding:** `df.to_csv(path, index=False, encoding="utf-8-sig")` — UTF-8 with BOM so Excel opens it correctly without garbled Arabic characters.

- **Rank column:** Add a `rank` column derived from position after `sort_values("risk_score", ascending=False).reset_index(drop=True)`. Rank = `index + 1`. Do NOT add COL_RANK to the DataFrame permanently — derive it in the helper function scope only.

- **Phase 3 pattern for plan sequencing:** Phase 3 split into Plan 03-01 (config + templates) → Plan 03-02 (engine implementation) → Plan 03-03 (wiring + tests). Phase 4 should follow the same wave pattern: Plan 04-01 (config constants + CSV writer + run_log writer) → Plan 04-02 (Excel writers — priority list + campus dashboards) → Plan 04-03 (main.py wiring + full test suite).

</specifics>

<deferred>
## Deferred Ideas

- `intervention_report.docx` (OUT-04) — Phase 5
- `facilitator_dashboard.html` (OUT-05) — Phase 5
- Per-campus color theming (different palette per campus) — out of scope for v1
- Excel charts/sparklines in campus dashboards — FUTV2, adds python-xlsxwriter dependency conflict

</deferred>

---

*Phase: 4-Excel-CSV-Output-Generation*
*Context gathered: 2026-05-23*
