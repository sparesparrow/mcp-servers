#!/bin/bash

# Exit on error
set -e

echo "Building fixed Python MCP server..."

# Build Docker image
docker build -t prompt-manager:latest -f Dockerfile.fixed .

# Create Docker volume if it doesn't exist
docker volume create mcp-prompt-manager-data

echo "Python MCP server built successfully."
echo "Testing server..."
echo "Press Ctrl+C after a few seconds to stop the test."

# Run the server
docker run --rm -i -v mcp-prompt-manager-data:/data -v /home/sparrow/mcp/data/prompts:/data/prompts prompt-manager:latest
