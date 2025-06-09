# Understanding Nix for SDR Development

## What is Nix?

Nix is a **package manager** and **build system** that creates reproducible, isolated development environments. Think of it as a way to ensure that everyone working on this project has exactly the same software setup, regardless of their operating system or what other software they have installed.

### Why Traditional Package Management is Problematic

Imagine you're working on a team where:
- Alice has Python 3.11, Bob has Python 3.12
- Alice installed NumPy with `pip`, Bob used `conda`
- Alice is on Ubuntu, Bob is on macOS
- Alice has version 1.24 of NumPy, Bob has 1.26

When Alice's code works but Bob's doesn't, is it a bug in the code or a difference in the environment? **This is the problem Nix solves.**

## Why We Use Nix for SDR

### The SDR Challenge

Software Defined Radio has unique challenges:

1. **Complex Dependencies**: SoapySDR needs to be compiled against specific C++ libraries
2. **Hardware Drivers**: Different SDR devices need different drivers
3. **Performance**: Signal processing needs optimized math libraries (BLAS, FFTW)
4. **System Integration**: Some features need special permissions or kernel modules

### Traditional Approaches Fall Short

- **pip**: Can't install SoapySDR (not on PyPI)
- **conda**: Limited SDR packages, version conflicts
- **apt/yum**: Different versions across distributions
- **Docker**: Heavy, doesn't handle hardware access well

### The Nix Solution

Nix gives us:
- ✅ **Reproducible**: Same environment everywhere
- ✅ **Complete**: All dependencies, from Python to C libraries
- ✅ **Fast**: No compilation time for users
- ✅ **Isolated**: Doesn't interfere with your system
- ✅ **Declarative**: Environment defined in code

## How Nix Works

### The Nix Store

Nix installs everything in `/nix/store/` with cryptographic hashes:

```
/nix/store/abc123-python-3.12.10/
/nix/store/def456-numpy-1.24.3/
/nix/store/xyz789-soapysdr-0.8.1/
```

This means:
- Multiple versions can coexist
- No conflicts between projects
- Exact reproducibility

### Flakes

Our project uses **Nix flakes**, which are:
- Self-contained project definitions
- Version-locked dependencies
- Easy to share and reproduce

## Working with Our Nix Environment

### Basic Commands

```bash
# Enter the development environment
nix develop

# See what's installed
which python
python --version
python -c "import SoapySDR; print('SoapySDR works!')"

# Exit the environment
exit
```

### What Happens When You Run `nix develop`

1. Nix reads `flake.nix` (our environment definition)
2. Downloads pre-built packages from the Nix cache
3. Creates an isolated shell with all dependencies
4. Sets up environment variables for SDR libraries
5. Gives you a prompt ready for development

### The First Time is Slow

The first `nix develop` may take several minutes because:
- Nix downloads Python, NumPy, SoapySDR, etc.
- It sets up the complete environment
- Everything is cached for next time

**Subsequent times are instant!**

## Understanding Our Setup

### What's in `flake.nix`

```nix
{
  description = "SDR Python Development Environment";
  
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };
  
  outputs = { self, nixpkgs, ... }: {
    devShells.x86_64-linux.default = 
      let
        pkgs = nixpkgs.legacyPackages.x86_4-linux;
        
        # Create Python environment with SDR packages
        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
          soapysdr     # The core SDR library
          numpy        # Fast array processing
          matplotlib   # Plotting and visualization
          scipy        # Scientific computing
        ]);
        
      in pkgs.mkShell {
        packages = with pkgs; [
          pythonEnv                # Our Python environment
          soapysdr-with-plugins    # SDR drivers
          soapyremote             # Remote SDR support
          hackrf                  # HackRF driver
          rtl-sdr                 # RTL-SDR driver
          uhd                     # USRP driver
          uv                      # Python package manager
        ];
        
        env = {
          # Tell SoapySDR where to find plugins
          SOAPY_SDR_PLUGIN_PATH = "${pkgs.soapysdr-with-plugins}/lib/SoapySDR/modules0.8-3";
          # Tell uv to use our Python
          UV_PYTHON = "${pythonEnv}/bin/python";
        };
      };
  };
}
```

This defines:
- Which Python version (3.12)
- Which packages to include
- How to configure them
- Environment variables to set

### Package Sources

Our packages come from:
1. **System packages**: From nixpkgs (Python, SoapySDR, drivers)
2. **Python packages**: Added to `pyproject.toml` and managed by `uv`

## Adding New Packages

### System/Compiled Packages → flake.nix

For packages that need compilation or system integration:

```nix
pythonEnv = pkgs.python312.withPackages (ps: with ps; [
  soapysdr
  numpy
  matplotlib
  scipy
  tensorflow  # Add here for compiled packages
]);
```

### Pure Python Packages → pyproject.toml

For packages from PyPI:

```toml
dependencies = [
    "numpy>=1.24.0",
    "matplotlib>=3.7.0",
    "scipy>=1.11.0",
    "requests>=2.31.0",  # Add here for pure Python
]
```

Then: `nix develop --command uv add requests`

## Common Workflows

### Daily Development

```bash
# Enter environment
nix develop

# Your normal Python workflow
python my_script.py
python -m pytest
python -c "import any_installed_package"

# Add a new package
uv add pandas

# Leave environment
exit
```

### Updating Dependencies

```bash
# Update flake inputs
nix flake update

# Enter updated environment
nix develop
```

### Sharing Your Environment

Since everything is in `flake.nix` and `flake.lock`, anyone can reproduce your exact environment:

```bash
git clone your-repo
cd your-repo
nix develop  # Identical environment!
```

## Troubleshooting

### "command not found: nix"

Nix isn't installed. See the README for installation instructions.

### "error: experimental feature 'nix-command' is required"

You need to enable flakes. Run:
```bash
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### "No module named 'SoapySDR'"

You're not in the Nix environment. Run `nix develop` first.

### Environment feels slow

The first setup is slow, but subsequent uses are fast. If it's always slow:
- Check your internet connection
- Consider using a Nix binary cache mirror

### Can't find a package

- Search nixpkgs: https://search.nixos.org/packages
- For Python packages: Check if it needs to be in flake.nix vs pyproject.toml

## Advanced Topics

### Understanding the Nix Store

```bash
# See what's in the environment
echo $PATH

# Find where packages live
which python
ls -la $(which python)
```

### Debugging the Environment

```bash
# What Python packages are available?
python -c "import sys; print('\n'.join(sys.path))"

# What SoapySDR modules are loaded?
python -c "import SoapySDR; print(SoapySDR.listModules())"

# What environment variables are set?
env | grep -E "(SOAPY|PYTHON|UV)"
```

### Temporary Package Testing

```bash
# Try a package without adding it permanently
nix develop --command python -c "import requests; print('works!')"
nix develop --command bash -c "pip install requests && python -c 'import requests'"
```

## Why This Approach is Better

### Before Nix
- "It works on my machine" problems
- Complex setup instructions
- Version conflicts
- Different behavior on different systems

### With Nix
- Same environment for everyone
- One command setup (`nix develop`)
- No conflicts with your system
- Reproducible builds and results

## Learning More

- **Nix Pills**: https://nixos.org/guides/nix-pills/ (deep dive)
- **Nix Package Search**: https://search.nixos.org/packages
- **Zero to Nix**: https://zero-to-nix.com/ (beginner guide)
- **NixOS Wiki**: https://nixos.wiki/wiki/Development_environment_with_nix-shell

Remember: You don't need to understand everything about Nix to use it effectively. The key is knowing how to enter the environment (`nix develop`) and add packages when needed! 