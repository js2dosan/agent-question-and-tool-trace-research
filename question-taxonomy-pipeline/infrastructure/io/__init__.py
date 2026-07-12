"""I/O utilities: filesystem operations and dataset loading."""

from infrastructure.io.datasets import detect_question_and_label_columns_from_test_data, read_table
from infrastructure.io.fs import ensure_exists, read_text, write_json

__all__ = ["read_table", "ensure_exists", "read_text", "write_json", "detect_question_and_label_columns_from_test_data"]
