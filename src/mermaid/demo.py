#!/usr/bin/env python3
"""
Mermaid MCP Server Demo Script

This script demonstrates the capabilities of the Mermaid MCP Server,
particularly focusing on the styling features.
"""

import os
import sys
import json
import argparse
import base64
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import server classes
from src.mermaid.mermaid_server import MermaidServer
try:
    from src.mermaid.mermaid_orchestrator import MermaidOrchestratorServer
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# ANSI color codes for terminal output
COLORS = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m"
}

def print_colored(text: str, color: str) -> None:
    """Print text with color."""
    print(f"{COLORS.get(color, '')}{text}{COLORS['ENDC']}")

def print_section(title: str) -> None:
    """Print a section title."""
    print("\n" + "=" * 80)
    print_colored(f"  {title}  ".center(80, "="), "HEADER")
    print("=" * 80 + "\n")

def print_json(data: Dict[str, Any]) -> None:
    """Print formatted JSON."""
    print_colored(json.dumps(data, indent=2), "CYAN")
    print()

def save_diagram_to_file(diagram: str, filename: str) -> None:
    """Save a Mermaid diagram to a file."""
    with open(filename, "w") as f:
        f.write(diagram)
    print_colored(f"Diagram saved to {filename}", "GREEN")

def demo_generate_diagram(server: MermaidServer, theme: Optional[str] = None) -> str:
    """Demonstrate generate_diagram tool."""
    print_section("Generating a Diagram")
    
    query = "Create a flowchart showing a user authentication process with registration, login, and account management steps"
    
    print_colored("Query:", "BOLD")
    print(query)
    print()
    
    theme_str = f" with '{theme}' theme" if theme else ""
    print_colored(f"Generating diagram{theme_str}...", "YELLOW")
    
    try:
        result = server.generate_diagram(query, theme=theme)
        print_colored("Generated Mermaid Diagram:", "BOLD")
        print(result)
        return result
    except Exception as e:
        print_colored(f"Error: {str(e)}", "RED")
        return ""

def demo_analyze_diagram(server: MermaidServer, diagram: str) -> None:
    """Demonstrate analyze_diagram tool."""
    print_section("Analyzing a Diagram")
    
    print_colored("Analyzing diagram...", "YELLOW")
    
    try:
        result = server.analyze_diagram(diagram)
        print_colored("Analysis:", "BOLD")
        print(result)
    except Exception as e:
        print_colored(f"Error: {str(e)}", "RED")

def demo_modify_diagram(server: MermaidServer, diagram: str, theme: Optional[str] = None) -> str:
    """Demonstrate modify_diagram tool."""
    print_section("Modifying a Diagram")
    
    modification = "Add a 'Forgot Password' flow that connects to the login process"
    
    print_colored("Original Diagram:", "BOLD")
    print(diagram)
    print()
    
    print_colored("Modification Request:", "BOLD")
    print(modification)
    print()
    
    theme_str = f" with '{theme}' theme" if theme else ""
    print_colored(f"Modifying diagram{theme_str}...", "YELLOW")
    
    try:
        result = server.modify_diagram(diagram, modification, theme=theme)
        print_colored("Modified Mermaid Diagram:", "BOLD")
        print(result)
        return result
    except Exception as e:
        print_colored(f"Error: {str(e)}", "RED")
        return diagram

def demo_validate_diagram(server: MermaidServer, diagram: str) -> None:
    """Demonstrate validate_diagram tool."""
    print_section("Validating a Diagram")
    
    print_colored("Validating diagram...", "YELLOW")
    
    try:
        result = server.validate_diagram(diagram)
        print_colored("Validation Result:", "BOLD")
        print_json(result)
    except Exception as e:
        print_colored(f"Error: {str(e)}", "RED")

def demo_theme_info(server: MermaidServer) -> None:
    """Demonstrate get_theme_info tool."""
    print_section("Theme Information")
    
    print_colored("Getting theme information...", "YELLOW")
    
    try:
        result = server.get_theme_info()
        print_colored("Available Themes:", "BOLD")
        print_json(result)
        
        # Show specific theme details
        theme = result["default_theme"]
        print_colored(f"Details for '{theme}' theme:", "BOLD")
        theme_details = server.get_theme_info(theme)
        print_json(theme_details)
    except Exception as e:
        print_colored(f"Error: {str(e)}", "RED")

def demo_theme_comparison(server: MermaidServer) -> None:
    """Demonstrate the same diagram with different themes."""
    print_section("Theme Comparison")
    
    simple_diagram = """graph TD
    A[Start] --> B[Process]
    B --> C[End]
    B --> D[Alternative]"""
    
    print_colored("Base Diagram:", "BOLD")
    print(simple_diagram)
    print()
    
    # Apply each theme and show the result
    themes = ["default", "dark", "pastel", "vibrant"]
    styled_diagrams = {}
    
    for theme in themes:
        print_colored(f"Applying '{theme}' theme...", "YELLOW")
        try:
            style_manager = server.style_manager
            styled = style_manager.add_styling_to_diagram(simple_diagram, theme)
            styled_diagrams[theme] = styled
            print(styled)
            print()
        except Exception as e:
            print_colored(f"Error: {str(e)}", "RED")
    
    return styled_diagrams

def demo_add_custom_theme(server: MermaidServer) -> str:
    """Demonstrate adding a custom theme."""
    print_section("Adding a Custom Theme")
    
    # Define a custom theme (blue-based)
    custom_theme = {
        "node_fill": "#e6f2ff",
        "node_border": "#3366cc",
        "node_text": "#333333",
        "edge": "#3366cc",
        "highlight": "#0052cc",
        "success": "#57d9a3",
        "warning": "#ffab00",
        "error": "#ff5630"
    }
    
    theme_name = "demo-blue"
    
    print_colored("Creating custom theme:", "BOLD")
    print_json(custom_theme)
    
    try:
        result = server.add_custom_theme(theme_name, custom_theme)
        if result:
            print_colored(f"Custom theme '{theme_name}' created successfully!", "GREEN")
            return theme_name
        else:
            print_colored(f"Failed to create custom theme '{theme_name}'", "RED")
            return ""
    except Exception as e:
        print_colored(f"Error: {str(e)}", "RED")
        return ""

def demo_preview_diagram(server: MermaidServer, diagram: str, theme: Optional[str] = None) -> None:
    """Demonstrate the preview_diagram functionality."""
    print_section("Generating SVG Preview")
    
    print_colored("Diagram to preview:", "BOLD")
    print(diagram)
    print()
    
    theme_str = f" with '{theme}' theme" if theme else ""
    print_colored(f"Generating SVG preview{theme_str}...", "YELLOW")
    
    try:
        result = server.preview_diagram(diagram, theme=theme)
        
        print_colored("Base64-encoded SVG generated successfully!", "GREEN")
        print_colored("First 100 characters of base64 string:", "BOLD")
        print(result[:100] + "...")
        print()
        
        # Save SVG to file
        svg_bytes = base64.b64decode(result)
        svg_path = f"./demo_output/preview_{theme or 'default'}.svg"
        
        with open(svg_path, "wb") as f:
            f.write(svg_bytes)
            
        print_colored(f"SVG saved to {svg_path}", "GREEN")
        print()
        
        # Show HTML for embedding
        print_colored("HTML code to embed this diagram:", "BOLD")
        html = f'<img src="data:image/svg+xml;base64,{result}" alt="Mermaid Diagram" />'
        print_colored(html[:100] + "...", "CYAN")
        
    except Exception as e:
        print_colored(f"Error: {str(e)}", "RED")

def demo_orchestrator_features(server) -> None:
    """Demonstrate orchestrator-specific features."""
    if not hasattr(server, 'generate_class_diagram'):
        print_colored("Orchestrator features not available", "RED")
        return
    
    print_section("Orchestrator Features")
    
    # Simple code example
    code = """
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        
    def get_profile(self):
        return f"{self.name} <{self.email}>"

class Admin(User):
    def __init__(self, name, email, role):
        super().__init__(name, email)
        self.role = role
        
    def get_permissions(self):
        return ["read", "write", "admin"]
"""
    
    print_colored("Sample Code:", "BOLD")
    print(code)
    print()
    
    # Generate class diagram
    print_colored("Generating class diagram...", "YELLOW")
    try:
        diagram = server.generate_class_diagram(code)
        print_colored("Generated Class Diagram:", "BOLD")
        print(diagram)
        
        # Save diagram
        with open("./demo_output/class_diagram.mmd", "w") as f:
            f.write(diagram)
        print_colored("Class diagram saved to ./demo_output/class_diagram.mmd", "GREEN")
    except Exception as e:
        print_colored(f"Error generating class diagram: {str(e)}", "RED")

def main() -> None:
    """Main demo function."""
    parser = argparse.ArgumentParser(description="Mermaid MCP Server Demo")
    parser.add_argument("--api-key", help="Anthropic API key")
    parser.add_argument("--theme", choices=["default", "dark", "pastel", "vibrant"], 
                        default="default", help="Default theme to use")
    parser.add_argument("--output-dir", default="./demo_output", 
                        help="Directory to save output files")
    parser.add_argument("--custom-themes-path", 
                        help="Path to custom themes JSON file")
    parser.add_argument("--server-type", choices=["standard", "orchestrator"],
                        default="standard", help="Type of server to demonstrate")
    
    args = parser.parse_args()
    
    # Use API key from args or environment
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print_colored("Error: Anthropic API key is required. Provide it with --api-key or set ANTHROPIC_API_KEY environment variable.", "RED")
        sys.exit(1)
    
    # Check if orchestrator is requested but not available
    if args.server_type == "orchestrator" and not ORCHESTRATOR_AVAILABLE:
        print_colored("Warning: Orchestrator server requested but dependencies are not available. Falling back to standard server.", "YELLOW")
        args.server_type = "standard"
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print_colored(f"Mermaid MCP {args.server_type.capitalize()} Server Demo", "BOLD")
    print(f"Using theme: {args.theme}")
    
    # Initialize server based on type
    if args.server_type == "orchestrator" and ORCHESTRATOR_AVAILABLE:
        server = MermaidOrchestratorServer(
            api_key=api_key, 
            default_theme=args.theme,
            custom_themes_path=args.custom_themes_path
        )
        print_colored("Using orchestrator server with extended capabilities", "GREEN")
    else:
        server = MermaidServer(
            api_key=api_key, 
            default_theme=args.theme,
            custom_themes_path=args.custom_themes_path
        )
        print_colored("Using standard Mermaid server", "GREEN")
    
    # Demo theme info
    demo_theme_info(server)
    
    # Demo theme comparison
    styled_diagrams = demo_theme_comparison(server)
    
    # Save theme comparison examples
    for theme, diagram in styled_diagrams.items():
        save_diagram_to_file(diagram, f"{args.output_dir}/theme_{theme}.mmd")
    
    # Create a custom theme
    custom_theme = demo_add_custom_theme(server)
    
    # Generate a diagram
    diagram = demo_generate_diagram(server, theme=args.theme)
    if diagram:
        save_diagram_to_file(diagram, f"{args.output_dir}/generated_diagram.mmd")
        
        # Generate a preview
        demo_preview_diagram(server, diagram, args.theme)
    
    # Analyze the diagram
    if diagram:
        demo_analyze_diagram(server, diagram)
    
    # Modify the diagram with a different theme
    if diagram:
        # Use a different theme for modification to showcase theme switching
        modified_theme = "dark" if args.theme != "dark" else "vibrant"
        modified = demo_modify_diagram(server, diagram, theme=modified_theme)
        if modified:
            save_diagram_to_file(modified, f"{args.output_dir}/modified_diagram.mmd")
    
    # Validate a diagram
    if diagram:
        demo_validate_diagram(server, diagram)
    
    # If we created a custom theme, try it out
    if custom_theme:
        print_section("Using Custom Theme")
        
        print_colored(f"Generating a diagram with the custom '{custom_theme}' theme...", "YELLOW")
        custom_themed_diagram = demo_generate_diagram(server, theme=custom_theme)
        
        if custom_themed_diagram:
            save_diagram_to_file(custom_themed_diagram, f"{args.output_dir}/custom_theme_diagram.mmd")
            
            # Generate a preview with the custom theme
            demo_preview_diagram(server, custom_themed_diagram, custom_theme)
            
            # Clean up - remove the demo theme
            print_section("Removing Custom Theme")
            try:
                result = server.remove_custom_theme(custom_theme)
                if result:
                    print_colored(f"Custom theme '{custom_theme}' removed successfully!", "GREEN")
                else:
                    print_colored(f"Failed to remove custom theme '{custom_theme}'", "RED")
            except Exception as e:
                print_colored(f"Error: {str(e)}", "RED")
    
    # Demonstrate orchestrator features if available
    if args.server_type == "orchestrator" and ORCHESTRATOR_AVAILABLE:
        demo_orchestrator_features(server)
    
    print_section("Demo Complete")
    print_colored(f"Output files have been saved to {args.output_dir}/", "GREEN")
    print("To render these diagrams, you can use the Mermaid Live Editor:")
    print("https://mermaid.live/")
    print()
    print("SVG previews can be viewed directly in a web browser or image viewer.")

if __name__ == "__main__":
    main() 