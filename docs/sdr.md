# Software Defined Radio (SDR) Guide

## What is Software Defined Radio?

**Software Defined Radio (SDR)** is a technology that uses software to perform radio signal processing that was traditionally done by hardware. Instead of having dedicated circuits for tuning, filtering, and demodulating radio signals, an SDR does all of this in software.

### Traditional Radio vs SDR

**Traditional Radio:**
```
Antenna → Filter → Amplifier → Mixer → Demodulator → Audio
   ↑        ↑         ↑         ↑         ↑         ↑
 hardware hardware hardware hardware hardware hardware
```

**Software Defined Radio:**
```
Antenna → ADC → Computer (Software does everything else)
   ↑       ↑         ↑
 hardware hardware software
```

### Why SDR is Revolutionary

1. **Flexibility**: One device can be a FM radio, WiFi analyzer, GPS receiver, etc.
2. **Upgradeable**: New features through software updates
3. **Educational**: You can see and understand how radio works
4. **Research**: Easy to experiment with new radio protocols
5. **Cost**: One SDR can replace many specialized devices

## SDR Hardware We Support

### RTL-SDR (~$25)
- **Frequency Range**: 24 MHz - 1.7 GHz
- **Receive Only**: Can't transmit
- **Best For**: Learning, AM/FM radio, ADS-B aircraft tracking
- **Pros**: Very cheap, excellent for beginners
- **Cons**: Limited frequency range, no transmit

### HackRF One (~$300)
- **Frequency Range**: 1 MHz - 6 GHz
- **Half Duplex**: Can transmit OR receive (not both simultaneously)
- **Sample Rate**: 20 MSPS
- **Best For**: General purpose SDR work, research
- **Pros**: Wide frequency range, transmit capable, open source
- **Cons**: Limited to half-duplex

### USRP Series (~$800+)
- **Professional Grade**: High performance, full duplex
- **Frequency Range**: Depends on daughterboards
- **Best For**: Research, commercial applications
- **Pros**: High performance, modular, industry standard
- **Cons**: Expensive

### PlutoSDR (~$200)
- **Frequency Range**: 325 MHz - 3.8 GHz
- **Full Duplex**: Can transmit and receive simultaneously
- **Best For**: Learning, educational use
- **Pros**: Good balance of features and price
- **Cons**: Limited frequency range

## Key SDR Concepts

### Sampling and Analog-to-Digital Conversion (ADC)

The SDR converts continuous radio waves into digital samples:

```python
# Radio wave: continuous analog signal
# ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿

# After ADC: discrete digital samples
# [0.1, 0.3, 0.7, 0.9, 0.8, 0.4, -0.1, -0.5, ...]
```

**Sample Rate**: How many samples per second
- Higher = can capture higher frequencies
- Lower = less data to process

### I/Q (In-phase/Quadrature) Data

SDRs typically provide **complex samples** with two components:
- **I (In-phase)**: Real part
- **Q (Quadrature)**: Imaginary part

```python
import numpy as np

# Each sample is a complex number
sample = 0.5 + 0.3j  # I=0.5, Q=0.3

# This represents magnitude and phase
magnitude = abs(sample)  # 0.583
phase = np.angle(sample)  # 0.540 radians
```

**Why I/Q?**
- Captures both amplitude AND phase information
- Allows processing of signals on both sides of center frequency
- Enables advanced signal processing techniques

### Center Frequency and Bandwidth

**Center Frequency**: The frequency your SDR is "tuned" to
**Bandwidth**: The range of frequencies you can see around the center

```
    Bandwidth = 10 MHz
    ┌─────────────────┐
────┼─────────────────┼────► Frequency
   95MHz           105MHz
         ↑
   Center = 100MHz
```

### Waterfall Displays

A **waterfall** shows how the frequency spectrum changes over time:
- **X-axis**: Frequency
- **Y-axis**: Time (scrolling down)
- **Color**: Signal strength (bright = strong signal)

```
Time  Frequency →
  ↓   88 90 92 94 96 98 100 102 104 106 108 MHz
  │   ░░░██░░░░░░░░░██░░░░░░░░░░░░██░░░░░░░
  │   ░░░██░░░░░░░░░██░░░░░░░░░░░░██░░░░░░░
  │   ░░░██░░░░░░░░░██░░░░░░░░░░░░██░░░░░░░
  ▼   ░░░██░░░░░░░░░██░░░░░░░░░░░░██░░░░░░░
```

## Our SDR Tools

### 1. `verify_ptp_clock.py` - Timing and Synchronization

**What it does**: Tests if your SDR supports precise timing using PTP (Precision Time Protocol)

**Why timing matters**:
- **Direction Finding**: Multiple SDRs need synchronized timestamps
- **TDOA (Time Difference of Arrival)**: Locating transmitters
- **Research**: Precise measurements need accurate timing

**Example usage**:
```bash
# Test local HackRF
sdr-verify-ptp --args "driver=hackrf" --debug

# Test remote SDR
sdr-verify-ptp --args "remote=tcp://192.168.1.100:2500"
```

**What to look for**:
- Large timestamps (billions) = Epoch time, good for synchronization
- Small timestamps (thousands) = Relative time, limited synchronization

### 2. `waterfall.py` - Real-time Spectrum Visualization

**What it does**: Shows a live waterfall display of the radio spectrum

**Educational value**:
- **See radio activity** in real-time
- **Identify signal types** by their patterns
- **Understand bandwidth** and frequency allocation

**Example usage**:
```bash
# FM radio band
sdr-waterfall --args "driver=hackrf" --freq 100e6 --rate 10e6

# ISM band (WiFi, Bluetooth)
sdr-waterfall --args "driver=hackrf" --freq 2.4e9 --rate 20e6
```

**What you'll see**:
- **FM Radio**: Strong vertical lines at 88-108 MHz
- **WiFi**: Wide bursts around 2.4 GHz
- **Cell phones**: Various patterns depending on location

### 3. `MeasureDelay.py` - RF Propagation Measurement

**What it does**: Measures the time it takes for radio signals to travel through space

**Applications**:
- **Cable length measurement**: Using radio frequency signals
- **Distance measurement**: Time-of-flight calculations
- **System calibration**: Accounting for known delays

**Physics background**:
```
Speed of light = 3×10⁸ m/s
Time = Distance / Speed

For 100 meters:
Time = 100m / (3×10⁸ m/s) = 333 nanoseconds
```

### 4. `sdr-kitty-test` - Terminal Graphics Test

**What it does**: Tests if your terminal supports advanced graphics for visualization

**Why important**:
- Modern terminals can display images inline
- Better visualization of signal data
- More efficient than separate graphics windows

## SoapySDR: The Common Interface

All our tools use **SoapySDR**, which provides a common interface to different SDR hardware.

### Device Arguments

SoapySDR uses "device arguments" to specify which SDR to use:

```python
# Local devices
"driver=hackrf"                    # HackRF
"driver=rtlsdr"                   # RTL-SDR
"driver=uhd"                      # USRP

# Remote devices
"remote=tcp://192.168.1.100:2500" # Remote SDR server

# Specific devices (if multiple)
"driver=hackrf,serial=12345"      # Specific HackRF
```

### Common Parameters

All SDR operations need:
- **Sample Rate**: How fast to sample (Hz)
- **Center Frequency**: What frequency to tune to (Hz)
- **Gain**: Amplification level (dB)

```python
import SoapySDR

# Open device
sdr = SoapySDR.Device("driver=hackrf")

# Configure
sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, 10e6)  # 10 MSPS
sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, 100e6)  # 100 MHz
sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 30)          # 30 dB gain
```

## Signal Processing Basics

### FFT (Fast Fourier Transform)

Converts time-domain samples to frequency-domain spectrum:

```python
import numpy as np
import matplotlib.pyplot as plt

# Time domain samples (what SDR gives you)
samples = np.array([complex numbers...])

# Frequency domain (what you see in waterfall)
spectrum = np.fft.fftshift(np.fft.fft(samples))
frequencies = np.fft.fftshift(np.fft.fftfreq(len(samples), 1/sample_rate))

# Plot spectrum
plt.plot(frequencies, np.abs(spectrum))
```

### Complex Numbers in SDR

```python
# A complex sample represents amplitude and phase
sample = 0.5 + 0.3j

# Amplitude (signal strength)
amplitude = abs(sample)  # √(0.5² + 0.3²) = 0.583

# Phase (timing information)
phase = np.angle(sample)  # arctan(0.3/0.5) = 0.540 radians

# Power (for signal detection)
power = sample.real**2 + sample.imag**2  # 0.34
```

## Remote SDR Operation

### Why Remote SDRs?

1. **Share expensive hardware** among multiple users
2. **Remote sensing**: Place SDR at optimal location
3. **Safety**: Keep powerful transmitters away from users
4. **Accessibility**: Use SDR from anywhere on network

### Setting Up Remote Access

**On the SDR host machine**:
```bash
# Install SoapyRemote server
sudo apt install soapyremote-server

# Start server (replace with actual IP)
SoapySDRServer --bind=192.168.1.100:2500
```

**On your development machine**:
```bash
# Connect to remote SDR
sdr-verify-ptp --args "remote=tcp://192.168.1.100:2500"
```

## Safety and Legal Considerations

### Transmitting Safety

⚠️ **Before transmitting with any SDR**:
1. **Check local laws**: Some frequencies require licenses
2. **Use appropriate antennas**: Wrong antenna can damage SDR
3. **Limit power**: Start with low power settings
4. **Check frequency allocation**: Don't interfere with critical services

### Common Legal Frequencies for Experimentation

- **ISM Bands**: 433 MHz, 915 MHz, 2.4 GHz (low power)
- **Amateur Radio**: If you have a license
- **Receive Only**: Generally legal to listen to most frequencies

### Best Practices

1. **Start receive-only**: Learn before transmitting
2. **Use dummy loads**: For testing transmitters
3. **Check power output**: Use spectrum analyzer or power meter
4. **Respect others**: Don't cause interference

## Learning Exercises

### Beginner Projects

1. **FM Radio Reception**:
   ```bash
   sdr-waterfall --args "driver=rtlsdr" --freq 100e6 --rate 2e6
   ```

2. **ADS-B Aircraft Tracking**:
   ```bash
   sdr-waterfall --args "driver=rtlsdr" --freq 1090e6 --rate 2e6
   ```

3. **WiFi Channel Monitoring**:
   ```bash
   sdr-waterfall --args "driver=hackrf" --freq 2.437e9 --rate 20e6
   ```

### Intermediate Projects

1. **Signal Identification**: Learn to recognize different signal types
2. **Power Measurements**: Measure signal strength accurately
3. **Timing Analysis**: Understand timestamp behavior

### Advanced Projects

1. **Direction Finding**: Use multiple SDRs for TDOA
2. **Protocol Reverse Engineering**: Analyze unknown signals
3. **Custom Demodulators**: Implement your own signal processing

## Further Learning Resources

### Books
- **"Software Defined Radio for Engineers" (PySDR)**: Free online textbook
- **"Understanding Digital Signal Processing"**: Math foundation
- **"Wireless Communications & Networks"**: System-level understanding

### Online Resources
- **GNU Radio Wiki**: Excellent tutorials and examples
- **RTL-SDR Blog**: News, tutorials, and project ideas
- **Reddit r/RTLSDR**: Community discussions and help

### Hands-on Learning
- **Amateur Radio License**: Learn regulations and theory
- **GNU Radio Companion**: Visual signal processing
- **Hack RF Academy**: Structured learning path

---

**Ready to explore the radio spectrum?** Start with `sdr-waterfall` to see what signals are around you, then dive deeper into the specific tools based on your interests! 