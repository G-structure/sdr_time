"""Waterfall visualization for SDR data."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from typing import Optional

from kitty_graphics import display_current_plt_figure_kitty_adapted, is_kitty_terminal
from ..core.signal import compute_psd_db


class WaterfallDisplay:
    """Real-time waterfall display for spectrum data."""
    
    def __init__(
        self,
        fft_size: int = 1024,
        history_length: int = 60,
        min_db: float = -100,
        max_db: float = -30,
        image_id: int = 1
    ):
        """
        Initialize waterfall display.
        
        Args:
            fft_size: FFT size for spectrum computation
            history_length: Number of spectrum lines to keep in history
            min_db: Minimum dB value for display scaling
            max_db: Maximum dB value for display scaling
            image_id: Unique image ID for terminal display
        """
        self.fft_size = fft_size
        self.history_length = history_length
        self.min_db = min_db
        self.max_db = max_db
        self.image_id = image_id
        
        # Initialize waterfall data with empty spectra
        self.waterfall_data = deque(maxlen=history_length)
        for _ in range(history_length):
            self.waterfall_data.append(np.full(fft_size, min_db))
        
        self.is_kitty = is_kitty_terminal()
        
        # Configure matplotlib for better performance
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['figure.dpi'] = 75
        
    def add_samples(self, samples: np.ndarray) -> None:
        """
        Add new samples to the waterfall display.
        
        Args:
            samples: Complex samples from SDR
        """
        # Compute PSD and add to waterfall
        psd_db = compute_psd_db(samples, self.fft_size, self.min_db)
        self.waterfall_data.append(psd_db)
        
    def update_display(self) -> None:
        """Update the waterfall display if running in Kitty terminal."""
        if not self.is_kitty:
            return
            
        # Convert deque to numpy array for plotting
        plot_data = np.array(list(self.waterfall_data))
        
        # Clear and plot
        plt.clf()
        plt.imshow(
            plot_data,
            aspect='auto',
            cmap='viridis',
            interpolation='nearest',
            origin='lower',
            vmin=self.min_db,
            vmax=self.max_db
        )
        plt.axis('off')
        
        # Display using Kitty protocol
        display_current_plt_figure_kitty_adapted(
            plt,
            print_error_func=None,
            image_id=self.image_id,
            suppress_errors=True
        )
        
    def get_current_spectrum(self) -> np.ndarray:
        """
        Get the most recent spectrum.
        
        Returns:
            Most recent spectrum in dB
        """
        if len(self.waterfall_data) > 0:
            return self.waterfall_data[-1].copy()
        else:
            return np.full(self.fft_size, self.min_db)
            
    def clear(self) -> None:
        """Clear the waterfall history."""
        self.waterfall_data.clear()
        for _ in range(self.history_length):
            self.waterfall_data.append(np.full(self.fft_size, self.min_db)) 