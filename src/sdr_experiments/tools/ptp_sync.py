#!/usr/bin/env python3
"""PTP Clock Synchronization Tool

This tool helps set up and verify PTP (Precision Time Protocol) synchronization
between multiple machines for synchronized SDR operations.
"""

import subprocess
import time
import argparse
import sys
import os
from typing import Dict, List, Optional, Tuple


class PTPManager:
    """Manages PTP synchronization setup and monitoring."""
    
    def find_ptp_devices(self) -> List[str]:
        """Find available PTP devices on the system."""
        devices = []
        for i in range(10):  # Check /dev/ptp0 through /dev/ptp9
            device = f"/dev/ptp{i}"
            if os.path.exists(device):
                devices.append(device)
        return devices
    
    def check_ptp_support(self) -> Dict[str, bool]:
        """Check if system supports PTP and related tools."""
        checks = {
            'ptp4l_installed': self._command_exists('ptp4l'),
            'phc2sys_installed': self._command_exists('phc2sys'),
            'ptp_devices_present': len(self.find_ptp_devices()) > 0,
            'root_privileges': os.geteuid() == 0,
            'clock_tai_support': self._check_clock_tai()
        }
        return checks
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run([command, '--help'], capture_output=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_clock_tai(self) -> bool:
        """Check if CLOCK_TAI is available."""
        try:
            import ctypes
            import ctypes.util
            
            # Load libc
            libc_name = ctypes.util.find_library('c')
            if not libc_name:
                return False
            
            libc = ctypes.CDLL(libc_name)
            
            # Define clock_gettime
            class timespec(ctypes.Structure):
                _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
            
            libc.clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
            libc.clock_gettime.restype = ctypes.c_int
            
            # Try CLOCK_TAI (value is usually 11)
            CLOCK_TAI = 11
            ts = timespec()
            result = libc.clock_gettime(CLOCK_TAI, ctypes.byref(ts))
            return result == 0
        except Exception:
            return False
    
    def get_network_interfaces(self) -> List[str]:
        """Get list of network interfaces that might support PTP."""
        interfaces = []
        try:
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ': ' in line and 'state UP' in line:
                        # Extract interface name
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            iface = parts[1].split('@')[0]  # Remove VLAN info
                            if not iface.startswith('lo'):  # Skip loopback
                                interfaces.append(iface)
        except Exception as e:
            print(f"Error getting network interfaces: {e}")
        return interfaces
    
    def start_ptp_master(self, interface: str) -> bool:
        """Start PTP master on specified interface."""
        if not self.check_ptp_support()['root_privileges']:
            print("Error: Root privileges required to start PTP master")
            return False
        
        try:
            # Kill any existing ptp4l processes
            subprocess.run(['pkill', '-f', 'ptp4l'], capture_output=True)
            time.sleep(1)
            
            # Start ptp4l as master with simple config
            cmd = ['ptp4l', '-i', interface, '-m', '-s', '-l', '6']
            print(f"Starting PTP master: {' '.join(cmd)}")
            
            # Start in background
            process = subprocess.Popen(cmd)
            time.sleep(3)  # Give it time to start
            
            if process.poll() is None:  # Still running
                print(f"PTP master started successfully on {interface}")
                return True
            else:
                print("PTP master failed to start")
                return False
                
        except Exception as e:
            print(f"Error starting PTP master: {e}")
            return False
    
    def start_ptp_slave(self, interface: str) -> bool:
        """Start PTP slave on specified interface."""
        if not self.check_ptp_support()['root_privileges']:
            print("Error: Root privileges required to start PTP slave")
            return False
        
        try:
            # Kill any existing ptp4l processes
            subprocess.run(['pkill', '-f', 'ptp4l'], capture_output=True)
            time.sleep(1)
            
            # Start ptp4l as slave
            cmd = ['ptp4l', '-i', interface, '-s', '-l', '6']
            print(f"Starting PTP slave: {' '.join(cmd)}")
            
            # Start in background
            process = subprocess.Popen(cmd)
            time.sleep(3)
            
            if process.poll() is None:  # Still running
                print(f"PTP slave started successfully on {interface}")
                # Also start phc2sys to sync system clock to PTP
                self._start_phc2sys()
                return True
            else:
                print("PTP slave failed to start")
                return False
                
        except Exception as e:
            print(f"Error starting PTP slave: {e}")
            return False
    
    def _start_phc2sys(self):
        """Start phc2sys to synchronize system clock to PTP hardware clock."""
        try:
            ptp_devices = self.find_ptp_devices()
            if ptp_devices:
                ptp_device = ptp_devices[0]  # Use first available PTP device
                cmd = ['phc2sys', '-s', ptp_device, '-c', 'CLOCK_REALTIME', '-w', '-l', '6']
                print(f"Starting phc2sys: {' '.join(cmd)}")
                subprocess.Popen(cmd)
            else:
                print("Warning: No PTP devices found for phc2sys")
        except Exception as e:
            print(f"Warning: Could not start phc2sys: {e}")
    
    def get_ptp_status(self) -> Dict:
        """Get current PTP synchronization status."""
        status = {
            'ptp4l_running': self._is_process_running('ptp4l'),
            'phc2sys_running': self._is_process_running('phc2sys'),
            'sync_offset': None,
            'master_identified': False
        }
        
        # Try to get sync status from pmc (PTP Management Client)
        try:
            result = subprocess.run(['pmc', '-u', '-b', '0', 'GET CURRENT_DATA_SET'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse pmc output for offset information
                for line in result.stdout.split('\n'):
                    if 'offsetFromMaster' in line:
                        # Extract offset value
                        import re
                        match = re.search(r'offsetFromMaster\s+(-?\d+)', line)
                        if match:
                            status['sync_offset'] = int(match.group(1))
                    elif 'grandmasterIdentity' in line:
                        status['master_identified'] = True
        except Exception:
            pass
        
        return status
    
    def _is_process_running(self, process_name: str) -> bool:
        """Check if a process is running."""
        try:
            result = subprocess.run(['pgrep', '-f', process_name], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def stop_ptp_services(self):
        """Stop all PTP-related services."""
        services = ['ptp4l', 'phc2sys']
        for service in services:
            try:
                subprocess.run(['pkill', '-f', service], capture_output=True)
                print(f"Stopped {service}")
            except Exception as e:
                print(f"Error stopping {service}: {e}")


def get_high_precision_time() -> Tuple[int, int, int]:
    """Get high-precision time from different clock sources.
    
    Returns:
        Tuple of (tai_time_ns, realtime_ns, monotonic_ns)
        TAI time will be 0 if not available.
    """
    import ctypes
    import ctypes.util
    
    # Load libc
    libc_name = ctypes.util.find_library('c')
    if not libc_name:
        raise RuntimeError("Could not find libc")
    
    libc = ctypes.CDLL(libc_name)
    
    # Define structures
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
    
    libc.clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
    libc.clock_gettime.restype = ctypes.c_int
    
    # Clock constants (Linux)
    CLOCK_REALTIME = 0
    CLOCK_MONOTONIC = 1  
    CLOCK_TAI = 11
    
    def get_time_ns(clock_id: int) -> int:
        ts = timespec()
        result = libc.clock_gettime(clock_id, ctypes.byref(ts))
        if result != 0:
            return 0  # Clock not available
        return ts.tv_sec * 1_000_000_000 + ts.tv_nsec
    
    tai_time = get_time_ns(CLOCK_TAI)
    realtime = get_time_ns(CLOCK_REALTIME)
    monotonic = get_time_ns(CLOCK_MONOTONIC)
    
    return tai_time, realtime, monotonic


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--check', action='store_true',
                       help='Check PTP support and current status')
    parser.add_argument('--start-master', metavar='INTERFACE',
                       help='Start PTP master on specified interface')
    parser.add_argument('--start-slave', metavar='INTERFACE', 
                       help='Start PTP slave on specified interface')
    parser.add_argument('--stop', action='store_true',
                       help='Stop all PTP services')
    parser.add_argument('--status', action='store_true',
                       help='Show current PTP synchronization status')
    parser.add_argument('--list-interfaces', action='store_true',
                       help='List available network interfaces')
    parser.add_argument('--test-clocks', action='store_true',
                       help='Test access to different clock sources')
    parser.add_argument('--monitor', action='store_true',
                       help='Monitor PTP synchronization continuously')
    
    args = parser.parse_args()
    
    ptp_manager = PTPManager()
    
    if args.check:
        print("=== PTP System Check ===")
        checks = ptp_manager.check_ptp_support()
        for check, status in checks.items():
            status_str = "✓" if status else "✗"
            print(f"{status_str} {check.replace('_', ' ').title()}: {status}")
        
        print(f"\nPTP Devices: {ptp_manager.find_ptp_devices()}")
        
    elif args.list_interfaces:
        interfaces = ptp_manager.get_network_interfaces()
        print("Available network interfaces:")
        for iface in interfaces:
            print(f"  {iface}")
            
    elif args.start_master:
        if ptp_manager.start_ptp_master(args.start_master):
            print("PTP master started successfully")
            print("Other machines can now sync to this master")
        else:
            print("Failed to start PTP master")
            sys.exit(1)
            
    elif args.start_slave:
        if ptp_manager.start_ptp_slave(args.start_slave):
            print("PTP slave started successfully")
            print("This machine will sync to detected PTP master")
        else:
            print("Failed to start PTP slave")
            sys.exit(1)
            
    elif args.stop:
        ptp_manager.stop_ptp_services()
        print("All PTP services stopped")
        
    elif args.status:
        status = ptp_manager.get_ptp_status()
        print("=== PTP Status ===")
        print(f"ptp4l running: {status['ptp4l_running']}")
        print(f"phc2sys running: {status['phc2sys_running']}")
        print(f"Master identified: {status['master_identified']}")
        if status['sync_offset'] is not None:
            print(f"Sync offset: {status['sync_offset']} ns")
        else:
            print("Sync offset: Unknown")
            
    elif args.test_clocks:
        print("=== Clock Source Test ===")
        try:
            tai_time, realtime, monotonic = get_high_precision_time()
            print(f"CLOCK_TAI:      {tai_time} ns {'(available)' if tai_time > 0 else '(not available)'}")
            print(f"CLOCK_REALTIME: {realtime} ns")
            print(f"CLOCK_MONOTONIC: {monotonic} ns")
            
            if tai_time > 0:
                # TAI is ahead of UTC by leap seconds (37 as of 2023)
                tai_utc_diff = (tai_time - realtime) / 1e9
                print(f"TAI-UTC difference: {tai_utc_diff:.1f} seconds")
        except Exception as e:
            print(f"Error accessing clocks: {e}")
            
    elif args.monitor:
        print("=== PTP Monitor ===")
        print("Press Ctrl+C to stop")
        try:
            while True:
                status = ptp_manager.get_ptp_status()
                try:
                    tai_time, realtime, monotonic = get_high_precision_time()
                    print(f"\r"
                          f"ptp4l: {'ON' if status['ptp4l_running'] else 'OFF'} | "
                          f"Offset: {status['sync_offset'] or 'N/A'} ns | "
                          f"TAI: {tai_time} | "
                          f"Real: {realtime}", end='', flush=True)
                except Exception:
                    print(f"\r"
                          f"ptp4l: {'ON' if status['ptp4l_running'] else 'OFF'} | "
                          f"Offset: {status['sync_offset'] or 'N/A'} ns | "
                          f"Clock access error", end='', flush=True)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            
    else:
        parser.print_help()


if __name__ == '__main__':
    main() 