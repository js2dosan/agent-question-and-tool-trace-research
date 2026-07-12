"""
Use-case: run a full experiment (inference -> serialize -> evaluate -> artifacts).

Best practice:
- Accept already-constructed dependencies (adapter, prompts, artifact_store).
- Do NOT load files, parse CLI args, or construct infrastructure objects here.
  Those belong in the composition root (main.py).
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from application.constants import PRED_LABEL_COL, PRED_SUBCATEGORY_COL
from application.evaluation import log_evaluation_summary, run_evaluation_if_labels_available
from application.inference import run_inference
from application.ports.artifact_store import ArtifactStore
from application.ports.config import RunConfig
from application.ports.prompts import PromptObj
from application.ports.provider import ProviderAdapter
from application.serialize import build_prediction_records
from domain.evaluation import compute_subcategory_alignment_table

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunExperimentRequest:
    cfg: RunConfig
    adapter: ProviderAdapter
    system_prompt: PromptObj
    user_prompt: PromptObj
    examples_text: str

    test_df: pd.DataFrame
    question_col: str
    label_col: str | None

    run_id: str
    artifact_store: ArtifactStore

    # paths/logging context (optional but useful for callers)
    run_dir: Path
    log_path: Path


@dataclass(frozen=True)
class RunExperimentResult:
    predictions_path: Path
    metrics_path: Path
    subcategory_table_path: Path | None
    metrics: dict[str, Any]
    usage_stats: dict[str, int | float]
    test_df_out: pd.DataFrame
    cm_df: pd.DataFrame | None
    sub_cm_df: pd.DataFrame | None


def run_experiment(req: RunExperimentRequest) -> RunExperimentResult:
    """
    Run inference and evaluation for a single run_id, saving artifacts via ArtifactStore.

    Args:
        req: RunExperimentRequest with all dependencies and parameters.

    Returns:
        RunExperimentResult with paths and computed outputs.
    """
    cfg = req.cfg

    # ---- Inference ----
    pred_map, subcat_map, usage_stats = run_inference(
        cfg=cfg,
        adapter=req.adapter,
        system_prompt=req.system_prompt,
        user_prompt=req.user_prompt,
        examples_text=req.examples_text,
        test_df=req.test_df,
        question_col=req.question_col,
        run_id=req.run_id,
        artifact_store=req.artifact_store,
    )

    # ---- Attach predictions + save predictions JSON ----
    test_df_out, records = build_prediction_records(
        cfg=cfg,
        test_df=req.test_df,
        question_col=req.question_col,
        label_col=req.label_col,
        pred_map=pred_map,
        subcat_map=subcat_map if cfg.label_subcategories else None,
    )
    predictions_path = req.artifact_store.save_predictions_json(req.run_id, records)
    logger.info("Saved predictions JSON: %s", predictions_path)

    # ---- Evaluation (only if human labels exist) ----
    metrics, cm_df, sub_cm_df = run_evaluation_if_labels_available(
        cfg=cfg,
        test_df_out=test_df_out,
        label_col=req.label_col,
    )

    # Merge usage stats into metrics and save
    metrics.update(usage_stats)
    metrics_path = req.artifact_store.save_metrics_json(req.run_id, metrics)
    logger.info("Saved metrics to %s", metrics_path)

    # ---- Subcategory alignment table (optional) ----
    subcategory_table_path: Path | None = None

    human_subcat_col = (
        cfg.columns.test_subcategory_col
        if (cfg.columns.test_subcategory_col and cfg.columns.test_subcategory_col in test_df_out.columns)
        else None
    )

    if (
        req.label_col is not None
        and human_subcat_col is not None
        and PRED_SUBCATEGORY_COL in test_df_out.columns
        and getattr(cfg.taxonomy, "ordering", None) is not None
    ):
        table_df = compute_subcategory_alignment_table(
            df=test_df_out,
            human_top_label_col=req.label_col,
            human_subcat_col=human_subcat_col,
            llm_top_label_col=PRED_LABEL_COL,
            llm_subcat_col=PRED_SUBCATEGORY_COL,
            labels_order=cfg.stats.labels_order,
            taxonomy_ordering=cfg.taxonomy.ordering,
            normalize_subcategory=cfg.taxonomy.normalize_subcategory,
        )
        subcategory_table_path = req.artifact_store.save_subcategory_alignment_csv(
            req.run_id,
            table_df.to_csv(index=False),
        )
        logger.info("Saved subcategory alignment table to %s", subcategory_table_path)

    # ---- Human-readable summary ----
    log_evaluation_summary(
        metrics=metrics,
        cm_df=cm_df,
        sub_cm_df=sub_cm_df,
        label_col=req.label_col,
        usage_stats=usage_stats,
        predictions_path=predictions_path,
        metrics_path=metrics_path,
    )

    logger.info("Finished experiment run: %s", req.run_id)

    return RunExperimentResult(
        predictions_path=predictions_path,
        metrics_path=metrics_path,
        subcategory_table_path=subcategory_table_path,
        metrics=metrics,
        usage_stats=usage_stats,
        test_df_out=test_df_out,
        cm_df=cm_df,
        sub_cm_df=sub_cm_df,
    )
