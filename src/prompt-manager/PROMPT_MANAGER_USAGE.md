# Using the Prompt Manager with Project Orchestration

This guide explains how to use the Prompt Manager MCP server with the project orchestration template to generate new project structures based on design patterns and templates.

## Setup

The prompt-manager MCP server has been configured in Cursor IDE and can be used to manage prompt templates. The server is running in a Docker container and stores templates in a persistent volume.

### Configuration Files

- **Docker Image**: `prompt-manager:latest`
- **Data Volume**: `mcp-prompt-manager-data:/data`
- **Prompts Directory**: `/home/sparrow/mcp/data/prompts`

## Project Orchestration Template

A special template called "project_orchestration" has been added to the prompt manager. This template orchestrates the creation of new projects based on design patterns and templates from the `/home/sparrow/projects/mcp-project-orchestrator` directory.

### Template Arguments

The project_orchestration template requires three arguments:

1. **project_templates**: JSON data with available project templates (automatically loaded from `/home/sparrow/projects/mcp-project-orchestrator/project_templates.json`)
2. **project_orchestration**: JSON data with project orchestration workflow (automatically loaded from `/home/sparrow/projects/mcp-project-orchestrator/project_orchestration.json`)
3. **project_idea**: The user's project idea description (user input)

## Using the Template in Cursor IDE

1. Restart Cursor IDE to load the updated configuration

2. In Cursor IDE, use the prompt-manager-py MCP server to add a template:
   ```
   add_template
   Add a new prompt template to the prompt manager
   From server: prompt-manager-py
   ```

3. When prompted, specify "project_orchestration" as the template name, and Cursor will use the pre-defined template.

4. When asked for the project idea, provide a detailed description of your project. For example:
   ```
   Create a web application for managing personal fitness routines, tracking workouts, and providing nutrition guidance based on fitness goals.
   ```

5. The template will:
   - Analyze your idea and identify suitable design patterns
   - Select a project template from the catalog
   - Create project documentation
   - Prepare a file structure
   - Define an implementation plan

## Example Usage

Here's an example conversation with Cursor using the project orchestration template:

**User**: 
```
Please use prompt-manager-py to create a project for a real-time chat application with end-to-end encryption and support for file sharing.
```

**Cursor**: 
*Cursor will analyze your request, select suitable design patterns (like WebSockets for real-time communication and Observer pattern for message distribution), choose an appropriate project template (like EventDrivenArchitectureProject), and generate a comprehensive project structure with documentation.*

## Troubleshooting

If you encounter issues with the prompt manager, try the following:

1. Check if the Docker container is running:
   ```bash
   docker ps | grep prompt-manager
   ```

2. Restart the Docker container:
   ```bash
   docker run --rm -i -v mcp-prompt-manager-data:/data -v /home/sparrow/mcp/data/prompts:/data/prompts prompt-manager:latest
   ```

3. Verify the template is correctly installed:
   ```bash
   ./test_project_orchestration_template.py
   ```

4. If needed, reinstall the template:
   ```bash
   ./add_project_orchestration_template.py
   ``` 