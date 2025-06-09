"""Utility functions for SDR experiments."""

import base64
import sys
from io import BytesIO
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np


def serialize_gr_command(**cmd) -> bytes:
    """
    Serialize a graphics command for the kitty terminal.
    This follows the kitty graphics protocol.
    """
    payload = cmd.pop('payload', None)
    cmd_str = ','.join(f'{k}={v}' for k, v in cmd.items())
    ans = []
    w = ans.append
    w(b'\033_G')  # Start graphics command
    w(cmd_str.encode('ascii'))
    if payload:
        w(b';')
        w(payload)
    w(b'\033\\')  # End graphics command
    return b''.join(ans)


def write_chunked(**cmd) -> None:
    """
    Write image data in chunks using the kitty graphics protocol.
    This allows sending larger images without hitting terminal buffer limits.
    """
    data = base64.b64encode(cmd.pop('data'))
    chunk_size = 4096
    
    # Preserve all command keys for the first chunk
    first_chunk_cmd_dict = {k: v for k, v in cmd.items() if k != 'data'}

    idx = 0
    while data:
        chunk, data = data[:chunk_size], data[chunk_size:]
        
        current_payload = chunk
        more_data_follows = 1 if data else 0
        
        if idx == 0:  # First chunk
            command_to_send = first_chunk_cmd_dict.copy()
            command_to_send['payload'] = current_payload
            command_to_send['m'] = more_data_follows
        else:  # Subsequent chunks - only 'm' and 'payload'
            command_to_send = {'m': more_data_follows, 'payload': current_payload}

        sys.stdout.buffer.write(serialize_gr_command(**command_to_send))
        sys.stdout.buffer.flush()
        idx += 1


def display_current_plt_figure_kitty_adapted(
    plt_instance: plt,
    print_error_func: callable,
    image_id: int,
    dpi: int = 75
) -> None:
    """
    Saves the current matplotlib figure to a buffer and displays it using Kitty graphics protocol.
    """
    try:
        if not plt_instance:
            return

        buf = BytesIO()
        plt_instance.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0.01)
        buf.seek(0)
        png_data = buf.getvalue()
        
        if not png_data:
            return
            
        write_chunked(a='T', f=100, i=image_id, q=1, data=png_data)
    
    except Exception as e:
        if print_error_func:
            print_error_func(f"Error displaying figure: {e}")


def generate_cf32_pulse(num_samps: int, width: float = 5, scale_factor: float = 0.3) -> np.ndarray:
    """
    Create a sinc pulse for SDR transmission.
    
    Args:
        num_samps: Number of samples in the pulse
        width: Width parameter for the sinc function
        scale_factor: Scaling factor for the pulse amplitude
        
    Returns:
        Complex64 numpy array containing the pulse
    """
    rel_time = np.linspace(-width, width, num_samps)
    pulse = np.sinc(rel_time).astype(np.complex64)
    return pulse * scale_factor


def normalize_samples(samps: np.ndarray) -> np.ndarray:
    """
    Normalize samples by removing DC, taking magnitude, and normalizing to peak.
    
    Args:
        samps: Input samples (complex or real)
        
    Returns:
        Normalized magnitude samples
    """
    samps = samps - np.mean(samps)  # Remove DC
    samps = np.absolute(samps)  # Magnitude
    max_val = np.max(samps)
    if max_val > 0:
        samps = samps / max_val  # Normalize amplitude to peak
    return samps


def compute_psd_db(samples: np.ndarray, fft_size: Optional[int] = None, min_val_db: float = -100) -> np.ndarray:
    """
    Compute power spectral density in dB.
    
    Args:
        samples: Input samples
        fft_size: FFT size (defaults to length of samples)
        min_val_db: Minimum value in dB for clipping
        
    Returns:
        PSD in dB, fftshifted
    """
    if fft_size is None:
        fft_size = len(samples)
    
    if len(samples) >= fft_size:
        samples_for_fft = samples[:fft_size]
    else:
        samples_for_fft = np.pad(samples, (0, fft_size - len(samples)), 'constant', constant_values=(0,))
    
    spectrum = np.fft.fft(samples_for_fft, n=fft_size)
    psd_line = np.abs(spectrum)**2
    psd_line_shifted = np.fft.fftshift(psd_line)
    psd_line_db = 10 * np.log10(psd_line_shifted + 1e-12)
    psd_line_db = np.clip(psd_line_db, min_val_db, None)
    
    return psd_line_db 