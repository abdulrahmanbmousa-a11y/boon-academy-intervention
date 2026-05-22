"""Ingestion module for boon-academy-intervention.

Loads the three source CSVs, cleans per-row with full error containment,
and merges into a single canonical one-row-per-student DataFrame.

The locked signature `ingest(data_paths)` is the contract between Phase 1
and all downstream phases (2-8). Do NOT change the signature or the returned
column schema without updating STATE.md and all downstream callers.

Patterns applied (01-RESEARCH.md):
  Pattern 2 — dtype-locked CSV reader (no inferred types)
  Pattern 3 — per-row error containment (errors='coerce', warnings list)
  Pattern 4 — three-CSV merge strategy (aggregate before merge)
"""
import logging
from pathlib import Path

import pandas as pd

from src import config as cfg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level dtype dictionaries (01-PATTERNS.md L137-167)
# Keys use cfg constants — never hardcoded strings.
# "string"  -> pandas StringDtype (nullable, preserves leading zeros)
# "Float64" -> pandas Float64Dtype (nullable numeric, capital F)
# ---------------------------------------------------------------------------

DTYPE_METRICS: dict[str, str] = {
    cfg.COL_STUDENT_ID:  "string",
    cfg.COL_METRIC_DATE: "string",    # parse to datetime AFTER load (Pitfall #6)
    cfg.COL_SESSION_MIN: "string",    # load as string so read_csv never crashes on "many"/"abc"
    cfg.COL_PRACTICE_Q:  "string",    # _fill_numeric_with_zero applies pd.to_numeric(errors='coerce')
}

# The final in-memory dtype for numeric columns after coercion (Float64 = nullable, capital F)
_NUMERIC_DTYPE: str = "Float64"

DTYPE_NOTES: dict[str, str] = {
    cfg.COL_STUDENT_ID: "string",
    cfg.COL_NOTE_DATE:  "string",   # parse to datetime AFTER load
    cfg.COL_NOTE_TEXT:  "string",
}

DTYPE_META: dict[str, str] = {
    cfg.COL_STUDENT_ID:        "string",
    cfg.COL_STUDENT_NAME:      "string",
    cfg.COL_CAMPUS_ID:         "string",
    cfg.COL_PARENT_PHONE:      "string",   # CRITICAL — never let pandas infer as int (Pitfall #3)
    cfg.COL_FACILITATOR_EMAIL: "string",
}

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

# Module-level counter for UNKNOWN placeholder IDs (reset per ingest() call via closure)
_unknown_counter: list[int] = [0]


def _read_csv_safe(path: Path, dtype: dict[str, str]) -> pd.DataFrame:
    """Read a CSV with dtype-locked columns and standard NA handling.

    Catches EmptyDataError (header-only or truly empty files) and returns an
    empty DataFrame with the expected columns rather than raising.

    Args:
        path:  Absolute or relative path to the CSV file.
        dtype: Per-column dtype mapping (values must be pandas dtype strings).

    Returns:
        DataFrame with exactly the columns in dtype, or empty DataFrame on
        EmptyDataError.

    Raises:
        FileNotFoundError: propagated as-is so main.py can surface a clear error.
    """
    try:
        return pd.read_csv(
            path,
            dtype=dtype,
            keep_default_na=True,
            na_values=["", "N/A", "n/a", "NULL", "null", "-"],
            encoding="utf-8",
        )
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV at {path} has no data rows — returning empty DataFrame")
        return pd.DataFrame(columns=list(dtype.keys()))


def _ensure_ids(
    df: pd.DataFrame,
    warnings: list[dict],
    id_col: str | None = None,
) -> pd.DataFrame:
    """Scan student_id (and campus_id if present) for NaN/empty; assign UNKNOWN_NNN placeholders.

    Per D-10: missing or unparseable ID columns get an auto-incremented placeholder
    so the row is preserved for downstream analysis rather than silently discarded.

    Args:
        df:       DataFrame to scan and repair in-place.
        warnings: Mutable warnings accumulator — entries appended here.
        id_col:   Specific ID column to scan. Defaults to cfg.COL_STUDENT_ID.
                  Pass cfg.COL_CAMPUS_ID to scan campus_id separately.

    Returns:
        The same DataFrame with missing IDs replaced.
    """
    cols_to_check = [cfg.COL_STUDENT_ID]
    if cfg.COL_CAMPUS_ID in df.columns:
        cols_to_check.append(cfg.COL_CAMPUS_ID)

    for col in cols_to_check:
        if col not in df.columns:
            continue
        missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        for idx in df.index[missing_mask]:
            _unknown_counter[0] += 1
            placeholder = f"UNKNOWN_{_unknown_counter[0]:03d}"
            df.at[idx, col] = placeholder
            logger.warning(
                f"missing {col} at row_index={idx} — assigned placeholder={placeholder}"
            )
            warnings.append(
                {
                    "type": "missing_id",
                    "column": col,
                    "row_index": int(idx),
                    "assigned": placeholder,
                }
            )

    return df


def _coerce_dates(
    df: pd.DataFrame,
    date_col: str,
    warnings: list[dict],
) -> pd.DataFrame:
    """Parse a date column from string to datetime, coercing bad values to NaT.

    Per D-11: unparseable dates become NaT (not an exception). Explicit
    format="%Y-%m-%d" prevents Pitfall #6 (ambiguous date interpretation).

    Args:
        df:       DataFrame containing date_col as a string column.
        date_col: Name of the column to parse.
        warnings: Mutable warnings accumulator.

    Returns:
        DataFrame with date_col replaced by datetime64 values (NaT for bad rows).
    """
    if date_col not in df.columns:
        return df

    parsed = pd.to_datetime(df[date_col], errors="coerce", format="%Y-%m-%d")
    # bad_mask: had a non-null string value that failed to parse
    bad_mask = parsed.isna() & df[date_col].notna()
    for sid in df.loc[bad_mask, cfg.COL_STUDENT_ID]:
        logger.warning(
            f"unparseable {date_col} for student_id={sid} — assigned NaT"
        )
        warnings.append({"type": "bad_date", "column": date_col, "student_id": str(sid)})

    df = df.copy()
    df[date_col] = parsed
    return df


def _fill_numeric_with_zero(
    df: pd.DataFrame,
    col: str,
    warnings: list[dict],
) -> pd.DataFrame:
    """Coerce a numeric column, filling NaN (missing or type-mismatch) with 0.

    Two-step per DATA-05 + D-09:
      1. pd.to_numeric(errors='coerce') converts any string-type cells to NaN
         safely (logs as type_mismatch).
      2. Remaining NaN cells (originally missing) are filled with 0
         (logs as missing_numeric).

    Args:
        df:       DataFrame containing col.
        col:      Column name to repair.
        warnings: Mutable warnings accumulator.

    Returns:
        DataFrame with col fully numeric, no NaN values.
    """
    if col not in df.columns:
        return df

    # Step 1: convert any string-typed values to numeric; bad strings become NaN
    original_na = df[col].isna()
    numeric_series = pd.to_numeric(df[col], errors="coerce")
    type_mismatch_mask = ~original_na & numeric_series.isna()

    for sid in df.loc[type_mismatch_mask, cfg.COL_STUDENT_ID]:
        raw_val = str(df.loc[type_mismatch_mask & (df[cfg.COL_STUDENT_ID] == sid), col].iloc[0])
        logger.warning(
            f"type mismatch in {col} for student_id={sid} — non-numeric value coerced to 0"
        )
        warnings.append(
            {"type": "type_mismatch", "column": col, "student_id": str(sid), "raw_value": raw_val}
        )

    # Step 2: fill remaining NaN (originally missing, or type-mismatch now NaN)
    missing_mask = numeric_series.isna()
    for sid in df.loc[missing_mask & ~type_mismatch_mask, cfg.COL_STUDENT_ID]:
        logger.warning(
            f"missing {col} for student_id={sid} — filled with 0"
        )
        warnings.append({"type": "missing_numeric", "column": col, "student_id": str(sid)})

    df = df.copy()
    df[col] = numeric_series.fillna(0).astype(_NUMERIC_DTYPE)
    return df


def _dedupe_student_ids(
    df: pd.DataFrame,
    warnings: list[dict],
) -> pd.DataFrame:
    """Remove duplicate student_id rows, keeping the last occurrence.

    Per D-04: logs a warning per duplicated student_id and appends a
    duplicate_id entry to the warnings accumulator.

    Args:
        df:       DataFrame (typically student_metadata).
        warnings: Mutable warnings accumulator.

    Returns:
        DataFrame with unique student_id values (keep='last').
    """
    dupes = df[df.duplicated(subset=[cfg.COL_STUDENT_ID], keep=False)]
    for sid in dupes[cfg.COL_STUDENT_ID].unique():
        logger.warning(f"duplicate student_id={sid} — keeping last occurrence")
        warnings.append({"type": "duplicate_id", "student_id": str(sid)})

    return df.drop_duplicates(subset=[cfg.COL_STUDENT_ID], keep="last").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public API — locked signature (STATE.md L93)
# ---------------------------------------------------------------------------


def ingest(data_paths: dict[str, Path]) -> pd.DataFrame:
    """Load 3 CSVs, clean per-row, merge to canonical one-row-per-student DataFrame.

    Applies Pattern 2 (dtype-locked read), Pattern 3 (per-row error containment),
    and Pattern 4 (aggregate-then-merge) from 01-RESEARCH.md.

    Args:
        data_paths: dict with keys "metrics", "notes", "metadata" mapping to
                    Path objects for the corresponding CSV files.

    Returns:
        Single DataFrame with one row per student_id containing columns:
            student_id, student_name, campus_id, parent_phone, facilitator_email,
            session_total_min, practice_total_q, attendance_days,
            daily_session_series (list[float]), daily_practice_series (list[float]),
            daily_dates (list[str]), latest_note_date, latest_note_text.

        df.attrs["data_quality_warnings"]: list[dict] — cleaning events accumulated
        during ingestion. Each entry has a "type" key with one of:
        missing_numeric | duplicate_id | bad_date | missing_id | type_mismatch.

    Raises:
        FileNotFoundError: if any path in data_paths does not exist on disk.
        KeyError: if data_paths is missing required keys "metrics", "notes", "metadata".
    """
    # Reset the module-level UNKNOWN counter for each ingest() call
    _unknown_counter[0] = 0

    warnings: list[dict] = []

    # ------------------------------------------------------------------
    # Pattern 2: dtype-locked CSV reads
    # ------------------------------------------------------------------
    metrics = _read_csv_safe(data_paths["metrics"], DTYPE_METRICS)
    notes = _read_csv_safe(data_paths["notes"], DTYPE_NOTES)
    metadata = _read_csv_safe(data_paths["metadata"], DTYPE_META)

    # ------------------------------------------------------------------
    # D-10: Validate / repair missing IDs in all three DataFrames
    # ------------------------------------------------------------------
    metadata = _ensure_ids(metadata, warnings)
    metrics = _ensure_ids(metrics, warnings)
    notes = _ensure_ids(notes, warnings)

    # ------------------------------------------------------------------
    # D-11: Parse dates with explicit format (Pitfall #6 pre-emption)
    # ------------------------------------------------------------------
    metrics = _coerce_dates(metrics, cfg.COL_METRIC_DATE, warnings)
    notes = _coerce_dates(notes, cfg.COL_NOTE_DATE, warnings)

    # ------------------------------------------------------------------
    # D-09 + DATA-05: Coerce numerics and fill NaN with 0
    # ------------------------------------------------------------------
    metrics = _fill_numeric_with_zero(metrics, cfg.COL_SESSION_MIN, warnings)
    metrics = _fill_numeric_with_zero(metrics, cfg.COL_PRACTICE_Q, warnings)

    # ------------------------------------------------------------------
    # D-04: Deduplicate metadata (keep='last')
    # ------------------------------------------------------------------
    metadata = _dedupe_student_ids(metadata, warnings)

    # ------------------------------------------------------------------
    # Pattern 4: Aggregate metrics per-student BEFORE merge
    # (avoids row explosion; daily series kept for Phase 2 trend calc)
    # ------------------------------------------------------------------
    if len(metrics) > 0:
        metrics_agg = (
            metrics.groupby(cfg.COL_STUDENT_ID)
            .agg(
                session_total_min=(cfg.COL_SESSION_MIN, "sum"),
                practice_total_q=(cfg.COL_PRACTICE_Q, "sum"),
                attendance_days=(cfg.COL_SESSION_MIN, lambda s: int((s > 0).sum())),
                daily_session_series=(cfg.COL_SESSION_MIN, list),
                daily_practice_series=(cfg.COL_PRACTICE_Q, list),
                daily_dates=(cfg.COL_METRIC_DATE, list),
            )
            .reset_index()
        )
    else:
        # Empty metrics — produce empty aggregation with correct columns
        metrics_agg = pd.DataFrame(
            columns=[
                cfg.COL_STUDENT_ID,
                "session_total_min",
                "practice_total_q",
                "attendance_days",
                "daily_session_series",
                "daily_practice_series",
                "daily_dates",
            ]
        )

    # ------------------------------------------------------------------
    # Aggregate notes: latest note per student
    # ------------------------------------------------------------------
    if len(notes) > 0:
        notes_sorted = notes.sort_values(cfg.COL_NOTE_DATE, ascending=False)
        notes_latest = notes_sorted.drop_duplicates(
            subset=[cfg.COL_STUDENT_ID], keep="first"
        )
        notes_latest = notes_latest.rename(
            columns={
                cfg.COL_NOTE_DATE: "latest_note_date",
                cfg.COL_NOTE_TEXT: "latest_note_text",
            }
        )[[cfg.COL_STUDENT_ID, "latest_note_date", "latest_note_text"]]
    else:
        notes_latest = pd.DataFrame(
            columns=[cfg.COL_STUDENT_ID, "latest_note_date", "latest_note_text"]
        )

    # ------------------------------------------------------------------
    # Merge: metadata (base) <- metrics_agg <- notes_latest
    # how="left" ensures every metadata row survives even if metrics/notes absent
    # ------------------------------------------------------------------
    df = metadata.merge(metrics_agg, on=cfg.COL_STUDENT_ID, how="left")
    df = df.merge(notes_latest, on=cfg.COL_STUDENT_ID, how="left")

    # ------------------------------------------------------------------
    # Post-merge: fill numeric aggregation columns with 0 for students
    # who had no metrics rows (left-join produces NaN for them — D-09 spirit)
    # ------------------------------------------------------------------
    numeric_fill_cols = ["session_total_min", "practice_total_q", "attendance_days"]
    for col in numeric_fill_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # ------------------------------------------------------------------
    # Attach warnings side-channel (caller flushes to run_log in Phase 4)
    # ------------------------------------------------------------------
    df.attrs["data_quality_warnings"] = warnings
    logger.info(
        f"ingestion complete — {len(df)} students, {len(warnings)} warnings"
    )

    return df
