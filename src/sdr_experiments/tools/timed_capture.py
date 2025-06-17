#!/usr/bin/env python3
"""Timed SDR Data Capture Tool

This tool continuously streams SDR data in a background thread with a circular buffer,
then captures data within specific time windows for spectrogram analysis.
"""

import argparse
import threading
import time
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple, List
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

import SoapySDR
from ..core.logging import SoapyLogHandler
from ..core.timing import get_ptp_time_ns, get_realtime_ns
from ..graphics.waterfall import WaterfallDisplay
from kitty_graphics import display_current_plt_figure_kitty_adapted, is_kitty_terminal


@dataclass
class TimestampedSample:
    """A sample with its timestamp."""
    timestamp_ns: int
    samples: np.ndarray


class CircularTimestampBuffer:
    """Thread-safe circular buffer for timestamped SDR samples."""
    
    def __init__(self, max_duration_seconds: float = 10.0):
        self.max_duration_ns = int(max_duration_seconds * 1e9)
        self.buffer = deque()
        self.lock = threading.RLock()
        self._total_samples = 0
    
    def add_samples(self, timestamp_ns: int, samples: np.ndarray):
        """Add samples with timestamp to the buffer."""
        with self.lock:
            # Add new samples
            self.buffer.append(TimestampedSample(timestamp_ns, samples.copy()))
            self._total_samples += len(samples)
            
            # Remove old samples beyond max duration
            cutoff_time = timestamp_ns - self.max_duration_ns
            while self.buffer and self.buffer[0].timestamp_ns < cutoff_time:
                removed = self.buffer.popleft()
                self._total_samples -= len(removed.samples)
    
    def get_samples_in_range(self, start_time_ns: int, end_time_ns: int) -> Tuple[np.ndarray, List[int]]:
        """Extract samples within the specified time range."""
        with self.lock:
            collected_samples = []
            timestamps = []
            
            for entry in self.buffer:
                if start_time_ns <= entry.timestamp_ns <= end_time_ns:
                    collected_samples.append(entry.samples)
                    timestamps.extend([entry.timestamp_ns] * len(entry.samples))
            
            if collected_samples:
                return np.concatenate(collected_samples), timestamps
            else:
                return np.array([], dtype=np.complex64), []
    
    def get_buffer_info(self) -> dict:
        """Get information about current buffer state."""
        with self.lock:
            if not self.buffer:
                return {
                    'entries': 0,
                    'total_samples': 0,
                    'duration_seconds': 0.0,
                    'oldest_timestamp': 0,
                    'newest_timestamp': 0
                }
            
            oldest = self.buffer[0].timestamp_ns
            newest = self.buffer[-1].timestamp_ns
            duration = (newest - oldest) / 1e9 if newest > oldest else 0.0
            
            return {
                'entries': len(self.buffer),
                'total_samples': self._total_samples,
                'duration_seconds': duration,
                'oldest_timestamp': oldest,
                'newest_timestamp': newest
            }


class SDRStreamer:
    """Handles continuous SDR streaming in a background thread."""
    
    def __init__(self, device_args: str, sample_rate: float, frequency: float, 
                 rf_gain: Optional[bool] = None, if_gain: Optional[int] = None, 
                 bb_gain: Optional[int] = None, legacy_gain: Optional[float] = None,
                 buffer_duration: float = 10.0):
        self.device_args = device_args
        self.sample_rate = sample_rate
        self.frequency = frequency
        self.rf_gain = rf_gain  # True/False for HackRF RF amp
        self.if_gain = if_gain  # 0-40 dB in 8 dB steps
        self.bb_gain = bb_gain  # 0-62 dB in 2 dB steps
        self.legacy_gain = legacy_gain  # Overall gain for backward compatibility
        
        self.buffer = CircularTimestampBuffer(buffer_duration)
        self.streaming_thread = None
        self.stop_event = threading.Event()
        self.started_event = threading.Event()
        self.error_event = threading.Event()
        self.error_message = ""
        
        # SDR device (will be created in streaming thread)
        self.sdr = None
        self.rx_stream = None
    
    def start_streaming(self):
        """Start the streaming thread."""
        if self.streaming_thread and self.streaming_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.started_event.clear()
        self.error_event.clear()
        
        self.streaming_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self.streaming_thread.start()
    
    def stop_streaming(self):
        """Stop the streaming thread."""
        self.stop_event.set()
        if self.streaming_thread:
            self.streaming_thread.join(timeout=5.0)
    
    def wait_for_data(self, timeout: float = 10.0) -> bool:
        """Wait for streaming to start and have some data."""
        if not self.started_event.wait(timeout):
            return False
        
        # Wait for some data to accumulate
        start_time = time.time()
        while time.time() - start_time < timeout:
            info = self.buffer.get_buffer_info()
            if info['total_samples'] > 0:
                return True
            time.sleep(0.1)
        
        return False
    
    def _streaming_loop(self):
        """Main streaming loop (runs in background thread)."""
        try:
            # Initialize SDR device
            print(f"Opening SDR device: {self.device_args}")
            self.sdr = SoapySDR.Device(self.device_args)
            
            # Configure device
            self.sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, self.sample_rate)
            self.sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, self.frequency)
            
            # Set individual gain stages for HackRF
            try:
                # List available gain elements
                gain_elements = self.sdr.listGains(SoapySDR.SOAPY_SDR_RX, 0)
                print(f"Available gain elements: {gain_elements}")
                
                # Set RF gain (amp) - 0 or ~11 dB
                if self.rf_gain is not None:
                    if 'AMP' in gain_elements:
                        rf_value = 11.0 if self.rf_gain else 0.0
                        self.sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 'AMP', rf_value)
                        print(f"RF Gain (AMP): {rf_value} dB")
                
                # Set IF gain (lna) - 0 to 40 dB in 8 dB steps
                if self.if_gain is not None:
                    if 'LNA' in gain_elements:
                        # Validate IF gain (must be multiple of 8, 0-40 dB)
                        if_value = max(0, min(40, (self.if_gain // 8) * 8))
                        self.sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 'LNA', if_value)
                        print(f"IF Gain (LNA): {if_value} dB")
                
                # Set baseband gain (vga) - 0 to 62 dB in 2 dB steps  
                if self.bb_gain is not None:
                    if 'VGA' in gain_elements:
                        # Validate BB gain (must be multiple of 2, 0-62 dB)
                        bb_value = max(0, min(62, (self.bb_gain // 2) * 2))
                        self.sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 'VGA', bb_value)
                        print(f"Baseband Gain (VGA): {bb_value} dB")
                        
                # If no individual gains specified, check for legacy gain or print current settings
                if all(g is None for g in [self.rf_gain, self.if_gain, self.bb_gain]):
                    if self.legacy_gain is not None:
                        # Use legacy overall gain setting
                        self.sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, self.legacy_gain)
                        print(f"Legacy overall gain: {self.legacy_gain} dB")
                    else:
                        # Print current gain settings
                        for gain_name in gain_elements:
                            current_gain = self.sdr.getGain(SoapySDR.SOAPY_SDR_RX, 0, gain_name)
                            print(f"Current {gain_name} gain: {current_gain} dB")
                        
            except Exception as gain_error:
                print(f"Warning: Could not set individual gains: {gain_error}")
                if self.legacy_gain is not None:
                    print(f"Falling back to legacy overall gain: {self.legacy_gain} dB")
                    self.sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, self.legacy_gain)
                else:
                    print("Using device default gain settings")
            
            actual_rate = self.sdr.getSampleRate(SoapySDR.SOAPY_SDR_RX, 0)
            print(f"Actual sample rate: {actual_rate/1e6:.3f} MSPS")
            
            # Setup stream
            self.rx_stream = self.sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CF32, [0])
            print(f"Stream MTU: {self.sdr.getStreamMTU(self.rx_stream)} samples")
            
            # Activate stream
            self.sdr.activateStream(self.rx_stream)
            print("SDR streaming started")
            
            # Signal that streaming has started
            self.started_event.set()
            
            # Streaming loop
            buffer_size = 8192  # Samples per read
            samples_buffer = np.empty(buffer_size, np.complex64)
            
            while not self.stop_event.is_set():
                # Calculate timeout based on buffer size and sample rate
                timeout_us = int(2 * (buffer_size / actual_rate) * 1e6)
                
                # Get timestamp before reading
                timestamp_ns = get_realtime_ns()
                if timestamp_ns == 0:  # Fallback if high-precision timing fails
                    timestamp_ns = time.time_ns()
                
                # Read samples
                ret = self.sdr.readStream(self.rx_stream, [samples_buffer], buffer_size, 
                                        timeoutUs=timeout_us)
                
                if ret.ret > 0:
                    # Add samples to buffer with timestamp
                    self.buffer.add_samples(timestamp_ns, samples_buffer[:ret.ret])
                elif ret.ret == SoapySDR.SOAPY_SDR_TIMEOUT:
                    continue  # Just continue on timeout
                elif ret.ret == SoapySDR.SOAPY_SDR_OVERFLOW:
                    print("Warning: SDR overflow detected")
                    continue
                else:
                    print(f"Stream error: {SoapySDR.errToStr(ret.ret)}")
                    break
            
        except Exception as e:
            self.error_message = str(e)
            self.error_event.set()
            print(f"Streaming error: {e}")
        finally:
            # Cleanup
            if self.sdr and self.rx_stream:
                try:
                    self.sdr.deactivateStream(self.rx_stream)
                    self.sdr.closeStream(self.rx_stream)
                except:
                    pass
            print("SDR streaming stopped")


def generate_spectrogram(samples: np.ndarray, sample_rate: float, 
                        title: str = "Spectrogram") -> None:
    """Generate and display spectrogram using Kitty graphics."""
    if len(samples) == 0:
        print("No samples to generate spectrogram")
        return
    
    if not is_kitty_terminal():
        print("Kitty terminal not detected - spectrogram display disabled")
        return
    
    # Calculate spectrogram parameters
    nperseg = min(1024, len(samples) // 4)  # FFT size
    if nperseg < 64:
        nperseg = 64
    
    # Generate spectrogram
    plt.figure(figsize=(12, 8))
    plt.specgram(samples, NFFT=nperseg, Fs=sample_rate, cmap='viridis')
    plt.colorbar(label='Power (dB)')
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    plt.title(f'{title}\nSamples: {len(samples)}, Duration: {len(samples)/sample_rate:.3f}s')
    
    # Display using Kitty protocol
    display_current_plt_figure_kitty_adapted(
        plt,
        print_error_func=None,
        image_id=1,
        suppress_errors=True
    )
    
    plt.close()


def main():
    """Main function for timed capture tool."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--args", type=str, default="driver=hackrf",
                       help="SoapySDR device arguments")
    parser.add_argument("--rate", type=float, default=20e6,
                       help="Sample rate in Hz")
    parser.add_argument("--freq", type=float, default=100e6,
                       help="Center frequency in Hz")
    # Individual HackRF gain controls
    parser.add_argument("--rf-gain", action='store_true', default=None,
                       help="Enable RF amplifier (~11 dB) - HackRF only")
    parser.add_argument("--no-rf-gain", action='store_true', 
                       help="Disable RF amplifier (0 dB) - HackRF only")
    parser.add_argument("--if-gain", type=int, default=None, metavar='DB',
                       help="IF/LNA gain in dB (0-40 in 8dB steps) - HackRF only")
    parser.add_argument("--bb-gain", type=int, default=None, metavar='DB', 
                       help="Baseband/VGA gain in dB (0-62 in 2dB steps) - HackRF only")
    
    # Backward compatibility
    parser.add_argument("--gain", type=float, default=None,
                       help="Overall RX gain in dB (legacy - use individual controls for HackRF)")
    parser.add_argument("--buffer-duration", type=float, default=10.0,
                       help="Buffer duration in seconds")
    parser.add_argument("--task-duration", type=float, default=1.0,
                       help="Task duration in seconds")
    parser.add_argument("--debug", action='store_true',
                       help="Enable debug output")
    
    args = parser.parse_args()
    
    # Process RF gain arguments
    rf_gain_setting = None
    if args.rf_gain:
        rf_gain_setting = True
    elif args.no_rf_gain:
        rf_gain_setting = False
    
    # Configure logging
    if args.debug:
        SoapySDR.setLogLevel(SoapySDR.SOAPY_SDR_DEBUG)
    else:
        SoapySDR.setLogLevel(SoapySDR.SOAPY_SDR_INFO)
    
    print("=== Timed SDR Capture Tool ===")
    print(f"Device: {args.args}")
    print(f"Sample Rate: {args.rate/1e6:.3f} MSPS")
    print(f"Frequency: {args.freq/1e6:.3f} MHz")
    
    # Display gain settings
    if rf_gain_setting is not None:
        print(f"RF Gain: {'ON (~11 dB)' if rf_gain_setting else 'OFF (0 dB)'}")
    else:
        print("RF Gain: Auto")
        
    if args.if_gain is not None:
        # Validate and round IF gain
        validated_if = max(0, min(40, (args.if_gain // 8) * 8))
        print(f"IF Gain: {validated_if} dB")
        if validated_if != args.if_gain:
            print(f"  (Note: IF gain rounded from {args.if_gain} to {validated_if} dB)")
    else:
        print("IF Gain: Auto")
        
    if args.bb_gain is not None:
        # Validate and round BB gain  
        validated_bb = max(0, min(62, (args.bb_gain // 2) * 2))
        print(f"Baseband Gain: {validated_bb} dB")
        if validated_bb != args.bb_gain:
            print(f"  (Note: BB gain rounded from {args.bb_gain} to {validated_bb} dB)")
    else:
        print("Baseband Gain: Auto")
        
    if args.gain is not None:
        print(f"Legacy Overall Gain: {args.gain} dB")
        
    print(f"Buffer Duration: {args.buffer_duration} seconds")
    print(f"Task Duration: {args.task_duration} seconds")
    print()
    
    # Create and start streamer
    streamer = SDRStreamer(
        device_args=args.args,
        sample_rate=args.rate,
        frequency=args.freq,
        rf_gain=rf_gain_setting,
        if_gain=args.if_gain,
        bb_gain=args.bb_gain,
        legacy_gain=args.gain,
        buffer_duration=args.buffer_duration
    )
    
    try:
        print("Starting SDR streaming...")
        streamer.start_streaming()
        
        # Wait for streaming to start and accumulate some data
        print("Waiting for streaming to stabilize...")
        if not streamer.wait_for_data(timeout=15.0):
            print("Error: Failed to start streaming or no data received")
            return 1
        
        # Check for streaming errors
        if streamer.error_event.is_set():
            print(f"Streaming error: {streamer.error_message}")
            return 1
        
        # Show buffer status
        info = streamer.buffer.get_buffer_info()
        print(f"Buffer ready: {info['entries']} entries, {info['total_samples']} samples, "
              f"{info['duration_seconds']:.2f}s duration")
        print()
        
        # Main task execution
        print("=== Starting Timed Task ===")
        
        # Record start time
        start_time_ns = get_realtime_ns()
        if start_time_ns == 0:
            start_time_ns = time.time_ns()
        
        print(f"Task start time: {start_time_ns} ns")
        
        # Perform the task (sleep for specified duration)
        print(f"Executing task for {args.task_duration} seconds...")
        time.sleep(args.task_duration)
        
        # Record stop time
        stop_time_ns = get_realtime_ns()
        if stop_time_ns == 0:
            stop_time_ns = time.time_ns()
        
        print(f"Task stop time: {stop_time_ns} ns")
        print(f"Actual task duration: {(stop_time_ns - start_time_ns) / 1e9:.3f} seconds")
        print()
        
        # Extract data from the time window
        print("Extracting data from time window...")
        samples, timestamps = streamer.buffer.get_samples_in_range(start_time_ns, stop_time_ns)
        
        if len(samples) == 0:
            print("No samples found in the specified time range!")
            return 1
        
        print(f"Extracted {len(samples)} samples from time window")
        print(f"Data duration: {len(samples) / args.rate:.3f} seconds")
        
        # Generate and display spectrogram
        print("Generating spectrogram...")
        generate_spectrogram(
            samples, 
            args.rate, 
            f"Timed Capture ({args.freq/1e6:.1f} MHz)"
        )
        
        print("=== Task Complete ===")
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        # Stop streaming
        print("Stopping SDR streaming...")
        streamer.stop_streaming()


if __name__ == '__main__':
    exit(main()) 