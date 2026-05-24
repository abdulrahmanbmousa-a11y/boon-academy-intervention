# Phase 6: Documentation Suite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 06-documentation-suite
**Areas discussed:** Generation trigger, Content authoring, Module structure

---

## Generation Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Part of main.py | Docs generated every run after write_outputs(). Direct access to df and run_log. | ✓ |
| Separate script generate_docs.py | Standalone script reads outputs/run_log.json for numbers. Runs independently. | |
| main.py with GENERATE_DOCS flag | Added to main.py but gated by env var — docs only when explicitly requested. | |

**User's choice:** Part of main.py (recommended)
**Notes:** No follow-up clarification needed — clear preference for self-contained pipeline.

---

| Option | Description | Selected |
|--------|-------------|----------|
| write_docs(df, run_log, docs_dir) | Same calling convention as write_outputs(). Live df and run_log access. | ✓ |
| Only run_log (not df) | run_log aggregates sufficient for analysis.md numbers. | |

**User's choice:** write_docs(df, run_log, docs_dir) — full signature
**Notes:** df retained so risk-level distribution can be computed on-demand if run_log doesn't pre-aggregate it.

---

| Option | Description | Selected |
|--------|-------------|----------|
| dict[str, Path] with named keys | Same pattern as write_outputs(). Named keys per file. | ✓ |
| list[Path] | Simpler, loses named access. | |

**User's choice:** dict[str, Path] — named keys

---

## Content Authoring

| Option | Description | Selected |
|--------|-------------|----------|
| YAML content templates | Single docs_content.yaml, loaded at runtime. Text stays out of Python code. | ✓ |
| Inline Python string constants | All narrative text as multi-line strings in doc_generator.py. | |
| Markdown source files | Write docs as .md files, convert to .docx at runtime (new dependency). | |

**User's choice:** YAML content templates (recommended)
**Notes:** Mirrors llm_templates.yaml pattern already established in Phase 3.

---

| Option | Description | Selected |
|--------|-------------|----------|
| One shared docs_content.yaml | All 8 docs in one file with top-level keys per doc. | ✓ |
| One .yaml file per doc | architecture.yaml, security.yaml, etc. in src/templates/docs/. | |

**User's choice:** One shared docs_content.yaml
**Notes:** Simpler to locate, consistent with llm_templates.yaml single-file pattern.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Aggregate stats from run_log | Total students, risk counts, api_calls, tokens, fallbacks, timestamp. | ✓ |
| Aggregate + per-campus breakdown from df | Adds per-campus risk distribution table to analysis.md. | |

**User's choice:** Aggregate stats from run_log
**Notes:** Sufficient for DOCS-01 compliance. Per-campus breakdown deferred.

---

## Module Structure

| Option | Description | Selected |
|--------|-------------|----------|
| New src/doc_generator.py | Clean separation. Mirrors output_generator.py structure. | ✓ |
| Extend output_generator.py | One fewer module but blurs responsibilities. | |

**User's choice:** New src/doc_generator.py (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| One private function per file | _write_analysis_md, _write_architecture, etc. Max flexibility per doc. | ✓ |
| Generic _write_static_doc + _write_analysis | Less code but loses per-doc flexibility. | |

**User's choice:** One private function per file (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| heading + body (paragraphs/bullets) per section | type field per body item ('paragraph' or 'bullet'). Covers all requirements. | ✓ |
| heading + body + optional table | Adds table key per section. More expressive but more complex YAML schema. | |

**User's choice:** heading + body with type field per item
**Notes:** Tables that need programmatic data (e.g., scalability cost projection) are handled in the individual _write_* helper, not YAML.

---

## Claude's Discretion

- Exact narrative text in docs_content.yaml — Claude writes all content based on REQUIREMENTS.md section specs and actual src/ implementation
- ASCII pipeline diagram layout in architecture.docx
- Cost projection numbers in scalability.docx (anchored to $200/month from DOCS-07)
- Exact word count for analysis.md (hard limit: ≤600 words from DOCS-01)

## Deferred Ideas

- Per-campus breakdown in analysis.md — deferred (aggregate numbers satisfy DOCS-01)
- Doc content accuracy tests (assert correct phase count, etc.) — Phase 7 scope
- PDF export of docs — requires headless Chrome; out of Phase 6 scope
