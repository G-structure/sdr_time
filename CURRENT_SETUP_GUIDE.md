# SDR Development Setup Guide

## Current Situation

You're trying to run SDR scripts that require `SoapySDR` Python bindings, but you're getting:
```
ModuleNotFoundError: No module named 'SoapySDR'
```

This happens because `SoapySDR` is not available on PyPI - it needs to be compiled against the system SoapySDR C++ library.

## Option 1: Install System Dependencies (Current System)

Since Nix is not installed on this system, you can install the required packages manually:

### Ubuntu/Debian:
```bash
# Install SoapySDR and Python bindings
sudo apt update
sudo apt install -y \
    soapysdr-tools \
    libsoapysdr-dev \
    python3-soapysdr \
    python3-numpy \
    python3-matplotlib \
    python3-scipy

# Install SDR hardware drivers
sudo apt install -y \
    soapysdr-module-hackrf \
    soapysdr-module-rtlsdr \
    soapysdr-module-uhd

# Test the installation
python3 -c "import SoapySDR; print('SoapySDR available:', SoapySDR.__version__)"
```

### Run Your Scripts:
```bash
# Now you can run the scripts directly
python3 verify_ptp_clock.py --help
python3 waterfall.py --help
python3 MeasureDelay.py --help
```

## Option 2: Install Nix (Recommended)

The Nix setup we created provides a much better, reproducible environment:

### Install Nix:
```bash
# Run the setup script we created
./setup-nix.sh
```

### Use the Environment:
```bash
# Enter the development environment
nix develop

# All dependencies are automatically available
python verify_ptp_clock.py --help
python waterfall.py --help
```

## Option 3: Docker Alternative

If you prefer Docker, here's a quick Dockerfile:

```dockerfile
FROM ubuntu:22.04

RUN apt update && apt install -y \
    soapysdr-tools \
    libsoapysdr-dev \
    python3-soapysdr \
    python3-numpy \
    python3-matplotlib \
    python3-scipy \
    python3-pip \
    soapysdr-module-hackrf \
    soapysdr-module-rtlsdr

WORKDIR /workspace
COPY . .

CMD ["bash"]
```

Build and run:
```bash
docker build -t sdr-env .
docker run -it --privileged -v $(pwd):/workspace sdr-env
```

## Current Scripts Available

- `verify_ptp_clock.py` - PTP clock verification
- `waterfall.py` - Real-time waterfall visualization  
- `MeasureDelay.py` - RF delay measurement
- `kitty_test.py` - Kitty terminal graphics test

## Dependencies Required

- **SoapySDR**: Core SDR abstraction layer
- **NumPy**: Numerical computing
- **Matplotlib**: Plotting and visualization
- **Hardware drivers**: For RTL-SDR, HackRF, USRP, etc.

## Why Nix is Better

The Nix approach provides:
- ✅ Reproducible environments across all systems
- ✅ Automatic dependency management
- ✅ Optimized builds (OpenBLAS, FFTW, etc.)
- ✅ No conflicts with system packages
- ✅ Easy switching between environments
- ✅ Works identically on all team members' machines

Choose the option that works best for your current setup! 