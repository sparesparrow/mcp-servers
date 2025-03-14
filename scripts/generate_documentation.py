#!/usr/bin/env python
"""
MCP Architecture Documentation Generator

This script generates comprehensive architectural documentation for the MCP servers and router.
"""

import os
import sys
import argparse
import logging
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import datetime
import subprocess
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('doc_generator')

# Add src directory to path to import modules
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Import diagram generator
from common.diagram_generator import DiagramGenerator, create_standard_diagram_generator

# Import configuration and capabilities
from common.server_configs import (
    ServerConfig,
    OrchestratorConfig,
    ProjectOrchestratorConfig,
    PromptsServerConfig,
    MemoryServerConfig,
    FilesystemServerConfig
)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate MCP architecture documentation")
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(project_root / "docs" / "architecture.md"),
        help="Output file path for the documentation"
    )
    
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["markdown", "html", "pdf"],
        default="markdown",
        help="Output format (markdown, html, or pdf)"
    )
    
    parser.add_argument(
        "--discover",
        "-d",
        action="store_true",
        help="Automatically discover MCP servers in the project"
    )
    
    parser.add_argument(
        "--router-url",
        type=str,
        default="http://localhost:3000",
        help="URL of the MCP Router for querying live server information"
    )
    
    parser.add_argument(
        "--live",
        "-l",
        action="store_true",
        help="Query live server information from the MCP Router"
    )
    
    parser.add_argument(
        "--include-router",
        "-r",
        action="store_true",
        help="Include MCP Router documentation"
    )
    
    parser.add_argument(
        "--include-code",
        "-c",
        action="store_true",
        help="Include relevant code snippets in the documentation"
    )
    
    parser.add_argument(
        "--include-examples",
        "-e",
        action="store_true",
        help="Include usage examples in the documentation"
    )
    
    parser.add_argument(
        "--theme",
        "-t",
        type=str,
        choices=["default", "github", "minimal", "technical"],
        default="default",
        help="Documentation theme (for HTML output)"
    )
    
    return parser.parse_args()

def discover_servers() -> List[Dict[str, Any]]:
    """
    Automatically discover MCP servers in the project.
    
    Returns:
        List of server information dictionaries
    """
    logger.info("Discovering MCP servers...")
    servers = []
    
    # Directories to search
    search_dirs = [
        src_dir,
        Path("/home/sparrow/projects/mcp-project-orchestrator/src"),
        Path("/home/sparrow/projects/mcp-prompts/src")
    ]
    
    # File patterns to look for
    patterns = [
        "*_server.py",
        "*server.py",
        "enhanced_*.py"
    ]
    
    # Search for server files
    for directory in search_dirs:
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            continue
        
        for pattern in patterns:
            for file_path in directory.glob(f"**/{pattern}"):
                logger.info(f"Found potential server file: {file_path}")
                
                # Extract server information
                server_info = extract_server_info(file_path)
                if server_info:
                    servers.append(server_info)
    
    logger.info(f"Discovered {len(servers)} MCP servers")
    return servers

def extract_server_info(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Extract server information from a server file.
    
    Args:
        file_path: Path to the server file
        
    Returns:
        Server information dictionary or None if not a valid server
    """
    try:
        # Read file content
        content = file_path.read_text()
        
        # Check if it's an MCP server
        if "FastMCP" not in content and "McpServer" not in content:
            return None
        
        # Extract server ID
        server_id_match = re.search(r'server_id\s*=\s*["\']([^"\']+)["\']', content)
        server_id = server_id_match.group(1) if server_id_match else file_path.stem.replace("_", "-")
        
        # Extract server type
        server_type = "unknown"
        if "OrchestratorConfig" in content or "orchestrator" in file_path.stem.lower():
            server_type = "orchestrator"
        elif "ProjectOrchestratorConfig" in content or "project-orchestrator" in file_path.stem.lower():
            server_type = "project-orchestrator"
        elif "PromptsServerConfig" in content or "prompts" in file_path.stem.lower():
            server_type = "prompts"
        elif "MemoryServerConfig" in content or "memory" in file_path.stem.lower():
            server_type = "memory"
        elif "FilesystemServerConfig" in content or "filesystem" in file_path.stem.lower():
            server_type = "filesystem"
        
        # Extract capabilities
        capabilities = []
        capability_match = re.search(r'capabilities\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if capability_match:
            capability_str = capability_match.group(1)
            capability_items = re.findall(r'["\']([^"\']+)["\']', capability_str)
            capabilities = capability_items
        
        # Use default capabilities if none found
        if not capabilities:
            if server_type == "orchestrator":
                capabilities = ["code-analysis", "code-visualization", "documentation-generation", "diagram-generation"]
            elif server_type == "project-orchestrator":
                capabilities = ["project-orchestration", "project-template-application", "project-structure-generation", "mermaid-diagram-generation", "design-pattern-analysis"]
            elif server_type == "prompts":
                capabilities = ["prompt-management", "prompt-template-application", "prompt-versioning", "prompt-import-export"]
            elif server_type == "memory":
                capabilities = ["knowledge-graph-management", "entity-storage", "relation-management", "graph-querying"]
            elif server_type == "filesystem":
                capabilities = ["file-read", "file-write", "directory-listing", "file-search"]
        
        return {
            "id": server_id,
            "type": server_type,
            "path": str(file_path),
            "capabilities": capabilities
        }
    except Exception as e:
        logger.warning(f"Error extracting server info from {file_path}: {str(e)}")
        return None

def get_live_server_info(router_url: str) -> List[Dict[str, Any]]:
    """
    Query live server information from the MCP Router.
    
    Args:
        router_url: URL of the MCP Router
        
    Returns:
        List of server information dictionaries
    """
    import requests
    
    logger.info(f"Querying live server information from {router_url}...")
    
    try:
        # Get list of servers
        response = requests.get(f"{router_url}/api/mcp/capabilities/servers", timeout=5)
        
        if response.status_code != 200:
            logger.warning(f"Failed to get server list: HTTP {response.status_code}")
            return []
        
        data = response.json()
        server_list = data.get("servers", [])
        
        # Get detailed information for each server
        servers = []
        for server_info in server_list:
            server_id = server_info.get("id")
            
            # Get detailed server info
            try:
                detail_response = requests.get(f"{router_url}/api/mcp/capabilities/servers/{server_id}", timeout=5)
                
                if detail_response.status_code == 200:
                    server_detail = detail_response.json().get("server", {})
                    
                    # Extract relevant information
                    server = {
                        "id": server_id,
                        "type": server_detail.get("type", "unknown"),
                        "capabilities": server_detail.get("capabilities", []),
                        "health": server_detail.get("health", {}).get("status", "unknown"),
                        "isAvailable": server_detail.get("isAvailable", False),
                        "metadata": server_detail.get("metadata", {})
                    }
                    
                    servers.append(server)
                else:
                    logger.warning(f"Failed to get server details for {server_id}: HTTP {detail_response.status_code}")
                    
                    # Use basic info
                    servers.append({
                        "id": server_id,
                        "type": "unknown",
                        "capabilities": server_info.get("capabilities", [])
                    })
            except Exception as e:
                logger.warning(f"Error getting server details for {server_id}: {str(e)}")
        
        logger.info(f"Found {len(servers)} live servers")
        return servers
    except Exception as e:
        logger.warning(f"Error querying live server information: {str(e)}")
        return []

def extract_code_snippets(server_info: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract relevant code snippets from a server file.
    
    Args:
        server_info: Server information dictionary
        
    Returns:
        Dictionary of code snippet names to code snippets
    """
    snippets = {}
    
    try:
        file_path = server_info.get("path")
        if not file_path:
            return snippets
        
        # Read file content
        content = Path(file_path).read_text()
        
        # Extract server initialization
        init_match = re.search(r'(def\s+__init__.*?)def\s+', content, re.DOTALL)
        if init_match:
            snippets["initialization"] = init_match.group(1).strip()
        
        # Extract tool implementations
        tool_matches = re.findall(r'(@mcp\.tool\(\).*?def\s+\w+.*?)(?=@|def\s+\w+\s*\((?!\s*self))', content, re.DOTALL)
        if tool_matches:
            snippets["tools"] = "\n\n".join(match.strip() for match in tool_matches)
        
        # Extract resource implementations
        resource_matches = re.findall(r'(@mcp\.resource\(\S+\).*?def\s+\w+.*?)(?=@|def\s+\w+\s*\((?!\s*self))', content, re.DOTALL)
        if resource_matches:
            snippets["resources"] = "\n\n".join(match.strip() for match in resource_matches)
        
        # Extract router integration
        if "router_integration" in content:
            router_match = re.search(r'(class\s+RouterIntegration.*?)(?=class\s+|$)', content, re.DOTALL)
            if router_match:
                snippets["router_integration"] = router_match.group(1).strip()
    except Exception as e:
        logger.warning(f"Error extracting code snippets: {str(e)}")
    
    return snippets

def create_usage_examples(server_info: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Create usage examples for a server.
    
    Args:
        server_info: Server information dictionary
        
    Returns:
        List of usage example dictionaries
    """
    examples = []
    
    # Create examples based on server type
    server_type = server_info.get("type", "unknown")
    
    if server_type == "orchestrator":
        examples.append({
            "title": "Analyzing and Visualizing Code",
            "description": "This example demonstrates how to analyze code and generate a visualization.",
            "code": """
# Import required libraries
import requests

# Define the code to analyze
code = '''
class UserManager:
    def __init__(self, database):
        self.database = database
        
    def create_user(self, username, email, password):
        # Create a new user in the database
        return self.database.insert('users', {
            'username': username,
            'email': email,
            'password': password
        })
        
    def get_user(self, user_id):
        # Get user details from the database
        return self.database.find_one('users', {'id': user_id})
'''

# Call the analyze_and_visualize tool
response = requests.post(
    "http://localhost:8000/tools/analyze_and_visualize",
    json={
        "code": code
    }
)

# Check response
if response.status_code == 200:
    result = response.json()
    print("Analysis:", result["analysis"])
    print("Diagram:", result["diagram"])
else:
    print("Error:", response.text)
"""
        })
    
    elif server_type == "project-orchestrator":
        examples.append({
            "title": "Creating a New Project from an Idea",
            "description": "This example demonstrates how to create a new project from a high-level idea.",
            "code": """
# Import required libraries
import requests

# Define the project idea
idea = "Create a microservices application for order management with event-driven architecture"

# Call the orchestrate_new_project tool
response = requests.post(
    "http://localhost:8000/tools/orchestrate_new_project",
    json={
        "user_idea": idea
    }
)

# Check response
if response.status_code == 200:
    result = response.json()
    print("Project Created:", result)
else:
    print("Error:", response.text)
"""
        })
    
    elif server_type == "prompts":
        examples.append({
            "title": "Managing and Applying Prompt Templates",
            "description": "This example demonstrates how to manage and apply prompt templates.",
            "code": """
# Import required libraries
import requests

# Create a new prompt template
template = {
    "name": "project_analysis",
    "content": "Analyze the following project description and identify key components, architecture patterns, and potential challenges:\\n\\n{{project_description}}",
    "description": "Template for analyzing project descriptions",
    "variables": ["project_description"]
}

# Add the prompt template
response = requests.post(
    "http://localhost:8000/tools/add_prompt",
    json={
        "prompt": template
    }
)

# Check response
if response.status_code == 200:
    prompt_id = response.json()["id"]
    print("Created prompt with ID:", prompt_id)
    
    # Apply the template with variables
    apply_response = requests.post(
        "http://localhost:8000/tools/apply_template",
        json={
            "id": prompt_id,
            "variables": {
                "project_description": "A distributed system for processing financial transactions with high throughput and low latency requirements."
            }
        }
    )
    
    if apply_response.status_code == 200:
        result = apply_response.json()
        print("Applied Template:", result)
    else:
        print("Error applying template:", apply_response.text)
else:
    print("Error creating prompt:", response.text)
"""
        })
    
    return examples

def generate_markdown_documentation(args: argparse.Namespace) -> str:
    """
    Generate markdown documentation for MCP servers.
    
    Args:
        args: Command line arguments
        
    Returns:
        Markdown documentation
    """
    # Create diagram generator
    generator = DiagramGenerator()
    
    # Add servers
    servers = []
    
    if args.discover:
        # Auto-discover servers
        discovered_servers = discover_servers()
        servers.extend(discovered_servers)
    
    if args.live:
        # Get live server information
        live_servers = get_live_server_info(args.router_url)
        servers.extend(live_servers)
    
    # If no servers discovered or queried, use standard ones
    if not servers:
        logger.info("Using standard MCP servers")
        generator = create_standard_diagram_generator()
    else:
        # Add discovered/live servers to generator
        for server in servers:
            generator.add_server(
                server["id"],
                server["type"],
                server["capabilities"]
            )
    
    # Generate comprehensive documentation
    documentation = generator.generate_comprehensive_documentation()
    
    # Add code snippets if requested
    if args.include_code:
        documentation += "\n\n## Code Snippets\n\n"
        documentation += "This section provides relevant code snippets from the MCP server implementations."
        
        for server in servers:
            if "path" in server:
                snippets = extract_code_snippets(server)
                
                if snippets:
                    documentation += f"\n\n### {server['id']} Code Snippets\n\n"
                    
                    for name, snippet in snippets.items():
                        documentation += f"#### {name.title()}\n\n"
                        documentation += f"```python\n{snippet}\n```\n\n"
    
    # Add examples if requested
    if args.include_examples:
        documentation += "\n\n## Usage Examples\n\n"
        documentation += "This section provides examples of how to use the MCP servers."
        
        for server in servers:
            examples = create_usage_examples(server)
            
            if examples:
                documentation += f"\n\n### {server['id']} Examples\n\n"
                
                for example in examples:
                    documentation += f"#### {example['title']}\n\n"
                    documentation += f"{example['description']}\n\n"
                    documentation += f"```python\n{example['code']}\n```\n\n"
    
    # Add generation timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    documentation += f"\n\n---\n\nGenerated on {timestamp}"
    
    return documentation

def convert_markdown_to_html(markdown_content: str, theme: str) -> str:
    """
    Convert markdown content to HTML.
    
    Args:
        markdown_content: Markdown content
        theme: HTML theme
        
    Returns:
        HTML content
    """
    try:
        import markdown
        from bs4 import BeautifulSoup
        
        # Convert markdown to HTML
        html = markdown.markdown(markdown_content, extensions=['fenced_code', 'tables'])
        
        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Add syntax highlighting for code blocks
        for code_block in soup.find_all('code'):
            if code_block.parent.name == 'pre':
                # Get language class if available
                language = ""
                if 'class' in code_block.attrs:
                    language = code_block['class'][0]
                
                # Add syntax highlighting class
                code_block['class'] = code_block.get('class', []) + ['prettyprint']
                
                if language:
                    code_block['class'].append(f'lang-{language}')
        
        # Create complete HTML document
        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Architecture Documentation</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/default.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
    <style>
        body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
        }}
        @media (max-width: 767px) {{
            body {{
                padding: 15px;
            }}
        }}
        /* Theme-specific styles */
        {get_theme_css(theme)}
    </style>
</head>
<body class="markdown-body">
    {soup}
</body>
</html>"""
        
        return html_template
    except ImportError:
        logger.warning("Could not convert to HTML. Missing dependencies: markdown, beautifulsoup4")
        return markdown_content

def convert_to_pdf(html_content: str, output_path: str) -> bool:
    """
    Convert HTML content to PDF.
    
    Args:
        html_content: HTML content
        output_path: Output file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import weasyprint
        
        # Convert HTML to PDF
        weasyprint.HTML(string=html_content).write_pdf(output_path)
        
        return True
    except ImportError:
        logger.warning("Could not convert to PDF. Missing dependency: weasyprint")
        return False

def get_theme_css(theme: str) -> str:
    """
    Get CSS for the specified theme.
    
    Args:
        theme: Theme name
        
    Returns:
        CSS code
    """
    if theme == "github":
        return """
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                color: #24292e;
            }
            h1, h2 {
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
            }
            pre {
                background-color: #f6f8fa;
                border-radius: 3px;
                padding: 16px;
            }
        """
    elif theme == "minimal":
        return """
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                color: #333;
                line-height: 1.6;
            }
            h1, h2, h3, h4, h5, h6 {
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                color: #000;
            }
            pre {
                background-color: #f8f8f8;
                border-radius: 3px;
                padding: 12px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
            }
            table, th, td {
                border: 1px solid #ddd;
            }
            th, td {
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f8f8f8;
            }
        """
    elif theme == "technical":
        return """
            body {
                font-family: Consolas, Monaco, 'Courier New', monospace;
                color: #333;
                line-height: 1.5;
                background-color: #fafafa;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: Arial, sans-serif;
                color: #333;
            }
            pre {
                background-color: #282c34;
                color: #abb2bf;
                border-radius: 5px;
                padding: 16px;
            }
            code {
                color: #e06c75;
            }
            pre code {
                color: inherit;
            }
            table {
                border-collapse: collapse;
                width: 100%;
            }
            table, th, td {
                border: 1px solid #ccc;
            }
            th, td {
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #eee;
            }
        """
    else:  # default
        return """
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                color: #24292e;
                line-height: 1.5;
            }
            h1, h2 {
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
            }
            h1, h2, h3, h4, h5, h6 {
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
            }
            pre {
                background-color: #f6f8fa;
                border-radius: 6px;
                padding: 16px;
                overflow: auto;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 16px;
            }
            table, th, td {
                border: 1px solid #dfe2e5;
            }
            th, td {
                padding: 6px 13px;
            }
            th {
                background-color: #f6f8fa;
                font-weight: 600;
            }
            tr:nth-child(2n) {
                background-color: #f6f8fa;
            }
        """

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate documentation in the requested format
    if args.format == "markdown":
        # Generate markdown documentation
        content = generate_markdown_documentation(args)
        
        # Write to file
        with open(output_path, "w") as f:
            f.write(content)
        
        logger.info(f"Generated markdown documentation: {output_path}")
    elif args.format == "html":
        # Generate markdown documentation
        markdown_content = generate_markdown_documentation(args)
        
        # Convert to HTML
        html_content = convert_markdown_to_html(markdown_content, args.theme)
        
        # Write to file
        with open(output_path.with_suffix(".html"), "w") as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML documentation: {output_path.with_suffix('.html')}")
    elif args.format == "pdf":
        # Generate markdown documentation
        markdown_content = generate_markdown_documentation(args)
        
        # Convert to HTML
        html_content = convert_markdown_to_html(markdown_content, args.theme)
        
        # Convert to PDF
        pdf_path = output_path.with_suffix(".pdf")
        if convert_to_pdf(html_content, str(pdf_path)):
            logger.info(f"Generated PDF documentation: {pdf_path}")
        else:
            # Fall back to HTML
            html_path = output_path.with_suffix(".html")
            with open(html_path, "w") as f:
                f.write(html_content)
            
            logger.info(f"Could not generate PDF. Generated HTML instead: {html_path}")

if __name__ == "__main__":
    main()
