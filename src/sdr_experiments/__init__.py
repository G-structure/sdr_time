"""
SDR Experiments Package

A collection of Software Defined Radio experiments and tools.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("sdr-experiments")
except importlib.metadata.PackageNotFoundError:
    # Package is not installed, use development version
    __version__ = "0.1.0-dev"

__author__ = "SDR Team"
__email__ = "team@example.com"

# Import core modules for convenience
from . import core
from . import graphics
from . import utils

# Import key classes/functions for easy access
from .core.logging import SoapyLogHandler
from .core.signal import generate_cf32_pulse, normalize_samples, compute_psd_db
from .core.device import setup_sdr_device, get_device_info
from .graphics.waterfall import WaterfallDisplay
from kitty_graphics import is_kitty_terminal

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "core",
    "graphics", 
    "utils",
    "SoapyLogHandler",
    "generate_cf32_pulse",
    "normalize_samples",
    "compute_psd_db",
    "setup_sdr_device",
    "get_device_info",
    "WaterfallDisplay",
    "is_kitty_terminal",
] 