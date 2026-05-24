# Phase 6: Documentation Suite - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `src/doc_generator.py` — a new module that generates all 9 documentation outputs:

1. `analysis.md` — 5-section memo at repo root with live pipeline numbers
2. `docs/analysis.docx` — same content as analysis.md formatted as Word document
3. `docs/architecture.docx` — ASCII pipeline diagram + component rationale + tech choices
4. `docs/security.docx` — API key handling, PII masking, data retention
5. `docs/engineering_decisions.docx` — rationale for every technical choice
6. `docs/data_handling.docx` — schema, cleaning, imputation, edge cases
7. `docs/scalability.docx` — 20 vs 100 campuses, migration path, cost projection
8. `docs/system_design.docx` — AI choices, failure modes, human review loop
9. `docs/alternatives.docx` — what was NOT built and why

Content for the 7 static docs (architecture through alternatives) is loaded from `src/templates/docs_content.yaml`. The two analysis files embed live aggregate stats from `run_log`.

`write_docs(df, run_log, docs_dir)` is called from `main.py` after `write_outputs()`.

**Phase 6 does NOT:** generate per-student content, make API calls, modify existing modules, or change the output_generator.py interface.

</domain>

<decisions>
## Implementation Decisions

### Generation Trigger (D-01 through D-03)

- **D-01 (Entry point):** `write_docs(df: pd.DataFrame, run_log: dict, docs_dir: Path) -> dict[str, Path]` — public function in `src/doc_generator.py`. Called from `main.py` immediately after `write_outputs()`, using the same `df` and `run_log` already in scope.

- **D-02 (main.py wiring):** `from src import doc_generator` at top of main.py; `doc_paths = doc_generator.write_docs(df, run_log, cfg.DOCS_DIR)` after the `write_outputs()` call; `logger.info("docs written: %s", list(doc_paths.keys()))`.

- **D-03 (Return value):** `dict[str, Path]` with named keys: `analysis_md`, `analysis_docx`, `architecture`, `security`, `engineering_decisions`, `data_handling`, `scalability`, `system_design`, `alternatives`. Same pattern as `write_outputs()` return dict.

### Content Authoring (D-04 through D-07)

- **D-04 (Content file):** Single `src/templates/docs_content.yaml` with a top-level key per static doc (`architecture`, `security`, `engineering_decisions`, `data_handling`, `scalability`, `system_design`, `alternatives`). Loaded once at module import.

- **D-05 (Load pattern):** `Path(__file__).parent / "templates" / "docs_content.yaml"` via `yaml.safe_load()` — identical to the `llm_templates.yaml` pattern in `src/llm_engine.py`.

- **D-06 (YAML section schema):** Each doc has a top-level `title` (str) and `sections` (list). Each section has:
  ```yaml
  - heading: "Section Title"
    body:
      - type: paragraph
        text: "Narrative text..."
      - type: bullet
        text: "Bullet point..."
  ```
  `type` is either `paragraph` or `bullet`. No tables in YAML — if a doc needs a table (e.g., scalability cost projection), it is generated programmatically in its `_write_*` helper from hardcoded data.

- **D-07 (Real numbers for analysis files):** analysis.md and analysis.docx pull from `run_log` only — no `df` processing needed for the 5 sections. Required numbers: `students_processed`, `api_calls_made`, `tokens_used`, `fallbacks_triggered`, `errors_encountered`, `run_timestamp`, and risk-level distribution (from `run_log` if present, else derived from `df[COL_RISK_LEVEL].value_counts()` as a one-time aggregation inside `_write_analysis_md`).

### Module Structure (D-08 through D-12)

- **D-08 (Module location):** New `src/doc_generator.py` — independent of `output_generator.py`. Same file-level discipline: `logging.getLogger(__name__)`, type hints on all functions, docstrings on public functions.

- **D-09 (Private helpers — one per output file):**
  - `_write_analysis_md(run_log, docs_dir) -> Path` — writes `analysis.md` at project root (not in docs_dir; path from `cfg.PROJECT_ROOT / "analysis.md"` or equivalent)
  - `_write_analysis_docx(run_log, docs_dir, content) -> Path` — writes `docs/analysis.docx`
  - `_write_architecture(docs_dir, content) -> Path`
  - `_write_security(docs_dir, content) -> Path`
  - `_write_engineering_decisions(docs_dir, content) -> Path`
  - `_write_data_handling(docs_dir, content) -> Path`
  - `_write_scalability(docs_dir, content) -> Path`
  - `_write_system_design(docs_dir, content) -> Path`
  - `_write_alternatives(docs_dir, content) -> Path`

  Each returns a `Path`. `content` parameter receives the per-doc YAML dict loaded by `write_docs()` so helpers don't re-read the YAML file.

- **D-10 (python-docx patterns — carry from Phase 5):**
  - Built-in heading levels only: `add_heading(text, level=0)` for title, `level=1` for sections
  - `'Table Grid'` for any tables added programmatically
  - No `OxmlElement` usage (python-docx 1.1.2 pitfall from STATE.md)
  - No binary template files

- **D-11 (analysis.md format):** Plain Markdown written with `open(..., "w", encoding="utf-8")`. Not python-docx. Structure:
  ```
  # Analysis: boon-academy-intervention

  ## Diagnosis
  ## What You Found
  ## What You Built
  ## What You Cut
  ## What Next
  ```
  Max ~600 words (DOCS-01 constraint). Uses f-strings with live `run_log` values.

- **D-12 (docs/ directory creation):** `docs_dir.mkdir(parents=True, exist_ok=True)` at the start of `write_docs()` — same pattern as `output_dir.mkdir()` in `write_outputs()`.

### Claude's Discretion

- Exact narrative text content for the 7 static docs — Claude writes the content in `docs_content.yaml` based on the REQUIREMENTS.md section descriptions and the project's actual implementation (read `src/` files for accuracy)
- ASCII pipeline diagram layout in architecture.docx — Claude designs it to fit the 5-module pipeline
- Cost projection numbers in scalability.docx — derive from current token usage in STATE.md open questions (`$200/month` budget anchor from DOCS-07)
- Exact analysis.md word count — stay under 600 words (DOCS-01 hard limit)
- analysis.md risk distribution: if `run_log` does not contain a pre-computed breakdown, compute `df[COL_RISK_LEVEL].value_counts().to_dict()` once in `_write_analysis_md` — `df` is still passed to `write_docs()` for this purpose

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 6 Requirements
- `.planning/REQUIREMENTS.md` §DOCS-01 through DOCS-09 — exact content spec per document: sections, constraints, specific topics each doc must cover
- `.planning/ROADMAP.md` §Phase 6 — 4 success criteria (8 .docx files, analysis.md format, security.docx specifics, scalability.docx specifics)

### Locked Module Contracts
- `.planning/STATE.md` §Module contracts — `write_outputs()` signature and return dict; use same conventions for `write_docs()`
- `.planning/STATE.md` §Key Decisions — python-docx 1.1.2 rationale, known pitfalls (OxmlElement, table-border issues, built-in styles only)
- `.planning/STATE.md` §Session Continuity — stack versions: python-docx 1.1.2, PyYAML 6.0.3

### Existing Code to Read Before Implementing
- `src/output_generator.py` — reference implementation for module structure, helper discipline, docstring style
- `src/llm_engine.py` — YAML loading pattern (`Path(__file__).parent / "templates" / "..."`, `yaml.safe_load()`)
- `src/config.py` — all COL_* constants; `DOCS_DIR` env var path (if already defined); use constants not bare strings
- `main.py` — wiring pattern for write_outputs(); doc_generator wiring follows same structure

### Critical Pitfalls (from prior phases)
- `CLAUDE.md` §Critical Pitfalls — `PatternFill fill_type="solid"`, openpyxl 8-char hex (not relevant to this phase but carried forward)
- `.planning/phases/05-html-dashboard-word-report/05-CONTEXT.md` D-10 — python-docx: `add_heading(level=0)` = Title style; `'Table Grid'` table style; no OxmlElement
- `CLAUDE.md` §Code Standards — type hints on ALL functions, docstrings on all public methods, zero print statements, all paths from env vars

### Code Standards
- `CLAUDE.md` — `logging.getLogger(__name__)`, no hardcoded paths, no print statements, type hints required

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/output_generator.py` — entire module is the structural analog; `_write_report()` is the closest helper (python-docx, YAML-driven, pure helper discipline)
- `src/llm_engine.py:~30` — `Path(__file__).parent / "llm_templates.yaml"` + `yaml.safe_load()` — exact pattern for loading `docs_content.yaml`
- `src/templates/` — directory already exists (contains `dashboard.html.j2`); `docs_content.yaml` goes here
- `src/config.py` — `DOCS_DIR` path constant (may need to be added if not present); all COL_* constants for risk level column in analysis.md risk breakdown

### Established Patterns
- Public orchestrator + private `_write_*` helpers returning `Path` — `write_docs()` follows same pattern as `write_outputs()`
- `logging.getLogger(__name__)` — zero print statements in all `src/` modules
- `df.copy()` at entry if transformation needed — pure helper discipline (df not mutated)
- `docs_dir.mkdir(parents=True, exist_ok=True)` — same as `output_dir.mkdir()` in `write_outputs()`

### Integration Points
- `main.py` — add `from src import doc_generator`; add `doc_paths = doc_generator.write_docs(df, run_log, cfg.DOCS_DIR)` after `write_outputs()` call; log `list(doc_paths.keys())`
- `src/config.py` — check if `DOCS_DIR` is defined; if not, add it with `os.getenv("DOCS_DIR", "docs")` pattern (consistent with D-08 from Phase 1)
- `run_log` dict — already has: `run_timestamp`, `students_processed`, `api_calls_made`, `tokens_used`, `errors_encountered`, `fallbacks_triggered`, `data_quality_warnings`

</code_context>

<specifics>
## Specific Ideas

- **analysis.md structure (DOCS-01):**
  ```markdown
  # Analysis: boon-academy-intervention

  ## Diagnosis
  [Problem statement — facilitator intervention rate 30% → 80%+ target]

  ## What You Found
  [Real numbers: N students processed, X CRITICAL, Y HIGH, Z total at-risk]

  ## What You Built
  [5-phase pipeline summary: ingest → score → LLM → outputs → dashboards]

  ## What You Cut
  [Out-of-scope items with rationale: ML model, real-time server, OAuth, Docker]

  ## What Next
  [Phase 7-8 work + open questions from STATE.md]
  ```
  Under 600 words. f-strings embed `run_log["students_processed"]`, risk counts, tokens used.

- **docs_content.yaml structure (example):**
  ```yaml
  architecture:
    title: "System Architecture"
    sections:
      - heading: "Pipeline Overview"
        body:
          - type: paragraph
            text: "The pipeline processes student data in five stages..."
          - type: bullet
            text: "ingestion.py — Merges 3 CSV files into a unified DataFrame"
  ```

- **scalability.docx cost projection (DOCS-07):** $200/month budget anchor; derive tokens-per-student from `run_log["tokens_used"]` / `run_log["students_processed"]`; project to 100 campuses × N students.

- **security.docx (DOCS-04) must explicitly state:** env-var-only API key (never logged, never in outputs), PII masking (names and phones masked at INFO/DEBUG), data retention recommendation ("do not persist student data beyond the run day"), what must NOT appear in any output file.

</specifics>

<deferred>
## Deferred Ideas

- Per-campus breakdown in analysis.md (campus × risk level cross-tab) — deferred to Phase 8 polish if needed; aggregate numbers satisfy DOCS-01
- Auto-generated test for doc content accuracy (assert doc mentions correct number of phases, etc.) — Phase 7 scope
- PDF export of docs — requires headless Chrome or reportlab; not in Phase 6 scope

</deferred>

---

*Phase: 6-documentation-suite*
*Context gathered: 2026-05-24*
