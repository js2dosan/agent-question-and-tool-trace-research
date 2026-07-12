"""Application-level constants."""

# Keys for serialization
ORIGINAL_INDEX_KEY = "original_index"
SOURCE_ROW_NUMBER_KEY = "source_row_number"
QUESTION_KEY = "question"
HUMAN_LABEL_KEY = "human_label"
HUMAN_SUBCATEGORY_KEY = "human_subcategory"
HUMAN_SUBCATEGORY_NORMALIZED_KEY = "human_subcategory_normalized"
LLM_SUBCATEGORY_NORMALIZED_KEY = "LLM_Subcategory_normalized"

# Column names for predictions
PRED_LABEL_COL = "LLM_Label"
PRED_SUBCATEGORY_COL = "LLM_Subcategory"
BATCH_OUTPUT_PAYLOAD = "batch_output_payload"

# Output directory structure
LOG_FILENAME = "run.log"
