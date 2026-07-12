"""Utilities for configuring Opik SDK based on environment variables."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import opik

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpikConfigInfo:
    """Details about resolved Opik configuration."""

    mode: str  # "cloud" | "self_hosted" | "config_file"
    project_name: str | None
    config_path: str
    url_override: str | None
    workspace: str | None


def initialize_opik(project_name: str | None = None, force: bool = False) -> OpikConfigInfo:
    """
    Configure Opik for Cloud or self-hosted deployments based on environment variables.

    Configuration Modes (in order of precedence):
      1. Cloud: OPIK_API_KEY + OPIK_WORKSPACE
      2. Self-hosted: OPIK_URL_OVERRIDE (no API key needed)
      3. Config file: Existing ~/.opik.config (created via `opik configure`)

    Args:
        project_name: Route traces to specific Opik project (sets OPIK_PROJECT_NAME)
        force: Overwrite existing Opik SDK configuration

    Returns:
        OpikConfigInfo with resolved configuration details

    Raises:
        ValueError: If partial configuration is provided
        RuntimeError: If no valid configuration source is found
    """
    # Set project routing (Opik SDK env var)
    if project_name:
        os.environ["OPIK_PROJECT_NAME"] = project_name

    # Read environment variables
    api_key = os.getenv("OPIK_API_KEY")
    workspace = os.getenv("OPIK_WORKSPACE")
    url_override = os.getenv("OPIK_URL_OVERRIDE")
    cfg_path = Path(os.getenv("OPIK_CONFIG_PATH", str(Path.home() / ".opik.config")))

    if force:
        logger.warning("force=True: Overwriting existing Opik configuration")

    # 1) Cloud mode
    if api_key:
        if not workspace:
            raise ValueError("OPIK_API_KEY is set but OPIK_WORKSPACE is missing. Set OPIK_WORKSPACE to use Opik Cloud.")
        try:
            opik.configure(
                api_key=api_key,
                workspace=workspace,
                use_local=False,
                force=force,
                automatic_approvals=True,
            )
        except Exception as e:
            logger.error("Failed to configure Opik (cloud mode): %s", e)
            raise RuntimeError(f"Opik cloud configuration failed: {e}") from e

        logger.info(
            "Opik configured (cloud). project=%s workspace=%s",
            os.getenv("OPIK_PROJECT_NAME"),
            workspace,
        )
        return OpikConfigInfo(
            mode="cloud",
            project_name=os.getenv("OPIK_PROJECT_NAME"),
            config_path=str(cfg_path),
            url_override=None,
            workspace=workspace,
        )

    # 2) Self-hosted mode
    if url_override:
        try:
            opik.configure(
                url=url_override,
                use_local=True,
                force=force,
                automatic_approvals=True,
            )
        except Exception as e:
            logger.error("Failed to configure Opik (self-hosted mode): %s", e)
            raise RuntimeError(f"Opik self-hosted configuration failed: {e}") from e

        logger.info(
            "Opik configured (self_hosted). project=%s url=%s",
            os.getenv("OPIK_PROJECT_NAME"),
            url_override,
        )
        return OpikConfigInfo(
            mode="self_hosted",
            project_name=os.getenv("OPIK_PROJECT_NAME"),
            config_path=str(cfg_path),
            url_override=url_override,
            workspace=None,
        )

    # 3) Config file fallback
    if cfg_path.exists():
        logger.info(
            "Opik using existing config file at %s (project=%s)",
            cfg_path,
            os.getenv("OPIK_PROJECT_NAME"),
        )
        return OpikConfigInfo(
            mode="config_file",
            project_name=os.getenv("OPIK_PROJECT_NAME"),
            config_path=str(cfg_path),
            url_override=None,
            workspace=None,
        )

    # No valid configuration
    raise RuntimeError(
        "Opik is not configured. Set either:\n"
        "  - OPIK_API_KEY and OPIK_WORKSPACE (Opik Cloud), or\n"
        "  - OPIK_URL_OVERRIDE (self-hosted Opik), or\n"
        "  - run `opik configure` to create ~/.opik.config.\n"
        "Optionally set OPIK_PROJECT_NAME to route traces to a project."
    )
