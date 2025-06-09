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

# Import main modules for convenience
from . import utils
from . import soapy_log_handle

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "utils",
    "soapy_log_handle",
] 