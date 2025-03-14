#!/bin/bash

# Exit on error
set -e

# Navigate to the script directory
cd "$(dirname "$0")"

# Create Python virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv .venv
    echo "Virtual environment created at: $(pwd)/.venv"
fi

# Activate virtual environment
source .venv/bin/activate

# Install development dependencies
echo "Installing development requirements..."
pip install --upgrade pip
pip install -e .
pip install pytest pytest-asyncio jupyter

# Create shared prompt directory structure
echo "Setting up shared prompt directories..."
mkdir -p "/home/sparrow/mcp/data/prompts"

echo ""
echo "Development environment setup complete!"
echo ""
echo "To activate this environment, run:"
echo "  source $(pwd)/.venv/bin/activate"
echo ""
echo "To run the server in development mode:"
echo "  python -m mcp_prompt_manager"
echo ""
echo "To build the Docker container:"
echo "  ./build-container.sh"
