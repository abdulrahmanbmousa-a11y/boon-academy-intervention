"""Documentation generation module for boon-academy-intervention.

Phase 6 implements write_docs() and its nine private helper stubs for writing
all documentation output files from the enriched DataFrame and run_log.

D-01 (Signature): write_docs(df, run_log, docs_dir) — produces 9 documentation
files: analysis.md (Markdown at project root), analysis.docx, and seven static
technical .docx files (architecture, security, engineering_decisions, data_handling,
scalability, system_design, alternatives).

D-04 / D-05 (Content loading): Static content for the 7 .docx files is loaded
once at module import from src/templates/docs_content.yaml via yaml.safe_load().
Identical pattern to llm_templates.yaml in src/llm_engine.py.

D-08 (Module discipline): logging.getLogger(__name__), type hints on all functions,
docstrings on public functions, zero print() statements.

D-09 (Helper list): Nine private _write_* helpers — one per output file — each
returning a Path.  Implementations are Wave 2; this module provides the skeleton
so Wave 2 plans can implement helpers independently.

Security:
- T-06-02: No ANTHROPIC_API_KEY or student PII in any logger.* call — stubs log path only
- T-06-03: yaml.safe_load() (not yaml.load()) — tamper-resistant YAML loading
"""
import logging
from pathlib import Path

import pandas as pd
import yaml
from docx import Document

from src import config as cfg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level YAML load — loaded once at import time (D-04, D-05)
# ---------------------------------------------------------------------------

_CONTENT_PATH = Path(__file__).parent / "templates" / "docs_content.yaml"
with _CONTENT_PATH.open(encoding="utf-8") as _fh:
    _DOCS_CONTENT: dict = yaml.safe_load(_fh)


# ---------------------------------------------------------------------------
# Shared rendering helper
# ---------------------------------------------------------------------------

def _render_doc_from_content(content_dict: dict, docs_dir: Path, filename: str) -> Path:
    """Render a YAML content dict into a .docx file using python-docx.

    Renders a single documentation file from a parsed YAML content block.
    Each content_dict must have a top-level 'title' (str) and 'sections' (list).
    Each section has 'heading' (str) and 'body' (list of {type, text} dicts).
    Supported body types: 'paragraph' and 'bullet'.

    D-10: Uses only built-in python-docx styles — add_heading(level=0/1),
    add_paragraph(), paragraph.style. No OxmlElement, no custom styles.

    Args:
        content_dict: Parsed YAML dict with 'title' and 'sections' keys.
        docs_dir: Directory to write the .docx file into.
        filename: Output filename (e.g. 'architecture.docx').

    Returns:
        Path to the written .docx file.
    """
    doc = Document()

    title = content_dict.get("title", filename.replace(".docx", "").replace("_", " ").title())
    doc.add_heading(title, level=0)

    for section in content_dict.get("sections", []):
        heading = section.get("heading", "")
        if heading:
            doc.add_heading(heading, level=1)

        for item in section.get("body", []):
            item_type = item.get("type", "paragraph")
            text = item.get("text", "")
            if item_type == "bullet":
                para = doc.add_paragraph(text, style="List Bullet")
            else:
                doc.add_paragraph(text)

    path = docs_dir / filename
    # str() required for python-docx 1.1.2 on Windows (CLAUDE.md critical pitfall)
    doc.save(str(path))
    logger.info("Wrote doc: %s", path)
    return path


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------

def write_docs(df: pd.DataFrame, run_log: dict, docs_dir: Path) -> dict[str, Path]:
    """Write all 9 documentation files and return a dict of named paths.

    Creates docs_dir (including parents) if it does not exist, then delegates
    to nine private helpers — one per output file — and returns a unified dict
    mapping semantic keys to resolved Path objects (D-01, D-03).

    D-09 helper list:
      _write_analysis_md  — analysis.md at project root (Markdown, live run_log numbers)
      _write_analysis_docx — docs/analysis.docx (Word version of analysis.md)
      _write_architecture  — docs/architecture.docx
      _write_security      — docs/security.docx
      _write_engineering_decisions — docs/engineering_decisions.docx
      _write_data_handling — docs/data_handling.docx
      _write_scalability   — docs/scalability.docx
      _write_system_design — docs/system_design.docx
      _write_alternatives  — docs/alternatives.docx

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
            Used by _write_analysis_md to compute risk-level distribution.
        run_log: In-memory pipeline run metadata dict with keys: run_timestamp,
            students_processed, api_calls_made, tokens_used, errors_encountered,
            fallbacks_triggered, data_quality_warnings.
        docs_dir: Directory to write .docx files into (cfg.DOCS_DIR).

    Returns:
        Dict mapping output file keys to their resolved Path objects.
        Keys: analysis_md, analysis_docx, architecture, security,
              engineering_decisions, data_handling, scalability,
              system_design, alternatives.
    """
    docs_dir.mkdir(parents=True, exist_ok=True)  # D-12

    paths: dict[str, Path] = {}

    paths["analysis_md"] = _write_analysis_md(df, run_log, docs_dir)
    paths["analysis_docx"] = _write_analysis_docx(run_log, docs_dir, _DOCS_CONTENT)
    paths["architecture"] = _write_architecture(docs_dir, _DOCS_CONTENT.get("architecture", {}))
    paths["security"] = _write_security(docs_dir, _DOCS_CONTENT.get("security", {}))
    paths["engineering_decisions"] = _write_engineering_decisions(
        docs_dir, _DOCS_CONTENT.get("engineering_decisions", {})
    )
    paths["data_handling"] = _write_data_handling(
        docs_dir, _DOCS_CONTENT.get("data_handling", {})
    )
    paths["scalability"] = _write_scalability(
        docs_dir, _DOCS_CONTENT.get("scalability", {})
    )
    paths["system_design"] = _write_system_design(
        docs_dir, _DOCS_CONTENT.get("system_design", {})
    )
    paths["alternatives"] = _write_alternatives(
        docs_dir, _DOCS_CONTENT.get("alternatives", {})
    )

    logger.info("docs written: %s", list(paths.keys()))
    return paths


# ---------------------------------------------------------------------------
# Private helpers — stubs (Wave 2 will implement each)
# ---------------------------------------------------------------------------

def _write_analysis_md(df: pd.DataFrame, run_log: dict, docs_dir: Path) -> Path:
    """Write analysis.md at project root as a 5-section Markdown memo.

    TODO (Wave 2): Implement full Markdown content with live run_log numbers
    and risk-level distribution derived from df[cfg.COL_RISK_LEVEL].value_counts().
    analysis.md is written at the project root (docs_dir.parent / "analysis.md"),
    not inside docs_dir, because it is the primary deliverable memo (D-11).

    Args:
        df: Enriched DataFrame — used for risk-level distribution counts (D-07).
        run_log: Pipeline run metadata dict with live numbers.
        docs_dir: docs/ directory — parent is the project root for analysis.md.

    Returns:
        Path to analysis.md at project root.
    """
    path = docs_dir.parent / "analysis.md"
    return path


def _write_analysis_docx(run_log: dict, docs_dir: Path, content: dict) -> Path:
    """Write docs/analysis.docx — Word version of analysis.md.

    TODO (Wave 2): Implement full Word document mirroring analysis.md structure
    using python-docx. Pulls live numbers from run_log. Five sections:
    Diagnosis, What You Found, What You Built, What You Cut, What Next.

    Args:
        run_log: Pipeline run metadata dict with live numbers.
        docs_dir: Directory to write analysis.docx into.
        content: Full _DOCS_CONTENT dict (analysis.docx uses run_log, not YAML sections).

    Returns:
        Path to docs/analysis.docx.
    """
    path = docs_dir / "analysis.docx"
    return path


def _write_architecture(docs_dir: Path, content: dict) -> Path:
    """Write docs/architecture.docx — system architecture reference document.

    TODO (Wave 2): Implement using _render_doc_from_content(content, docs_dir,
    'architecture.docx'). Content loaded from docs_content.yaml 'architecture' key.

    Args:
        docs_dir: Directory to write architecture.docx into.
        content: Parsed YAML dict for the 'architecture' doc block.

    Returns:
        Path to docs/architecture.docx.
    """
    path = docs_dir / "architecture.docx"
    return path


def _write_security(docs_dir: Path, content: dict) -> Path:
    """Write docs/security.docx — security design document.

    TODO (Wave 2): Implement using _render_doc_from_content(content, docs_dir,
    'security.docx'). Content loaded from docs_content.yaml 'security' key.

    Args:
        docs_dir: Directory to write security.docx into.
        content: Parsed YAML dict for the 'security' doc block.

    Returns:
        Path to docs/security.docx.
    """
    path = docs_dir / "security.docx"
    return path


def _write_engineering_decisions(docs_dir: Path, content: dict) -> Path:
    """Write docs/engineering_decisions.docx — engineering decisions rationale.

    TODO (Wave 2): Implement using _render_doc_from_content(content, docs_dir,
    'engineering_decisions.docx'). Content from docs_content.yaml 'engineering_decisions' key.

    Args:
        docs_dir: Directory to write engineering_decisions.docx into.
        content: Parsed YAML dict for the 'engineering_decisions' doc block.

    Returns:
        Path to docs/engineering_decisions.docx.
    """
    path = docs_dir / "engineering_decisions.docx"
    return path


def _write_data_handling(docs_dir: Path, content: dict) -> Path:
    """Write docs/data_handling.docx — data handling reference document.

    TODO (Wave 2): Implement using _render_doc_from_content(content, docs_dir,
    'data_handling.docx'). Content loaded from docs_content.yaml 'data_handling' key.

    Args:
        docs_dir: Directory to write data_handling.docx into.
        content: Parsed YAML dict for the 'data_handling' doc block.

    Returns:
        Path to docs/data_handling.docx.
    """
    path = docs_dir / "data_handling.docx"
    return path


def _write_scalability(docs_dir: Path, content: dict) -> Path:
    """Write docs/scalability.docx — scalability analysis document.

    TODO (Wave 2): Implement using _render_doc_from_content(content, docs_dir,
    'scalability.docx'). Content loaded from docs_content.yaml 'scalability' key.

    Args:
        docs_dir: Directory to write scalability.docx into.
        content: Parsed YAML dict for the 'scalability' doc block.

    Returns:
        Path to docs/scalability.docx.
    """
    path = docs_dir / "scalability.docx"
    return path


def _write_system_design(docs_dir: Path, content: dict) -> Path:
    """Write docs/system_design.docx — system design and AI integration document.

    TODO (Wave 2): Implement using _render_doc_from_content(content, docs_dir,
    'system_design.docx'). Content loaded from docs_content.yaml 'system_design' key.

    Args:
        docs_dir: Directory to write system_design.docx into.
        content: Parsed YAML dict for the 'system_design' doc block.

    Returns:
        Path to docs/system_design.docx.
    """
    path = docs_dir / "system_design.docx"
    return path


def _write_alternatives(docs_dir: Path, content: dict) -> Path:
    """Write docs/alternatives.docx — alternatives considered document.

    TODO (Wave 2): Implement using _render_doc_from_content(content, docs_dir,
    'alternatives.docx'). Content loaded from docs_content.yaml 'alternatives' key.

    Args:
        docs_dir: Directory to write alternatives.docx into.
        content: Parsed YAML dict for the 'alternatives' doc block.

    Returns:
        Path to docs/alternatives.docx.
    """
    path = docs_dir / "alternatives.docx"
    return path
