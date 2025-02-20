from mcp.server.fastmcp import FastMCP, Context
import asyncio
import subprocess
import os
import json
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

class DisplayMode(str, Enum):
    VNC = "vnc"
    HTML5 = "html5"

@dataclass
class XpraConfig:
    """Configuration for an Xpra session."""
    display: str = ":0"
    bind_address: str = "0.0.0.0"
    vnc_port: int = 5900
    html_port: int = 8080
    password_file: Optional[str] = None
    enable_audio: bool = False
    enable_encryption: bool = False
    read_only: bool = True

class XpraServer:
    """MCP server for managing Xpra sessions."""
    
    def __init__(self):
        """Initialize the Xpra MCP server."""
        self.mcp = FastMCP("xpra-server")
        self.active_sessions: Dict[str, subprocess.Popen] = {}
        self.setup_tools()
        
    def setup_tools(self):
        """Set up MCP tools."""
        
        @self.mcp.tool()
        async def start_application(
            application: str,
            mode: str = "vnc",
            display: str = ":0",
            enable_audio: bool = False,
            enable_encryption: bool = False,
            password_file: Optional[str] = None,
            ctx: Context = None
        ) -> str:
            """Start an application in an Xpra session.
            
            Args:
                application: Name of the application to start
                mode: Display mode ('vnc' or 'html5')
                display: X display number (e.g., ':0')
                enable_audio: Enable audio forwarding
                enable_encryption: Enable AES encryption (VNC mode only)
                password_file: Path to password file for authentication
            
            Returns:
                str: Connection instructions for the client
            """
            config = XpraConfig(
                display=display,
                password_file=password_file,
                enable_audio=enable_audio,
                enable_encryption=enable_encryption
            )
            
            # Build command based on mode
            cmd = ["xpra", "start", config.display]
            cmd.extend(["--start-child", application])
            cmd.append("--read-only" if config.read_only else "")
            
            if mode.lower() == "html5":
                cmd.extend([
                    "--html=on",
                    f"--bind-tcp={config.bind_address}:{config.html_port}"
                ])
            else:  # VNC mode
                cmd.extend([f"--bind-tcp={config.bind_address}:{config.vnc_port}"])
                if config.enable_encryption:
                    cmd.append("--encryption=AES")
            
            if config.enable_audio:
                cmd.append("--speaker=on")
            
            if config.password_file:
                cmd.extend(["--password-file", config.password_file])
            
            try:
                # Start Xpra process
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Store process reference
                session_id = f"{application}_{display}"
                self.active_sessions[session_id] = process
                
                # Generate connection instructions
                if mode.lower() == "html5":
                    connection_info = {
                        "mode": "HTML5",
                        "url": f"http://<server_ip>:{config.html_port}",
                        "notes": "Access via web browser"
                    }
                else:
                    connection_info = {
                        "mode": "VNC",
                        "host": "<server_ip>",
                        "port": config.vnc_port,
                        "notes": "Use a VNC client to connect"
                    }
                
                # Log progress
                if ctx:
                    ctx.info(f"Started {application} on {display}")
                
                return json.dumps(connection_info, indent=2)
                
            except Exception as e:
                if ctx:
                    ctx.error(f"Failed to start {application}: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def list_sessions(ctx: Context = None) -> str:
            """List active Xpra sessions.
            
            Returns:
                str: JSON formatted list of active sessions
            """
            sessions = []
            for session_id, process in self.active_sessions.items():
                if process.poll() is None:  # Check if process is still running
                    app_name = session_id.split('_')[0]
                    display = session_id.split('_')[1]
                    sessions.append({
                        "application": app_name,
                        "display": display,
                        "status": "running"
                    })
            
            if ctx:
                ctx.info(f"Found {len(sessions)} active sessions")
            
            return json.dumps(sessions, indent=2)
        
        @self.mcp.tool()
        async def stop_session(
            session_id: str,
            ctx: Context = None
        ) -> str:
            """Stop an active Xpra session.
            
            Args:
                session_id: ID of the session to stop (format: "application_display")
            
            Returns:
                str: Status message
            """
            if session_id in self.active_sessions:
                process = self.active_sessions[session_id]
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    try:
                        process.wait(timeout=5)  # Wait for clean shutdown
                    except subprocess.TimeoutExpired:
                        process.kill()  # Force kill if it doesn't shut down
                    
                    if ctx:
                        ctx.info(f"Stopped session {session_id}")
                    
                    del self.active_sessions[session_id]
                    return f"Session {session_id} stopped successfully"
                else:
                    if ctx:
                        ctx.warn(f"Session {session_id} was already stopped")
                    return f"Session {session_id} was not running"
            else:
                if ctx:
                    ctx.error(f"Session {session_id} not found")
                raise ValueError(f"Session {session_id} not found")
        
        @self.mcp.tool()
        async def configure_firewall(
            mode: str = "vnc",
            ctx: Context = None
        ) -> str:
            """Configure firewall rules for Xpra.
            
            Args:
                mode: Display mode ('vnc' or 'html5')
            
            Returns:
                str: Status message
            """
            try:
                if mode.lower() == "html5":
                    subprocess.run(
                        ["sudo", "ufw", "allow", "8080"],
                        check=True
                    )
                    if ctx:
                        ctx.info("Opened port 8080 for HTML5 mode")
                    return "Firewall configured for HTML5 mode (port 8080)"
                else:
                    subprocess.run(
                        ["sudo", "ufw", "allow", "5900"],
                        check=True
                    )
                    if ctx:
                        ctx.info("Opened port 5900 for VNC mode")
                    return "Firewall configured for VNC mode (port 5900)"
            except subprocess.CalledProcessError as e:
                if ctx:
                    ctx.error(f"Firewall configuration failed: {str(e)}")
                raise
    
    def run(self):
        """Run the MCP server."""
        self.mcp.run()

def main():
    """Main entry point."""
    server = XpraServer()
    server.run()

if __name__ == "__main__":
    main()
