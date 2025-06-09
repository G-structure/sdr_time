"""
SDR Experiments Package

A collection of Software Defined Radio experiments and tools.
"""

try:
    from ._version import version as __version__
except ImportError:
    # Version not available when not installed via setuptools-scm
    __version__ = "unknown"

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
from .graphics.kitty import is_kitty_terminal

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