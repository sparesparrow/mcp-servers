# MCP Prompt Manager

An MCP server that provides reusable prompt templates to help structure conversations with language models like Claude.

## Features

- **Pre-defined Prompt Templates** - Ready-to-use templates for common tasks:
  - Structured Analysis Framework
  - Comparative Analysis Framework
  - Step-by-Step Guide Template

- **Custom Prompt Templates** - Add your own templates via:
  - The `add_template` tool from within Claude
  - CLI commands for bulk operations
  - Importing templates from JSON files

- **Template Persistence** - Save and load templates between sessions:
  - Automatically persist templates to disk
  - Import/export templates for sharing
  - Load templates from directories

- **Configuration System** - Customize server behavior:
  - Configure via file, environment variables, or CLI arguments
  - Control logging levels
  - Set persistence options

- **CLI Interface** - Powerful command-line capabilities:
  - List, add, remove templates
  - Import/export templates
  - Server configuration

- **Documentation Resources** - Built-in documentation:
  - Access detailed template guides via resources API
  - View server configuration

## Installation

### Using pip

```bash
pip install mcp-prompt-manager
```

### From Source

```bash
git clone https://github.com/yourusername/mcp-prompt-manager.git
cd mcp-prompt-manager
pip install -e .
```

### Using Docker

```bash
# Build the image
docker build -t prompt-manager:latest .

# Run the container
docker run --rm -i -v prompt-manager-data:/data prompt-manager:latest
```

### Using Docker Compose

```bash
docker-compose up -d
```

## Usage

### Running the Server

To run the server with default settings:

```bash
python -m prompt_manager_server
```

With custom configuration:

```bash
python -m prompt_manager_server --config config.json
```

With command-line options:

```bash
python -m prompt_manager_server --template-dir ./templates --persistence --log-level DEBUG
```

### CLI Commands

List available templates:

```bash
python -m prompt_manager_server list
```

Add a new template:

```bash
python -m prompt_manager_server add mytemplte --file template.md --description "My custom template"
```

Export templates:

```bash
python -m prompt_manager_server export templates.json
python -m prompt_manager_server export templates.md --format markdown
```

Import templates:

```bash
python -m prompt_manager_server import templates.json
```

### Integrating with Claude Desktop

Add the following to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "prompt-manager": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-v", "prompt-manager-data:/data", "prompt-manager:latest"]
    }
  }
}
```

For a simplified setup, use the provided Makefile:

```bash
make claude-desktop-config
```

## Configuration

The server can be configured through:

1. **Configuration file** (JSON format)
2. **Environment variables**:
   - `MCP_PROMPT_MANAGER_NAME` - Server name
   - `MCP_PROMPT_MANAGER_LOG_LEVEL` - Logging level
   - `MCP_PROMPT_MANAGER_TEMPLATE_DIR` - Template directory
   - `MCP_PROMPT_MANAGER_PERSISTENCE` - Enable persistence
   - `MCP_PROMPT_MANAGER_PERSISTENCE_FILE` - Path to save templates
3. **Command-line arguments**

## Available Prompt Templates

### 1. Structured Analysis Framework

A template for comprehensive analysis of a single topic.

**Required Arguments:**
- `topic`: The subject to analyze

### 2. Comparative Analysis Framework

A template for comparing two items or concepts.

**Required Arguments:**
- `item1`: First item to compare
- `item2`: Second item to compare

### 3. Step-by-Step Guide Template

A template for creating detailed tutorials or guides.

**Required Arguments:**
- `title`: Title of the guide
- `overview`: Brief overview
- `steps`: The main steps

**Optional Arguments:**
- `prerequisites`: Knowledge prerequisites
- `tools_materials`: Required tools and materials
- `troubleshooting`: Common issues and solutions
- `resources`: Additional resources
- `summary`: Brief summary

## MCP Tools

### 1. add_template

Add a new prompt template to the prompt manager.

**Parameters:**
- `name` (string): Name of the new prompt template
- `description` (string): Description of what the template does
- `template` (string): The template text with placeholders in {placeholder} format
- `arguments` (array, optional): List of arguments for the template

### 2. remove_template

Remove a custom prompt template.

**Parameters:**
- `name` (string): Name of the template to remove

### 3. template_info

Get detailed information about a specific template.

**Parameters:**
- `name` (string): Name of the template to get info about

### 4. enable_persistence

Enable or disable template persistence.

**Parameters:**
- `enabled` (boolean): Whether to enable template persistence
- `path` (string, optional): Custom path for the persistence file

## MCP Resources

### 1. Prompt Templates Documentation

Access detailed documentation about available templates.

**URI:** `doc://prompt-templates/guide`

### 2. Server Configuration

View the current server configuration.

**URI:** `config://server`

## Using with Claude

1. Access the MCP menu in Claude (paperclip icon)
2. Select "Choose an integration" 
3. Select "prompt-manager"
4. Choose "Prompts" and select one of the available templates
5. Fill in the required arguments
6. Submit to generate a structured prompt

## Creating Custom Templates

Template files should use Markdown format with placeholders in curly braces:

```markdown
# My Template: {topic}

## Introduction
{introduction}

## Details
{details}
```

Each template can have associated metadata:

```json
{
  "my-template": {
    "description": "Description of the template",
    "arguments": [
      {
        "name": "topic",
        "description": "The main topic",
        "required": true
      },
      {
        "name": "introduction",
        "description": "Introductory paragraph",
        "required": true
      },
      {
        "name": "details",
        "description": "Detailed information",
        "required": false
      }
    ]
  }
}
```

## Development

Install development dependencies:

```bash
pip install -e ".[dev,test]"
```

Run tests:

```bash
pytest tests/
```

## License

MIT 