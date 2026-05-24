# boon-academy-intervention

AI-powered student intervention pipeline. Raises facilitator intervention rates from 30% to 80%+
by scoring student risk and drafting WhatsApp parent messages using Claude.

## Quick Start

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
make demo      # Unix/macOS
./make.ps1 demo  # Windows
```

## What it produces

- `outputs/intervention_priority_list.xlsx` — all students ranked
- `outputs/facilitator_dashboard_*.xlsx` — per-campus dashboards
- `outputs/whatsapp_messages.csv` — pre-drafted parent messages
- `outputs/intervention_report.docx` — full narrative report
- `outputs/facilitator_dashboard.html` — self-contained browser dashboard
- `outputs/run_log.json` — pipeline run metadata (student counts, token usage)
- `docs/` — 8 documentation .docx files (architecture, security, scalability, and more)

## Requirements

Python 3.12 required (pandas==2.2.3 has no wheel for Python 3.14).
