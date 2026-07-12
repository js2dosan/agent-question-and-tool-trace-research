"""Version control system (VCS) utilities."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def git_commit() -> str | None:
    """
    Get the current git commit hash.

    Returns:
        The full commit hash (SHA-1) if in a git repository, None otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        logger.debug("Not in a git repository or git command failed")
        return None
    except FileNotFoundError:
        logger.debug("git executable not found")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("git command timed out")
        return None
