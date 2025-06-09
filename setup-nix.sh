#!/bin/bash
set -e

echo "🔧 Setting up Nix for SDR Experiments"
echo "====================================="

# Check if running on a supported system
if [[ "$OSTYPE" != "linux-gnu"* && "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script supports Linux and macOS only"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Nix if not present
if ! command_exists nix; then
    echo "📦 Installing Nix..."
    
    # Use the Determinate Systems installer for better experience
    if command_exists curl; then
        curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
    else
        echo "❌ curl is required to install Nix"
        exit 1
    fi
    
    # Source Nix in current session
    if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
        source '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
    fi
    
    echo "✅ Nix installed successfully"
else
    echo "✅ Nix is already installed"
fi

# Verify Nix installation
if ! command_exists nix; then
    echo "❌ Nix installation failed or not in PATH"
    echo "Please restart your shell and run this script again"
    exit 1
fi

# Check if flakes are enabled
echo "🔍 Checking Nix flakes support..."
if ! nix --version | grep -q "flakes"; then
    echo "⚠️  Enabling experimental flakes feature..."
    mkdir -p ~/.config/nix
    echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
fi

# Install direnv if not present (optional but recommended)
if ! command_exists direnv; then
    echo "📦 Installing direnv..."
    if command_exists nix; then
        nix profile install nixpkgs#direnv
        echo "✅ direnv installed"
        echo "⚠️  Add 'eval \"\$(direnv hook bash)\"' to your ~/.bashrc"
        echo "    or 'eval \"\$(direnv hook zsh)\"' to your ~/.zshrc"
    else
        echo "⚠️  direnv not installed. You can install it manually for better experience"
    fi
else
    echo "✅ direnv is already installed"
fi

# Test the flake
echo "🧪 Testing the Nix flake..."
if nix flake check --no-build; then
    echo "✅ Flake configuration is valid"
else
    echo "❌ Flake configuration has issues"
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart your shell to ensure Nix is in your PATH"
echo "2. Run 'nix develop' to enter the development environment"
echo "3. Or run 'direnv allow' if you have direnv configured"
echo ""
echo "Available commands:"
echo "  nix develop           # Default development shell"
echo "  nix develop .#pure    # Pure Nix environment"
echo "  nix develop .#editable # Editable development shell"
echo "  nix build             # Build the package"
echo "  nix run .#waterfall   # Run waterfall script"
echo ""
echo "For more information, see README.md" 