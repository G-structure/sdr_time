#!/bin/bash

# Set PYTHONPATH to include both common SoapySDR installation locations
export PYTHONPATH="/usr/local/lib/python3.9/site-packages:/usr/lib/python3.9/dist-packages:$PYTHONPATH"

# Try to find SoapySDR in the system installation paths
SOAPYSDR_PY_PATH=""
SOAPYSDR_SO_PATH=""

# Check common installation locations for SoapySDR.py
if [ -f "/usr/local/lib/python3.9/site-packages/SoapySDR.py" ]; then
    SOAPYSDR_PY_PATH="/usr/local/lib/python3.9/site-packages/SoapySDR.py"
    SOAPYSDR_SO_PATH="/usr/local/lib/python3.9/site-packages/_SoapySDR.so"
elif [ -f "/usr/lib/python3.9/dist-packages/SoapySDR.py" ]; then
    SOAPYSDR_PY_PATH="/usr/lib/python3.9/dist-packages/SoapySDR.py"
    SOAPYSDR_SO_PATH="/usr/lib/python3.9/dist-packages/_SoapySDR.so"
fi

if [ -z "$SOAPYSDR_PY_PATH" ]; then
    echo "Error: SoapySDR.py not found in system. Please install SoapySDR first."
    exit 1
fi

echo "Found SoapySDR.py at: $SOAPYSDR_PY_PATH"

# Use the local site-packages directory (this is what the virtual environment uses)
VENV_SITE_PACKAGES="./site-packages"
TARGET_PY_LINK="$VENV_SITE_PACKAGES/SoapySDR.py"
TARGET_SO_LINK="$VENV_SITE_PACKAGES/_SoapySDR.so"

# Create the site-packages directory if it doesn't exist
mkdir -p "$VENV_SITE_PACKAGES"

# Remove existing symbolic links if they exist
if [ -L "$TARGET_PY_LINK" ] || [ -e "$TARGET_PY_LINK" ]; then
    rm -f "$TARGET_PY_LINK"
    echo "Removed existing SoapySDR.py link/file"
fi

if [ -L "$TARGET_SO_LINK" ] || [ -e "$TARGET_SO_LINK" ]; then
    rm -f "$TARGET_SO_LINK"
    echo "Removed existing _SoapySDR.so link/file"
fi

# Create symbolic links to system-level SoapySDR installation
ln -s "$SOAPYSDR_PY_PATH" "$TARGET_PY_LINK"
echo "Linked SoapySDR.py"

if [ -f "$SOAPYSDR_SO_PATH" ]; then
    ln -s "$SOAPYSDR_SO_PATH" "$TARGET_SO_LINK"
    echo "Linked _SoapySDR.so"
fi

# Create a .pth file to add the site-packages directory to Python path
PTH_FILE="$VENV_SITE_PACKAGES/soapysdr_path.pth"
echo "$(pwd)/site-packages" > "$PTH_FILE"
echo "Created .pth file to add site-packages to Python path"

# Print a success message
echo "Successfully created symbolic links for SoapySDR in local site-packages."

# Note: Don't call deactivate here as it should be sourced in the shell
echo "Note: If you need to deactivate the virtual environment, use 'source deactivate' or 'deactivate'"