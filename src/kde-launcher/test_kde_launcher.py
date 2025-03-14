#!/usr/bin/env python3
"""
Simple test client for the KDE Launcher MCP server.

This script demonstrates how to interact with the KDE Launcher MCP server
using direct JSON communication over stdin/stdout.
"""

import json
import os
import sys
import time

def send_request(request):
    """Send a request to the MCP server and get the response.
    
    Args:
        request: Dictionary containing the request
        
    Returns:
        Dictionary containing the response
    """
    print(f"--- Sending request: {json.dumps(request)}", file=sys.stderr)
    print(json.dumps(request))
    sys.stdout.flush()
    
    response_text = input()
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        print(f"Failed to parse response: {response_text}", file=sys.stderr)
        return None

def test_search_applications():
    """Test the search_applications tool."""
    print("\n=== Testing search_applications ===", file=sys.stderr)
    
    search_request = {
        "name": "search_applications",
        "parameters": {
            "query": "terminal"
        }
    }
    
    search_result = send_request(search_request)
    print(f"Search result: {json.dumps(search_result, indent=2)}", file=sys.stderr)
    
    return search_result.get("result", []) if search_result else []

def test_launch_application(app_id):
    """Test the launch_application tool with the given app_id.
    
    Args:
        app_id: Application ID to launch
    """
    print(f"\n=== Testing launch_application for {app_id} ===", file=sys.stderr)
    
    launch_request = {
        "name": "launch_application",
        "parameters": {
            "app_id": app_id,
            "args": []
        }
    }
    
    launch_result = send_request(launch_request)
    print(f"Launch result: {json.dumps(launch_result, indent=2)}", file=sys.stderr)
    
    # Give the application a chance to start
    time.sleep(2)
    
    return launch_result.get("result", {}) if launch_result else {}

def test_list_running_applications():
    """Test the list_running_applications tool."""
    print("\n=== Testing list_running_applications ===", file=sys.stderr)
    
    list_request = {
        "name": "list_running_applications",
        "parameters": {}
    }
    
    list_result = send_request(list_request)
    print(f"List result: {json.dumps(list_result, indent=2)}", file=sys.stderr)
    
    return list_result.get("result", []) if list_result else []

def test_control_window(window_id, action="minimize"):
    """Test the control_window tool with the given window_id and action.
    
    Args:
        window_id: Window ID to control
        action: Control action to perform
    """
    print(f"\n=== Testing control_window for {window_id} with action {action} ===", 
          file=sys.stderr)
    
    control_request = {
        "name": "control_window",
        "parameters": {
            "window_id": window_id,
            "action": action
        }
    }
    
    control_result = send_request(control_request)
    print(f"Control result: {json.dumps(control_result, indent=2)}", file=sys.stderr)
    
    return control_result.get("result", False) if control_result else False

def test_create_launcher():
    """Test the create_launcher tool."""
    print("\n=== Testing create_launcher ===", file=sys.stderr)
    
    create_launcher_request = {
        "name": "create_launcher",
        "parameters": {
            "name": "Test App",
            "command": "/usr/bin/xterm",
            "icon": "utilities-terminal",
            "categories": ["System", "TerminalEmulator"]
        }
    }
    
    create_launcher_result = send_request(create_launcher_request)
    print(f"Create launcher result: {json.dumps(create_launcher_result, indent=2)}", 
          file=sys.stderr)
    
    return create_launcher_result.get("result", False) if create_launcher_result else False

def main():
    """Run all tests in sequence."""
    try:
        # Test searching for applications
        search_results = test_search_applications()
        
        # If search found any applications, launch the first one
        if search_results:
            app_id = search_results[0]["app_id"]
            launch_result = test_launch_application(app_id)
            
            # Wait a bit for the application to start
            time.sleep(3)
            
            # List running applications
            running_apps = test_list_running_applications()
            
            # If any applications are running, control the first one
            if running_apps:
                window_id = running_apps[0]["window_id"]
                
                # Try minimizing the window
                minimize_result = test_control_window(window_id, "minimize")
                time.sleep(1)
                
                # Try maximizing the window
                maximize_result = test_control_window(window_id, "maximize")
                time.sleep(1)
                
                # Try focusing the window
                focus_result = test_control_window(window_id, "focus")
                time.sleep(1)
                
                # Note: We're not testing closing windows as that might be disruptive
        
        # Test creating a custom launcher
        create_launcher_result = test_create_launcher()
        
        print("\n=== All tests completed ===", file=sys.stderr)
        
    except Exception as e:
        print(f"Error during testing: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 