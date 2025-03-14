# MCP Mermaid Diagram Server

This MCP server provides tools for generating, analyzing, and modifying [Mermaid](https://mermaid.js.org/) diagrams using natural language instructions. Mermaid is a markdown-based diagramming and charting tool that renders text definitions into diagrams.

## Features

- **Generate Mermaid diagrams** from natural language descriptions
- **Analyze existing diagrams** for clarity, structure, and improvement opportunities
- **Modify diagrams** based on natural language instructions
- **Apply beautiful styling** with preset themes (default, dark, pastel, vibrant)
- **Create custom themes** to match your brand or preferences
- **Generate SVG previews** of diagrams for embedding in documents
- **Validate diagrams** to ensure they follow proper Mermaid syntax

## Installation

### Using pip

```bash
pip install mcp-mermaid-server
```

### Using uvx

```bash
uvx mcp-server-mermaid
```

### From source

```bash
git clone https://github.com/sparesparrow/mcp-servers.git
cd mcp-servers
pip install -e .
```

## Usage

### Running the server

You can run the server directly:

```bash
python -m src.mermaid.mermaid_server
```

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)
- `CACHE_TTL`: Cache time-to-live in seconds (default: 3600)
- `CALLS_PER_MINUTE`: Rate limit for API calls (default: 25)
- `DEFAULT_THEME`: Default color theme (default: "default")
- `CUSTOM_THEMES_PATH`: Path to JSON file containing custom themes (default: "~/.mermaid_themes.json")

## Tools

### generate_diagram

Generates a Mermaid diagram from a text description with optional styling.

```json
{
  "tool": "generate_diagram",
  "params": {
    "query": "Create a flowchart showing user authentication with registration, login, and logout steps",
    "theme": "pastel"
  }
}
```

Available themes: `default`, `dark`, `pastel`, `vibrant`, and any custom themes you've created

### analyze_diagram

Analyzes a Mermaid diagram and provides insights.

```json
{
  "tool": "analyze_diagram",
  "params": {
    "diagram": "graph TD\nA[Start] --> B[Process]\nB --> C[End]"
  }
}
```

### modify_diagram

Modifies an existing Mermaid diagram based on instructions.

```json
{
  "tool": "modify_diagram",
  "params": {
    "diagram": "graph TD\nA[Start] --> B[Process]\nB --> C[End]",
    "modification": "Add an alternative path from Process to a new node called Alternative",
    "theme": "vibrant",
    "keep_styling": false
  }
}
```

Parameters:
- `diagram`: The original Mermaid diagram code
- `modification`: Description of changes to make
- `theme`: Optional color theme to apply
- `keep_styling`: Whether to preserve existing styling (default: true)

### preview_diagram

Generates an SVG preview of a Mermaid diagram.

```json
{
  "tool": "preview_diagram",
  "params": {
    "diagram": "graph TD\nA[Start] --> B[Process]\nB --> C[End]",
    "theme": "dark"
  }
}
```

Returns a base64-encoded SVG string that can be embedded in HTML or Markdown:

```html
<img src="data:image/svg+xml;base64,BASE64_ENCODED_SVG_HERE" alt="Mermaid Diagram" />
```

### validate_diagram

Validates Mermaid diagram syntax.

```json
{
  "tool": "validate_diagram",
  "params": {
    "diagram": "graph TD\nA[Start] --> B[Process]\nB --> C[End]"
  }
}
```

### add_custom_theme

Adds a new custom color theme.

```json
{
  "tool": "add_custom_theme",
  "params": {
    "name": "my-brand-theme",
    "colors": {
      "node_fill": "#f5f5f5",
      "node_border": "#999999",
      "node_text": "#444444",
      "edge": "#888888",
      "highlight": "#ff9900",
      "success": "#99cc99",
      "warning": "#ffdd99",
      "error": "#ff9999"
    }
  }
}
```

Required color keys:
- `node_fill`: Background color for nodes
- `node_border`: Border color for nodes
- `node_text`: Text color for nodes
- `edge`: Color for connections between nodes
- `highlight`: Color for emphasized elements
- `success`: Color for success states
- `warning`: Color for warning states
- `error`: Color for error states

All colors must be valid hex codes (#RRGGBB or #RGB).

### remove_custom_theme

Removes a custom color theme.

```json
{
  "tool": "remove_custom_theme",
  "params": {
    "name": "my-brand-theme"
  }
}
```

Note: Built-in themes (default, dark, pastel, vibrant) cannot be removed.

### get_theme_info

Gets information about available color themes.

```json
{
  "tool": "get_theme_info",
  "params": {
    "theme_name": "dark"
  }
}
```

### clear_cache

Clears the server's response cache.

```json
{
  "tool": "clear_cache",
  "params": {}
}
```

### get_status

Gets the current server status.

```json
{
  "tool": "get_status",
  "params": {}
}
```

## Color Themes

The Mermaid server supports several built-in color themes and allows you to create custom themes:

### Built-in Themes

- **Default Theme**: A clean, professional theme with light backgrounds and subtle colors.
- **Dark Theme**: Dark backgrounds with high-contrast text for low-light environments.
- **Pastel Theme**: Soft, pastel colors for a gentle visual experience.
- **Vibrant Theme**: Bright, energetic colors for emphasis and visual impact.

### Custom Themes

Custom themes are stored in a JSON file (default location: `~/.mermaid_themes.json`) and can be created or removed using the `add_custom_theme` and `remove_custom_theme` tools. 

Example custom theme:
```json
{
  "my-brand-theme": {
    "node_fill": "#f5f5f5",
    "node_border": "#999999",
    "node_text": "#444444",
    "edge": "#888888",
    "highlight": "#ff9900",
    "success": "#99cc99",
    "warning": "#ffdd99",
    "error": "#ff9999"
  }
}
```

## Integration with Claude Desktop

To use this server with Claude Desktop, add the following to your `.claude-config.json` file:

```json
{
  "mcpServers": {
    "mermaid-generator": {
      "command": "python",
      "args": ["-m", "src.mermaid.mermaid_server"],
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "DEFAULT_THEME": "pastel",
        "CUSTOM_THEMES_PATH": "${HOME}/.mermaid_themes.json"
      }
    }
  }
}
```

Alternatively, using Docker:

```json
{
  "mcpServers": {
    "mermaid-generator": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-mermaid-server"],
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "DEFAULT_THEME": "pastel"
      },
      "volumes": [
        "${HOME}/.mermaid_themes.json:/root/.mermaid_themes.json"
      ]
    }
  }
}
```

## Example Conversations

### Generating a Diagram

**User**: "Create a sequence diagram showing how a user interacts with a login system"

**Claude**: "I'll create a sequence diagram for a login system with a dark theme. Let me use the Mermaid diagram generator."

*Claude uses the generate_diagram tool with the 'dark' theme*

**Claude**: "Here's a sequence diagram showing a user's interaction with a login system:

```mermaid
%%{init: {
    'theme': 'base',
    'themeVariables': {
        'primaryColor': '#ff9933',
        'primaryTextColor': '#fff',
        'primaryBorderColor': '#aaaaaa',
        'lineColor': '#888888',
        'secondaryColor': '#2d2d2d',
        'tertiaryColor': '#2d2d2d'
    }
} }%%
sequenceDiagram
    actor User
    participant UI as Login UI
    participant Auth as Authentication Service
    participant DB as User Database
    
    User->>UI: Enter credentials
    UI->>Auth: Submit credentials
    Auth->>DB: Validate credentials
    DB-->>Auth: Return validation result
    
    alt Valid credentials
        Auth-->>UI: Authentication successful
        UI-->>User: Show dashboard
    else Invalid credentials
        Auth-->>UI: Authentication failed
        UI-->>User: Show error message
    end
```

This diagram shows:
1. The user entering credentials in the UI
2. The UI submitting those credentials to the authentication service
3. The authentication service validating against the user database
4. Different paths for successful vs. failed authentication"

### Creating a Custom Theme

**User**: "I want to create a custom theme for my brand with blue as the primary color"

**Claude**: "I'll help you create a custom theme for your brand. Let me use the Mermaid tools to do that."

*Claude uses the add_custom_theme tool*

**Claude**: "I've created a custom theme called 'brand-blue' with your brand's color scheme. You can now use this theme when generating diagrams by specifying `theme: 'brand-blue'`. Here's a preview of what a diagram would look like with your new theme:

<img src='data:image/svg+xml;base64,..." alt="Brand-themed diagram" />

You can use this theme for all your future diagrams, and it will be saved for future sessions as well."

## Testing

Run the tests with pytest:

```bash
pytest tests/test_mermaid_server.py
```

## Docker

Build and run the Docker container:

```bash
docker build -t mcp-mermaid-server -f Dockerfile.mermaid .
docker run -i --rm \
  -e ANTHROPIC_API_KEY=your_api_key \
  -e DEFAULT_THEME=vibrant \
  -v ~/.mermaid_themes.json:/root/.mermaid_themes.json \
  mcp-mermaid-server
```

## License

MIT 