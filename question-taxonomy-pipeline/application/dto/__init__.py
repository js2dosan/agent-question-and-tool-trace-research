"""
Data Transfer Objects (DTOs) for structured LLM outputs.

Contains Pydantic models that define the schema for LLM responses,
including question labels and subcategories from the Eris taxonomy.
"""

from .question_labeling import BatchLabels, QuestionLabel, Subcategory

__all__ = ["BatchLabels", "QuestionLabel", "Subcategory"]
