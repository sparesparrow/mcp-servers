#!/bin/bash

# Exit on error
set -e

# Navigate to the script directory
cd "$(dirname "$0")"

# Default values
CONTAINER_ENGINE="docker"
TAG="latest"
PUSH=false
REGISTRY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --podman)
      CONTAINER_ENGINE="podman"
      shift
      ;;
    --tag)
      TAG="$2"
      shift 2
      ;;
    --push)
      PUSH=true
      shift
      ;;
    --registry)
      REGISTRY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Determine image name
IMAGE_NAME="prompt-manager"
if [ -n "$REGISTRY" ]; then
  IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"
fi
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

echo "Building container image with $CONTAINER_ENGINE: $FULL_IMAGE_NAME"

# Build the container
$CONTAINER_ENGINE build -t "$FULL_IMAGE_NAME" -f Dockerfile.production .

# Create volume if it doesn't exist
if ! $CONTAINER_ENGINE volume inspect mcp-prompt-manager-data &>/dev/null; then
  echo "Creating volume: mcp-prompt-manager-data"
  $CONTAINER_ENGINE volume create mcp-prompt-manager-data
fi

echo "Testing the container..."
$CONTAINER_ENGINE run --rm -i --entrypoint python "$FULL_IMAGE_NAME" -c "import mcp_prompt_manager; print('MCP Prompt Manager successfully loaded')"

# Push to registry if requested
if [ "$PUSH" = true ] && [ -n "$REGISTRY" ]; then
  echo "Pushing image to registry: $FULL_IMAGE_NAME"
  $CONTAINER_ENGINE push "$FULL_IMAGE_NAME"
fi

echo ""
echo "Container build complete: $FULL_IMAGE_NAME"
echo ""
echo "To use with Claude Desktop, add this to your configuration:"
echo ""
echo "\"prompt-manager\": {"
echo "  \"command\": \"$CONTAINER_ENGINE\","
echo "  \"args\": ["
echo "    \"run\","
echo "    \"--rm\","
echo "    \"-i\","
echo "    \"-v\","
echo "    \"mcp-prompt-manager-data:/data\","
echo "    \"-v\","
echo "    \"/home/sparrow/mcp/data/prompts:/data/prompts\","
echo "    \"$FULL_IMAGE_NAME\""
echo "  ]"
echo "}"
