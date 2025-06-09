import SoapySDR
import numpy as np
import time
import argparse # Added argparse
from ..core.logging import SoapyLogHandler
from ..core.timing import get_ptp_time_ns, get_realtime_ns, get_monotonic_ns, compare_clocks

def verify_clock_source(device_args_str, sample_rate_hz, frequency_hz):
    # Create log handler instance
    log_handler = SoapyLogHandler()
    
    def soapy_log_callback(level, message):
        log_handler.log_handler(level, message)
        # Also print the message for visibility
        try:
            level_str = SoapySDR.SoapySDR_logLevelToString(level)
        except AttributeError:
            level_str = str(level)
        print(f"SoapyLOG: [{level_str}] {message}")

    # SoapySDR.registerLogHandler(soapy_log_callback) # Registering from main to catch early logs
    # SoapySDR.setLogLevel(SoapySDR.SOAPY_SDR_DEBUG)

    NUM_SAMPLES_PER_BUFFER = 1024 * 16 # Number of samples per readStream call
    N_BUFFERS_TO_READ = 10

    sdr = None
    try:
        print(f"Attempting to open device with args: '{device_args_str}'")
        sdr = SoapySDR.Device(device_args_str) # Use parsed args string
        print("Device opened.")

        sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, sample_rate_hz)
        sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, frequency_hz)
        print(f"Actual Rx Rate {sdr.getSampleRate(SoapySDR.SOAPY_SDR_RX, 0)/1e6} Msps")
        # sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 30) # Example gain, can be added as arg if needed

        # Setup stream
        rx_stream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS8, [0])
        print(f"RX Stream MTU: {sdr.getStreamMTU(rx_stream)} samples")
        
        sdr.activateStream(rx_stream)
        print("RX Stream activated.")

        # Buffers for data
        buff = np.empty(NUM_SAMPLES_PER_BUFFER, np.complex64)
        
        print("\n--- Timestamp Verification ---")
        print("Reading buffers and comparing timestamps...")
        print("SoapyTimestamp (ns) | Python time_ns() (Epoch) | Python monotonic_ns() | Delta Soapy (ms) | Ret Flags")
        print("---------------------|--------------------------|-----------------------|------------------|-----------")

        last_soapy_ts = None

        for i in range(N_BUFFERS_TO_READ):
            python_epoch_before = time.time_ns()
            python_mono_before = time.monotonic_ns()
            
            timeout_val_us = int(2 * (NUM_SAMPLES_PER_BUFFER / sample_rate_hz) * 1e6)
            ret = sdr.readStream(rx_stream, [buff], NUM_SAMPLES_PER_BUFFER, timeoutUs=timeout_val_us)
            
            python_epoch_after = time.time_ns()
            python_mono_after = time.monotonic_ns()

            avg_python_epoch = (python_epoch_before + python_epoch_after) // 2
            avg_python_mono = (python_mono_before + python_mono_after) // 2

            soapy_ts_ns = 0
            ret_flags_str = "N/A"

            if ret.ret > 0:
                soapy_ts_ns = ret.timeNs
                ret_flags_str = f"0x{ret.flags:X}"
                if ret.flags & SoapySDR.SOAPY_SDR_HAS_TIME == 0:
                    ret_flags_str += " (NO_TIME!)"
                if ret.flags & SoapySDR.SOAPY_SDR_END_ABRUPT:
                     ret_flags_str += " (OVERFLOW/ABRUPT)"
                
                delta_soapy_str = "N/A"
                if last_soapy_ts is not None:
                    delta_soapy_ms = (soapy_ts_ns - last_soapy_ts) / 1e6
                    delta_soapy_str = f"{delta_soapy_ms:.3f}"
                last_soapy_ts = soapy_ts_ns

                print(f"{soapy_ts_ns:<20} | {avg_python_epoch:<24} | {avg_python_mono:<21} | {delta_soapy_str:<16} | {ret_flags_str}")
            elif ret.ret == SoapySDR.SOAPY_SDR_TIMEOUT:
                print(f"Timeout occurred for buffer {i}. SoapyTS: N/A, Python Epoch: {avg_python_epoch}, Python Mono: {avg_python_mono}")
            else:
                print(f"Error reading stream for buffer {i}: {SoapySDR.errToStr(ret.ret)} ({ret.ret})")
                break
            
            time.sleep(0.05) # Small delay between reads

    except RuntimeError as e: # SoapySDR errors are typically RuntimeError
        print(f"SoapySDR Runtime Error: {e}")
    except AttributeError as e: # Catch attribute errors for SoapySDR specific types if not found
        print(f"SoapySDR (or other) AttributeError: {e}")
        print("This might indicate an issue with SoapySDR Python bindings or version compatibility.")
    except Exception as e:
        print(f"General Error: {e}")
    finally:
        if sdr and 'rx_stream' in locals() and rx_stream is not None:
            print("Deactivating stream...")
            sdr.deactivateStream(rx_stream)
            print("Closing stream...")
            sdr.closeStream(rx_stream)
        if sdr:
            print("Device closed.")

        print("\n--- Log Summary ---")
        
        # Get log status from handler
        ptp_mode_logged = log_handler.ptp_mode_logged
        monotonic_fallback_logged = log_handler.monotonic_fallback_logged
        tai_failed_logged = log_handler.tai_failed_logged
        
        if ptp_mode_logged and not monotonic_fallback_logged and not tai_failed_logged:
            print("SUCCESS: Driver logged intention to use PTP clock, and no fallback messages for PTP were observed.")
            print("         Timestamps should be large (epoch-like) if PTP (via CLOCK_TAI) is working correctly.")
        elif monotonic_fallback_logged:
            print("INFO: Driver logged fallback to MONOTONIC clock because /dev/ptp0 could not be opened.")
            print("      Timestamps will be based on a monotonic clock relative to device/stream start (or setHardwareTime).")
        elif ptp_mode_logged and tai_failed_logged:
            print("WARNING: Driver intended to use PTP, but CLOCK_TAI failed. Fell back to CLOCK_MONOTONIC_RAW.")
            print("         Timestamps will be based on CLOCK_MONOTONIC_RAW.")
            print("         Check if your system supports CLOCK_TAI and if ptp4l is configuring it.")
        elif ptp_mode_logged: # PTP logged, but no TAI failure, no explicit fallback
             print("INFO: Driver logged intention to use PTP clock. CLOCK_TAI was attempted.")
             print("      If CLOCK_TAI is working and synchronized by PTP, timestamps should be epoch-like.")
             print("      If CLOCK_TAI is not available/working, timestamps might be from CLOCK_MONOTONIC_RAW (if that fallback in getHardwareTime was hit).")
        else:
            print("INFO: No specific PTP or explicit monotonic fallback messages logged. Default behavior might be monotonic, or logs were not detailed enough.")
            print("      Inspect the magnitude of SoapyTimestamps compared to Python's epoch and monotonic time.")

def main():
    parser = argparse.ArgumentParser(
        description="Verify PTP clock usage with SoapySDR device (local or remote).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--args", type=str, help="SoapySDR device arguments (e.g., 'driver=hackrf' or 'remote=tcp://server:port')", default="driver=hackrf")
    parser.add_argument("--rate", type=float, help="Sample rate in Hz", default=10e6)
    parser.add_argument("--freq", type=float, help="Center frequency in Hz", default=100e6)
    # Add other arguments from MeasureDelay.py if needed for consistency, e.g., gain, antenna, etc.
    # For now, only essential ones for this script's core function are included.
    parser.add_argument("--debug", action='store_true', help="Enable SoapySDR debug messages")

    options = parser.parse_args()

    # Create global log handler for early messages
    global_handler = SoapyLogHandler()
    
    def global_log_callback(level, message):
        global_handler.log_handler(level, message)
        try:
            level_str = SoapySDR.SoapySDR_logLevelToString(level)
        except AttributeError:
            level_str = str(level)
        print(f"SoapyLOG: [{level_str}] {message}")

    SoapySDR.registerLogHandler(global_log_callback) # Register log handler early
    if options.debug:
        SoapySDR.setLogLevel(SoapySDR.SOAPY_SDR_DEBUG)
    else:
        SoapySDR.setLogLevel(SoapySDR.SOAPY_SDR_INFO) # Default to INFO if not debug

    verify_clock_source(options.args, options.rate, options.freq)

if __name__ == '__main__':
    main() 
