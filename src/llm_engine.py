"""LLM enrichment engine for boon-academy-intervention.

Implements campus-batched Claude API enrichment with three-layer fallback.
Signature is LOCKED per STATE.md — all downstream phases depend on it.

Patterns applied (03-RESEARCH.md):
- Pattern 1: Anthropic client instantiated inside function (not module-level — Pitfall 3)
- Pattern 2: tool-use structured output (avoid markdown-wrapped JSON — STATE.md pitfall)
- Pattern 3: three-layer fallback (SDK retry -> re-prompt -> YAML template)
- Pattern 5: YAML templates loaded once at module import (not per-call)
- Pattern 6: tuple return (df, counts_dict) — df.attrs is fragile in pandas 2.2.x
- Pattern 7: chunk loop with CRITICAL-first sort using map key (Pitfall 2)

Decisions applied (03-CONTEXT.md):
- D-01: templates in src/llm_templates.yaml, loaded at import time
- D-02: 2 variants — CRITICAL and HIGH
- D-03: format_map() interpolation with row.to_dict()
- D-04: chunks of MAX_STUDENTS_PER_LLM_CALL (default 10); 15 students -> 2 calls (10+5)
- D-05: CRITICAL first (risk_score desc), then HIGH (risk_score desc); uses map key not alpha sort
- D-06: 4 new columns — facilitator_summary, whatsapp_message, generated_by, llm_error_reason
- D-07: MEDIUM/LOW rows get None in all 4 columns (not empty string, not 'skipped')
- D-08: generated_by: 'llm' or 'template' only; never None for CRITICAL/HIGH

Security (T-03-03, T-03-04, T-03-05, T-03-06, T-03-07):
- student_name and parent_phone NEVER appear in any log statement or API prompt
- api_key NEVER logged
- KeyError/StopIteration on tool response routed to Layer 3 (malformed_response)
- yaml.safe_load() (not yaml.load()) — prevents code execution from YAML
- format_map() uses known keys only from row.to_dict()

Pitfalls avoided:
- Pitfall 1: KeyError on tool_block.input['students'] caught -> Layer 3
- Pitfall 2: CRITICAL-first sort via map key {'CRITICAL':0,'HIGH':1} (not alphabetical)
- Pitfall 3: Anthropic() instantiated inside enrich_with_llm(), not at module level
- Pitfall 5: YAML >- block scalars prevent misinterpretation of {format_placeholders}
- Pitfall 6: http_client injected via Anthropic(http_client=...) with max_retries=0 in tests
"""
import logging
from pathlib import Path
from typing import Optional

import anthropic
import httpx
import pandas as pd
import yaml

from src import config as cfg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants — loaded once at import time (Pattern 5, D-01)
# ---------------------------------------------------------------------------

_TEMPLATES_PATH = Path(__file__).parent / "llm_templates.yaml"

with _TEMPLATES_PATH.open("r", encoding="utf-8") as _f:
    _TEMPLATES: dict = yaml.safe_load(_f)
# Loaded once at import — not per-call (D-01)

INTERVENTION_TOOL: dict = {
    "name": "generate_interventions",
    "description": (
        "Generate facilitator intervention summaries and WhatsApp parent messages "
        "for a list of at-risk students. Return one result object per student_id provided."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "students": {
                "type": "array",
                "description": "One result per student in the request, in the same order.",
                "items": {
                    "type": "object",
                    "properties": {
                        cfg.COL_STUDENT_ID: {
                            "type": "string",
                            "description": "The student_id from the request.",
                        },
                        cfg.COL_FACILITATOR_SUMMARY: {
                            "type": "string",
                            "description": (
                                "Exactly 2 sentences. Action-oriented summary for "
                                "the facilitator describing what to do and why."
                            ),
                        },
                        cfg.COL_WHATSAPP_MESSAGE: {
                            "type": "string",
                            "description": (
                                "WhatsApp-ready parent message. Under 100 words. "
                                "Warm, professional tone. Does not mention risk scores."
                            ),
                        },
                    },
                    "required": [
                        cfg.COL_STUDENT_ID,
                        cfg.COL_FACILITATOR_SUMMARY,
                        cfg.COL_WHATSAPP_MESSAGE,
                    ],
                },
            }
        },
        "required": ["students"],
    },
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _classify_error(exc: anthropic.APIError) -> str:
    """Classify an Anthropic API exception into a short error reason string.

    Returns:
        'timeout' for APITimeoutError, 'rate_limit' for RateLimitError,
        'max_retries_exceeded' for all other APIError subtypes.
    """
    if isinstance(exc, anthropic.APITimeoutError):
        return "timeout"
    if isinstance(exc, anthropic.RateLimitError):
        return "rate_limit"
    return "max_retries_exceeded"


def _apply_templates(chunk: pd.DataFrame, error_reason: str) -> list[dict]:
    """Generate fallback intervention content from YAML templates for a chunk of students.

    Uses str.format_map() with row.to_dict() — all format keys come from the scored
    DataFrame columns (known keys only; no user-controlled free text). Never includes
    student_name or parent_phone in log output (T-03-06, LLM-08).

    Args:
        chunk: DataFrame slice containing only CRITICAL or HIGH rows.
        error_reason: Short string explaining why the template was used
            (e.g. 'timeout', 'malformed_response', 'llm_disabled').

    Returns:
        List of dicts with keys: student_id, facilitator_summary, whatsapp_message,
        generated_by='template', llm_error_reason=error_reason.
    """
    results: list[dict] = []
    for _, row in chunk.iterrows():
        risk_level = row[cfg.COL_RISK_LEVEL]
        # Coerce numpy scalars to native Python types so format specifiers like :.0% work
        row_dict = {k: (v.item() if hasattr(v, "item") else v) for k, v in row.to_dict().items()}
        tmpl = _TEMPLATES.get(risk_level, {})
        if not tmpl:
            continue
        facilitator_summary = tmpl[cfg.COL_FACILITATOR_SUMMARY].format_map(row_dict)
        whatsapp_message = tmpl[cfg.COL_WHATSAPP_MESSAGE].format_map(row_dict)
        results.append(
            {
                cfg.COL_STUDENT_ID: row[cfg.COL_STUDENT_ID],
                cfg.COL_FACILITATOR_SUMMARY: facilitator_summary,
                cfg.COL_WHATSAPP_MESSAGE: whatsapp_message,
                cfg.COL_GENERATED_BY: "template",
                cfg.COL_LLM_ERROR_REASON: error_reason,
            }
        )
    return results


def _build_prompt(student_data: list[dict]) -> str:
    """Build a PII-safe batch prompt string from a list of student dicts.

    Only includes: student_id, risk_level, risk_score, attendance_rate,
    avg_practice_questions, trend_direction, days_since_last_note,
    recommended_action. Never includes student_name or parent_phone (LLM-08, T-03-04).
    """
    return (
        f"Generate intervention content for {len(student_data)} at-risk students. "
        f"For each student in the list below:\n"
        f"- facilitator_summary must be exactly 2 sentences, action-oriented.\n"
        f"- whatsapp_message must be under 100 words, warm and professional, "
        f"and must NOT mention risk scores.\n\n"
        f"Student data:\n{student_data}"
    )


def _write_results_back(
    df: pd.DataFrame,
    results: list[dict],
    generated_by: str,
    llm_error_reason: Optional[str] = None,
) -> None:
    """Write result dicts back into df rows matched by student_id.

    Mutates df in-place (caller already holds a copy). Uses df.loc for
    safe row-level assignment (Pattern from 03-PATTERNS.md).

    Args:
        df: The working copy of the DataFrame.
        results: List of result dicts, each with 'student_id', 'facilitator_summary',
            'whatsapp_message'. May also have 'generated_by' and 'llm_error_reason'
            keys (from _apply_templates); if present they take precedence over args.
        generated_by: 'llm' or 'template' — used when not already in result dict.
        llm_error_reason: Error string for fallback rows; None for successful LLM rows.
    """
    for result in results:
        sid = result[cfg.COL_STUDENT_ID]
        idx = df.index[df[cfg.COL_STUDENT_ID] == sid]
        if len(idx) == 0:
            logger.warning(
                "student_id from LLM response not found in DataFrame chunk — skipping"
            )
            continue
        df.loc[idx, cfg.COL_FACILITATOR_SUMMARY] = result[cfg.COL_FACILITATOR_SUMMARY]
        df.loc[idx, cfg.COL_WHATSAPP_MESSAGE] = result[cfg.COL_WHATSAPP_MESSAGE]
        # result dict from _apply_templates already has generated_by/llm_error_reason
        df.loc[idx, cfg.COL_GENERATED_BY] = result.get(cfg.COL_GENERATED_BY, generated_by)
        df.loc[idx, cfg.COL_LLM_ERROR_REASON] = result.get(
            cfg.COL_LLM_ERROR_REASON, llm_error_reason
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_with_llm(
    df: pd.DataFrame,
    api_key: str,
    http_client: Optional[httpx.Client] = None,
) -> tuple[pd.DataFrame, dict]:
    """Enrich student DataFrame with Claude-generated intervention recommendations.

    Groups CRITICAL and HIGH students by campus, sorts them (CRITICAL first then HIGH,
    both descending by risk_score), chunks into batches of at most
    cfg.MAX_STUDENTS_PER_LLM_CALL, and calls the Anthropic Claude API once per chunk
    using tool-use structured output.

    Three-layer fallback per chunk:
      Layer 1: SDK automatic retry (max_retries=3 with exponential backoff).
               Handles transient network errors without any code here.
      Layer 2: One re-prompt attempt on APIConnectionError/APITimeoutError/
               RateLimitError/APIStatusError after Layer 1 exhaustion.
      Layer 3: YAML template fallback on re-prompt failure OR malformed tool response
               (KeyError/StopIteration). Always succeeds.

    Never raises — the pipeline always completes even on total API failure.

    LLM_ENABLED=false bypass: applies templates for all CRITICAL/HIGH with
    llm_error_reason='llm_disabled' and makes zero API calls.

    PII discipline (LLM-08, T-03-03, T-03-04):
      - student_name and parent_phone are NEVER sent to the API prompt.
      - student_name and parent_phone are NEVER included in any log statement.
      - api_key is NEVER logged.

    MEDIUM and LOW students receive None in all 4 output columns (D-07).

    Args:
        df: One-row-per-student DataFrame with risk scores from score_risk().
        api_key: Anthropic API key — never logged (LLM-07).
        http_client: Optional httpx.Client for test injection (respx mock transport).
            If None, production client is created with max_retries=3.
            If provided, max_retries=0 to prevent SDK retry loops in tests.

    Returns:
        Tuple of:
          - DataFrame (copy) with 4 new columns:
              cfg.COL_FACILITATOR_SUMMARY, cfg.COL_WHATSAPP_MESSAGE,
              cfg.COL_GENERATED_BY, cfg.COL_LLM_ERROR_REASON
          - counts dict:
              {"api_calls_made": int, "tokens_used": {"input": int, "output": int},
               "fallbacks_triggered": int}
    """
    # Purity guarantee — mirrors score_risk() pattern (Pitfall 8 / CLAUDE.md)
    df = df.copy()

    # Initialize all 4 output columns to None for every row (D-07: MEDIUM/LOW stay None)
    df[cfg.COL_FACILITATOR_SUMMARY] = None
    df[cfg.COL_WHATSAPP_MESSAGE] = None
    df[cfg.COL_GENERATED_BY] = None
    df[cfg.COL_LLM_ERROR_REASON] = None

    # Local accumulators — returned as second element of tuple (Pattern 6)
    api_calls: int = 0
    tokens: dict[str, int] = {"input": 0, "output": 0}
    fallbacks: int = 0

    # Filter to CRITICAL/HIGH only — MEDIUM/LOW already have None columns (D-07)
    at_risk_mask = df[cfg.COL_RISK_LEVEL].isin(["CRITICAL", "HIGH"])
    at_risk_df = df[at_risk_mask]

    # ------------------------------------------------------------------
    # LLM_ENABLED=false early-exit path (D-09)
    # ------------------------------------------------------------------
    if not cfg.LLM_ENABLED:
        if not at_risk_df.empty:
            results = _apply_templates(at_risk_df, "llm_disabled")
            _write_results_back(df, results, generated_by="template")
            fallbacks += len(at_risk_df)
            logger.info(
                f"LLM_ENABLED=false — applied templates for {len(at_risk_df)} "
                f"CRITICAL/HIGH students; 0 API calls made"
            )
        return df, {
            "api_calls_made": api_calls,
            "tokens_used": tokens,
            "fallbacks_triggered": fallbacks,
        }

    # ------------------------------------------------------------------
    # Client instantiation — inside function, never at module level (Pitfall 3, Pattern 1)
    # ------------------------------------------------------------------
    if http_client is None:
        # Production path: SDK handles Layer 1 retries automatically (LLM-04)
        client = anthropic.Anthropic(
            api_key=api_key,
            max_retries=3,
            timeout=float(cfg.TIMEOUT_SECONDS),
        )
    else:
        # Test injection path: max_retries=0 prevents SDK retry loops masking assertions
        client = anthropic.Anthropic(
            api_key=api_key,
            http_client=http_client,
            max_retries=0,
        )

    # ------------------------------------------------------------------
    # Campus loop — skip entirely if no at-risk students
    # ------------------------------------------------------------------
    if at_risk_df.empty:
        logger.info(
            "enrich_with_llm: no CRITICAL/HIGH students — skipping API calls"
        )
        return df, {
            "api_calls_made": api_calls,
            "tokens_used": tokens,
            "fallbacks_triggered": fallbacks,
        }

    for campus_id, campus_df in at_risk_df.groupby(cfg.COL_CAMPUS_ID):
        # D-05: CRITICAL first (descending risk_score), then HIGH (descending risk_score)
        # Cannot use plain ascending=[True,False] on risk_level strings — "CRITICAL" > "HIGH"
        # alphabetically, which sorts HIGH-first (Pitfall 2). Use map key instead.
        campus_students = campus_df.sort_values(
            by=[cfg.COL_RISK_LEVEL, cfg.COL_RISK_SCORE],
            ascending=[True, False],
            key=lambda col: (
                col.map({"CRITICAL": 0, "HIGH": 1})
                if col.name == cfg.COL_RISK_LEVEL
                else col
            ),
        )

        logger.info(
            f"Campus {campus_id}: processing {len(campus_students)} CRITICAL/HIGH students"
        )

        # D-04: chunk loop — 15 students -> 2 calls (10+5), no truncation
        for i in range(0, len(campus_students), cfg.MAX_STUDENTS_PER_LLM_CALL):
            chunk = campus_students.iloc[i : i + cfg.MAX_STUDENTS_PER_LLM_CALL]

            # Build PII-safe student data list for the prompt (LLM-08, T-03-04)
            # NEVER include student_name or parent_phone
            student_data = [
                {
                    cfg.COL_STUDENT_ID: row[cfg.COL_STUDENT_ID],
                    cfg.COL_RISK_LEVEL: row[cfg.COL_RISK_LEVEL],
                    cfg.COL_RISK_SCORE: float(row[cfg.COL_RISK_SCORE]),
                    cfg.COL_ATTENDANCE_RATE: float(row[cfg.COL_ATTENDANCE_RATE]),
                    cfg.COL_AVG_PRACTICE: float(row[cfg.COL_AVG_PRACTICE]),
                    cfg.COL_TREND_DIR: row[cfg.COL_TREND_DIR],
                    cfg.COL_DAYS_SINCE_NOTE: float(row[cfg.COL_DAYS_SINCE_NOTE]),
                    cfg.COL_RECOMMENDED_ACTION: row[cfg.COL_RECOMMENDED_ACTION],
                }
                for _, row in chunk.iterrows()
            ]

            prompt = _build_prompt(student_data)

            logger.debug(
                f"Campus {campus_id}: chunk {i // cfg.MAX_STUDENTS_PER_LLM_CALL + 1} — "
                f"{len(chunk)} students"
            )

            # ----------------------------------------------------------
            # Layer 1: SDK call (max_retries=3 in production, 0 in tests)
            # Layer 2: one re-prompt on API exceptions
            # Layer 3: YAML template on re-prompt failure or malformed response
            # ----------------------------------------------------------
            try:
                response = client.messages.create(
                    model=cfg.ANTHROPIC_MODEL,
                    max_tokens=cfg.MAX_TOKENS,
                    temperature=cfg.TEMPERATURE,
                    tools=[INTERVENTION_TOOL],
                    tool_choice={"type": "tool", "name": "generate_interventions"},
                    messages=[{"role": "user", "content": prompt}],
                )
                # Parse tool response — KeyError -> Layer 3 (Pitfall 1, T-03-05)
                if response.stop_reason == "max_tokens":
                    logger.warning(
                        f"Campus {campus_id}: response truncated (max_tokens={cfg.MAX_TOKENS}) "
                        f"— increase MAX_TOKENS env var"
                    )
                    raise ValueError("max_tokens exceeded")
                tool_block = next(
                    b for b in response.content
                    if isinstance(b, anthropic.types.ToolUseBlock)
                )
                results = tool_block.input["students"]  # KeyError falls to outer except
                tokens["input"] += response.usage.input_tokens
                tokens["output"] += response.usage.output_tokens
                api_calls += 1
                _write_results_back(df, results, generated_by="llm")
                logger.debug(
                    f"Campus {campus_id}: chunk LLM success — "
                    f"input_tokens={response.usage.input_tokens}, "
                    f"output_tokens={response.usage.output_tokens}"
                )

            except (
                anthropic.APIConnectionError,
                anthropic.APITimeoutError,
                anthropic.RateLimitError,
                anthropic.APIStatusError,
            ) as exc:
                # Layer 1 exhausted — attempt Layer 2 re-prompt
                error_reason = _classify_error(exc)
                logger.warning(
                    f"Campus {campus_id}: API error ({error_reason}) after retries — "
                    f"attempting re-prompt"
                )
                try:
                    # Layer 2: simplified re-prompt (same structure)
                    response2 = client.messages.create(
                        model=cfg.ANTHROPIC_MODEL,
                        max_tokens=cfg.MAX_TOKENS,
                        temperature=cfg.TEMPERATURE,
                        tools=[INTERVENTION_TOOL],
                        tool_choice={"type": "tool", "name": "generate_interventions"},
                        messages=[{"role": "user", "content": prompt}],
                    )
                    tool_block2 = next(
                        b for b in response2.content
                        if isinstance(b, anthropic.types.ToolUseBlock)
                    )
                    results2 = tool_block2.input["students"]
                    tokens["input"] += response2.usage.input_tokens
                    tokens["output"] += response2.usage.output_tokens
                    api_calls += 1
                    _write_results_back(df, results2, generated_by="llm")
                    logger.info(
                        f"Campus {campus_id}: re-prompt succeeded for chunk"
                    )

                except Exception:
                    # Layer 3: YAML template fallback
                    logger.warning(
                        f"Campus {campus_id}: re-prompt failed — "
                        f"applying template fallback for {len(chunk)} students"
                    )
                    template_results = _apply_templates(chunk, error_reason)
                    _write_results_back(df, template_results, generated_by="template")
                    fallbacks += len(chunk)

            except (KeyError, ValueError, StopIteration) as exc:
                # Malformed tool response — skip directly to Layer 3 (Pitfall 1, T-03-05)
                logger.warning(
                    f"Campus {campus_id}: malformed LLM tool response ({type(exc).__name__}) "
                    f"— applying template fallback for {len(chunk)} students"
                )
                template_results = _apply_templates(chunk, "malformed_response")
                _write_results_back(df, template_results, generated_by="template")
                fallbacks += len(chunk)

    # Aggregate log only — no per-student identifiers (LLM-08, T-03-03)
    logger.info(
        f"enrich_with_llm complete — "
        f"api_calls={api_calls}, tokens_input={tokens['input']}, "
        f"tokens_output={tokens['output']}, fallbacks={fallbacks}"
    )

    return df, {
        "api_calls_made": api_calls,
        "tokens_used": tokens,
        "fallbacks_triggered": fallbacks,
    }
