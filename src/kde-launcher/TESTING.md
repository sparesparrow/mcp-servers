# KDE Launcher MCP Server - Manual Testing Guide

This document provides instructions for manually testing the KDE Launcher MCP server on a Linux system with KDE Plasma desktop environment.

## Prerequisites

Before testing, ensure you have the following installed:

1. KDE Plasma desktop environment
2. Python 3.9+
3. Required Python packages:
   - mcp
   - dbus-python
   - PyGObject

Install the required system packages:

```bash
sudo apt-get install python3-dbus python3-gi libdbus-1-dev libdbus-glib-1-dev
```

Install the required Python packages:

```bash
pip install mcp anthropic dbus-python PyGObject
```

## Basic Server Testing

### 1. Start the Server

Run the server in a terminal:

```bash
cd /path/to/mcp-servers
python -m src.kde-launcher.kde_launcher_server
```

You should see output similar to:

```
2024-03-08 12:00:00,000 - kde-launcher-server - INFO - D-Bus interfaces initialized successfully
2024-03-08 12:00:00,000 - kde-launcher-server - INFO - KDE Launcher server initialized
2024-03-08 12:00:00,000 - kde-launcher-server - INFO - Starting KDE Launcher server
```

### 2. Test with MCP Client

Use a sample MCP client to test the server:

```python
#!/usr/bin/env python3
import json
import os
import sys

# Simple test client for the KDE Launcher MCP server
def send_request(request):
    print(f"Sending request: {json.dumps(request)}")
    print(json.dumps(request))
    response_text = input()
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        print(f"Failed to parse response: {response_text}", file=sys.stderr)
        return None

# Test search_applications
search_request = {
    "name": "search_applications",
    "parameters": {
        "query": "firefox"
    }
}
search_result = send_request(search_request)
print(f"Search result: {json.dumps(search_result, indent=2)}")

# Test launch_application with the first result (if any found)
if search_result and "result" in search_result and search_result["result"]:
    app_id = search_result["result"][0]["app_id"]
    launch_request = {
        "name": "launch_application",
        "parameters": {
            "app_id": app_id,
            "args": ["--new-window"]
        }
    }
    launch_result = send_request(launch_request)
    print(f"Launch result: {json.dumps(launch_result, indent=2)}")

# Test list_running_applications
list_request = {
    "name": "list_running_applications",
    "parameters": {}
}
list_result = send_request(list_request)
print(f"List result: {json.dumps(list_result, indent=2)}")

# Test control_window (if any windows found)
if list_result and "result" in list_result and list_result["result"]:
    window_id = list_result["result"][0]["window_id"]
    control_request = {
        "name": "control_window",
        "parameters": {
            "window_id": window_id,
            "action": "minimize"
        }
    }
    control_result = send_request(control_request)
    print(f"Control result: {json.dumps(control_result, indent=2)}")
```

Save this script as `test_kde_launcher.py` and run:

```bash
python test_kde_launcher.py | python -m src.kde-launcher.kde_launcher_server
```

## Testing Individual Tools

You can also test each tool individually using direct JSON stdin/stdout communication.

### 1. Search Applications

```bash
echo '{"name": "search_applications", "parameters": {"query": "terminal"}}' | python -m src.kde-launcher.kde_launcher_server
```

Expected output:
```json
{
  "result": [
    {
      "name": "Konsole",
      "description": "Terminal",
      "app_id": "org.kde.konsole.desktop"
    },
    {
      "name": "Terminal",
      "description": "Terminal emulator",
      "app_id": "gnome-terminal.desktop"
    }
  ]
}
```

### 2. Launch Application

```bash
echo '{"name": "launch_application", "parameters": {"app_id": "org.kde.konsole.desktop"}}' | python -m src.kde-launcher.kde_launcher_server
```

Expected output:
```json
{
  "result": {
    "success": true,
    "app_id": "org.kde.konsole.desktop",
    "args": []
  }
}
```

### 3. List Running Applications

```bash
echo '{"name": "list_running_applications", "parameters": {}}' | python -m src.kde-launcher.kde_launcher_server
```

Expected output:
```json
{
  "result": [
    {
      "window_id": "123456789",
      "title": "Dolphin",
      "class": "dolphin",
      "desktop": 1
    },
    {
      "window_id": "987654321",
      "title": "Firefox",
      "class": "firefox",
      "desktop": 1
    }
  ]
}
```

### 4. Control Window

```bash
echo '{"name": "control_window", "parameters": {"window_id": "123456789", "action": "minimize"}}' | python -m src.kde-launcher.kde_launcher_server
```

Expected output:
```json
{
  "result": true
}
```

### 5. Create Launcher

```bash
echo '{"name": "create_launcher", "parameters": {"name": "Test App", "command": "/usr/bin/firefox", "icon": "firefox", "categories": ["Network", "WebBrowser"]}}' | python -m src.kde-launcher.kde_launcher_server
```

Expected output:
```json
{
  "result": true
}
```

## Testing with Claude Desktop

To test with Claude Desktop, update your Claude Desktop configuration file (~/.claude/config.json) to include:

```json
{
  "mcpServers": {
    "kde-launcher": {
      "command": "python",
      "args": ["-m", "src.kde-launcher.kde_launcher_server"],
      "env": {},
      "cwd": "${HOME}/projects/mcp-servers"
    }
  }
}
```

Then restart Claude Desktop and ask it to interact with the KDE desktop, e.g.:
- "Find and launch Firefox"
- "Show me all running applications"
- "Close the Firefox window"
- "Create a launcher for Visual Studio Code"

## Testing Security Measures

Test input validation by attempting to inject commands:

```bash
echo '{"name": "launch_application", "parameters": {"app_id": "firefox & rm -rf /"}}' | python -m src.kde-launcher.kde_launcher_server
```

Expected output should include an error about invalid application ID.

## Testing Fallback Mechanisms

Test the fallback mechanism by stopping D-Bus temporarily:

```bash
# In one terminal, stop D-Bus (this requires root)
sudo systemctl stop dbus

# In another terminal, run the server
python -m src.kde-launcher.kde_launcher_server

# Test search by fallback to desktop files
echo '{"name": "search_applications", "parameters": {"query": "firefox"}}' | python -m src.kde-launcher.kde_launcher_server

# Restart D-Bus
sudo systemctl start dbus
```

## Troubleshooting

If you encounter issues:

1. Check that KDE's D-Bus services are running:
   ```bash
   qdbus org.kde.krunner /PlasmaRunnerManager
   qdbus org.kde.KWin /KWin
   ```

2. Verify D-Bus permissions:
   ```bash
   dbus-send --session --dest=org.kde.krunner --type=method_call --print-reply /PlasmaRunnerManager org.kde.krunner.App.Match string:"test"
   ```

3. Run the server with increased logging:
   ```bash
   KDE_LAUNCHER_LOG_LEVEL=DEBUG python -m src.kde-launcher.kde_launcher_server
   ```

If all else fails, check for error messages in the KDE Launcher server output and ensure that all required dependencies are installed correctly. 