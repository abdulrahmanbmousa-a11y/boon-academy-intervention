"""LLM enrichment engine stub for boon-academy-intervention.

Phase 3 will implement campus-batched Claude API enrichment with 3-layer fallback.
Signature is LOCKED per STATE.md — all downstream phases depend on it.
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def enrich_with_llm(df: pd.DataFrame, api_key: str) -> pd.DataFrame:
    """Enrich student DataFrame with Claude-generated intervention recommendations.

    Phase 3 implementation: batches CRITICAL/HIGH students by campus, calls
    Claude API once per campus batch, writes WhatsApp messages and action items.
    Three-layer fallback: HTTP retry -> re-prompt -> rule-based template.
    Never raises — pipeline always completes even on API failure.

    Args:
        df: One-row-per-student DataFrame with risk scores from score_risk().
        api_key: Anthropic API key (cfg.ANTHROPIC_API_KEY).

    Returns:
        DataFrame with LLM-generated intervention text columns added.

    Raises:
        NotImplementedError: Until Phase 3 is implemented.
    """
    raise NotImplementedError("Phase 3")
