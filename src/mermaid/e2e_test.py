#!/usr/bin/env python3
"""
End-to-End Test for Mermaid MCP Server with Claude Desktop

This script runs end-to-end tests against a locally running
Mermaid MCP server configured in Claude Desktop.

Make sure the server is configured in your Claude Desktop
config file (~/.claude/config.json) before running this test.
"""

import os
import sys
import json
import time
import base64
import subprocess
import requests
from typing import Dict, Any, Optional

# Config
MCP_SERVER_NAME = "mermaid-generator"
MCP_SERVER_PORTS = [8080, 3000, 5000]  # Try multiple ports
MCP_SERVER_PORT = 8080  # Default port, will be updated if server is found on a different port
TEST_TIMEOUT = 30  # Maximum wait time for server to start (seconds)
TEST_OUTPUT_DIR = "./e2e_test_output"

def print_header(text: str) -> None:
    """Print a header with the given text."""
    print("\n" + "=" * 80)
    print(f"  {text}  ".center(80, "="))
    print("=" * 80 + "\n")

def print_step(text: str) -> None:
    """Print a step with the given text."""
    print(f"🔹 {text}")

def print_success(text: str) -> None:
    """Print a success message with the given text."""
    print(f"✅ {text}")

def print_failure(text: str) -> None:
    """Print a failure message with the given text."""
    print(f"❌ {text}")

def start_server() -> subprocess.Popen:
    """Start the MCP server as a subprocess."""
    print_step("Starting Mermaid MCP server...")
    
    # Check environment variable
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print_failure("ANTHROPIC_API_KEY environment variable not set!")
        print("Please set your API key first:")
        print("  export ANTHROPIC_API_KEY=your-api-key-here")
        sys.exit(1)
    
    # Start the server
    cmd = ["python", "-m", "src.mermaid.mermaid_server"]
    env = os.environ.copy()
    env["DEFAULT_THEME"] = "pastel"
    
    # Use specific path for custom themes if needed
    custom_themes_path = os.path.expanduser("~/.mermaid_themes.json")
    if os.path.exists(custom_themes_path):
        env["CUSTOM_THEMES_PATH"] = custom_themes_path
        
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    print_step(f"Waiting for server to initialize (up to {TEST_TIMEOUT} seconds)...")
    start_time = time.time()
    while time.time() - start_time < TEST_TIMEOUT:
        for port in MCP_SERVER_PORTS:
            try:
                response = requests.post(
                    f"http://localhost:{port}/tools",
                    headers={"Content-Type": "application/json"},
                    json={"id": "test", "tool": "get_status", "params": {}},
                    timeout=1
                )
                if response.status_code == 200:
                    print_success(f"Server started successfully on port {port}!")
                    # Update the global port for future requests
                    global MCP_SERVER_PORT
                    MCP_SERVER_PORT = port
                    return process
            except requests.exceptions.ConnectionError:
                # Server not ready yet on this port
                pass
            except requests.exceptions.Timeout:
                # Request timed out
                pass
        
        # Sleep before trying again
        time.sleep(0.5)
    
    # If we get here, server failed to start
    print_failure("Server failed to start within timeout!")
    kill_server(process)
    sys.exit(1)

def kill_server(process: subprocess.Popen) -> None:
    """Kill the MCP server subprocess."""
    print_step("Shutting down server...")
    if process.poll() is None:  # Still running
        process.terminate()
        process.wait(timeout=5)
    
    if process.poll() is None:  # Still running after terminate
        process.kill()
    
    print_success("Server shutdown complete.")

def make_request(tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make a request to the MCP server."""
    try:
        response = requests.post(
            f"http://localhost:{MCP_SERVER_PORT}/tools",
            headers={"Content-Type": "application/json"},
            json={"id": "test", "tool": tool, "params": params},
            timeout=60  # Allow up to 60 seconds for the request to complete
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_failure(f"Error making request: {str(e)}")
        return {"error": str(e)}

def test_server_status() -> bool:
    """Test the server status endpoint."""
    print_step("Testing server status...")
    response = make_request("get_status", {})
    
    if "error" in response:
        print_failure(f"Failed to get server status: {response['error']}")
        return False
    
    print_success("Server status: OK")
    print(f"  Available themes: {response.get('result', {}).get('styling', {}).get('available_themes', [])}")
    return True

def test_theme_info() -> bool:
    """Test getting theme information."""
    print_step("Testing theme info...")
    response = make_request("get_theme_info", {})
    
    if "error" in response:
        print_failure(f"Failed to get theme info: {response['error']}")
        return False
    
    print_success("Theme info retrieved successfully")
    
    # Check for custom theme if it exists
    themes = response.get("result", {}).get("available_themes", [])
    if "brand-blue" in themes:
        print_success("Custom 'brand-blue' theme detected!")
    
    return True

def test_generate_diagram() -> (bool, Optional[str]):
    """Test diagram generation."""
    print_step("Testing diagram generation...")
    
    query = "Create a simple flowchart showing user registration, login, and logout"
    response = make_request("generate_diagram", {"query": query, "theme": "pastel"})
    
    if "error" in response:
        print_failure(f"Failed to generate diagram: {response['error']}")
        return False, None
    
    diagram = response.get("result", "")
    if not diagram:
        print_failure("Received empty diagram response")
        return False, None
    
    # Make sure it looks like a valid Mermaid diagram
    if not ("graph" in diagram.lower() or "flowchart" in diagram.lower()):
        print_failure("Response doesn't appear to be a valid Mermaid diagram")
        return False, None
    
    print_success("Diagram generated successfully")
    
    # Save the diagram for further testing
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    with open(f"{TEST_OUTPUT_DIR}/generated_diagram.mmd", "w") as f:
        f.write(diagram)
    
    print_success(f"Diagram saved to {TEST_OUTPUT_DIR}/generated_diagram.mmd")
    return True, diagram

def test_analyze_diagram(diagram: str) -> bool:
    """Test diagram analysis."""
    print_step("Testing diagram analysis...")
    
    response = make_request("analyze_diagram", {"diagram": diagram})
    
    if "error" in response:
        print_failure(f"Failed to analyze diagram: {response['error']}")
        return False
    
    analysis = response.get("result", "")
    if not analysis:
        print_failure("Received empty analysis response")
        return False
    
    print_success("Diagram analyzed successfully")
    
    # Save the analysis
    with open(f"{TEST_OUTPUT_DIR}/diagram_analysis.txt", "w") as f:
        f.write(analysis)
    
    print_success(f"Analysis saved to {TEST_OUTPUT_DIR}/diagram_analysis.txt")
    return True

def test_preview_diagram(diagram: str) -> bool:
    """Test diagram preview generation."""
    print_step("Testing diagram preview generation...")
    
    response = make_request("preview_diagram", {"diagram": diagram, "theme": "dark"})
    
    if "error" in response:
        print_failure(f"Failed to generate preview: {response['error']}")
        return False
    
    svg_base64 = response.get("result", "")
    if not svg_base64:
        print_failure("Received empty SVG response")
        return False
    
    # Try to decode the base64 string to make sure it's valid
    try:
        svg_data = base64.b64decode(svg_base64)
        if not svg_data.startswith(b"<svg"):
            print_failure("Decoded data doesn't appear to be valid SVG")
            return False
    except Exception as e:
        print_failure(f"Failed to decode SVG data: {str(e)}")
        return False
    
    print_success("Preview generated successfully")
    
    # Save the SVG
    with open(f"{TEST_OUTPUT_DIR}/preview.svg", "wb") as f:
        f.write(svg_data)
    
    print_success(f"SVG saved to {TEST_OUTPUT_DIR}/preview.svg")
    return True

def test_modify_diagram(diagram: str) -> bool:
    """Test diagram modification."""
    print_step("Testing diagram modification...")
    
    modification = "Add error handling for registration failure"
    response = make_request("modify_diagram", {
        "diagram": diagram, 
        "modification": modification,
        "theme": "vibrant"
    })
    
    if "error" in response:
        print_failure(f"Failed to modify diagram: {response['error']}")
        return False
    
    modified_diagram = response.get("result", "")
    if not modified_diagram:
        print_failure("Received empty modified diagram response")
        return False
    
    print_success("Diagram modified successfully")
    
    # Save the modified diagram
    with open(f"{TEST_OUTPUT_DIR}/modified_diagram.mmd", "w") as f:
        f.write(modified_diagram)
    
    print_success(f"Modified diagram saved to {TEST_OUTPUT_DIR}/modified_diagram.mmd")
    return True

def test_custom_theme() -> bool:
    """Test custom theme creation and removal."""
    print_step("Testing custom theme creation...")
    
    # Only test if custom themes file exists
    if not os.path.exists(os.path.expanduser("~/.mermaid_themes.json")):
        print_step("Skipping custom theme test (no themes file)")
        return True
    
    # Create a test custom theme
    test_theme = {
        "node_fill": "#f0f0f0",
        "node_border": "#555555",
        "node_text": "#333333",
        "edge": "#777777",
        "highlight": "#ff6600",
        "success": "#66cc66",
        "warning": "#ffcc66",
        "error": "#ff6666"
    }
    
    response = make_request("add_custom_theme", {
        "name": "e2e-test-theme",
        "colors": test_theme
    })
    
    if "error" in response:
        print_failure(f"Failed to create custom theme: {response['error']}")
        return False
    
    print_success("Custom theme created successfully")
    
    # Test removing the theme
    print_step("Testing custom theme removal...")
    
    response = make_request("remove_custom_theme", {
        "name": "e2e-test-theme"
    })
    
    if "error" in response:
        print_failure(f"Failed to remove custom theme: {response['error']}")
        return False
    
    print_success("Custom theme removed successfully")
    return True

def run_tests() -> None:
    """Run all tests."""
    print_header("MERMAID MCP SERVER END-TO-END TESTS")
    
    # Start the server
    server_process = start_server()
    
    try:
        # Basic server tests
        if not test_server_status():
            return
            
        if not test_theme_info():
            return
            
        # Test diagram generation
        success, diagram = test_generate_diagram()
        if not success or diagram is None:
            return
            
        # Test diagram analysis
        if not test_analyze_diagram(diagram):
            return
            
        # Test diagram preview
        if not test_preview_diagram(diagram):
            return
            
        # Test diagram modification
        if not test_modify_diagram(diagram):
            return
            
        # Test custom theme creation/removal
        if not test_custom_theme():
            return
            
        # All tests passed!
        print_header("ALL TESTS PASSED SUCCESSFULLY")
        print("Test outputs are available in the following directory:")
        print(f"  {os.path.abspath(TEST_OUTPUT_DIR)}")
        
    finally:
        # Always kill the server when we're done
        kill_server(server_process)

if __name__ == "__main__":
    run_tests() 