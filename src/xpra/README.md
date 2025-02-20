# Xpra MCP Server

The Xpra MCP Server enables remote application windowing through the Model Context Protocol. It provides a standardized interface for starting, managing, and controlling Xpra sessions, allowing remote display and control of specific applications and their child windows.

## Features

### Current Capabilities

The server currently provides the following tools for Xpra session management:

**Application Control**
- Start applications in new Xpra sessions with VNC or HTML5 display modes
- Automatically manage child windows from the started applications
- Configure audio forwarding and encryption options
- Support for password-based authentication

**Session Management**
- List all active Xpra sessions
- Stop individual sessions with graceful shutdown
- Monitor session status and process health

**Network Configuration**
- Configure firewall rules for VNC (port 5900) or HTML5 (port 8080) access
- Support for binding to specific network interfaces
- Control read-only access for display-only sessions

### Tool Reference

1. `start_application`
   - Launches an application in a new Xpra session
   - Parameters:
     - application (str): Name of the application to start
     - mode (str, optional): Display mode ('vnc' or 'html5'), defaults to 'vnc'
     - display (str, optional): X display number, defaults to ':0'
     - enable_audio (bool, optional): Enable audio forwarding
     - enable_encryption (bool, optional): Enable AES encryption (VNC mode only)
     - password_file (str, optional): Path to password file for authentication
   - Returns: JSON-formatted connection instructions

2. `list_sessions`
   - Lists all active Xpra sessions
   - Returns: JSON array of active sessions with status information

3. `stop_session`
   - Stops an active Xpra session
   - Parameters:
     - session_id (str): ID of the session to stop (format: "application_display")
   - Returns: Status message indicating success or failure

4. `configure_firewall`
   - Configures system firewall rules for Xpra access
   - Parameters:
     - mode (str, optional): Display mode to configure ('vnc' or 'html5')
   - Returns: Status message confirming firewall configuration

## Technical Review and Improvement Recommendations

### Architecture Strengths

The current implementation demonstrates several strong architectural choices:
1. Clear separation of concerns between session management and network configuration
2. Robust error handling with process monitoring
3. Effective use of MCP Context for logging and progress tracking
4. Type-safe implementation with proper parameter validation

### Recommended Improvements

**Resource Integration**
The server would benefit from exposing session information as MCP resources. This would allow clients to:
- Monitor session status through resource subscriptions
- Access detailed session information without executing tools
- Receive real-time updates on session changes

Example resource implementation:
```python
@server.mcp.resource("sessions://{session_id}")
async def get_session_info(session_id: str) -> str:
    """Get detailed information about a specific Xpra session."""
    if session_id in server.active_sessions:
        process = server.active_sessions[session_id]
        return json.dumps({
            "application": session_id.split('_')[0],
            "display": session_id.split('_')[1],
            "status": "running" if process.poll() is None else "stopped",
            "pid": process.pid
        })
    return None
```

**Enhanced Tool Schemas**
Tool definitions should include more detailed input schemas to improve client integration. Example:
```python
@self.mcp.tool(
    input_schema={
        "type": "object",
        "properties": {
            "application": {
                "type": "string",
                "description": "Name of the application to start"
            },
            "mode": {
                "type": "string",
                "enum": ["vnc", "html5"],
                "default": "vnc"
            }
        },
        "required": ["application"]
    }
)
```

**Progress Reporting**
Implement more granular progress reporting for long-running operations:
```python
async def start_application(...):
    await ctx.report_progress(0, 100, "Validating configuration")
    # ... configuration validation ...
    await ctx.report_progress(20, 100, "Starting Xpra process")
    # ... process startup ...
    await ctx.report_progress(100, 100, "Session ready")
```

**Session Event Notifications**
Add support for session state change notifications:
```python
async def _notify_session_change(self, session_id: str, status: str):
    notification = {
        "session_id": session_id,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    await self.mcp.send_notification(
        "notifications/sessions/status_changed",
        notification
    )
```

**Configuration Management**
Move configuration handling to a dedicated module with validation:
```python
@dataclass
class XpraServerConfig:
    bind_address: str = "0.0.0.0"
    default_vnc_port: int = 5900
    default_html_port: int = 8080

    def validate(self):
        if not (1024 <= self.default_vnc_port <= 65535):
            raise ValueError(f"Invalid VNC port: {self.default_vnc_port}")
```

**Error Handling**
Implement domain-specific error types:
```python
class XpraError(Exception):
    """Base error for Xpra-related operations."""
    pass

class SessionError(XpraError):
    """Error related to session operations."""
    pass
```

### Deployment Considerations

**Network Security**
- Implement automatic port conflict detection
- Add support for TLS in HTML5 mode
- Include connection validation and timeout handling

**Resource Management**
- Add session cleanup on server shutdown
- Implement session resource limits
- Monitor system resource usage

**Scalability**
- Support multiple display configurations
- Add session persistence across server restarts
- Implement session migration capabilities

## Contributing

We welcome contributions to improve the Xpra MCP Server. Please see our contributing guidelines for more information.

## License

[Insert License Information]

## Quick Start

### Installation

1. Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get install xpra x11-xserver-utils

# Fedora/RHEL
sudo dnf install xpra xorg-x11-server-utils
```

2. Install the package:
```bash
pip install mcp-xpra-server
```

### Usage

1. Start the server:
```bash
xpra-mcp
```

2. Basic Python client usage:
```python
from mcp.client import Client

async def main():
    client = Client()
    
    # Start a Firefox session
    result = await client.start_application(
        application="firefox",
        mode="html5"
    )
    print(f"Connection instructions: {result}")
    
    # List active sessions
    sessions = await client.list_sessions()
    print(f"Active sessions: {sessions}")
    
    # Stop a session
    await client.stop_session("firefox_:0")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mcp-xpra-server.git
cd mcp-xpra-server
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Run tests:
```bash
pytest tests/
```
