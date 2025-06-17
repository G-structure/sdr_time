import argparse
import sys
import SoapySDR
import numpy as np
import time

from ..graphics.waterfall import WaterfallDisplay
from kitty_graphics import is_kitty_terminal
from ..core.logging import SoapyLogHandler

def run_waterfall(device_args_str, sample_rate_hz, frequency_hz, gain_db):
    """Run the waterfall display."""
    
    # Initialize waterfall display
    waterfall = WaterfallDisplay(
        fft_size=1024,
        history_length=60,
        min_db=-100,
        max_db=-30,
        image_id=1
    )
    
    NUM_SAMPLES_PER_BUFFER = waterfall.fft_size * 4 
    if NUM_SAMPLES_PER_BUFFER < waterfall.fft_size:
        NUM_SAMPLES_PER_BUFFER = waterfall.fft_size

    sdr = None
    rx_stream = None
    try:
        sdr = SoapySDR.Device(device_args_str) 

        sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, sample_rate_hz)
        sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, frequency_hz)
        actual_rate = sdr.getSampleRate(SoapySDR.SOAPY_SDR_RX, 0)
        sample_rate_hz = actual_rate 

        sdr.setGainMode(SoapySDR.SOAPY_SDR_RX, 0, False)
        sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, gain_db)

        # Setup stream with error recovery for "stream already opened"
        try:
            rx_stream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS8, [0])
        except RuntimeError as e:
            if "stream already opened" in str(e).lower():
                print("Warning: Stream already opened on remote device. This may indicate:")
                print("  - Another application is using the SDR")
                print("  - Previous session was not properly closed")
                print("  - Remote SoapyRemote server needs restart")
                print("Please check the remote device and restart SoapyRemote if needed.")
                raise RuntimeError(f"Cannot open stream: {e}") from e
            else:
                raise
        
        sdr.activateStream(rx_stream)

        buff = np.empty(NUM_SAMPLES_PER_BUFFER, np.complex64)
        
        print(f"Waterfall display {'enabled' if waterfall.is_kitty else 'disabled (not in Kitty terminal)'}")
        
        buffer_count = 0

        while True: 
            timeout_val_us = int(5 * (NUM_SAMPLES_PER_BUFFER / sample_rate_hz) * 1e6) 
            ret = sdr.readStream(rx_stream, [buff], NUM_SAMPLES_PER_BUFFER, timeoutUs=timeout_val_us)
            
            samples_read = ret.ret

            if samples_read > 0:
                # Use waterfall class to handle samples
                samples_to_process = buff[:samples_read] if samples_read >= waterfall.fft_size else buff[:samples_read]
                waterfall.add_samples(samples_to_process)
                waterfall.update_display() 
            
            elif samples_read == SoapySDR.SOAPY_SDR_TIMEOUT:
                pass
            elif samples_read == SoapySDR.SOAPY_SDR_OVERFLOW:
                pass
            else: 
                break 
            
            buffer_count += 1

    except KeyboardInterrupt:
        print("\nWaterfall display stopped by user")
    except RuntimeError as e: 
        print(f"SDR Runtime error: {e}")
    except AttributeError as e: 
        print(f"Attribute error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if sdr and rx_stream is not None:
            sdr.deactivateStream(rx_stream)
            sdr.closeStream(rx_stream)
        if sdr:
            pass

def main():
    parser = argparse.ArgumentParser(
        description="Display waterfall in Kitty from SoapySDR device.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--args", type=str, help="SoapySDR device arguments", default="driver=hackrf")
    parser.add_argument("--rate", type=float, help="Sample rate in Hz", default=10e6)
    parser.add_argument("--freq", type=float, help="Center frequency in Hz", default=100e6)
    parser.add_argument("--gain", type=float, help="Overall RX gain in dB (e.g., 0-40, try higher if signal is weak)", default=25.0)
    parser.add_argument("--debug", action='store_true', help="Enable SoapySDR debug messages (still suppressed from terminal output)")

    options = parser.parse_args()

    SoapySDR.setLogLevel(SoapySDR.SOAPY_SDR_FATAL)

    run_waterfall(options.args, options.rate, options.freq, options.gain)

if __name__ == '__main__':
    main() 

