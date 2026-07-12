"""Prediction serialization utilities."""

import pandas as pd

from application.constants import (
    HUMAN_LABEL_KEY,
    HUMAN_SUBCATEGORY_KEY,
    HUMAN_SUBCATEGORY_NORMALIZED_KEY,
    LLM_SUBCATEGORY_NORMALIZED_KEY,
    ORIGINAL_INDEX_KEY,
    PRED_LABEL_COL,
    PRED_SUBCATEGORY_COL,
    QUESTION_KEY,
    SOURCE_ROW_NUMBER_KEY,
)
from application.ports.config import RunConfig


def build_prediction_records(
    cfg: RunConfig,
    test_df: pd.DataFrame,
    question_col: str,
    label_col: str | None,
    pred_map: dict[int, str],
    subcat_map: dict[int, str | None] | None,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """
    Attach predictions (and optional subcategories) to the DataFrame and build JSON records.

    Args:
        cfg: RunConfig instance with taxonomy configuration
        test_df: Test DataFrame with questions and optional human labels
        question_col: Column name containing questions
        label_col: Column name containing human labels (optional)
        pred_map: Dictionary mapping DataFrame indices to predicted labels
        subcat_map: Dictionary mapping DataFrame indices to predicted subcategories (optional)

    Returns:
        Tuple of (DataFrame with predictions attached, list of JSON-serializable records)
    """
    test_df_out = test_df.copy()
    human_subcat_col = (
        cfg.columns.test_subcategory_col
        if (cfg.columns.test_subcategory_col and cfg.columns.test_subcategory_col in test_df_out.columns)
        else None
    )
    test_df_out[PRED_LABEL_COL] = test_df_out.index.map(lambda idx: pred_map.get(idx))

    if subcat_map is not None:
        # Only create the column if we are in subcategory mode
        test_df_out[PRED_SUBCATEGORY_COL] = test_df_out.index.map(lambda idx: subcat_map.get(idx))

    records: list[dict] = []
    for _, row in test_df_out.iterrows():
        record: dict[str, object] = {}

        if ORIGINAL_INDEX_KEY in test_df_out.columns:
            record[ORIGINAL_INDEX_KEY] = row[ORIGINAL_INDEX_KEY]
        if SOURCE_ROW_NUMBER_KEY in test_df_out.columns:
            record[SOURCE_ROW_NUMBER_KEY] = row[SOURCE_ROW_NUMBER_KEY]

        record[QUESTION_KEY] = row[question_col]

        # Human top-level category (LLQ/DRQ/GDQ)
        record[HUMAN_LABEL_KEY] = row[label_col] if label_col is not None else None

        # Human subcategory (raw)
        if human_subcat_col is not None:
            raw_human_sub = row[human_subcat_col]
            record[HUMAN_SUBCATEGORY_KEY] = raw_human_sub
            # Normalized human subcategory (optional extra field)
            record[HUMAN_SUBCATEGORY_NORMALIZED_KEY] = cfg.taxonomy.normalize_subcategory(raw_human_sub)
        else:
            record[HUMAN_SUBCATEGORY_KEY] = None
            record[HUMAN_SUBCATEGORY_NORMALIZED_KEY] = None

        # LLM predictions
        record[PRED_LABEL_COL] = row[PRED_LABEL_COL]

        if PRED_SUBCATEGORY_COL in test_df_out.columns:
            raw_llm_sub = row[PRED_SUBCATEGORY_COL]
            record[PRED_SUBCATEGORY_COL] = raw_llm_sub
            record[LLM_SUBCATEGORY_NORMALIZED_KEY] = cfg.taxonomy.normalize_subcategory(raw_llm_sub)
        else:
            record[PRED_SUBCATEGORY_COL] = None
            record[LLM_SUBCATEGORY_NORMALIZED_KEY] = None

        records.append(record)

    return test_df_out, records
