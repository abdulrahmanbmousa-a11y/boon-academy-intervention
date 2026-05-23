# Phase 5: HTML Dashboard + Word Report - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `src/output_generator.py` with two new private helpers called from `write_outputs()`:

1. `_write_html_dashboard(df, output_dir) -> Path` — writes `outputs/facilitator_dashboard.html` (OUT-05)
2. `_write_report(df, run_log, output_dir) -> Path` — writes `outputs/intervention_report.docx` (OUT-04)

Both helpers follow the same Phase 4 pattern: independently testable, pure in spirit (df not mutated), return a resolved `Path`.

`write_outputs()` is extended to call both helpers and add `"dashboard"` and `"report"` keys to its return dict.

**Phase 5 does NOT:** create new modules, add new dependencies (python-docx and jinja2 are already installed), or generate new API calls.

</domain>

<decisions>
## Implementation Decisions

### HTML Template (D-01 through D-03)

- **D-01 (Template engine):** Use Jinja2 with a template file — `src/templates/dashboard.html.j2`. Loaded at runtime via `Path(__file__).parent / "templates" / "dashboard.html.j2"` — same pattern as `llm_templates.yaml` loaded in Phase 3. Clean separation of HTML/CSS/JS from Python logic.

- **D-02 (Data injection):** Embed only display columns as a JS const:
  ```python
  DISPLAY_COLS = [
      COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
      COL_RISK_SCORE, COL_RISK_LEVEL,
      COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
      COL_DAYS_SINCE_NOTE, COL_FACILITATOR_SUMMARY,
      COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
  ]
  ```
  Inject via `json.dumps(records).replace("</", "<\\/")` (CLAUDE.md pitfall) into the template's `{{ students_json }}` variable.

- **D-03 (Template constants):** Pass `campus_ids` (sorted unique list) to the template so the campus filter `<select>` is generated from data, not hardcoded.

### HTML CSS + JS (D-04 through D-06)

- **D-04 (CSS):** Vanilla CSS inline in the template — no embedded framework. ~100 lines. Covers: table layout, risk-level row color-coding (matching Phase 4 palette: CRITICAL=#FFCCCC, HIGH=#FFE5CC, MEDIUM=#FFFFCC, LOW=#CCFFCC), filter bar, expanded row panel, responsive enough for 1280px and 1920px.

- **D-05 (JS interactivity):** Vanilla JS only — no framework embedded. Handles:
  - Campus filter (`<select>`) — filter `studentsData` array on `campus_id`
  - Risk-level filter buttons (CRITICAL / HIGH / MEDIUM / LOW / ALL) — filter on `risk_level`
  - Name search (`<input>`) — case-insensitive substring match on `student_name`
  - Expandable row — clicking a row shows/hides a detail panel below it with risk breakdown, facilitator summary, WhatsApp message, and copy button
  - Summary stats at top — total students, CRITICAL count, HIGH count, intervention coverage % — computed from `studentsData` on load

- **D-06 (Copy button):** Clipboard API with execCommand fallback:
  ```javascript
  try {
    await navigator.clipboard.writeText(message);
    btn.textContent = 'Copied!';
  } catch {
    // fallback: hidden textarea + execCommand
    const ta = document.createElement('textarea');
    ta.value = message;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    btn.textContent = 'Copied!';
  }
  setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
  ```

### Word Report Narrative (D-07 through D-09)

- **D-07 (Narrative source):** All narrative text is programmatic template strings — no extra Claude API calls. Example:
  ```python
  f"Of {total} students, {critical_count} ({critical_pct:.0f}%) are at CRITICAL risk requiring immediate intervention."
  ```
  Deterministic, no cost, no fallback path needed.

- **D-08 (Student deep-dives):** Exactly 4 deep-dive sections — one per risk tier (CRITICAL, HIGH, MEDIUM, LOW). Each features the highest `risk_score` student in that tier. If a tier has no students, that section is omitted (graceful degradation, not an error).

- **D-09 (Deep-dive content per student):** Each section includes:
  - Student name, campus, risk level, risk score
  - 4 component scores: attendance_rate, avg_practice_questions, trend_direction, days_since_last_note
  - Facilitator action summary (from `COL_FACILITATOR_SUMMARY`)
  - Recommended action (from `COL_RECOMMENDED_ACTION`)
  - **Not included:** WhatsApp message text (belongs in CSV/dashboard for copy-paste)

### Word Report Structure (D-10 through D-12)

- **D-10 (Build approach):** Build entirely programmatically using python-docx — no binary template file in the repo. `Document()` → headings → paragraphs → tables. Consistent with project philosophy (no binary artifacts committed except synthetic data).

- **D-11 (Heading style):** Built-in heading levels only — `add_heading(text, level=0/1/2)`. Avoids OxmlElement (known python-docx 1.1.2 issues per STATE.md). Renders cleanly in both Word and Google Docs.

- **D-12 (Table style):** `'Table Grid'` for all tables (risk breakdown, top-10, campus summary, deep-dive component scores). Safest python-docx built-in — borders render correctly in Word and Google Docs per STATE.md note on python-docx 1.1.2 table-border issues.

### Report Document Structure (D-13)

- **D-13 (Section order):**
  1. Cover page — title, run date, campus count, total students processed
  2. Executive summary — narrative paragraph + risk breakdown table (risk_level, count, %)
  3. Top 10 most at-risk students — table: rank, name, campus, risk_score, risk_level
  4. Campus summary — table: campus_id, total, critical, high, intervention_coverage_%
  5. Student deep-dives — 4 sections (one per tier, highest risk_score per tier)
  6. Data quality notes — warnings from run_log["data_quality_warnings"]
  7. Methodology appendix — risk formula description (weights from src/config.py constants)

### Claude's Discretion

- `_write_html_dashboard()` signature: `(df: pd.DataFrame, output_dir: Path) -> Path` — consistent with Phase 4 helper signatures
- `_write_report()` signature: `(df: pd.DataFrame, run_log: dict, output_dir: Path) -> Path` — needs `run_log` for data quality warnings and run timestamp on cover page
- Dashboard table column order: risk_score (sortable default desc), student_name, campus_id, risk_level, attendance_rate, avg_practice_questions, trend_direction — Claude to determine cleanest layout
- HTML file encoding: UTF-8 with `<meta charset="utf-8">` — handles Arabic student names
- Default sort on dashboard load: by `risk_score` descending (highest risk first)
- Word report page margins: python-docx defaults (1-inch margins) — no custom page setup
- Cover page styling: bold large title, run date, counts as a simple paragraph — no Word cover page XML magic

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 5 Requirements
- `.planning/REQUIREMENTS.md` §OUT-04 — exact docx structure: cover page, executive summary, risk breakdown table, top-10 table, campus summary table, 3-4 deep-dives, data quality notes, methodology appendix
- `.planning/REQUIREMENTS.md` §OUT-05 — exact HTML features: risk table, campus filter, risk-level filter buttons, name search, expandable row with risk breakdown + facilitator summary + WhatsApp message + copy button, summary stats at top

### Phase 5 Success Criteria
- `.planning/ROADMAP.md` §Phase 5 — 3 success criteria (file:// functionality, row expand behavior, docx rendering in Word + Google Docs)

### Locked Module Contract
- `.planning/phases/04-excel-csv-output-generation/04-CONTEXT.md` D-09 — "Phase 5 adds `_write_report()` and `_write_html_dashboard()` as private helpers in same `output_generator.py`; Phase 5 also updates return dict with `'report'` and `'dashboard'` keys"
- `.planning/STATE.md` §Module contracts — `write_outputs()` signature; `main.py` wiring
- `.planning/STATE.md` §Key Decisions — python-docx 1.1.2 rationale, known pitfalls

### Input Schema (from Phase 3/4)
- `src/config.py` — all COL_* constants; Phase 5 display columns list must use these, no bare strings
- `.planning/phases/03-claude-api-integration/03-CONTEXT.md` — LLM column values: `COL_FACILITATOR_SUMMARY`, `COL_WHATSAPP_MESSAGE`, `COL_GENERATED_BY`; MEDIUM/LOW have None/NaN in LLM cols

### Existing Code to Extend
- `src/output_generator.py` — existing Phase 4 implementation; Phase 5 adds two new private helpers and extends `write_outputs()`. Read full file before implementing.
- `src/config.py` — all existing constants; Phase 5 may add `DISPLAY_COLS_DASHBOARD` tuple if needed (same pattern as `OUTPUT_COLS_PRIORITY`/`OUTPUT_COLS_CAMPUS`)

### Critical Pitfalls
- `CLAUDE.md` §Critical Pitfalls — `json.dumps(data).replace("</", "<\\/")` before embedding in `<script>` tag (XSS safety + JSON parser safety)
- `.planning/STATE.md` §Key Decisions — python-docx 1.1.2: avoid OxmlElement + custom table styles; use built-in heading levels and 'Table Grid'

### Code Standards
- `CLAUDE.md` — type hints on all functions, docstrings on all public methods, no print statements, all column names as constants

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/output_generator.py:290` — `write_outputs()` orchestrator; Phase 5 extends it to call two new helpers and add keys to return dict
- `src/output_generator.py:28-59` — `_write_whatsapp_csv()` pattern: filter df, select columns, write file, return Path
- `src/config.py:109-133` — COLOR_* constants (CRITICAL/HIGH/MEDIUM/LOW) — reuse same palette in HTML dashboard CSS for row color-coding
- `src/config.py:120-133` — `OUTPUT_COLS_PRIORITY` tuple — reference for dashboard display column selection
- `src/llm_templates.yaml` + `src/llm_engine.py:~30` — `Path(__file__).parent / "llm_templates.yaml"` pattern for loading file-adjacent resources — same pattern for `src/templates/dashboard.html.j2`

### Established Patterns
- All column names via `cfg.COL_*` — no bare string literals in output logic
- `logging.getLogger(__name__)` — zero print statements
- Pure helper discipline: df not mutated, return Path
- `df.copy()` at entry for purity if transformation needed

### Integration Points
- `write_outputs()` return dict: add `"dashboard": Path(...)` and `"report": Path(...)` keys
- `main.py` already wires `write_outputs()` — no main.py changes needed for Phase 5 (helpers are internal to output_generator.py)
- `run_log` dict (from `main.py:46-54`): provides `run_timestamp`, `data_quality_warnings`, `students_processed` for report cover page and data quality notes section

</code_context>

<specifics>
## Specific Ideas

- **JSON injection safety (CLAUDE.md pitfall):**
  ```python
  students_json = json.dumps(records).replace("</", "<\\/")
  html = template.render(students_json=students_json, campus_ids=campus_ids)
  ```

- **Jinja2 loader pattern (mirrors llm_templates.yaml):**
  ```python
  from jinja2 import Environment, FileSystemLoader
  template_dir = Path(__file__).parent / "templates"
  env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)
  template = env.get_template("dashboard.html.j2")
  ```
  Note: `autoescape=False` because we're embedding pre-serialized JSON, not user-supplied HTML content.

- **HTML row color-coding:** Match Phase 4 Excel palette exactly:
  - CRITICAL: `#FFCCCC` (from `cfg.COLOR_CRITICAL = "FFFFCCCC"` → strip FF prefix → `#FFCCCC`)
  - HIGH: `#FFE5CC`
  - MEDIUM: `#FFFFCC`
  - LOW: `#CCFFCC`

- **python-docx risk breakdown table structure:**
  ```
  | Risk Level | Student Count | % of Total |
  |------------|---------------|------------|
  | CRITICAL   | 12            | 8%         |
  | HIGH       | 28            | 19%        |
  | MEDIUM     | 65            | 44%        |
  | LOW        | 43            | 29%        |
  ```

- **Methodology appendix content:** Describe the 4 components and weights (sourced from `src/config.py` constants — `WEIGHT_ATTENDANCE`, `WEIGHT_PRACTICE`, `WEIGHT_TREND`, `WEIGHT_NOTES`). Risk thresholds: CRITICAL ≥ 75, HIGH ≥ 50, MEDIUM ≥ 25, LOW < 25.

</specifics>

<deferred>
## Deferred Ideas

- Chart/sparkline in HTML dashboard (risk trend over time) — no time-series data in current pipeline; future phase
- PDF export button in HTML dashboard — would require a server or headless Chrome; future phase
- Per-campus color theming in HTML — consistent palette is simpler for v1
- Animated risk gauge in HTML — visual enhancement, not required for intervention use case

</deferred>

---

*Phase: 5-HTML-Dashboard-Word-Report*
*Context gathered: 2026-05-23*
