"""
Graphics and visualization utilities.

This module contains tools for displaying SDR data using various output methods.
"""

from .kitty import (
    serialize_gr_command,
    write_chunked, 
    display_current_plt_figure_kitty_adapted,
    is_kitty_terminal
)
from .waterfall import WaterfallDisplay

__all__ = [
    "serialize_gr_command",
    "write_chunked",
    "display_current_plt_figure_kitty_adapted", 
    "is_kitty_terminal",
    "WaterfallDisplay",
] 