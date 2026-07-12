"""
Infrastructure bootstrap for the CLI experiment run.

Best practice:
- This is the composition root moved out of main.py.
- It performs I/O and constructs concrete implementations:
  config loading, logging setup, Opik init, prompt loading,
  adapter creation, artifact store, data loading, snapshotting.
- It returns an application-layer request object for the use-case.
"""

import argparse
import logging
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from opik import opik_context

from application.constants import LOG_FILENAME
from application.observability import make_run_tag, set_log_context
from application.ports import RunSnapshotRequest
from application.ports.config import RunConfigDTO
from application.prompting import build_examples_text
from application.use_cases.capture_run_snapshot import capture_run_snapshot
from application.use_cases.run_experiment import RunExperimentRequest
from infrastructure.config import load_run_config
from infrastructure.io import detect_question_and_label_columns_from_test_data, ensure_exists, read_table
from infrastructure.io.artifacts.filesystem_store import FilesystemArtifactStore
from infrastructure.io.artifacts.layout import OUTPUT_ROOT_DIRNAME
from infrastructure.observability import configure_logging
from infrastructure.observability.opik_utils import initialize_opik
from infrastructure.prompting import PromptManager, PromptRole
from infrastructure.providers import make_adapter
from infrastructure.utils import set_seed

logger = logging.getLogger(__name__)

SOURCE_ROW_NUMBER_COL = "source_row_number"


def _run_id_part(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


def bootstrap_experiment(args: argparse.Namespace) -> RunExperimentRequest:
    """
    Bootstrap and initialize all dependencies for an experiment run.

    Performs the following initialization steps:
    1. Load environment variables and configuration
    2. Initialize Opik observability
    3. Set up output directories and logging
    4. Load test and ICL demo datasets
    5. Load and resolve prompts
    6. Create provider adapter
    7. Capture run snapshot

    Args:
        args: Command-line arguments containing paths to configuration files
              and logging settings

    Returns:
        RunExperimentRequest with all dependencies wired and ready for execution

    Raises:
        FileNotFoundError: If required configuration or data files are missing
        ValueError: If configuration is invalid or incomplete
    """
    # --- env + config ---
    env_file = Path(args.env)
    ensure_exists(env_file, "environment variables file")
    load_dotenv(env_file, override=True)

    experiment_path = Path(args.experiment)
    ensure_exists(experiment_path, "experiment.yaml")

    cfg = load_run_config(experiment_path)
    set_seed(cfg.stats.seed)

    cfg_port = RunConfigDTO.from_impl(cfg)

    # --- Opik ---
    initialize_opik()

    # --- run id / output dir ---
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bs = "all" if cfg.batch_size is None else str(cfg.batch_size)

    run_id = (
        f"{ts}_"
        f"{_run_id_part(cfg.provider.value if not args.mock else 'mock_provider')}_"
        f"{_run_id_part(cfg.model if not args.mock else 'mock_model')}_"
        f"bs{bs}_"
        f"subcat{int(cfg.label_subcategories)}_"
        f"icl{int(cfg.include_icl_demo)}_"
        f"icl_sub{int(cfg.include_subcategory_in_icl_demo)}"
    )

    run_dir = Path(OUTPUT_ROOT_DIRNAME) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / LOG_FILENAME
    configure_logging(
        log_file=log_path,
        console_level=getattr(logging, args.console_level),
        file_level=getattr(logging, args.file_level),
    )

    set_log_context(
        run_id_full=run_id,
        provider=str(cfg.provider.value),
        model=str(cfg.model),
    )

    logger.info("Starting run: run_id=%s (run_tag=%s)", run_id, make_run_tag(run_id))
    logger.info("Run output directory: %s", run_dir)

    # --- data load ---
    logger.info("Loading test data from %s...", cfg.test_file_path)
    test_data_cols = [
        col
        for col in (
            cfg.columns.test_question_col,
            cfg.columns.test_category_col,
            cfg.columns.test_subcategory_col,
        )
        if col is not None
    ]
    test_df = read_table(cfg.test_file_path, test_data_cols)
    logger.info("Test data loaded: %d rows, %d columns", test_df.shape[0], test_df.shape[1])

    total_test_rows = int(test_df.shape[0])
    if cfg.row_start is not None or cfg.row_end is not None:
        start = cfg.row_start or 0
        end = cfg.row_end if cfg.row_end is not None else total_test_rows
        end = min(end, total_test_rows)
        if start >= total_test_rows:
            raise ValueError(f"row_start={start} is beyond the test dataset row count ({total_test_rows}).")
        test_df = test_df.iloc[start:end].copy()
        test_df.insert(0, SOURCE_ROW_NUMBER_COL, range(start, end))
        test_df = test_df.reset_index(drop=True)
        logger.info(
            "Applied row range: row_start=%d, row_end=%d, selected_rows=%d of %d.",
            start,
            end,
            test_df.shape[0],
            total_test_rows,
        )
    else:
        test_df = test_df.copy()
        test_df.insert(0, SOURCE_ROW_NUMBER_COL, range(total_test_rows))

    question_col, label_col = detect_question_and_label_columns_from_test_data(cfg=cfg, df=test_df)

    # --- ICL demo load (optional) ---
    icl_df = None
    icl_data_cols = [
        col
        for col in (
            cfg.columns.icl_demo_question_col,
            cfg.columns.icl_demo_category_col,
            cfg.columns.icl_demo_subcategory_col,
        )
        if col is not None
    ]
    if cfg.include_icl_demo:
        if cfg.icl_demo_file_path is None:
            raise ValueError("include_icl_demo=True but icl_demo_file_path is None")
        logger.info("Loading ICL demo data from %s...", cfg.icl_demo_file_path)
        icl_df = read_table(cfg.icl_demo_file_path, icl_data_cols)
        logger.info("ICL demo data loaded: %d rows, %d columns", icl_df.shape[0], icl_df.shape[1])
        examples_text = build_examples_text(icl_df, cfg_port)
    else:
        examples_text = ""
        logger.info("ICL demos disabled (include_icl_demo=False).")

    # --- prompts ---
    pm = PromptManager(prompts_root=cfg.prompts_root)
    system_prompt = pm.get_prompt(
        provider=cfg.provider,
        role=PromptRole.SYSTEM,
        cfg=cfg,
        override_path=cfg.system_prompt_path,
    )
    user_prompt = pm.get_prompt(
        provider=cfg.provider,
        role=PromptRole.USER,
        cfg=cfg,
        override_path=cfg.user_prompt_path,
    )

    prompt_metadata = {
        "system_prompt": {
            "name": getattr(system_prompt, "name", None),
            "commit": getattr(system_prompt, "commit", None),
            "metadata": getattr(system_prompt, "metadata", None),
        },
        "user_prompt": {
            "name": getattr(user_prompt, "name", None),
            "commit": getattr(user_prompt, "commit", None),
            "metadata": getattr(user_prompt, "metadata", None),
        },
    }

    execution_context = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "mock": bool(args.mock),
        "effective_provider": "mock_provider" if args.mock else cfg.provider.value,
        "effective_model": "mock_model" if args.mock else cfg.model,
        "cli": {
            "experiment": str(experiment_path),
            "env": str(env_file),
            "console_level": args.console_level,
            "file_level": args.file_level,
        },
        "row_range": {
            "row_start": cfg.row_start,
            "row_end": cfg.row_end,
            "selected_rows": int(test_df.shape[0]),
        },
    }

    # --- artifacts store ---
    artifact_store = FilesystemArtifactStore(outputs_root=Path(OUTPUT_ROOT_DIRNAME))

    # Save Opik trace ID
    trace = opik_context.get_current_trace_data()
    if trace is not None:
        trace_path = artifact_store.save_trace_id(run_id=run_id, trace_id=trace.id, source="opik")
        logger.info("Saved trace id: %s", trace_path)

    # --- snapshot ---
    capture_run_snapshot(
        artifact_store,
        RunSnapshotRequest(
            run_id=run_id,
            cfg_json=cfg.model_dump(mode="json"),
            system_prompt_text=system_prompt.prompt,
            user_prompt_text=user_prompt.prompt,
            icl_examples_text=examples_text,
            prompt_metadata=prompt_metadata,
            test_file=Path(cfg.test_file_path),
            test_rows=int(test_df.shape[0]),
            test_columns_used=test_data_cols,
            icl_demo_file=Path(cfg.icl_demo_file_path)
            if (cfg.include_icl_demo and cfg.icl_demo_file_path is not None)
            else None,
            icl_rows=int(icl_df.shape[0]) if (cfg.include_icl_demo and icl_df is not None) else None,
            icl_columns_used=icl_data_cols if cfg.include_icl_demo else None,
            experiment_yaml=experiment_path,
            execution_context=execution_context,
        ),
    )

    # --- adapter ---
    logger.info("Initializing provider (provider=%s, model=%s)...", cfg.provider.value, cfg.model)
    adapter = make_adapter(cfg, use_mock=bool(args.mock))

    return RunExperimentRequest(
        cfg=cfg_port,
        adapter=adapter,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        examples_text=examples_text,
        test_df=test_df,
        question_col=question_col,
        label_col=label_col,
        run_id=run_id,
        artifact_store=artifact_store,
        run_dir=run_dir,
        log_path=log_path,
    )
