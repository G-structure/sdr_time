#!/usr/bin/env python3
"""High-precision timing test tool.

This tool tests various system clocks and demonstrates low-latency access
to PTP/TAI time sources for SDR synchronization.
"""

import argparse
import time
import sys
from ..core.timing import (
    HighPrecisionClock, 
    get_ptp_time_ns, 
    get_realtime_ns, 
    get_monotonic_ns,
    compare_clocks,
    benchmark_clock_access,
    CLOCK_TAI,
    CLOCK_REALTIME, 
    CLOCK_MONOTONIC,
    CLOCK_MONOTONIC_RAW
)


def test_clock_availability():
    """Test which clocks are available on this system."""
    print("=== Clock Availability Test ===")
    
    clock = HighPrecisionClock()
    availability = clock.check_clock_availability()
    
    for clock_name, available in availability.items():
        status = "✓ Available" if available else "✗ Not available"
        print(f"{clock_name:<20}: {status}")
    
    return availability


def test_clock_values():
    """Show current values from different clocks."""
    print("\n=== Current Clock Values ===")
    
    clock_data = compare_clocks()
    
    print(f"TAI time:        {clock_data['tai_ns']} ns")
    print(f"Realtime:        {clock_data['realtime_ns']} ns")
    print(f"Monotonic:       {clock_data['monotonic_ns']} ns")
    print(f"Python time():   {clock_data['python_time_ns']} ns")
    print(f"Python monotonic: {clock_data['python_monotonic_ns']} ns")
    
    if clock_data['tai_available']:
        print(f"TAI-UTC offset:  {clock_data.get('tai_utc_diff_seconds', 'N/A')} seconds")
    else:
        print("TAI time not available - PTP may not be synchronized")


def test_clock_precision():
    """Test the precision and latency of clock access."""
    print("\n=== Clock Precision Test ===")
    
    clock = HighPrecisionClock()
    
    # Test different clocks if available
    clocks_to_test = [
        ('CLOCK_TAI', CLOCK_TAI),
        ('CLOCK_REALTIME', CLOCK_REALTIME),
        ('CLOCK_MONOTONIC', CLOCK_MONOTONIC),
        ('CLOCK_MONOTONIC_RAW', CLOCK_MONOTONIC_RAW)
    ]
    
    for clock_name, clock_id in clocks_to_test:
        if clock.get_time(clock_id) is not None:
            print(f"\nTesting {clock_name}:")
            latency_stats = clock.measure_clock_latency(clock_id, iterations=1000)
            
            print(f"  Min latency:    {latency_stats['min_ns']} ns")
            print(f"  Median latency: {latency_stats['median_ns']} ns")
            print(f"  Mean latency:   {latency_stats['mean_ns']:.1f} ns")
            print(f"  95th percentile: {latency_stats['p95_ns']} ns")
            print(f"  99th percentile: {latency_stats['p99_ns']} ns")
            print(f"  Max latency:    {latency_stats['max_ns']} ns")
        else:
            print(f"\n{clock_name}: Not available")


def benchmark_performance():
    """Benchmark different timing methods."""
    print("\n=== Performance Benchmark ===")
    
    benchmark_results = benchmark_clock_access(iterations=10000)
    
    print(f"Iterations: {benchmark_results['iterations']}")
    print(f"\nHigh-precision TAI:  {benchmark_results['hp_tai_per_call_ns']:.1f} ns/call")
    print(f"Python time_ns():    {benchmark_results['python_time_per_call_ns']:.1f} ns/call")
    print(f"Python monotonic():  {benchmark_results['python_monotonic_per_call_ns']:.1f} ns/call")
    
    # Calculate relative performance
    baseline = benchmark_results['python_time_per_call_ns']
    hp_speedup = baseline / benchmark_results['hp_tai_per_call_ns']
    print(f"\nHigh-precision TAI is {hp_speedup:.1f}x {'faster' if hp_speedup > 1 else 'slower'} than Python time_ns()")


def continuous_monitor(interval_ms: int = 100):
    """Continuously monitor clock values."""
    print(f"\n=== Continuous Monitor (every {interval_ms}ms) ===")
    print("Press Ctrl+C to stop")
    print("Time (s) | TAI (ns) | Realtime (ns) | Monotonic (ns) | TAI-Real (ns)")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        while True:
            current_time = time.time() - start_time
            
            tai = get_ptp_time_ns()
            realtime = get_realtime_ns()
            monotonic = get_monotonic_ns()
            
            tai_real_diff = tai - realtime if tai > 0 else 0
            
            print(f"{current_time:8.1f} | {tai:13d} | {realtime:13d} | {monotonic:14d} | {tai_real_diff:10d}")
            
            time.sleep(interval_ms / 1000.0)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--availability', action='store_true',
                       help='Test which clocks are available')
    parser.add_argument('--values', action='store_true', 
                       help='Show current clock values')
    parser.add_argument('--precision', action='store_true',
                       help='Test clock precision and latency')
    parser.add_argument('--benchmark', action='store_true',
                       help='Benchmark timing performance')
    parser.add_argument('--monitor', action='store_true',
                       help='Continuously monitor clock values')
    parser.add_argument('--monitor-interval', type=int, default=100,
                       help='Monitor interval in milliseconds (default: 100)')
    parser.add_argument('--all', action='store_true',
                       help='Run all tests')
    
    args = parser.parse_args()
    
    if not any([args.availability, args.values, args.precision, 
                args.benchmark, args.monitor, args.all]):
        # Default behavior - run basic tests
        args.availability = True
        args.values = True
    
    try:
        if args.all or args.availability:
            availability = test_clock_availability()
            
        if args.all or args.values:
            test_clock_values()
            
        if args.all or args.precision:
            test_clock_precision()
            
        if args.all or args.benchmark:
            benchmark_performance()
            
        if args.monitor:
            continuous_monitor(args.monitor_interval)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 