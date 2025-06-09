import argparse
import sys
import SoapySDR
import numpy as np
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import deque
import base64
import os
from io import BytesIO

# Global flag to store if PTP mode was logged
ptp_mode_logged = False
monotonic_fallback_logged = False
tai_failed_logged = False

# Kitty graphics helper functions
def serialize_gr_command(**cmd):
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

def write_chunked(**cmd):
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
        
        if idx == 0: # First chunk
            command_to_send = first_chunk_cmd_dict.copy()
            command_to_send['payload'] = current_payload
            command_to_send['m'] = more_data_follows
        else: # Subsequent chunks - only 'm' and 'payload'
            command_to_send = {'m': more_data_follows, 'payload': current_payload}
            # For subsequent chunks, ensure other control keys from the initial command are not resent
            # if they were accidentally included. The dict `command_to_send` here is fresh.

        sys.stdout.buffer.write(serialize_gr_command(**command_to_send))
        sys.stdout.buffer.flush()
        idx += 1

def display_current_plt_figure_kitty_adapted(plt_instance, print_error_func, image_id, dpi: int = 75):
    """Saves the current matplotlib figure to a buffer and displays it using Kitty graphics protocol."""
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
        pass


def soapy_log_handle(level, message):
    global ptp_mode_logged, monotonic_fallback_logged, tai_failed_logged
    try:
        level_str = SoapySDR.SoapySDR_logLevelToString(level)
    except AttributeError:
        level_str = str(level)
    if "Using PTP clock /dev/ptp0" in message:
        ptp_mode_logged = True
    if "Falling back to monotonic clock" in message:
        monotonic_fallback_logged = True
    if "clock_gettime(CLOCK_TAI) failed" in message:
        tai_failed_logged = True

def verify_clock_source(device_args_str, sample_rate_hz, frequency_hz, gain_db):
    global ptp_mode_logged, monotonic_fallback_logged, tai_failed_logged

    IMAGE_ID_WATERFALL = 1

    # Waterfall parameters
    fft_size = 1024
    waterfall_height = 60 
    waterfall_data = deque(maxlen=waterfall_height)
    min_val_db = -100

    for _ in range(waterfall_height):
        waterfall_data.append(np.full(fft_size, min_val_db))

    NUM_SAMPLES_PER_BUFFER = fft_size * 4 
    if NUM_SAMPLES_PER_BUFFER < fft_size:
        NUM_SAMPLES_PER_BUFFER = fft_size

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

        rx_stream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS8, [0])
        
        sdr.activateStream(rx_stream)

        buff = np.empty(NUM_SAMPLES_PER_BUFFER, np.complex64)
        
        is_kitty = os.environ.get('TERM') == 'xterm-kitty'
        if not is_kitty:
            pass


        buffer_count = 0

        while True: 
            timeout_val_us = int(5 * (NUM_SAMPLES_PER_BUFFER / sample_rate_hz) * 1e6) 
            ret = sdr.readStream(rx_stream, [buff], NUM_SAMPLES_PER_BUFFER, timeoutUs=timeout_val_us)
            
            samples_read = ret.ret

            if samples_read > 0:
                if samples_read >= fft_size:
                    samples_for_fft = buff[:fft_size]
                else: 
                    samples_for_fft = np.pad(buff[:samples_read], (0, fft_size - samples_read), 'constant', constant_values=(0,))
                
                spectrum = np.fft.fft(samples_for_fft, n=fft_size)
                psd_line = np.abs(spectrum)**2
                psd_line_shifted = np.fft.fftshift(psd_line)
                psd_line_db = 10 * np.log10(psd_line_shifted + 1e-12) 
                psd_line_db = np.clip(psd_line_db, min_val_db, None) 

                waterfall_data.append(psd_line_db)

                if is_kitty:
                    plot_data_np = np.array(list(waterfall_data))
                    
                    plt.clf()
                    fixed_vmin = -100.0
                    fixed_vmax = -30.0
                    
                    plt.imshow(plot_data_np, aspect='auto', cmap='viridis', interpolation='nearest', origin='lower', vmin=fixed_vmin, vmax=fixed_vmax)
                    plt.axis('off')
                    display_current_plt_figure_kitty_adapted(plt, lambda msg: print(msg, file=sys.stderr), image_id=IMAGE_ID_WATERFALL, dpi=75) 
            
            elif samples_read == SoapySDR.SOAPY_SDR_TIMEOUT:
                pass
            elif samples_read == SoapySDR.SOAPY_SDR_OVERFLOW:
                pass
            else: 
                break 
            
            buffer_count += 1

    except KeyboardInterrupt:
        pass
    except SoapySDR.RuntimeException as e: 
        pass
    except AttributeError as e: 
        pass
    except Exception as e:
        pass
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

    verify_clock_source(options.args, options.rate, options.freq, options.gain) # Corrected function name

if __name__ == '__main__':
    main() 

