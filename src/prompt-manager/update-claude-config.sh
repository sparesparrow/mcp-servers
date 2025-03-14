#!/bin/bash

# Exit on error
set -e

# Config file path
CONFIG_FILE="/home/sparrow/.config/Claude/claude_desktop_config.json"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Claude Desktop config file does not exist: $CONFIG_FILE"
    exit 1
fi

# Backup the existing config
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d%H%M%S)"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "Created backup of existing config: $BACKUP_FILE"

# Update the prompt-manager configuration
TMP_FILE=$(mktemp)
cat "$CONFIG_FILE" | jq '.mcpServers."prompt-manager" = {
  "command": "docker",
  "args": [
    "run",
    "--rm",
    "-i",
    "-v",
    "mcp-prompt-manager-data:/data",
    "prompt-manager:latest"
  ]
}' > "$TMP_FILE"

# Check if jq succeeded
if [ $? -eq 0 ]; then
    cp "$TMP_FILE" "$CONFIG_FILE"
    echo "Successfully updated Claude Desktop configuration"
else
    echo "Failed to update configuration. Please update manually."
    echo "Your original configuration is preserved."
fi

rm "$TMP_FILE"
