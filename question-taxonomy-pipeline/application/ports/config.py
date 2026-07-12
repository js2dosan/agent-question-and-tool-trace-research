"""
Configuration "port" for the application layer.

"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """Minimal provider shape used by application (Enum-like)."""

    value: str


@runtime_checkable
class DataColumnsConfig(Protocol):
    """Column name mapping for ICL demo and test datasets."""

    icl_demo_question_col: str | None
    icl_demo_category_col: str | None
    icl_demo_subcategory_col: str | None

    test_question_col: str
    test_category_col: str | None
    test_subcategory_col: str | None


@runtime_checkable
class StatsConfig(Protocol):
    """
    Configuration for evaluation statistics.

    Mirrors fields used by application + domain evaluation.
    """

    seed: int
    n_boot: int
    alpha: float
    labels_order: list[str]


@runtime_checkable
class Taxonomy(Protocol):
    """Minimal taxonomy interface consumed by application."""

    ordering: dict[str, list[str]]

    def normalize_subcategory(self, raw: object) -> str: ...


@runtime_checkable
class RunConfig(Protocol):
    """
    Runtime configuration (application-facing interface).

    Concrete implementation lives in infrastructure (`infrastructure.config.models.RunConfig`).
    """

    provider: Provider
    model: str
    batch_size: int | None
    row_start: int | None
    row_end: int | None

    # Opik I/O capture
    opik_capture_io: bool

    # Prompt selection flags
    label_subcategories: bool
    include_icl_demo: bool
    include_subcategory_in_icl_demo: bool

    # Columns + Stats + Taxonomy
    columns: DataColumnsConfig
    stats: StatsConfig
    taxonomy: Taxonomy

    # Optional grouping
    group_col: str | None


@dataclass(frozen=True)
class RunConfigDTO(RunConfig):
    provider: Provider
    model: str
    batch_size: int | None
    row_start: int | None
    row_end: int | None

    opik_capture_io: bool

    label_subcategories: bool
    include_icl_demo: bool
    include_subcategory_in_icl_demo: bool

    columns: DataColumnsConfig
    stats: StatsConfig
    taxonomy: Taxonomy

    group_col: str | None

    @classmethod
    def from_impl(cls, cfg: Any) -> "RunConfigDTO":
        # Runtime guard; avoids type checker false-positives at the call site
        if not isinstance(cfg, RunConfig):
            raise TypeError(f"cfg does not satisfy application.ports.config.RunConfig Protocol: {type(cfg)!r}")

        return cls(
            provider=cfg.provider,
            model=cfg.model,
            batch_size=cfg.batch_size,
            row_start=cfg.row_start,
            row_end=cfg.row_end,
            opik_capture_io=cfg.opik_capture_io,
            label_subcategories=cfg.label_subcategories,
            include_icl_demo=cfg.include_icl_demo,
            include_subcategory_in_icl_demo=cfg.include_subcategory_in_icl_demo,
            columns=cfg.columns,
            stats=cfg.stats,
            taxonomy=cfg.taxonomy,
            group_col=cfg.group_col,
        )
