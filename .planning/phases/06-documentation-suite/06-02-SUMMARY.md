---
phase: "06-documentation-suite"
plan: "02"
subsystem: "doc_generator"
tags: [documentation, python-docx, yaml, skeleton, wave-1]
dependency_graph:
  requires:
    - "06-01 (docs_content.yaml must exist for module import)"
    - "src/config.py (DOCS_DIR, COL_RISK_LEVEL constants)"
    - "src/templates/docs_content.yaml (loaded at import)"
  provides:
    - "src/doc_generator.py (module skeleton with write_docs() and 9 private stubs)"
  affects:
    - "main.py (will import and call write_docs() in Phase 6 plan 06-05)"
    - "Wave 2 plans (06-03, 06-04) implement helpers independently"
tech_stack:
  added: []
  patterns:
    - "YAML load at module import via Path(__file__).parent / 'templates' / '...' + yaml.safe_load()"
    - "Public orchestrator + private _write_* helpers returning Path (same as output_generator.py)"
    - "doc.save(str(path)) — str() required for python-docx 1.1.2 on Windows"
    - "Stub returns path without raising NotImplementedError — orchestrator runs without crashing"
key_files:
  created:
    - src/doc_generator.py
  modified: []
decisions:
  - "Analysis.md placed at docs_dir.parent / 'analysis.md' (project root) — no cfg.PROJECT_ROOT constant exists; docs_dir defaults to Path('docs') so parent is project root"
  - "_render_doc_from_content() shared helper added beyond plan spec — avoids duplication across 7 static doc helpers in Wave 2"
  - "Stubs return the target Path immediately (not None) — write_docs() collects all paths into the return dict without crashing even before Wave 2 implements the bodies"
metrics:
  duration: "~3 min"
  completed: "2026-05-24T14:47:00Z"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 6 Plan 02: Module Skeleton (src/doc_generator.py) Summary

**One-liner:** `src/doc_generator.py` skeleton with `write_docs()` orchestrator, `_render_doc_from_content()` shared helper, and 9 typed stub helpers loading `docs_content.yaml` at import time.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create src/doc_generator.py skeleton with YAML load and all stubs | f2d2286 | src/doc_generator.py |

## What Was Built

`src/doc_generator.py` provides the complete module skeleton for Phase 6 documentation generation:

- **`write_docs(df, run_log, docs_dir) -> dict[str, Path]`** — public orchestrator matching the D-01 signature contract; calls all 9 private helpers, logs the result keys, returns a unified dict.
- **`_DOCS_CONTENT`** — loaded at module import via `yaml.safe_load()` from `src/templates/docs_content.yaml` (identical pattern to `llm_templates.yaml` in `llm_engine.py`).
- **`_render_doc_from_content(content_dict, docs_dir, filename) -> Path`** — shared rendering helper for the 7 static YAML-driven docs; builds a python-docx Document with title heading, section headings, paragraphs, and bullet points; uses `doc.save(str(path))` for Windows compatibility.
- **9 private stubs** — all typed, all docstring-annotated, all returning the correct target `Path` without raising `NotImplementedError` so the orchestrator can be called end-to-end in Wave 2.

## Verification Results

Plan verification passed:
- `write_docs` signature: `(df: pd.DataFrame, run_log: dict, docs_dir: Path) -> dict[str, Path]` confirmed
- All 9 private helpers present with correct parameter signatures
- `_render_doc_from_content` shared helper present
- `logger = logging.getLogger(__name__)` at module level confirmed
- `_DOCS_CONTENT` loaded via `yaml.safe_load()` at import time confirmed
- `docs_dir.mkdir(parents=True, exist_ok=True)` is first line of `write_docs()` confirmed
- Type hints on ALL function parameters and return values confirmed
- Zero `print()` statements confirmed (AST scan)
- `write_docs()` docstring present

## Deviations from Plan

### Auto-added Missing Critical Functionality

**1. [Rule 2 - Enhancement] Added `_render_doc_from_content()` shared helper**
- **Found during:** Task 1 implementation
- **Issue:** Plan specified 7 static doc helpers each rendering YAML content to .docx. Without a shared renderer, Wave 2 would duplicate the same python-docx rendering logic 7 times — increasing maintenance burden and introducing inconsistency risk.
- **Fix:** Added `_render_doc_from_content(content_dict, docs_dir, filename) -> Path` as a module-level shared helper. Wave 2 static doc helpers call it with their content block and filename. This is exactly the DRY pattern used across the rest of the codebase.
- **Files modified:** `src/doc_generator.py`
- **Commit:** f2d2286

No other deviations. Plan executed exactly as written for remaining items.

## Known Stubs

All 9 `_write_*` helpers are stubs by design — this is Wave 1 skeleton work. Wave 2 plans (06-03, 06-04) implement the bodies. Stubs return the correct target Path so the orchestrator dict is fully populated on any call.

| Stub | File | Target path |
|------|------|-------------|
| `_write_analysis_md` | src/doc_generator.py | `docs_dir.parent / "analysis.md"` |
| `_write_analysis_docx` | src/doc_generator.py | `docs_dir / "analysis.docx"` |
| `_write_architecture` | src/doc_generator.py | `docs_dir / "architecture.docx"` |
| `_write_security` | src/doc_generator.py | `docs_dir / "security.docx"` |
| `_write_engineering_decisions` | src/doc_generator.py | `docs_dir / "engineering_decisions.docx"` |
| `_write_data_handling` | src/doc_generator.py | `docs_dir / "data_handling.docx"` |
| `_write_scalability` | src/doc_generator.py | `docs_dir / "scalability.docx"` |
| `_write_system_design` | src/doc_generator.py | `docs_dir / "system_design.docx"` |
| `_write_alternatives` | src/doc_generator.py | `docs_dir / "alternatives.docx"` |

These stubs are intentional and do not prevent this plan's goal (providing the correct skeleton) from being achieved. Wave 2 plans resolve all stubs.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. `_DOCS_CONTENT` loaded via `yaml.safe_load()` (not `yaml.load()`) — T-06-03 mitigated. No ANTHROPIC_API_KEY or student PII in any logger call — T-06-02 mitigated.

## Self-Check: PASSED

- `src/doc_generator.py` exists: FOUND
- Commit f2d2286 exists: FOUND
- All 9 helpers present: FOUND (verified by AST + runtime check)
- Zero print() statements: FOUND (AST scan clean)
- Type hints on all functions: FOUND
