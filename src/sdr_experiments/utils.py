"""General utility functions for SDR experiments."""

import os
import subprocess
from typing import Optional, List, Dict, Any


def get_system_info() -> Dict[str, Any]:
    """
    Get system information relevant to SDR operations.
    
    Returns:
        Dictionary containing system information
    """
    info = {}
    
    # Operating system
    info['os'] = os.name
    info['platform'] = os.uname() if hasattr(os, 'uname') else 'unknown'
    
    # Terminal information
    info['term'] = os.environ.get('TERM', 'unknown')
    info['term_program'] = os.environ.get('TERM_PROGRAM', 'unknown')
    
    # Python environment
    info['python_executable'] = os.sys.executable
    info['python_version'] = os.sys.version
    
    return info


def check_dependencies() -> Dict[str, bool]:
    """
    Check if required dependencies are available.
    
    Returns:
        Dictionary mapping dependency names to availability
    """
    deps = {}
    
    # Check Python modules
    try:
        import SoapySDR
        deps['soapysdr'] = True
    except ImportError:
        deps['soapysdr'] = False
    
    try:
        import numpy
        deps['numpy'] = True
    except ImportError:
        deps['numpy'] = False
        
    try:
        import matplotlib
        deps['matplotlib'] = True
    except ImportError:
        deps['matplotlib'] = False
    
    # Check system commands
    try:
        subprocess.run(['SoapySDRUtil', '--help'], 
                      capture_output=True, check=True)
        deps['soapysdr_util'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        deps['soapysdr_util'] = False
    
    return deps


def format_frequency(freq_hz: float) -> str:
    """
    Format frequency in human-readable units.
    
    Args:
        freq_hz: Frequency in Hz
        
    Returns:
        Formatted frequency string
    """
    if freq_hz >= 1e9:
        return f"{freq_hz/1e9:.3f} GHz"
    elif freq_hz >= 1e6:
        return f"{freq_hz/1e6:.3f} MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz/1e3:.3f} kHz"
    else:
        return f"{freq_hz:.1f} Hz"


def format_sample_rate(rate_hz: float) -> str:
    """
    Format sample rate in human-readable units.
    
    Args:
        rate_hz: Sample rate in Hz
        
    Returns:
        Formatted sample rate string
    """
    if rate_hz >= 1e6:
        return f"{rate_hz/1e6:.3f} MSPS"
    elif rate_hz >= 1e3:
        return f"{rate_hz/1e3:.3f} kSPS"
    else:
        return f"{rate_hz:.1f} SPS"


def format_time_duration(duration_ns: int) -> str:
    """
    Format time duration in human-readable units.
    
    Args:
        duration_ns: Duration in nanoseconds
        
    Returns:
        Formatted duration string
    """
    if duration_ns >= 1e9:
        return f"{duration_ns/1e9:.3f} s"
    elif duration_ns >= 1e6:
        return f"{duration_ns/1e6:.3f} ms"
    elif duration_ns >= 1e3:
        return f"{duration_ns/1e3:.3f} μs"
    else:
        return f"{duration_ns:.1f} ns" 