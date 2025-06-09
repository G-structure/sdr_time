"""
Kitty Graphics Package

Terminal graphics utilities specifically for the Kitty terminal emulator.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("kitty-graphics")
except importlib.metadata.PackageNotFoundError:
    # Package is not installed, use development version
    __version__ = "0.1.0-dev"

__author__ = "SDR Team"
__email__ = "team@example.com"

# Import core functionality
from .protocol import (
    serialize_gr_command,
    write_chunked,
    display_current_plt_figure_kitty_adapted,
    is_kitty_terminal
)
from .test import test_kitty_graphics

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "serialize_gr_command",
    "write_chunked", 
    "display_current_plt_figure_kitty_adapted",
    "is_kitty_terminal",
    "test_kitty_graphics",
] 