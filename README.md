# SDR Experiments with Nix

A professional Software Defined Radio (SDR) development environment using Nix flakes, uv, and pyproject.toml (PEP 518).

## 🌟 Features

- **Modern Python packaging** with pyproject.toml (PEP 518 compliant)
- **Nix flakes** for reproducible development environments
- **uv2nix integration** for dependency management
- **Multiple development shells** for different workflows
- **C extension support** with optimized builds for SDR libraries
- **SDR-specific optimizations** for NumPy, SciPy, and SoapySDR

## 🚀 Quick Start

### Prerequisites

- [Nix](https://nixos.org/download) with flakes enabled
- [direnv](https://direnv.net/) (optional but recommended)

### Enter the Development Environment

```bash
# Clone and enter the repository
cd sdr_exp

# Enter the default development shell
nix develop

# Or use direnv for automatic activation
echo "use flake" > .envrc
direnv allow
```

### Available Development Shells

1. **Default Shell** (`nix develop`): Hybrid approach with system packages from Nix
2. **Impure Shell** (`nix develop .#impure`): Recommended for uv workflow with Nix system deps
3. **Pure Shell** (`nix develop .#pure`): Pure Nix environment (when pyproject.toml exists)
4. **Editable Shell** (`nix develop .#editable`): Development with editable packages

## 📦 Project Structure

```
sdr_exp/
├── flake.nix              # Nix flake configuration
├── pyproject.toml         # Python project configuration (PEP 518)
├── src/
│   └── sdr_experiments/   # Main Python package
│       ├── __init__.py
│       ├── soapy_log_handle.py
│       └── utils.py
├── nix/
│   ├── overlays/
│   │   └── sdr-overrides.nix  # Custom Python package overrides
│   └── packages/          # Custom package definitions
├── tests/                 # Test files
├── docs/                  # Documentation
└── scripts/               # Standalone scripts
```

## 🔧 Development Workflows

### Using the Hybrid Approach (Recommended)

```bash
# Enter the default or impure development shell
nix develop
# or
nix develop .#impure

# Critical SDR packages (soapysdr, numpy, matplotlib) are provided by Nix
# Run scripts directly - no uv needed for basic usage
python waterfall.py
python MeasureDelay.py

# Add additional pure Python packages with uv
uv add scipy pandas plotly

# For packages requiring uv environment
uv run python script_with_additional_deps.py

# Development tools
uv add --dev pytest black isort mypy
uv run pytest
```

### Using Pure Nix

```bash
# Enter pure Nix shell
nix develop .#pure

# All dependencies are managed by Nix
python waterfall.py
python MeasureDelay.py
```

### Package Development

```bash
# Enter editable development shell
nix develop .#editable

# Changes to src/sdr_experiments/ are immediately available
python -c "import sdr_experiments; print(sdr_experiments.__version__)"
```

## 🛠 Building and Installing

### Build the Package

```bash
# Build the package
nix build

# Run the built package
./result/bin/sdr-waterfall --help
```

### Install in Environment

```bash
# Install in current environment
uv pip install -e .

# Or build wheel
uv build
```

## 🎯 SDR-Specific Features

### Optimized Libraries

The Nix environment includes optimized builds of:

- **NumPy**: Built with OpenBLAS for fast linear algebra
- **SciPy**: Optimized with FFTW and BLAS
- **SoapySDR**: Proper C library linking
- **Matplotlib**: Full backend support for visualization

### Hardware Support

Pre-configured support for:

- SoapySDR with plugins
- RTL-SDR dongles
- HackRF devices
- USRP (UHD)
- GNU Radio

### Environment Variables

The development shell automatically sets:

```bash
SOAPY_SDR_PLUGIN_PATH    # SoapySDR plugin discovery
LD_LIBRARY_PATH          # C library paths (Linux)
UV_PYTHON                # Force uv to use Nix Python
TERM=xterm-kitty         # Kitty terminal support
```

## 📋 Available Scripts

- `sdr-waterfall`: Real-time waterfall visualization
- `sdr-measure-delay`: RF delay measurement
- `sdr-verify-ptp`: PTP clock verification

## 🔧 Customization

### Adding Custom Packages

1. Create package definition in `nix/packages/my-package.nix`
2. Add to overlays in `nix/overlays/sdr-overrides.nix`
3. Reference in `flake.nix`

### Python Dependencies

Edit `pyproject.toml`:

```toml
[project]
dependencies = [
    "numpy>=1.24.0",
    "my-new-package>=1.0.0",
]

[project.optional-dependencies]
extra = [
    "additional-package>=2.0.0",
]
```

### C Extension Overrides

Add to `nix/overlays/sdr-overrides.nix`:

```nix
my-package = prev.my-package.overrideAttrs (old: {
  buildInputs = (old.buildInputs or []) ++ [ final.pkgs.my-c-library ];
  env = (old.env or {}) // {
    MY_C_LIBRARY_PATH = final.pkgs.my-c-library;
  };
});
```

## 🧪 Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=sdr_experiments

# Type checking
uv run mypy src/

# Code formatting
uv run black src/ tests/
uv run isort src/ tests/
```

## 📈 Performance Optimizations

### CPU-Specific Builds

The environment enables `-march=native` for C extensions when possible, optimizing for your specific CPU.

### Memory Management

- OpenBLAS threading is configured appropriately
- NumPy uses optimized BLAS routines
- Memory-mapped file support for large datasets

### SDR-Specific

- SoapySDR plugins are pre-loaded
- Hardware drivers are available
- Real-time scheduling support (where available)

## 🐛 Troubleshooting

### Common Issues

1. **Missing SoapySDR plugins**: Ensure `SOAPY_SDR_PLUGIN_PATH` is set
2. **Import errors**: Check that you're in the correct shell environment
3. **C extension build failures**: Review the overlay configuration

### Debug Commands

```bash
# Check Python environment
python -c "import sys; print(sys.path)"

# Check SoapySDR
python -c "import SoapySDR; print(SoapySDR.Device.enumerate())"

# Check library paths
echo $LD_LIBRARY_PATH
```

## 📚 Resources

- [Nix Flakes](https://nixos.wiki/wiki/Flakes)
- [uv2nix Documentation](https://pyproject-nix.github.io/uv2nix/)
- [PEP 518](https://peps.python.org/pep-0518/)
- [SoapySDR Documentation](https://github.com/pothosware/SoapySDR/wiki)

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Submit a pull request

The Nix environment ensures all contributors have identical development setups! 