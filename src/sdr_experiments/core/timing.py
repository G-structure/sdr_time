"""High-performance timing utilities for SDR applications.

This module provides low-latency access to various system clocks,
particularly useful for PTP-synchronized SDR operations.
"""

import ctypes
import ctypes.util
import time
from typing import Optional, Tuple, NamedTuple
import threading

# Clock constants for Linux
CLOCK_REALTIME = 0
CLOCK_MONOTONIC = 1
CLOCK_PROCESS_CPUTIME_ID = 2
CLOCK_THREAD_CPUTIME_ID = 3
CLOCK_MONOTONIC_RAW = 4
CLOCK_REALTIME_COARSE = 5
CLOCK_MONOTONIC_COARSE = 6
CLOCK_BOOTTIME = 7
CLOCK_REALTIME_ALARM = 8
CLOCK_BOOTTIME_ALARM = 9
CLOCK_SGI_CYCLE = 10
CLOCK_TAI = 11


class TimeStamp(NamedTuple):
    """Timestamp with nanosecond precision."""
    seconds: int
    nanoseconds: int
    
    @property
    def total_ns(self) -> int:
        """Total time in nanoseconds."""
        return self.seconds * 1_000_000_000 + self.nanoseconds
    
    @property
    def total_us(self) -> float:
        """Total time in microseconds."""
        return self.total_ns / 1_000.0
    
    @property
    def total_ms(self) -> float:
        """Total time in milliseconds."""
        return self.total_ns / 1_000_000.0
    
    @property
    def total_seconds(self) -> float:
        """Total time in seconds."""
        return self.seconds + self.nanoseconds / 1_000_000_000.0


class HighPrecisionClock:
    """High-precision clock access with minimal overhead."""
    
    def __init__(self):
        self._libc = None
        self._clock_gettime = None
        self._timespec_class = None
        self._init_libc()
    
    def _init_libc(self):
        """Initialize libc access for clock functions."""
        try:
            # Load libc
            libc_name = ctypes.util.find_library('c')
            if not libc_name:
                raise RuntimeError("Could not find libc library")
            
            self._libc = ctypes.CDLL(libc_name)
            
            # Define timespec structure
            class timespec(ctypes.Structure):
                _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
            
            self._timespec_class = timespec
            
            # Setup clock_gettime function
            self._libc.clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
            self._libc.clock_gettime.restype = ctypes.c_int
            
            # Test that it works
            ts = timespec()
            result = self._libc.clock_gettime(CLOCK_REALTIME, ctypes.byref(ts))
            if result != 0:
                raise RuntimeError("clock_gettime test failed")
                
        except Exception as e:
            raise RuntimeError(f"Failed to initialize high-precision clock: {e}")
    
    def get_time(self, clock_id: int = CLOCK_TAI) -> Optional[TimeStamp]:
        """Get time from specified clock with minimal latency.
        
        Args:
            clock_id: Clock identifier (e.g., CLOCK_TAI, CLOCK_REALTIME, CLOCK_MONOTONIC)
            
        Returns:
            TimeStamp object or None if clock is not available
        """
        try:
            ts = self._timespec_class()
            result = self._libc.clock_gettime(clock_id, ctypes.byref(ts))
            if result == 0:
                return TimeStamp(ts.tv_sec, ts.tv_nsec)
            else:
                return None
        except Exception:
            return None
    
    def get_time_ns(self, clock_id: int = CLOCK_TAI) -> int:
        """Get time in nanoseconds with minimal latency.
        
        Args:
            clock_id: Clock identifier
            
        Returns:
            Time in nanoseconds since epoch (or 0 if clock not available)
        """
        timestamp = self.get_time(clock_id)
        return timestamp.total_ns if timestamp else 0
    
    def get_multiple_clocks(self) -> Tuple[int, int, int]:
        """Get multiple clock sources in rapid succession.
        
        Returns:
            Tuple of (tai_ns, realtime_ns, monotonic_ns)
            Zero values indicate clock not available.
        """
        tai = self.get_time_ns(CLOCK_TAI)
        realtime = self.get_time_ns(CLOCK_REALTIME)
        monotonic = self.get_time_ns(CLOCK_MONOTONIC)
        return tai, realtime, monotonic
    
    def check_clock_availability(self) -> dict:
        """Check which clocks are available on this system.
        
        Returns:
            Dictionary mapping clock names to availability status
        """
        clocks_to_test = {
            'CLOCK_REALTIME': CLOCK_REALTIME,
            'CLOCK_MONOTONIC': CLOCK_MONOTONIC,
            'CLOCK_MONOTONIC_RAW': CLOCK_MONOTONIC_RAW,
            'CLOCK_TAI': CLOCK_TAI,
            'CLOCK_BOOTTIME': CLOCK_BOOTTIME,
        }
        
        availability = {}
        for name, clock_id in clocks_to_test.items():
            timestamp = self.get_time(clock_id)
            availability[name] = timestamp is not None
        
        return availability
    
    def measure_clock_latency(self, clock_id: int = CLOCK_TAI, iterations: int = 1000) -> dict:
        """Measure the latency of clock access.
        
        Args:
            clock_id: Clock to test
            iterations: Number of measurements to make
            
        Returns:
            Dictionary with latency statistics in nanoseconds
        """
        latencies = []
        
        # Warm up
        for _ in range(10):
            self.get_time_ns(clock_id)
        
        # Measure latencies
        for _ in range(iterations):
            start = time.perf_counter_ns()
            self.get_time_ns(clock_id)
            end = time.perf_counter_ns()
            latencies.append(end - start)
        
        latencies.sort()
        return {
            'min_ns': min(latencies),
            'max_ns': max(latencies),
            'median_ns': latencies[len(latencies) // 2],
            'mean_ns': sum(latencies) / len(latencies),
            'p95_ns': latencies[int(len(latencies) * 0.95)],
            'p99_ns': latencies[int(len(latencies) * 0.99)]
        }


class SynchronizedTimeBase:
    """Thread-safe time base for synchronized operations."""
    
    def __init__(self, preferred_clock: int = CLOCK_TAI):
        self.clock = HighPrecisionClock()
        self.preferred_clock = preferred_clock
        self._offset_ns = 0
        self._lock = threading.RLock()
        
        # Check if preferred clock is available
        if self.clock.get_time(preferred_clock) is None:
            # Fallback to CLOCK_REALTIME
            self.preferred_clock = CLOCK_REALTIME
    
    def set_reference_time(self, reference_time_ns: int):
        """Set a reference time offset for synchronized operations.
        
        Args:
            reference_time_ns: Reference time in nanoseconds
        """
        with self._lock:
            current_time = self.clock.get_time_ns(self.preferred_clock)
            if current_time > 0:
                self._offset_ns = reference_time_ns - current_time
    
    def get_synchronized_time_ns(self) -> int:
        """Get synchronized time in nanoseconds.
        
        Returns:
            Time adjusted by reference offset
        """
        with self._lock:
            current_time = self.clock.get_time_ns(self.preferred_clock)
            return current_time + self._offset_ns if current_time > 0 else 0
    
    def schedule_time_ns(self, delay_ns: int) -> int:
        """Calculate a future time for scheduling.
        
        Args:
            delay_ns: Delay in nanoseconds from now
            
        Returns:
            Future time in nanoseconds
        """
        return self.get_synchronized_time_ns() + delay_ns
    
    def time_until_ns(self, target_time_ns: int) -> int:
        """Calculate time remaining until target time.
        
        Args:
            target_time_ns: Target time in nanoseconds
            
        Returns:
            Nanoseconds until target time (negative if target has passed)
        """
        return target_time_ns - self.get_synchronized_time_ns()


# Global instance for convenience
_global_clock = None
_global_timebase = None


def get_global_clock() -> HighPrecisionClock:
    """Get the global high-precision clock instance."""
    global _global_clock
    if _global_clock is None:
        _global_clock = HighPrecisionClock()
    return _global_clock


def get_global_timebase() -> SynchronizedTimeBase:
    """Get the global synchronized time base."""
    global _global_timebase
    if _global_timebase is None:
        _global_timebase = SynchronizedTimeBase()
    return _global_timebase


def get_ptp_time_ns() -> int:
    """Get PTP/TAI time in nanoseconds with minimal latency.
    
    Returns:
        TAI time in nanoseconds, or 0 if not available
    """
    return get_global_clock().get_time_ns(CLOCK_TAI)


def get_realtime_ns() -> int:
    """Get system realtime in nanoseconds with minimal latency.
    
    Returns:
        Realtime in nanoseconds
    """
    return get_global_clock().get_time_ns(CLOCK_REALTIME)


def get_monotonic_ns() -> int:
    """Get monotonic time in nanoseconds with minimal latency.
    
    Returns:
        Monotonic time in nanoseconds
    """
    return get_global_clock().get_time_ns(CLOCK_MONOTONIC)


def compare_clocks() -> dict:
    """Compare different clock sources.
    
    Returns:
        Dictionary with current values from different clocks
    """
    clock = get_global_clock()
    tai, realtime, monotonic = clock.get_multiple_clocks()
    
    result = {
        'tai_ns': tai,
        'realtime_ns': realtime,
        'monotonic_ns': monotonic,
        'tai_available': tai > 0,
        'python_time_ns': time.time_ns(),
        'python_monotonic_ns': time.monotonic_ns()
    }
    
    if tai > 0 and realtime > 0:
        # TAI is ahead of UTC by leap seconds
        result['tai_utc_diff_seconds'] = (tai - realtime) / 1e9
    
    return result


def benchmark_clock_access(iterations: int = 10000) -> dict:
    """Benchmark different clock access methods.
    
    Args:
        iterations: Number of iterations to run
        
    Returns:
        Performance comparison results
    """
    clock = get_global_clock()
    
    # Test our high-performance method
    start = time.perf_counter()
    for _ in range(iterations):
        clock.get_time_ns(CLOCK_TAI)
    hp_time = time.perf_counter() - start
    
    # Test Python's time.time_ns()
    start = time.perf_counter()
    for _ in range(iterations):
        time.time_ns()
    python_time = time.perf_counter() - start
    
    # Test Python's time.monotonic_ns()
    start = time.perf_counter()
    for _ in range(iterations):
        time.monotonic_ns()
    monotonic_time = time.perf_counter() - start
    
    return {
        'iterations': iterations,
        'high_precision_tai_sec': hp_time,
        'python_time_ns_sec': python_time,
        'python_monotonic_ns_sec': monotonic_time,
        'hp_tai_per_call_ns': (hp_time / iterations) * 1e9,
        'python_time_per_call_ns': (python_time / iterations) * 1e9,
        'python_monotonic_per_call_ns': (monotonic_time / iterations) * 1e9
    } 