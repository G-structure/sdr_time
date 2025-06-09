# SDR Experiments Toolkit

Welcome to the SDR (Software Defined Radio) Experiments Toolkit! This project provides a comprehensive environment for experimenting with software-defined radio using Python and SoapySDR.

## 🎯 What You'll Learn

By working with this project, you'll learn:
- **Software Defined Radio (SDR)** fundamentals
- **Signal processing** with Python and NumPy
- **Real-time data visualization** with matplotlib
- **Remote SDR device control** over networks
- **Precision timing** and clock synchronization (PTP)
- **Modern development environments** with Nix

## 🚀 Quick Start

### Prerequisites

You need a Linux system (Ubuntu, Debian, NixOS, etc.) or WSL2 on Windows.

### 1. Install Nix

```bash
# Install Nix (the package manager)
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install

# Restart your shell or run:
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
```

### 2. Clone and Enter the Project

```bash
git clone <your-repo-url>
cd sdr_exp

# Enter the development environment (this may take a few minutes the first time)
nix develop
```

That's it! You now have a complete SDR development environment with all dependencies pre-installed.

### 3. Test Your Setup

```bash
# Test the environment
sdr-verify-ptp --help
sdr-waterfall --help
sdr-measure-delay --help

# Test with a remote SDR device (if you have one)
sdr-verify-ptp --args "remote=tcp://your-sdr-server:2500"
```

## 📁 Project Structure

```
sdr_exp/
├── README.md                 # This file
├── docs/                     # Documentation
│   ├── nix.md               # Nix environment guide
│   └── sdr.md               # SDR concepts and tools
├── src/                      # Source code (future modules)
├── flake.nix                # Nix environment definition
├── pyproject.toml           # Python project configuration
└── src/
    └── sdr_experiments/     # Main package
        ├── verify_ptp_clock.py  # PTP clock synchronization tester
        ├── waterfall.py         # Real-time spectrum waterfall
        ├── MeasureDelay.py      # RF propagation delay measurement
        ├── kitty_test.py        # Terminal graphics test
        └── soapy_log_handle.py  # SoapySDR logging utilities
```

## 🛠️ Available Tools

### Core Scripts

1. **`sdr-verify-ptp`** - Tests if your SDR device supports precise timing
   ```bash
   sdr-verify-ptp --args "driver=hackrf" --debug
   ```

2. **`sdr-waterfall`** - Real-time spectrum visualization
   ```bash
   sdr-waterfall --args "driver=hackrf" --freq 100e6
   ```

3. **`sdr-measure-delay`** - Measures signal propagation delays
   ```bash
   sdr-measure-delay --help
   ```

### Supported Hardware

- **HackRF One** - Entry-level SDR (1MHz-6GHz)
- **RTL-SDR** - Budget USB dongles (receive only)
- **USRP** - Professional SDR equipment
- **PlutoSDR** - Learning-focused SDR
- **Remote devices** - Connect to SDRs over the network

## 🎓 Learning Path

### New to SDR?
1. Read [`docs/sdr.md`](docs/sdr.md) - Learn SDR fundamentals
2. Start with `sdr-kitty-test` to verify your terminal
3. Try `sdr-verify-ptp` with a local device
4. Experiment with `sdr-waterfall` to see live signals

### New to Nix?
1. Read [`docs/nix.md`](docs/nix.md) - Understanding our development environment
2. Learn how to add new Python packages
3. Understand why we use Nix for this project

### Ready to Develop?
1. Look at the existing scripts as examples
2. Add your own experiments to the project
3. Use the established patterns for device handling

## 🔧 Adding Dependencies

### Python Packages

For pure Python packages, add them to `pyproject.toml`:

```toml
dependencies = [
    "numpy>=1.24.0",
    "matplotlib>=3.7.0",
    "scipy>=1.11.0",
    "requests>=2.31.0",  # Your new package
]
```

Then update the environment:
```bash
nix develop --command uv add requests
```

### System Packages

For packages that need compilation or system integration, add them to `flake.nix`:

```nix
pythonEnv = pkgs.python312.withPackages (ps: with ps; [
  soapysdr
  numpy
  matplotlib
  scipy
  # Add your package here
]);
```

## 🏠 Remote Development

### Connecting to Remote SDR Devices

Many SDR devices can be shared over the network using SoapySDRServer:

```bash
# On the machine with the SDR hardware
SoapySDRServer --bind=0.0.0.0:2500

# On your development machine
sdr-verify-ptp --args "remote=tcp://192.168.1.100:2500"
```

This allows multiple people to share expensive SDR hardware!

## 🐛 Troubleshooting

### Common Issues

**"No module named 'SoapySDR'"**
- Make sure you're in the Nix environment: `nix develop`

**"Device not found"**
- Check device connections and permissions
- Try listing devices: `python -c "import SoapySDR; print(SoapySDR.Device.enumerate())"`

**"Permission denied on /dev/ptp0"**
- For PTP timing, run the SDR server with sudo or fix permissions

### Getting Help

1. Check the documentation in `docs/`
2. Look at the existing script examples
3. Use `--help` flag on any script
4. Check SoapySDR logs with `--debug` flag

## 🤝 Contributing

1. All development happens in the Nix environment
2. Follow the established code patterns
3. Add documentation for new features
4. Test with multiple SDR devices when possible

## 📚 Further Reading

- [SoapySDR Documentation](https://github.com/pothosware/SoapySDR/wiki)
- [GNU Radio Tutorials](https://wiki.gnuradio.org/index.php/Tutorials)
- [SDR for Engineers](https://pysdr.org/) - Excellent online textbook
- [RTL-SDR Blog](https://www.rtl-sdr.com/) - News and tutorials

---

**Welcome to the world of Software Defined Radio!** 🎉

Start with [`docs/sdr.md`](docs/sdr.md) if you're new to SDR concepts, or [`docs/nix.md`](docs/nix.md) if you want to understand our development environment better. 