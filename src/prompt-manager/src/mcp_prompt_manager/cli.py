"""Command-line interface for MCP Prompt Manager."""
import argparse
import sys
import os
import logging
import asyncio
from typing import Dict, Any, Optional, List

from .config import config
from .templates import template_manager
from .prompt_manager_server import serve

logger = logging.getLogger("mcp-prompt-manager.cli")

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP Prompt Manager - An MCP server for managing prompt templates"
    )
    
    # Server configuration
    parser.add_argument(
        "--name", 
        dest="server_name",
        default=None,
        help="Server name (default: prompt-manager)"
    )
    
    parser.add_argument(
        "--log-level", 
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Logging level (default: INFO)"
    )
    
    # Template management
    parser.add_argument(
        "--template-dir", 
        dest="template_dir",
        default=None,
        help="Directory containing template files"
    )
    
    parser.add_argument(
        "--persistence", 
        dest="persistence",
        action="store_true",
        default=None,
        help="Enable template persistence"
    )
    
    parser.add_argument(
        "--no-persistence", 
        dest="persistence",
        action="store_false",
        help="Disable template persistence"
    )
    
    parser.add_argument(
        "--persistence-file", 
        dest="persistence_file",
        default=None,
        help="File to store persisted templates"
    )
    
    # Config file
    parser.add_argument(
        "--config", 
        dest="config_file",
        default=None,
        help="Path to configuration file"
    )
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List templates command
    list_parser = subparsers.add_parser("list", help="List available templates")
    
    # Add template command
    add_parser = subparsers.add_parser("add", help="Add a new template")
    add_parser.add_argument("name", help="Template name")
    add_parser.add_argument("--file", help="File containing template content")
    add_parser.add_argument("--description", help="Template description")
    
    # Remove template command
    remove_parser = subparsers.add_parser("remove", help="Remove a template")
    remove_parser.add_argument("name", help="Template name")
    
    # Export templates command
    export_parser = subparsers.add_parser("export", help="Export templates to a file")
    export_parser.add_argument("file", help="Output file path")
    export_parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    
    # Import templates command
    import_parser = subparsers.add_parser("import", help="Import templates from a file")
    import_parser.add_argument("file", help="Input file path")
    
    return parser.parse_args()

def update_config_from_args(args: argparse.Namespace) -> None:
    """Update configuration from command-line arguments."""
    # Update config with CLI arguments
    if args.server_name:
        config.set("server_name", args.server_name)
    
    if args.log_level:
        config.set("log_level", args.log_level)
    
    if args.template_dir:
        config.set("template_dir", args.template_dir)
    
    if args.persistence is not None:
        config.set("persistence", args.persistence)
    
    if args.persistence_file:
        config.set("persistence_file", args.persistence_file)

def list_templates() -> None:
    """List all available templates."""
    templates = template_manager.list_templates()
    
    if not templates:
        print("No templates available.")
        return
    
    print(f"Available templates ({len(templates)}):")
    for template in templates:
        builtin = " (built-in)" if template.get("builtin", False) else ""
        print(f"- {template['name']}{builtin}: {template['description']}")
        
        # Print arguments
        if template.get("arguments"):
            print("  Arguments:")
            for arg in template["arguments"]:
                required = " (required)" if arg.get("required", True) else " (optional)"
                print(f"  - {arg['name']}{required}: {arg['description']}")
        
        print()

def add_template(name: str, file: Optional[str] = None, description: Optional[str] = None) -> None:
    """Add a new template."""
    if file:
        try:
            with open(file, 'r') as f:
                template_content = f.read()
        except Exception as e:
            print(f"Error reading template file: {e}")
            sys.exit(1)
    else:
        print("Enter template content (Ctrl+D to finish):")
        template_content = sys.stdin.read()
    
    metadata = None
    if description:
        metadata = {
            "description": description,
            # Extract placeholders from content
            "arguments": []
        }
        
        # Extract placeholder names from template content
        import re
        placeholders = re.findall(r'{([^{}]*)}', template_content)
        metadata["arguments"] = [
            {
                "name": placeholder,
                "description": f"Value for {placeholder}",
                "required": True
            }
            for placeholder in set(placeholders)
        ]
    
    template_manager.add_template(name, template_content, metadata)
    print(f"Template '{name}' added successfully.")

def remove_template(name: str) -> None:
    """Remove a template."""
    success = template_manager.remove_template(name)
    if success:
        print(f"Template '{name}' removed successfully.")
    else:
        print(f"Failed to remove template '{name}'. It may be a built-in template or does not exist.")
        sys.exit(1)

def export_templates(file: str, format: str = "json") -> None:
    """Export templates to a file."""
    try:
        if format == "json":
            import json
            
            export_data = {
                "templates": template_manager._templates,
                "metadata": template_manager._metadata
            }
            
            with open(file, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        elif format == "markdown":
            templates = template_manager.list_templates()
            
            with open(file, 'w') as f:
                f.write("# MCP Prompt Manager Templates\n\n")
                
                for template in templates:
                    f.write(f"## {template['name']}\n\n")
                    f.write(f"{template['description']}\n\n")
                    
                    # Arguments
                    if template.get("arguments"):
                        f.write("### Arguments\n\n")
                        for arg in template["arguments"]:
                            required = " (required)" if arg.get("required", True) else " (optional)"
                            f.write(f"- **{arg['name']}**{required}: {arg['description']}\n")
                        f.write("\n")
                    
                    # Template content
                    f.write("### Template Content\n\n")
                    f.write("```markdown\n")
                    template_content = template_manager.get_template(template["name"]) or ""
                    f.write(template_content)
                    f.write("\n```\n\n")
        
        print(f"Templates exported to {file} in {format} format.")
    
    except Exception as e:
        print(f"Error exporting templates: {e}")
        sys.exit(1)

def import_templates(file: str) -> None:
    """Import templates from a file."""
    try:
        with open(file, 'r') as f:
            import json
            data = json.load(f)
        
        templates = data.get("templates", {})
        metadata = data.get("metadata", {})
        
        count = 0
        for name, content in templates.items():
            template_metadata = metadata.get(name)
            template_manager.add_template(name, content, template_metadata)
            count += 1
        
        print(f"Imported {count} templates successfully.")
    
    except Exception as e:
        print(f"Error importing templates: {e}")
        sys.exit(1)

def main() -> None:
    """Main entry point for the CLI."""
    args = parse_arguments()
    
    # Load configuration
    if args.config_file:
        config.load(args.config_file)
    else:
        config.from_env()
        config.load()
    
    # Update config with CLI arguments
    update_config_from_args(args)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load templates
    template_manager.load_templates()
    
    # Handle commands
    if args.command == "list":
        list_templates()
    elif args.command == "add":
        add_template(args.name, args.file, args.description)
    elif args.command == "remove":
        remove_template(args.name)
    elif args.command == "export":
        export_templates(args.file, args.format)
    elif args.command == "import":
        import_templates(args.file)
    else:
        # Run the server
        try:
            asyncio.run(serve())
        except KeyboardInterrupt:
            logger.info("Server shutdown due to keyboard interrupt")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main() 