# Phase 5: HTML Dashboard + Word Report - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 5-HTML-Dashboard-Word-Report
**Areas discussed:** HTML Template Strategy, HTML CSS + JS Approach, Word Report Narrative Text, Word Report Base Approach

---

## HTML Template Strategy

### Q1: Where should the HTML template live?

| Option | Description | Selected |
|--------|-------------|----------|
| Jinja2 template file | `src/templates/dashboard.html.j2` — clean separation of HTML/CSS/JS from Python. Jinja2 already installed. | ✓ |
| Python string in module | Multi-line string constant in `_write_html_dashboard()`. Simpler but mixes HTML with Python. | |

**User's choice:** Jinja2 template file (Recommended)

---

### Q2: Template loading approach?

| Option | Description | Selected |
|--------|-------------|----------|
| Load from filesystem | `Path(__file__).parent / 'templates' / 'dashboard.html.j2'` — same pattern as llm_templates.yaml. | ✓ |
| Embed as module-level string | `jinja2.Environment().from_string()`. No extra file but pollutes Python module. | |

**User's choice:** Load from filesystem (Recommended)

---

### Q3: What data to embed in the JS const?

| Option | Description | Selected |
|--------|-------------|----------|
| Display columns only | ~12 columns sufficient for UI. Keeps HTML file small. | ✓ |
| All DataFrame columns | Simple but includes unused internal columns, larger file. | |

**User's choice:** Display columns only (Recommended)

---

## HTML CSS + JS Approach

### Q1: CSS approach for offline dashboard?

| Option | Description | Selected |
|--------|-------------|----------|
| Vanilla CSS inline | ~100 lines, no framework bloat, minimal philosophy. | ✓ |
| Embed minified Bootstrap | ~150KB of CSS, polished but over-engineered for the use case. | |

**User's choice:** Vanilla CSS inline (Recommended)

---

### Q2: JS interactivity approach?

| Option | Description | Selected |
|--------|-------------|----------|
| Vanilla JS | Plain JS for filter/search/toggle. Works in all modern browsers via file://. | ✓ |
| Alpine.js embedded | ~44KB reactive JS — cleaner declarative HTML but large embed. | |

**User's choice:** Vanilla JS (Recommended)

---

### Q3: Copy button fallback strategy?

| Option | Description | Selected |
|--------|-------------|----------|
| Clipboard API + execCommand fallback | `navigator.clipboard.writeText()` first, fall back to hidden textarea + `execCommand('copy')`. Button shows 'Copied!' / 'Copy failed'. | ✓ |
| Clipboard API only | Simpler but fails silently on older browsers / restricted environments. | |

**User's choice:** Clipboard API with execCommand fallback (Recommended)

---

## Word Report Narrative Text

### Q1: Where does narrative text come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Template strings | Programmatic f-strings: `f"Of {total} students, {critical_count} ({critical_pct:.0f}%) are at CRITICAL risk..."` Deterministic, no API cost. | ✓ |
| Claude API | LLM-generated prose — richer but adds cost, round-trip, and fallback path. | |

**User's choice:** Template strings (Recommended)

---

### Q2: Which students get deep-dive sections?

| Option | Description | Selected |
|--------|-------------|----------|
| One per risk tier | Top 1 from CRITICAL, HIGH, MEDIUM, LOW — 4 sections showing full spectrum. Deterministic and representative. | ✓ |
| Top 3-4 CRITICAL only | Focused on urgent interventions but loses comparative view. | |

**User's choice:** One per risk tier (Recommended)

---

### Q3: Deep-dive section content?

| Option | Description | Selected |
|--------|-------------|----------|
| Data + action (no WhatsApp message) | Name, campus, risk level/score, 4 component scores, facilitator summary, recommended action. | ✓ |
| Full profile including WhatsApp message | Adds raw WhatsApp message text — better in CSV/dashboard for copy-paste. | |

**User's choice:** Data + action (Recommended)

---

## Word Report Base Approach

### Q1: How to build the .docx?

| Option | Description | Selected |
|--------|-------------|----------|
| Programmatic from scratch | `Document()`, `add_heading()`, `add_paragraph()`, `add_table()`. No binary in repo. | ✓ |
| Word template file | Pre-styled `.docx` base — cleaner default styles but adds binary file, harder to test. | |

**User's choice:** Programmatic from scratch (Recommended)

---

### Q2: Heading/style approach?

| Option | Description | Selected |
|--------|-------------|----------|
| Built-in heading levels | `add_heading(text, level=0/1/2)`. Renders in Word and Google Docs. Avoids OxmlElement issues. | ✓ |
| Custom paragraph styles via XML | OxmlElement for custom styles — known issues in python-docx 1.1.2 (STATE.md). | |

**User's choice:** Built-in heading levels only (Recommended)

---

### Q3: Table style?

| Option | Description | Selected |
|--------|-------------|----------|
| Table Grid | Safest built-in — borders render in both Word and Google Docs. STATE.md recommends. | ✓ |
| Light Shading Accent 1 | Polished in Word but may not render alternating row colors in Google Docs. | |

**User's choice:** Table Grid style (Recommended)

---

## Claude's Discretion

- `_write_html_dashboard()` signature: `(df, output_dir) -> Path`
- `_write_report()` signature: `(df, run_log, output_dir) -> Path`
- Dashboard default sort: `risk_score` descending on load
- HTML table column order (Claude to determine cleanest layout)
- HTML file encoding: UTF-8 with `<meta charset="utf-8">`
- Word report page margins: python-docx defaults (1-inch)
- Cover page styling: bold large title, run date, counts as paragraphs — no XML cover page magic

## Deferred Ideas

- Chart/sparkline in HTML dashboard (risk trend over time) — no time-series data in current pipeline
- PDF export button in HTML dashboard — requires server or headless Chrome
- Per-campus color theming in HTML
- Animated risk gauge
