# MCP Prompt Manager Setup Guide

This guide will help you set up the MCP Prompt Manager server for Claude Desktop.

## Overview

The MCP Prompt Manager is a server that provides reusable prompt templates to Claude. It allows you to:

- Use pre-defined templates for common tasks
- Create and save your own templates
- Share templates with others
- Access templates through Claude Desktop

## Prerequisites

- Docker installed
- Claude Desktop installed
- Basic command line knowledge

## Installation Options

### Option 1: Docker Installation (Recommended)

1. Navigate to the prompt manager directory:
   ```bash
   cd /home/sparrow/projects/mcp-servers/src/prompt-manager
   ```

2. Make the build script executable and run it:
   ```bash
   chmod +x build-and-install.sh
   ./build-and-install.sh
   ```

3. Update your Claude Desktop configuration:
   ```bash
   chmod +x update-claude-config.sh
   ./update-claude-config.sh
   ```

4. Restart Claude Desktop

### Option 2: Local Python Installation

1. Navigate to the prompt manager directory:
   ```bash
   cd /home/sparrow/projects/mcp-servers/src/prompt-manager
   ```

2. Install the package in development mode:
   ```bash
   pip install -e .
   ```

3. Update your Claude Desktop configuration to use the local installation:
   ```json
   "prompt-manager": {
     "command": "python",
     "args": [
       "-m",
       "mcp_prompt_manager"
     ],
     "env": {
       "MCP_PROMPT_MANAGER_PERSISTENCE": "true",
       "MCP_PROMPT_MANAGER_PERSISTENCE_FILE": "/home/sparrow/mcp/data/prompt-templates.json"
     }
   }
   ```

### Option 3: TypeScript Implementation

For the TypeScript implementation, follow these steps:

1. Navigate to the TypeScript project:
   ```bash
   cd /home/sparrow/projects/mcp-prompts
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the project:
   ```bash
   npm run build
   ```

4. Update your Claude Desktop configuration:
   ```json
   "prompt-manager": {
     "command": "node",
     "args": [
       "/home/sparrow/projects/mcp-prompts/build/index.js"
     ],
     "env": {
       "STORAGE_TYPE": "file",
       "PROMPTS_DIR": "/home/sparrow/mcp/data/prompts"
     }
   }
   ```

## Troubleshooting

If you encounter issues:

1. Check the Claude Desktop logs:
   ```bash
   cat /home/sparrow/.config/Claude/logs/mcp-server-prompt-manager.log
   ```

2. Try running the server manually to see any errors:
   ```bash
   # For Python implementation
   python -m mcp_prompt_manager
   
   # For TypeScript implementation
   node /home/sparrow/projects/mcp-prompts/build/index.js
   ```

3. Verify the Docker container is running:
   ```bash
   docker ps | grep prompt-manager
   ```

## Using Templates

After installation, you can access templates in Claude Desktop:

1. Click on the MCP icon in Claude Desktop
2. Select "Prompts" 
3. Choose a template
4. Fill in the required parameters
5. Submit to use the template

## Adding Custom Templates

You can add custom templates through the MCP tools by asking Claude:

"Can you add a new template called 'my-template' using the prompt-manager?"

Claude will guide you through the process using the `add_template` tool.

## Advanced Configuration

For advanced configuration options, see:
- `/home/sparrow/projects/mcp-servers/src/prompt-manager/src/mcp_prompt_manager/config.py`
- Docker environment variables in the `docker-compose.yml` file