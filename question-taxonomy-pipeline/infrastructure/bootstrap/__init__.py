"""
Bootstrap functions for experiment initialization.

Handles dependency injection and construction of all required components
for running experiments (config loading, logging setup, adapter creation).
"""

from infrastructure.bootstrap.experiment import bootstrap_experiment

__all__ = ["bootstrap_experiment"]
