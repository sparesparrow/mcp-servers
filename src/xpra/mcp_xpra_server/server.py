from mcp.server.fastmcp import FastMCP, Context
import asyncio
import subprocess
import os
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from asyncio.subprocess import PIPE

from . import __version__
from .config import ServerConfig
from .session import SessionManager, SessionInfo
from .exceptions import XpraError, SessionError, ConfigurationError, SystemDependencyError
from .utils import check_system_dependencies, get_xpra_binary, setup_logging
from .monitoring import SessionMonitor
from .schemas import (
    START_APPLICATION_SCHEMA,
    STOP_SESSION_SCHEMA,
    LIST_SESSIONS_SCHEMA,
    CONFIGURE_FIREWALL_SCHEMA
)

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
    
    def __init__(self, config: Optional[ServerConfig] = None, session_manager: Optional[SessionManager] = None):
        """Initialize the Xpra MCP server."""
        # Set up logging
        self.logger = setup_logging()
        self.logger.info("Initializing Xpra MCP server...")
        
        # Initialize configuration
        self.config = config or ServerConfig()
        try:
            self.config.validate()
        except ConfigurationError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
            
        # Find xpra binary
        try:
            self.xpra_binary = get_xpra_binary()
            self.logger.info(f"Found xpra binary at: {self.xpra_binary}")
        except RuntimeError as e:
            self.logger.error(f"Failed to find xpra binary: {e}")
            raise SystemDependencyError(str(e))
        
        # Initialize session manager
        storage_path = Path.home() / ".local/share/mcp-xpra-server/sessions"
        self.session_manager = session_manager or SessionManager(storage_path)
        
        # Initialize MCP server
        self.mcp = FastMCP("xpra-server", version=__version__)
        
        # Initialize session monitor
        self.monitor = SessionMonitor(self.mcp)
        
        self.setup_tools()
        self.setup_resources()
        
        self.logger.info("MCP server initialized successfully")
    
    async def _start_xpra_process(self, cmd: List[str]) -> asyncio.subprocess.Process:
        """Start an Xpra process with proper async management."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=PIPE,
            stderr=PIPE,
            limit=1024*1024  # 1MB buffer
        )
        return process

    async def _monitor_process(self, process: asyncio.subprocess.Process):
        """Monitor and clean up finished processes."""
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                self.logger.error(f"Xpra process failed: {stderr.decode()}")
        except asyncio.TimeoutError:
            self.logger.warning("Process monitoring timeout reached")

    def setup_tools(self):
        """Set up MCP tools."""
        
        @self.mcp.tool(name="start_application", description="Start an application in an Xpra session")
        async def start_application(
            ctx: Context,
            application: str,
            mode: str = "vnc",
            display: str = ":0",
            enable_audio: bool = False,
            enable_encryption: bool = False,
            password_file: Optional[str] = None
        ) -> Dict[str, Any]:
            """Start an application in an Xpra session."""
            self.logger.info(f"Starting application {application} in {mode} mode")
            await ctx.report_progress(0, 100)
            
            # Build command
            cmd = [self.xpra_binary, "start", display]
            cmd.extend(["--start-child", application])
            
            port = self.config.default_vnc_port if mode.lower() == "vnc" else self.config.default_html_port
            
            await ctx.report_progress(20, 100)
            
            if mode.lower() == "html5":
                cmd.extend([
                    "--html=on",
                    f"--bind-tcp={self.config.default_bind_address}:{port}"
                ])
            else:
                cmd.extend([f"--bind-tcp={self.config.default_bind_address}:{port}"])
                if enable_encryption:
                    cmd.append("--encryption=AES")
            
            if enable_audio:
                cmd.append("--speaker=on")
            
            if password_file:
                cmd.extend(["--password-file", password_file])
            
            await ctx.report_progress(40, 100)
            
            try:
                process = await self._start_xpra_process(cmd)
                self.logger.info(f"Started Xpra process PID: {process.pid}")
                
                # Add process monitoring task
                asyncio.create_task(self._monitor_process(process))
                
                await ctx.report_progress(60, 100)
                
                # Create session record
                session_info = self.session_manager.create_session(
                    application=application,
                    display=display,
                    mode=mode.upper(),
                    port=port,
                    pid=process.pid
                )
                
                # Add session to monitoring
                self.monitor.add_session(session_info)
                
                await ctx.report_progress(80, 100)
                
                # Generate connection info
                if mode.lower() == "html5":
                    connection_info = {
                        "mode": "HTML5",
                        "url": f"http://<server_ip>:{port}",
                        "notes": "Access via web browser"
                    }
                else:
                    connection_info = {
                        "mode": "VNC",
                        "host": "<server_ip>",
                        "port": port,
                        "notes": "Use a VNC client to connect"
                    }
                
                connection_info["session_id"] = session_info.session_id
                
                self.logger.info(f"Started {application} on {display}")
                await ctx.report_progress(100, 100)
                
                # Store process reference
                session_info.process = process
                
                return connection_info
                
            except Exception as e:
                self.logger.error(f"Process start failed: {str(e)}")
                raise SessionError(f"Process launch failed: {str(e)}")
        
        @self.mcp.tool(name="list_sessions", description="List active Xpra sessions")
        async def list_sessions(ctx: Context) -> Dict[str, Any]:
            """List active Xpra sessions."""
            self.logger.info("Listing active sessions")
            sessions = self.session_manager.list_sessions()
            return {"sessions": [s.to_dict() for s in sessions.values()]}
        
        @self.mcp.tool(name="stop_session", description="Stop an active Xpra session")
        async def stop_session(ctx: Context, session_id: str) -> Dict[str, str]:
            """Stop an active Xpra session."""
            self.logger.info(f"Stopping session {session_id}")
            
            session_info = self.session_manager.get_session(session_id)
            if not session_info:
                raise SessionError(f"Session {session_id} not found")
            
            # Stop the Xpra process
            if session_info.process:
                try:
                    session_info.process.terminate()
                    await asyncio.wait_for(session_info.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.logger.warning(f"Force killing PID {session_info.process.pid}")
                    session_info.process.kill()
                    
                self.monitor.remove_session(session_id)
                self.session_manager.remove_session(session_id)
                self.logger.info(f"Stopped session {session_id}")
                return {"status": "success", "message": f"Session {session_id} stopped successfully"}
            else:
                # Fallback to command-line stop if no process reference
                cmd = [self.xpra_binary, "stop", session_info.display]
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    self.monitor.remove_session(session_id)
                    self.session_manager.remove_session(session_id)
                    self.logger.info(f"Stopped session {session_id}")
                    return {"status": "success", "message": f"Session {session_id} stopped successfully"}
                except subprocess.CalledProcessError as e:
                    error = e.stderr.decode()
                    self.logger.error(f"Failed to stop session {session_id}: {error}")
                    raise SessionError(f"Failed to stop session: {error}")
        
        @self.mcp.tool(name="configure_firewall", description="Configure firewall rules for Xpra access")
        async def configure_firewall(ctx: Context, mode: str = "vnc") -> Dict[str, str]:
            """Configure firewall rules for Xpra access."""
            port = self.config.default_vnc_port if mode.lower() == "vnc" else self.config.default_html_port
            
            try:
                subprocess.run(
                    ["sudo", "ufw", "allow", str(port)],
                    check=True,
                    capture_output=True
                )
                self.logger.info(f"Configured firewall for {mode.upper()} mode on port {port}")
                return {
                    "status": "success",
                    "message": f"Firewall configured for {mode.upper()} mode (port {port})"
                }
            except subprocess.CalledProcessError as e:
                error = e.stderr.decode()
                self.logger.error(f"Failed to configure firewall: {error}")
                raise ConfigurationError(f"Failed to configure firewall: {error}")
    
    def setup_resources(self):
        """Set up MCP resources."""
        
        @self.mcp.resource("http://localhost/sessions")
        async def get_sessions() -> Dict[str, Any]:
            """Get all active sessions."""
            sessions = self.session_manager.list_sessions()
            return {"sessions": [s.to_dict() for s in sessions.values()]}
        
        @self.mcp.resource("http://localhost/sessions/{session_id}")
        async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
            """Get information about a specific session."""
            session = self.session_manager.get_session(session_id)
            return session.to_dict() if session else None
    
    async def startup(self):
        """Perform startup tasks."""
        await self.monitor.start()
        self.session_manager.cleanup_stale_sessions()
    
    async def shutdown(self):
        """Cleanup processes on shutdown."""
        self.logger.info("Stopping all Xpra sessions")
        for session in self.session_manager.list_sessions().values():
            if session.process and session.process.returncode is None:
                try:
                    session.process.terminate()
                    await asyncio.wait_for(session.process.wait(), timeout=5)
                except (subprocess.SubprocessError, asyncio.TimeoutError) as e:
                    self.logger.warning(f"Force killing PID {session.process.pid}")
                    session.process.kill()
        await self.monitor.stop()
        self.session_manager.cleanup_stale_sessions()
    
    def run(self):
        """Run the MCP server."""
        self.logger.info("Starting MCP server")
        
        # Create event loop for startup/shutdown
        loop = asyncio.get_event_loop()
        
        try:
            # Run startup tasks
            loop.run_until_complete(self.startup())
            
            # Run MCP server
            self.mcp.run()
            
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise
        finally:
            # Run shutdown tasks
            loop.run_until_complete(self.shutdown())

def main():
    """Main entry point."""
    try:
        error = check_system_dependencies()
        if error:
            raise SystemDependencyError(error)
            
        server = XpraServer()
        server.run()
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    main()