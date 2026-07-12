"""Subcategory alignment table generation."""

from collections.abc import Callable, Mapping, Sequence

import pandas as pd


def compute_subcategory_alignment_table(
    df: pd.DataFrame,
    human_top_label_col: str,
    human_subcat_col: str,
    llm_top_label_col: str,
    llm_subcat_col: str,
    labels_order: Sequence[str],
    taxonomy_ordering: Mapping[str, Sequence[str]],
    normalize_subcategory: Callable[[object], str],
) -> pd.DataFrame:
    """
    Build a table of subcategory-level alignment, grouped by human top-level label.

    Columns in the result:
      - Category: human top-level label (LLQ, DRQ, GDQ)
      - Sub-category: human subcategory string
      - Total count in dataset: number of questions with this (Category, Sub-category)
      - LLM alignment (count): count where both top-level and subcategory match the human labels
      - LLM alignment (%): alignment_count / total * 100

    Args:
        df: DataFrame with both human and LLM labels
        human_top_label_col: Column name for human top-level label
        human_subcat_col: Column name for human subcategory
        llm_top_label_col: Column name for LLM top-level label
        llm_subcat_col: Column name for LLM subcategory
        labels_order: Canonical ordering of top-level labels (e.g., ['LLQ', 'DRQ', 'GDQ'])
        taxonomy_ordering: Mapping of top-level label to ordered list of subcategories
        normalize_subcategory: Function to normalize subcategory strings

    Returns:
        DataFrame with alignment statistics, sorted by category and subcategory
    """
    sub_df = df.copy()

    # Ensure required columns exist
    for col in [human_top_label_col, human_subcat_col, llm_top_label_col, llm_subcat_col]:
        if col not in sub_df.columns:
            raise KeyError(f"Required column '{col}' not found in DataFrame.")

    # Drop rows with missing human subcategory
    sub_df = sub_df.dropna(subset=[human_subcat_col])

    # Normalize to strings + strip whitespace
    sub_df[human_top_label_col] = sub_df[human_top_label_col].astype(str).str.strip()
    sub_df[llm_top_label_col] = sub_df[llm_top_label_col].astype(str).str.strip()

    # Replace NaN values with None to prevent string conversion to "nan"
    # sub_df[llm_subcat_col] = sub_df[llm_subcat_col].where(sub_df[llm_subcat_col].notna(), None)

    # Apply subcategory normalisation to BOTH human and LLM subcategories
    sub_df[human_subcat_col] = sub_df[human_subcat_col].apply(normalize_subcategory)
    sub_df[llm_subcat_col] = sub_df[llm_subcat_col].apply(normalize_subcategory)

    rows: list[dict[str, object]] = []

    # Group by (human top-level, human subcategory)
    grouped = sub_df.groupby([human_top_label_col, human_subcat_col], dropna=False)

    for (top_label, subcat), group in grouped:
        total = len(group)

        # Alignment = both top-level AND subcategory match the human labels
        align_mask = (group[llm_top_label_col] == group[human_top_label_col]) & (
            group[llm_subcat_col] == group[human_subcat_col]
        )
        align_count = int(align_mask.sum())
        align_pct = (align_count / total * 100.0) if total > 0 else float("nan")

        rows.append(
            {
                "Category": top_label,
                "Sub-category": subcat,
                "Total count in dataset": total,
                "LLM alignment (count)": align_count,
                "LLM alignment (%)": round(align_pct, 1),
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return pd.DataFrame(
            columns=[
                "Category",
                "Sub-category",
                "Total count in dataset",
                "LLM alignment (count)",
                "LLM alignment (%)",
            ]
        )

    # Enforce LLQ -> DRQ -> GDQ order for the Category column
    category_order = pd.CategoricalDtype(
        categories=list(labels_order),
        ordered=True,
    )
    result["Category"] = result["Category"].astype(str).str.strip().astype(category_order)

    # Build a fast lookup: (Category, Sub-category) -> sort index
    order_map = {cat: {sub: idx for idx, sub in enumerate(subs)} for cat, subs in taxonomy_ordering.items()}

    def subcat_order(row):
        cat = str(row["Category"])
        sub = str(row["Sub-category"])
        mapping = order_map.get(cat, {})
        # Unknown subcategories get a large index so they appear after the known ones,
        # and then fall back to alphabetical by name.
        return mapping.get(sub, len(mapping))

    result["SubcatOrder"] = result.apply(subcat_order, axis=1)

    # Final ordering: Category (LLQ -> DRQ -> GDQ), then the custom SubcatOrder,
    # then Sub-category name as a tie-breaker
    result = result.sort_values(["Category", "SubcatOrder", "Sub-category"]).reset_index(drop=True)

    # Drop the helper column before returning
    return result.drop(columns=["SubcatOrder"])
