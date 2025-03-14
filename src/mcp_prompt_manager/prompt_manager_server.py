import os
import sys
import logging
import asyncio
from typing import Dict, List, Any, Optional
from mcp.server import Server, NotificationOptions
import mcp.types as types
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

# Import our modules
from .config import config
from .templates import template_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-prompt-manager")

# Handler functions - exposed for testing
async def handle_list_prompts() -> List[types.Prompt]:
    """Handle list_prompts request."""
    logger.debug("Handling list_prompts request")
    
    template_list = template_manager.list_templates()
    result = []
    
    for template in template_list:
        prompt = types.Prompt(
            name=template["name"],
            description=template["description"],
            arguments=[
                types.PromptArgument(
                    name=arg["name"],
                    description=arg["description"],
                    required=arg.get("required", True)
                )
                for arg in template["arguments"]
            ]
        )
        result.append(prompt)
    
    return result

async def handle_get_prompt(name: str, arguments: Dict[str, str] | None) -> types.GetPromptResult:
    """Handle get_prompt request."""
    logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
    
    template = template_manager.get_template(name)
    if not template:
        logger.error(f"Unknown prompt: {name}")
        raise ValueError(f"Unknown prompt: {name}")
    
    if not arguments:
        arguments = {}
        
    # Format template with provided arguments
    try:
        formatted_prompt = template.format(**arguments)
    except KeyError as e:
        missing_arg = str(e).strip("'")
        logger.error(f"Missing required argument: {missing_arg}")
        raise ValueError(f"Missing required argument: {missing_arg}")
    
    logger.debug(f"Generated prompt for {name}")
    metadata = template_manager.get_metadata(name) or {}
    
    return types.GetPromptResult(
        description=f"Template for {name}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=formatted_prompt.strip()),
            )
        ],
    )

async def handle_list_resources() -> List[types.Resource]:
    """Handle list_resources request."""
    logger.debug("Handling list_resources request")
    
    resources = [
        types.Resource(
            uri=AnyUrl("doc://prompt-templates/guide"),
            name="Prompt Templates Documentation",
            description="Documentation explaining the available prompt templates and how to use them",
            mimeType="text/markdown",
        )
    ]
    
    # Add resource for configuration if available
    if config.persistence and config.persistence_file:
        resources.append(
            types.Resource(
                uri=AnyUrl("config://server"),
                name="Server Configuration",
                description="Current server configuration",
                mimeType="application/json",
            )
        )
    
    return resources

async def handle_read_resource(uri: AnyUrl) -> str:
    """Handle read_resource request."""
    logger.debug(f"Handling read_resource request for URI: {uri}")
    
    scheme = uri.scheme
    path = str(uri).replace(f"{scheme}://", "")
    
    if scheme == "doc":
        if path == "prompt-templates/guide":
            # Generate documentation based on available templates
            templates = template_manager.list_templates()
            
            docs = """# Prompt Templates Guide

This MCP server provides reusable prompt templates that help structure conversations with Claude for specific purposes.

## Available Templates

"""
            # Add documentation for each template
            for idx, template in enumerate(templates, 1):
                docs += f"### {idx}. {template['name']}\n\n"
                docs += f"{template['description']}\n\n"
                
                # Required arguments
                required_args = [arg for arg in template["arguments"] if arg.get("required", True)]
                if required_args:
                    docs += "**Required Arguments:**\n"
                    for arg in required_args:
                        docs += f"- `{arg['name']}`: {arg['description']}\n"
                    docs += "\n"
                
                # Optional arguments
                optional_args = [arg for arg in template["arguments"] if not arg.get("required", True)]
                if optional_args:
                    docs += "**Optional Arguments:**\n"
                    for arg in optional_args:
                        docs += f"- `{arg['name']}`: {arg['description']}\n"
                    docs += "\n"
            
            docs += """
## How to Use
1. Access the MCP menu in Claude
2. Select "Choose an integration" 
3. Choose "Prompts" and select one of the available templates
4. Fill in the required arguments
5. Submit to generate a structured prompt

"""
            
            return docs
        else:
            logger.error(f"Unknown resource path: {path}")
            raise ValueError(f"Unknown resource path: {path}")
    elif scheme == "config":
        if path == "server":
            import json
            return json.dumps(config.as_dict(), indent=2)
        else:
            logger.error(f"Unknown config resource: {path}")
            raise ValueError(f"Unknown config resource: {path}")
    else:
        logger.error(f"Unsupported URI scheme: {scheme}")
        raise ValueError(f"Unsupported URI scheme: {scheme}")

async def handle_list_tools() -> List[types.Tool]:
    """Handle list_tools request."""
    logger.debug("Handling list_tools request")
    return [
        types.Tool(
            name="add_template",
            description="Add a new prompt template to the prompt manager",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the new prompt template"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what the prompt template does"
                    },
                    "template": {
                        "type": "string",
                        "description": "The prompt template with placeholders in {placeholder} format"
                    },
                    "arguments": {
                        "type": "array",
                        "description": "List of arguments for the template",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Argument name"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Argument description"
                                },
                                "required": {
                                    "type": "boolean",
                                    "description": "Whether the argument is required"
                                }
                            },
                            "required": ["name", "description"]
                        }
                    }
                },
                "required": ["name", "description", "template"]
            }
        ),
        types.Tool(
            name="remove_template",
            description="Remove a custom prompt template",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the template to remove"
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="template_info",
            description="Get detailed information about a specific template",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the template to get info about"
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="enable_persistence",
            description="Enable or disable template persistence",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether to enable template persistence"
                    },
                    "path": {
                        "type": "string",
                        "description": "Custom path for the persistence file (optional)"
                    }
                },
                "required": ["enabled"]
            }
        )
    ]

async def handle_execute_tool(name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Handle execute_tool request."""
    logger.debug(f"Handling execute_tool request for {name} with parameters {parameters}")
    
    if name == "add_template":
        template_name = parameters.get("name")
        template_text = parameters.get("template")
        description = parameters.get("description")
        arguments = parameters.get("arguments", [])
        
        if not template_name or not template_text:
            raise ValueError("Template name and content are required")
        
        # Create metadata if provided
        metadata = None
        if description or arguments:
            metadata = {
                "description": description or f"Custom template: {template_name}",
                "arguments": arguments
            }
        
        # Add the template to our manager
        template_manager.add_template(template_name, template_text, metadata)
        
        logger.info(f"Added new template: {template_name}")
        return {
            "status": "success",
            "message": f"Template '{template_name}' added successfully",
            "template_count": len(template_manager._templates)
        }
    
    elif name == "remove_template":
        template_name = parameters.get("name")
        if not template_name:
            raise ValueError("Template name is required")
        
        success = template_manager.remove_template(template_name)
        if success:
            logger.info(f"Removed template: {template_name}")
            return {
                "status": "success",
                "message": f"Template '{template_name}' removed successfully",
                "template_count": len(template_manager._templates)
            }
        else:
            logger.warning(f"Failed to remove template: {template_name}")
            return {
                "status": "error",
                "message": f"Could not remove template '{template_name}'. It may be a built-in template or does not exist.",
                "template_count": len(template_manager._templates)
            }
    
    elif name == "template_info":
        template_name = parameters.get("name")
        if not template_name:
            raise ValueError("Template name is required")
        
        template = template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        
        metadata = template_manager.get_metadata(template_name) or {}
        is_builtin = template_name in template_manager._templates
        
        return {
            "name": template_name,
            "description": metadata.get("description", ""),
            "arguments": metadata.get("arguments", []),
            "builtin": is_builtin,
            "content_preview": template[:200] + ("..." if len(template) > 200 else "")
        }
    
    elif name == "enable_persistence":
        enabled = parameters.get("enabled", False)
        path = parameters.get("path")
        
        config.set("persistence", enabled)
        if path:
            config.set("persistence_file", path)
        
        if enabled:
            # Save templates immediately
            template_manager.save_templates()
            return {
                "status": "success",
                "message": f"Persistence enabled. Templates will be saved to {config.persistence_file}",
                "persistence_enabled": True,
                "persistence_file": config.persistence_file
            }
        else:
            return {
                "status": "success",
                "message": "Persistence disabled. Templates will not be saved.",
                "persistence_enabled": False
            }
    
    else:
        logger.error(f"Unknown tool: {name}")
        raise ValueError(f"Unknown tool: {name}")

async def serve():
    """Run the prompt manager MCP server."""
    # Load configuration
    config.from_env()
    config.load()
    
    # Configure logging based on config
    logging.basicConfig(level=getattr(logging, config.log_level))
    logger.setLevel(getattr(logging, config.log_level))
    
    logger.info(f"Starting Prompt Manager MCP Server [{config.server_name}]")
    
    # Load templates
    template_manager.load_templates()
    logger.info(f"Loaded {len(template_manager._templates)} templates")
    
    # Create server instance
    server = Server(config.server_name)

    # Register handlers
    server.list_prompts()(handle_list_prompts)
    server.get_prompt()(handle_get_prompt)
    server.list_resources()(handle_list_resources)
    server.read_resource()(handle_read_resource)
    server.list_tools()(handle_list_tools)
    server.execute_tool()(handle_execute_tool)

    # Run the server with appropriate error handling
    try:
        options = InitializationOptions()
        await server.stdio_serve(options)
    except Exception as e:
        logger.error(f"Error running server: {e}")
        raise

def main():
    """Entry point for the command-line script."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server shutdown due to keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 