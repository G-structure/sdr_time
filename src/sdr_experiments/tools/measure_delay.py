#!/usr/bin/env python
"""Measure round trip delay through RF loopback/leakage

"""

import argparse
import os
import time

import numpy as np

import SoapySDR
from SoapySDR import * #SOAPY_SDR_ constants
from ..core.signal import generate_cf32_pulse, normalize_samples
from ..core.device import setup_sdr_device

def measure_delay(
        args,
        rate,
        freq=None,
        rx_bw=None,
        tx_bw=None,
        rx_chan=0,
        tx_chan=0,
        rx_ant=None,
        tx_ant=None,
        rx_gain=None,
        tx_gain=None,
        clock_rate=None,
        num_tx_samps=200,
        num_rx_samps=10000,
        dump_dir=None,
):
    """Transmit a bandlimited pulse, receive it and find the delay."""

    sdr = SoapySDR.Device(args)
    if not sdr.hasHardwareTime():
        raise Exception('this device does not support timed streaming')

    #set clock rate first
    if clock_rate is not None:
        sdr.setMasterClockRate(clock_rate)

    #set sample rate
    sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, rate)
    sdr.setSampleRate(SOAPY_SDR_TX, tx_chan, rate)
    print("Actual Rx Rate %f Msps"%(sdr.getSampleRate(SOAPY_SDR_RX, rx_chan) / 1e6))
    print("Actual Tx Rate %f Msps"%(sdr.getSampleRate(SOAPY_SDR_TX, tx_chan) / 1e6))

    #set antenna
    if rx_ant is not None:
        sdr.setAntenna(SOAPY_SDR_RX, rx_chan, rx_ant)
    if tx_ant is not None:
        sdr.setAntenna(SOAPY_SDR_TX, tx_chan, tx_ant)

    #set overall gain
    if rx_gain is not None:
        sdr.setGain(SOAPY_SDR_RX, rx_chan, rx_gain)
    if tx_gain is not None:
        sdr.setGain(SOAPY_SDR_TX, tx_chan, tx_gain)

    #tune frontends
    if freq is not None:
        sdr.setFrequency(SOAPY_SDR_RX, rx_chan, freq)
    if freq is not None:
        sdr.setFrequency(SOAPY_SDR_TX, tx_chan, freq)

    #set bandwidth
    if rx_bw is not None:
        sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, rx_bw)
    if tx_bw is not None:
        sdr.setBandwidth(SOAPY_SDR_TX, tx_chan, tx_bw)

    #create rx and tx streams
    print("Create Rx and Tx streams")
    #rx_stream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [rx_chan]) # Defer Rx stream setup
    tx_stream = sdr.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32, [tx_chan])

    #let things settle
    time.sleep(1)

    # --- Transmit Operation ---
    print("Activating Tx stream to send pulse...")
    sdr.activateStream(tx_stream)
    tx_pulse = generate_cf32_pulse(num_tx_samps)
    # Schedule Tx pulse 100ms in the future from current hardware time
    tx_time_0 = int(sdr.getHardwareTime("") + 0.1e9) # Ensure "" for default time source
    tx_flags = SOAPY_SDR_HAS_TIME | SOAPY_SDR_END_BURST
    status = sdr.writeStream(tx_stream, [tx_pulse], len(tx_pulse), tx_flags, tx_time_0)
    if status.ret != len(tx_pulse):
        raise Exception('transmit failed %s'%str(status))
    print(f"Tx pulse sent, status: {status.ret}, scheduled time: {tx_time_0} ns")

    # Wait for transmission to complete by checking stream status or a short delay
    # For END_BURST, the host just needs to wait a bit for the samples to clear the buffer.
    # A more robust way would be to poll readStreamStatus if the device supports it for TX.
    # For HackRF, a time delay proportional to buffer length should be sufficient.
    time.sleep( (len(tx_pulse) / rate) + 0.1 ) # Wait for pulse duration + a little extra

    print("Deactivating and closing Tx stream.")
    sdr.deactivateStream(tx_stream)
    sdr.closeStream(tx_stream)

    # --- Short Delay for T/R switch and device to settle ---
    # This delay might need tuning depending on the SDR and SoapySDR module behavior
    tr_switch_delay = 0.05 # 50 ms, adjust as needed
    print(f"Waiting {tr_switch_delay*1000} ms for T/R switch...")
    time.sleep(tr_switch_delay)

    # --- Receive Operation ---
    print("Setting up and activating Rx stream...")
    rx_stream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [rx_chan])

    rx_buffs = np.array([], np.complex64)
    rx_flags = SOAPY_SDR_HAS_TIME | SOAPY_SDR_END_BURST # Use END_BURST if you want a finite receive

    # Calculate when to start receiving.
    # We want to capture the pulse which started at tx_time_0.
    # The pulse has a duration, and we need to account for propagation and T/R switching.
    # Let's aim to start receiving shortly after the pulse was expected to be transmitted.
    # The exact receive_time will be the timestamp of the first received sample.
    # The num_rx_samps determines how long we listen *from* the activation time.
    
    # Estimate when the pulse finished transmitting
    tx_pulse_duration_ns = (len(tx_pulse) / rate) * 1e9
    estimated_tx_end_time_ns = tx_time_0 + tx_pulse_duration_ns

    # Start RX a bit after estimated TX end to catch the pulse.
    # The key is that the first sample of the Rx stream will be timestamped.
    # We set num_rx_samps to define the duration of the receive.
    # The activation time for RX should be now or in the near future.
    # For simplicity in half-duplex, activate RX to start ASAP after TX is done.
    # The actual timestamp will come from the first read.
    
    # Activate Rx stream to start as soon as possible and run for num_rx_samps
    # The 'timeNs' in activateStream for RX in this half-duplex scenario
    # will be relative to the device's current time when it actually starts.
    # We rely on the timestamp from the first readStream call.
    print(f"Activating Rx stream to capture {num_rx_samps} samples.")
    sdr.activateStream(rx_stream, SOAPY_SDR_END_BURST, 0, num_rx_samps) # timeNs=0 for immediate, numElems for burst
    rx_time_0 = None

    #accumulate receive buffer into large contiguous buffer
    while True:
        rx_buff = np.array([0]*1024, np.complex64)
        timeout_us = int(5e5) #500 ms >> stream time
        status = sdr.readStream(rx_stream, [rx_buff], len(rx_buff), timeoutUs=timeout_us)

        #stash time on first buffer
        if status.ret > 0 and rx_buffs.size == 0:
            rx_time_0 = status.timeNs
            if (status.flags & SOAPY_SDR_HAS_TIME) == 0:
                raise Exception('receive fail - no timestamp on first readStream %s'%(str(status)))

        #accumulate buffer or exit loop
        if status.ret > 0:
            rx_buffs = np.concatenate((rx_buffs, rx_buff[:status.ret]))
        else:
            break

    #cleanup streams
    print("Cleanup streams")
    #sdr.deactivateStream(tx_stream) # Already deactivated and closed
    sdr.deactivateStream(rx_stream)
    sdr.closeStream(rx_stream)
    #sdr.closeStream(tx_stream) # Already closed

    #check resulting buffer
    if len(rx_buffs) != num_rx_samps:
        raise Exception(
            'receive fail - captured samples %d out of %d'%(len(rx_buffs), num_rx_samps))
    if rx_time_0 is None:
        raise Exception('receive fail - no valid timestamp')

    #clear initial samples because transients
    rx_mean = np.mean(rx_buffs)
    for i in range(len(rx_buffs) // 100):
        rx_buffs[i] = rx_mean

    #normalize the samples
    tx_pulse_norm = normalize_samples(tx_pulse)
    rx_buffs_norm = normalize_samples(rx_buffs)

    #dump debug samples
    if dump_dir is not None:
        np.save(os.path.join(dump_dir, 'txNorm.npy'), tx_pulse_norm)
        np.save(os.path.join(dump_dir, 'rxNorm.npy'), rx_buffs_norm)
        np.save(os.path.join(dump_dir, 'rxRawI.npy'), np.real(rx_buffs))
        np.save(os.path.join(dump_dir, 'rxRawQ.npy'), np.imag(rx_buffs))

    #look for the for peak index for time offsets
    rx_argmax_index = np.argmax(rx_buffs_norm)
    tx_argmax_index = np.argmax(tx_pulse_norm)

    #check goodness of peak by comparing argmax and correlation
    rx_coor_index = np.argmax(np.correlate(rx_buffs_norm, tx_pulse_norm)) + len(tx_pulse_norm) // 2
    if abs(rx_coor_index-rx_argmax_index) > len(tx_pulse_norm)/4:
        raise Exception(
            'correlation(%d) does not match argmax(%d), probably bad data' %
            (rx_coor_index, rx_argmax_index))

    #calculate time offset
    tx_peak_time = int(tx_time_0 + (tx_argmax_index / rate) * 1e9)
    rx_peak_time = int(rx_time_0 + (rx_argmax_index / rate) * 1e9)
    time_delta = rx_peak_time - tx_peak_time
    print('>>> Time delta %f us'%(time_delta / 1e3))
    print("Done!")

def main():
    """Parse command line arguments and perform measurement."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--args", type=str, help="device factor arguments", default="")
    parser.add_argument("--rate", type=float, help="Tx and Rx sample rate", default=1e6)
    parser.add_argument("--rx-ant", type=str, help="Optional Rx antenna")
    parser.add_argument("--tx-ant", type=str, help="Optional Tx antenna")
    parser.add_argument("--rx-gain", type=float, help="Optional Rx gain (dB)")
    parser.add_argument("--tx-gain", type=float, help="Optional Tx gain (dB)")
    parser.add_argument("--rx-bw", type=float, help="Optional Rx filter bw (Hz)")
    parser.add_argument("--tx-bw", type=float, help="Optional Tx filter bw (Hz)")
    parser.add_argument("--rx-chan", type=int, help="Receiver channel (def=0)", default=0)
    parser.add_argument("--tx-chan", type=int, help="Transmitter channel (def=0)", default=0)
    parser.add_argument("--freq", type=float, help="Optional Tx and Rx freq (Hz)")
    parser.add_argument("--clock-rate", type=float, help="Optional clock rate (Hz)")
    parser.add_argument("--dump-dir", type=str, help="Optional directory to dump debug samples")
    parser.add_argument("--debug", action='store_true', help="Output debug messages")
    parser.add_argument(
        "--abort-on-error", action='store_true',
        help="Halts operations if the SDR logs an error")

    options = parser.parse_args()

    # Configure logging
    if options.debug:
        SoapySDR.setLogLevel(SOAPY_SDR_DEBUG)

    measure_delay(
        args=options.args,
        rate=options.rate,
        freq=options.freq,
        rx_bw=options.rx_bw,
        tx_bw=options.tx_bw,
        rx_ant=options.rx_ant,
        tx_ant=options.tx_ant,
        rx_gain=options.rx_gain,
        tx_gain=options.tx_gain,
        rx_chan=options.rx_chan,
        tx_chan=options.tx_chan,
        clock_rate=options.clock_rate,
        dump_dir=options.dump_dir,
    )

if __name__ == '__main__':
    main() 
