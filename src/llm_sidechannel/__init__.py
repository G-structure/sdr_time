"""
LLM Sidechannel Package

A collection of tools for analyzing Large Language Model internals,
particularly focused on Mixture of Experts (MoE) architectures like Mixtral.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("llm-sidechannel")
except importlib.metadata.PackageNotFoundError:
    # Package is not installed, use development version
    __version__ = "0.1.0-dev"

__author__ = "SDR Team"
__email__ = "team@example.com"

# Import core modules for convenience
from . import core
from . import models
from . import analysis

# Import key classes/functions for easy access
from .core.mixtral_client import MixtralClient
from .core.router_analyzer import RouterAnalyzer
from .models.mixtral_wrapper import MixtralWrapper
from .analysis.expert_usage import ExpertUsageAnalyzer

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "core",
    "models",
    "analysis",
    "MixtralClient",
    "RouterAnalyzer", 
    "MixtralWrapper",
    "ExpertUsageAnalyzer",
] 