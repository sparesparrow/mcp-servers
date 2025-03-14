#!/bin/bash

# Exit on error
set -e

# Navigate to the script directory
cd "$(dirname "$0")"

echo "Building prompt-manager Docker image..."
docker build -t prompt-manager:latest -f Dockerfile .

echo "Creating Docker volume for persistence..."
docker volume create mcp-prompt-manager-data

echo "Testing the Docker image..."
docker run --rm -i --entrypoint python prompt-manager:latest -c "print('MCP Prompt Manager package ready')"

echo "Done! The image is now available for use in Claude Desktop."
echo "Please restart Claude Desktop to apply the changes."