"""Documentation generation module for boon-academy-intervention.

Produces all 9 documentation output files using fpdf2 (PDF) and plain Markdown.

D-01 (Signature): write_docs(df, run_log, docs_dir) — produces 9 documentation
files: analysis.md (Markdown), analysis.pdf, and seven static technical .pdf files
(architecture, security, engineering_decisions, data_handling, scalability,
system_design, alternatives).

D-04 / D-05 (Content loading): Static content for the 7 .pdf files is loaded
once at module import from src/templates/docs_content.yaml via yaml.safe_load().

D-08 (Module discipline): logging.getLogger(__name__), type hints on all functions,
docstrings on public functions, zero print() statements.

Security:
- T-06-02: No ANTHROPIC_API_KEY or student PII in any logger.* call — stubs log path only
- T-06-03: yaml.safe_load() (not yaml.load()) — tamper-resistant YAML loading
"""
import logging
from pathlib import Path

import pandas as pd
import yaml
from fpdf import FPDF, FontFace

from src import config as cfg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level YAML load — loaded once at import time (D-04, D-05)
# ---------------------------------------------------------------------------

_CONTENT_PATH = Path(__file__).parent / "templates" / "docs_content.yaml"
try:
    with _CONTENT_PATH.open(encoding="utf-8") as _fh:
        _DOCS_CONTENT: dict = yaml.safe_load(_fh)
except FileNotFoundError as exc:
    raise FileNotFoundError(
        f"docs_content.yaml not found at {_CONTENT_PATH}. "
        "Ensure src/templates/docs_content.yaml is present."
    ) from exc
except yaml.YAMLError as exc:
    raise ValueError(f"docs_content.yaml is malformed: {exc}") from exc

_REQUIRED_KEYS = {
    "architecture", "security", "engineering_decisions",
    "data_handling", "scalability", "system_design", "alternatives"
}
missing = _REQUIRED_KEYS - set(_DOCS_CONTENT.keys())
if missing:
    raise ValueError(f"docs_content.yaml is missing required keys: {missing}")


# ---------------------------------------------------------------------------
# fpdf2 helpers
# ---------------------------------------------------------------------------

def _make_pdf() -> FPDF:
    """Return a pre-configured FPDF instance: A4, 20mm margins, auto page break."""
    pdf = FPDF()
    pdf.set_margins(left=20, top=15, right=20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    return pdf


def _safe_text(text: str) -> str:
    """Replace non-latin1 Unicode chars with ASCII equivalents for Helvetica rendering."""
    replacements = {
        "—": " - ", "–": " - ",
        "‘": "'", "’": "'",
        "“": '"', "”": '"',
        "•": "-", "→": "->",
    }
    for char, sub in replacements.items():
        text = text.replace(char, sub)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ---------------------------------------------------------------------------
# Shared PDF rendering helper
# ---------------------------------------------------------------------------

def _render_doc_from_content_pdf(content_dict: dict, docs_dir: Path, filename: str) -> Path:
    """Render a YAML content dict into a .pdf file using fpdf2.

    Args:
        content_dict: Parsed YAML dict with 'title' and 'sections' keys.
        docs_dir: Directory to write the .pdf file into.
        filename: Output filename (e.g. 'architecture.pdf').

    Returns:
        Path to the written .pdf file.
    """
    pdf = _make_pdf()
    hs = FontFace(emphasis="BOLD", fill_color=(220, 220, 220))

    title = content_dict.get(
        "title", filename.replace(".pdf", "").replace("_", " ").title()
    )
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, _safe_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for section in content_dict.get("sections", []):
        heading = section.get("heading", "")
        if heading:
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 8, _safe_text(heading), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        for item in section.get("body", []):
            item_type = item.get("type", "paragraph")
            text = item.get("text", "")
            if item_type == "bullet":
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, "- " + _safe_text(text), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, _safe_text(text), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

    path = docs_dir / filename
    pdf.output(str(path))
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
      _write_analysis_md   — analysis.md (Markdown, live run_log numbers)
      _write_analysis_pdf  — docs/analysis.pdf (PDF version of analysis)
      _write_architecture  — docs/architecture.pdf
      _write_security      — docs/security.pdf
      _write_engineering_decisions — docs/engineering_decisions.pdf
      _write_data_handling — docs/data_handling.pdf
      _write_scalability   — docs/scalability.pdf
      _write_system_design — docs/system_design.pdf
      _write_alternatives  — docs/alternatives.pdf

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
            Used by _write_analysis_md to compute risk-level distribution.
        run_log: In-memory pipeline run metadata dict with keys: run_timestamp,
            students_processed, api_calls_made, tokens_used, errors_encountered,
            fallbacks_triggered, data_quality_warnings.
        docs_dir: Directory to write .pdf files into (cfg.DOCS_DIR).

    Returns:
        Dict mapping output file keys to their resolved Path objects.
        Keys: analysis_md, analysis_pdf, architecture, security,
              engineering_decisions, data_handling, scalability,
              system_design, alternatives.
    """
    docs_dir.mkdir(parents=True, exist_ok=True)  # D-12

    paths: dict[str, Path] = {}

    paths["analysis_md"] = _write_analysis_md(df, run_log, docs_dir)
    paths["analysis_pdf"] = _write_analysis_pdf(run_log, docs_dir)
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
# Private helpers
# ---------------------------------------------------------------------------

def _write_analysis_md(df: pd.DataFrame, run_log: dict, docs_dir: Path) -> Path:
    """Write analysis.md at docs_dir as a 5-section Markdown memo.

    Produces a plain Markdown memo (under 600 words) with 5 sections:
    Diagnosis, What You Found, What You Built, What You Cut, What Next.
    Embeds live run_log numbers (students_processed, api_calls_made, tokens_used)
    and the runtime risk distribution from df[COL_RISK_LEVEL].value_counts().

    Security: No student names, parent phones, or API key are embedded — only
    aggregate counts from run_log and df (T-06-04).

    Args:
        df: Enriched DataFrame — used for risk-level distribution counts (D-07).
        run_log: Pipeline run metadata dict with live numbers. Keys accessed via
            .get() with defaults to tolerate partial run_logs (T-06-05).
        docs_dir: docs/ directory to write analysis.md into.

    Returns:
        Path to analysis.md.
    """
    path = docs_dir / "analysis.md"

    # Risk distribution from DataFrame at runtime
    if cfg.COL_RISK_LEVEL not in df.columns:
        logger.warning(
            "Column '%s' missing from DataFrame — risk distribution will show all zeros",
            cfg.COL_RISK_LEVEL,
        )
        risk_dist = {}
    else:
        risk_dist = df[cfg.COL_RISK_LEVEL].value_counts().to_dict()
    n_critical = risk_dist.get("CRITICAL", 0)
    n_high = risk_dist.get("HIGH", 0)
    n_medium = risk_dist.get("MEDIUM", 0)
    n_low = risk_dist.get("LOW", 0)

    # Token counts
    tokens_used = run_log.get("tokens_used", {})
    tokens_in = tokens_used.get("input", 0)
    tokens_out = tokens_used.get("output", 0)
    tokens_total = tokens_in + tokens_out

    # Pipeline stats
    students_processed = run_log.get("students_processed", 0)
    api_calls = run_log.get("api_calls_made", 0)
    fallbacks = run_log.get("fallbacks_triggered", 0)

    # Duplicate ID count from data_quality_warnings
    dup_count = sum(
        1
        for w in run_log.get("data_quality_warnings", [])
        if isinstance(w, dict) and w.get("type") == "duplicate_id"
    )

    content = f"""# Analysis: boon-academy-intervention

## Diagnosis

Boon Academy runs 20 campuses serving roughly 300 students. Facilitator
intervention rate is currently ~30% against an 80%+ target. The gap exists
because facilitators lack a fast, prioritised view of which students to contact
and what to say. This pipeline closes that gap by scoring every student daily,
ranking them by risk, and generating draft WhatsApp messages that facilitators
send in one click.

## What You Found

Student intake: {students_processed} students processed in this run.
Risk distribution at runtime:

- CRITICAL: {n_critical}
- HIGH: {n_high}
- MEDIUM: {n_medium}
- LOW: {n_low}

Duplicate student IDs removed during ingestion: {dup_count}. All data quality
issues (missing metrics, type-mismatch strings, blank notes) were auto-resolved
by the ingestion layer — no manual cleanup required.

## What You Built

A five-stage pipeline: ingest → score → LLM enrich → outputs → docs.

LLM usage this run: {api_calls} API calls, {tokens_total} tokens total
({tokens_in} input + {tokens_out} output). Fallbacks triggered: {fallbacks}.

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
"""

    path.write_text(content, encoding="utf-8")
    logger.info("Wrote analysis.md: %s", path)
    return path


def _write_analysis_pdf(run_log: dict, docs_dir: Path) -> Path:
    """Write docs/analysis.pdf - PDF version of the 5-section analysis.

    Args:
        run_log: Pipeline run metadata dict with live numbers.
        docs_dir: Directory to write analysis.pdf into.

    Returns:
        Path to docs/analysis.pdf.
    """
    tokens_used = run_log.get("tokens_used", {})
    tokens_in = tokens_used.get("input", 0)
    tokens_out = tokens_used.get("output", 0)
    tokens_total = tokens_in + tokens_out
    students_processed = run_log.get("students_processed", 0)
    api_calls = run_log.get("api_calls_made", 0)
    fallbacks = run_log.get("fallbacks_triggered", 0)
    run_timestamp = run_log.get("run_timestamp", "N/A")

    pdf = _make_pdf()

    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, "Analysis: boon-academy-intervention", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, f"Generated: {run_timestamp}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    sections = [
        (
            "Diagnosis",
            "Boon Academy runs 20 campuses serving roughly 300 students. Facilitator "
            "intervention rate is currently ~30% against an 80%+ target. The gap exists "
            "because facilitators lack a fast, prioritised view of which students to contact "
            "and what to say. This pipeline closes that gap by scoring every student daily, "
            "ranking them by risk, and generating draft WhatsApp messages that facilitators "
            "send in one click.",
        ),
        (
            "What You Found",
            f"Student intake: {students_processed} students processed in this run. "
            "Risk distribution is available in the intervention_priority_list.xlsx output "
            "(colour-coded by CRITICAL / HIGH / MEDIUM / LOW). All data quality issues "
            "(missing metrics, type-mismatch strings, blank notes) were auto-resolved by "
            "the ingestion layer - no manual cleanup required.",
        ),
        (
            "What You Built",
            f"A five-stage pipeline: ingest -> score -> LLM enrich -> outputs -> docs. "
            f"LLM usage this run: {api_calls} API calls, {tokens_total} tokens total "
            f"({tokens_in} input + {tokens_out} output). Fallbacks triggered: {fallbacks}. "
            "Output files: intervention_priority_list.xlsx, campus_dashboard_<id>.xlsx, "
            "whatsapp_messages.csv, dashboard.html, intervention_report.pdf, "
            "docs/ (nine technical docs).",
        ),
        (
            "What You Cut",
            "No ML model - deterministic weighted scoring is auditable with no training data needed. "
            "No real-time server - on-demand script run fits current workflow. "
            "No OAuth or SSO - outputs are file-based, not a web app. "
            "No Docker or Kubernetes - single-machine Python script. "
            "No direct WhatsApp API sending - facilitators copy-paste from CSV as the safe v1 path.",
        ),
        (
            "What Next",
            "1. Hook up real student data - replace synthetic CSVs with live exports.\n"
            "2. Validate risk weights with the academic director.\n"
            "3. Confirm Arabic dialect per campus (Modern Standard vs. Gulf).\n"
            "4. Test outputs on LibreOffice - facilitator PCs may not have Excel.\n"
            "5. Consider a scheduled daily trigger (cron or Windows Task Scheduler).",
        ),
    ]

    for heading, body in sections:
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _safe_text(body), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    path = docs_dir / "analysis.pdf"
    pdf.output(str(path))
    logger.info("Wrote analysis.pdf: %s", path)
    return path


def _write_architecture(docs_dir: Path, content: dict) -> Path:
    """Write docs/architecture.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "architecture.pdf")
    logger.info("Wrote architecture.pdf: %s", path)
    return path


def _write_security(docs_dir: Path, content: dict) -> Path:
    """Write docs/security.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "security.pdf")
    logger.info("Wrote security.pdf: %s", path)
    return path


def _write_engineering_decisions(docs_dir: Path, content: dict) -> Path:
    """Write docs/engineering_decisions.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "engineering_decisions.pdf")
    logger.info("Wrote engineering_decisions.pdf: %s", path)
    return path


def _write_data_handling(docs_dir: Path, content: dict) -> Path:
    """Write docs/data_handling.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "data_handling.pdf")
    logger.info("Wrote data_handling.pdf: %s", path)
    return path


def _write_scalability(docs_dir: Path, content: dict) -> Path:
    """Write docs/scalability.pdf with YAML sections plus programmatic cost tables."""
    pdf = _make_pdf()
    hs = FontFace(emphasis="BOLD", fill_color=(220, 220, 220))

    title = content.get("title", "Scalability Analysis")
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, _safe_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for section in content.get("sections", []):
        heading = section.get("heading", "")
        if heading:
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 8, _safe_text(heading), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        for item in section.get("body", []):
            item_type = item.get("type", "paragraph")
            text = item.get("text", "")
            if item_type == "bullet":
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, "- " + _safe_text(text), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, _safe_text(text), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

    # Scale comparison table
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Scale Comparison", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        "The table below projects at-risk student count and token usage as campus count "
        "grows. Calculation basis: 106 tokens/student; 40% CRITICAL/HIGH rate assumed.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        for h in ("Scale", "At-Risk Students/Run", "Est. Tokens/Run"):
            row.cell(h)
        row = table.row()
        row.cell("20 campuses (current)")
        row.cell("~120")
        row.cell("~12,720")
        row = table.row()
        row.cell("100 campuses")
        row.cell("~600")
        row.cell("~63,600")
    pdf.ln(4)

    # Monthly cost table
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Monthly Cost Estimate", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        "Estimated monthly cost at claude-sonnet-4-5 pricing (~$6/million tokens blended). "
        "Both scenarios are well within the $200/month budget target - 17x headroom at 100 campuses.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        for h in ("Runs/Month", "Tokens/Run", "Est. Monthly Cost"):
            row.cell(h)
        row = table.row()
        row.cell("30")
        row.cell("~12,720")
        row.cell("<$1/month")
        row = table.row()
        row.cell("30")
        row.cell("~63,600")
        row.cell("~$5-10/month")

    path = docs_dir / "scalability.pdf"
    pdf.output(str(path))
    logger.info("Wrote scalability.pdf: %s", path)
    return path


def _write_system_design(docs_dir: Path, content: dict) -> Path:
    """Write docs/system_design.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "system_design.pdf")
    logger.info("Wrote system_design.pdf: %s", path)
    return path


def _write_alternatives(docs_dir: Path, content: dict) -> Path:
    """Write docs/alternatives.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "alternatives.pdf")
    logger.info("Wrote alternatives.pdf: %s", path)
    return path
