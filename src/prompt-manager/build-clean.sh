#!/bin/bash

# Exit on error
set -e

echo "Building clean Python MCP server..."

# Create package __init__.py file if it doesn't exist
if [ ! -f "src/mcp_prompt_manager/__init__.py" ]; then
    echo "Creating __init__.py file..."
    echo "__version__ = \"0.1.0\"" > src/mcp_prompt_manager/__init__.py
fi

# Create __main__.py file if it doesn't exist
if [ ! -f "src/mcp_prompt_manager/__main__.py" ]; then
    echo "Creating __main__.py file..."
    cat > src/mcp_prompt_manager/__main__.py << 'EOF'
"""Main entry point for the MCP Prompt Manager."""
from .prompt_manager_server import main

if __name__ == "__main__":
    main()
EOF
fi

# Build Docker image
docker build -t prompt-manager:latest -f Dockerfile.clean .

# Create Docker volume if it doesn't exist
docker volume create mcp-prompt-manager-data

echo "Python MCP server built successfully."
echo "Try running it with:"
echo "docker run --rm -i -v mcp-prompt-manager-data:/data -v /home/sparrow/mcp/data/prompts:/data/prompts prompt-manager:latest"
