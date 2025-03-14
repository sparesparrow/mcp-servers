#!/bin/bash

# Exit on error
set -e

# Navigate to the script directory
cd "$(dirname "$0")"

echo "Checking package structure..."

# Check if the main module exists
if [ ! -f "src/mcp_prompt_manager/__init__.py" ]; then
    echo "ERROR: Missing src/mcp_prompt_manager/__init__.py"
    exit 1
fi

if [ ! -f "src/mcp_prompt_manager/__main__.py" ]; then
    echo "ERROR: Missing src/mcp_prompt_manager/__main__.py"
    echo "Creating __main__.py file..."
    cat > src/mcp_prompt_manager/__main__.py << 'EOF'
"""Main entry point for the MCP Prompt Manager."""
from .prompt_manager_server import main

if __name__ == "__main__":
    main()
EOF
fi

if [ ! -f "src/mcp_prompt_manager/prompt_manager_server.py" ]; then
    echo "ERROR: Missing src/mcp_prompt_manager/prompt_manager_server.py"
    exit 1
fi

# Check setup.py
if ! grep -q "entry_points" setup.py; then
    echo "WARNING: No entry points found in setup.py"
    echo "Adding entry points..."
    sed -i '/extras_require/i \
    entry_points={\
        "console_scripts": [\
            "mcp-prompt-manager=mcp_prompt_manager.prompt_manager_server:main",\
        ],\
    },\
    ' setup.py
fi

echo "Package structure check completed!"