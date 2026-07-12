"""Dataset loading utilities."""

import logging
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from infrastructure.config.models import RunConfig

logger = logging.getLogger(__name__)


def read_table(path: Path, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """
    Read tabular data file (Excel or CSV) based on file extension.

    Supported formats:
    - Excel: .xlsx, .xls
    - CSV: .csv
    - Plain text: .txt (one question per line, exposed as a "question" column)

    Args:
        path: Path to data file
        columns: Optional sequence of column names to select

    Returns:
        pandas DataFrame

    Raises:
        ValueError: If file format is not supported
        FileNotFoundError: If file does not exist
        Exception: If file cannot be read (pandas exceptions)
    """
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    suffix = path.suffix.lower()
    use_cols = list(columns) if columns is not None else None

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path, usecols=use_cols, engine="openpyxl")
    if suffix == ".csv":
        return pd.read_csv(path, usecols=use_cols)
    if suffix == ".txt":
        rows = path.read_text(encoding="utf-8-sig").splitlines()
        df = pd.DataFrame({"question": [row.strip() for row in rows if row.strip()]})
        if use_cols is not None:
            return df[use_cols]
        return df

    raise ValueError(f"Unsupported file format: {suffix}. Supported formats: .xlsx, .xls, .csv, .txt")


def detect_question_and_label_columns_from_test_data(
    cfg: RunConfig,
    df: pd.DataFrame,
) -> tuple[str, str | None]:
    """
    Resolve the question column (required) and the human label column (optional) from config for test data.

    Args:
        cfg: RunConfig instance
        df: Test DataFrame

    Returns:
        Tuple of (question_col, label_col) where label_col may be None

    Raises:
        KeyError: If configured question column not found in DataFrame
    """
    question_col = cfg.columns.test_question_col
    label_col = cfg.columns.test_category_col

    if question_col not in df.columns:
        raise KeyError(
            f"Configured test_question_col='{question_col}' not found in test dataset columns: {list(df.columns)}"
        )

    # Human label col is optional
    if label_col is None or not str(label_col).strip():
        return question_col, None

    if label_col not in df.columns:
        logger.warning(
            "Configured test_category_col='%s' not found in test dataset. "
            "Proceeding with label_col=None (inference only; evaluation will be skipped).",
            label_col,
        )
        return question_col, None

    return question_col, label_col
