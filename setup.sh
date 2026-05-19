#!/bin/bash

# RepoPath Sanitizer development setup script.

set -e

echo "======================================"
echo "RepoPath Sanitizer Setup"
echo "======================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is not installed. Please install Python 3.10 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_OK=$(python3 -c 'import sys; print(int(sys.version_info >= (3, 10)))')
echo "Python version: $PYTHON_VERSION"

if [ "$PYTHON_OK" != "1" ]; then
    echo "Error: Python 3.10 or later is required. Current version: $PYTHON_VERSION"
    exit 1
fi

if ! python3 -c 'import PyQt6' >/dev/null 2>&1; then
    echo ""
    echo "Warning: PyQt6 was not found in the system Python."
    echo "On Debian, install it with:"
    echo "  sudo apt install python3-pyqt6"
fi

echo ""
echo "Creating virtual environment with access to system packages..."
python3 -m venv .venv --system-site-packages

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "Installing RepoPath Sanitizer in editable development mode..."
pip install -e .[dev] --no-deps

echo ""
echo "======================================"
echo "Setup completed successfully!"
echo "======================================"
echo ""
echo "To run the application:"
echo "  source .venv/bin/activate"
echo "  repopath-sanitizer"
echo ""
echo "For CLI mode:"
echo "  repopath-sanitizer --cli --repo /path/to/repository"
