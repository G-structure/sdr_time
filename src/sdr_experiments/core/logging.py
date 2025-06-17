"""SoapySDR log handling utilities."""

try:
    import SoapySDR
    SOAPY_AVAILABLE = True
except ImportError:
    SOAPY_AVAILABLE = False
    SoapySDR = None


class SoapyLogHandler:
    """Handler for SoapySDR log messages with PTP clock detection."""
    
    def __init__(self):
        self.ptp_mode_logged = False
        self.monotonic_fallback_logged = False
        self.tai_failed_logged = False
        
        if not SOAPY_AVAILABLE:
            import warnings
            warnings.warn("SoapySDR not available, log handler will have limited functionality")
    
    def log_handler(self, level, message):
        """Handle SoapySDR log messages."""
        try:
            if SOAPY_AVAILABLE and SoapySDR:
                level_str = SoapySDR.SoapySDR_logLevelToString(level)
            else:
                level_str = str(level)
        except AttributeError:
            level_str = str(level)
        
        if "Using PTP clock /dev/ptp0" in message:
            self.ptp_mode_logged = True
        if "Falling back to monotonic clock" in message:
            self.monotonic_fallback_logged = True
        if "clock_gettime(CLOCK_TAI) failed" in message:
            self.tai_failed_logged = True


# Global handler instance for backward compatibility
_global_handler = SoapyLogHandler()

# Expose the global handler functions for backward compatibility
def soapy_log_handle(level, message):
    """Global log handler function for backward compatibility."""
    return _global_handler.log_handler(level, message)


def reset_log_flags():
    """Reset all log flags."""
    global _global_handler
    _global_handler.ptp_mode_logged = False
    _global_handler.monotonic_fallback_logged = False
    _global_handler.tai_failed_logged = False


def get_log_status():
    """Get the current status of log flags."""
    return {
        'ptp_mode_logged': _global_handler.ptp_mode_logged,
        'monotonic_fallback_logged': _global_handler.monotonic_fallback_logged,
        'tai_failed_logged': _global_handler.tai_failed_logged,
    } 