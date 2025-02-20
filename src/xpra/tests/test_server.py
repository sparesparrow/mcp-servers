"""Tests for the Xpra MCP server."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import shutil
import json
import os

from mcp.server.fastmcp.exceptions import ToolError
from mcp_xpra_server.server import XpraServer
from mcp_xpra_server.exceptions import SessionError, ConfigurationError
from mcp_xpra_server.config import ServerConfig
from mcp_xpra_server.session import SessionManager

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def config(temp_dir):
    """Create a test configuration."""
    return ServerConfig(
        log_dir=temp_dir / "logs",
        default_vnc_port=5900,
        default_html_port=8080
    )

@pytest.fixture
def session_manager(temp_dir):
    """Create a test session manager."""
    return SessionManager(temp_dir / "sessions")

@pytest.fixture
def server(config, session_manager):
    """Create a test server instance."""
    with patch("mcp_xpra_server.server.get_xpra_binary") as mock_get_binary:
        mock_get_binary.return_value = "/usr/bin/xpra"
        server = XpraServer(config=config, session_manager=session_manager)
        yield server

def test_server_initialization(server):
    """Test server initialization."""
    assert server.config is not None
    assert server.session_manager is not None
    assert server.xpra_binary == "/usr/bin/xpra"

@pytest.mark.asyncio
async def test_start_application(server):
    """Test starting an application."""
    with patch("asyncio.create_subprocess_exec") as mock_create_subprocess:
        # Setup mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.wait = Mock(return_value=None)
        mock_create_subprocess.return_value = mock_process

        # Mock request context
        request_context = Mock()
        request_context.meta = Mock()
        request_context.meta.progressToken = "test_token"
        request_context.session = Mock()
        request_context.session.send_progress_notification = AsyncMock()
        request_context.request_id = "test_request"
        
        # Create context
        context = server.mcp.get_context()
        context._request_context = request_context
        context._fastmcp = server.mcp
        
        # Patch get_context
        server.mcp.get_context = Mock(return_value=context)

        # Call start_application through MCP tool
        result = await server.mcp.call_tool("start_application", {
            "application": "firefox",
            "mode": "vnc",
            "display": ":0"
        })

        # Extract result from TextContent
        result_dict = json.loads(result[0].text)

        # Verify process was started
        assert mock_create_subprocess.called
        assert result_dict["session_id"] is not None
        assert result_dict["mode"] == "VNC"
        assert result_dict["port"] == server.config.default_vnc_port

@pytest.mark.asyncio
async def test_invalid_session_stop(server):
    """Test stopping a non-existent session."""
    # Mock request context
    request_context = Mock()
    request_context.meta = Mock()
    request_context.meta.progressToken = "test_token"
    request_context.session = Mock()
    request_context.session.send_progress_notification = AsyncMock()
    request_context.request_id = "test_request"
    
    # Create context
    context = server.mcp.get_context()
    context._request_context = request_context
    context._fastmcp = server.mcp
    
    # Patch get_context
    server.mcp.get_context = Mock(return_value=context)

    # Call stop_session through MCP tool
    with pytest.raises(ToolError) as exc_info:
        await server.mcp.call_tool("stop_session", {
            "session_id": "nonexistent_session"
        })
    assert "Session nonexistent_session not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_list_sessions(server):
    """Test listing sessions."""
    with patch("asyncio.create_subprocess_exec") as mock_create_subprocess:
        # Setup mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_create_subprocess.return_value = mock_process

        # Mock request context
        request_context = Mock()
        request_context.meta = Mock()
        request_context.meta.progressToken = "test_token"
        request_context.session = Mock()
        request_context.session.send_progress_notification = AsyncMock()
        request_context.request_id = "test_request"
        
        # Create context
        context = server.mcp.get_context()
        context._request_context = request_context
        context._fastmcp = server.mcp
        
        # Patch get_context
        server.mcp.get_context = Mock(return_value=context)

        # Start a test session
        start_result = await server.mcp.call_tool("start_application", {
            "application": "firefox",
            "mode": "vnc",
            "display": ":0"
        })

        # List sessions
        result = await server.mcp.call_tool("list_sessions", {})

        # Extract result from TextContent
        result_dict = json.loads(result[0].text)

        # Verify session is listed
        assert len(result_dict["sessions"]) == 1
        assert result_dict["sessions"][0]["application"] == "firefox"

@pytest.mark.asyncio
async def test_stop_session(server):
    """Test stopping a session."""
    with patch("asyncio.create_subprocess_exec") as mock_create_subprocess:
        # Setup mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.terminate = Mock()
        mock_create_subprocess.return_value = mock_process

        # Mock request context
        request_context = Mock()
        request_context.meta = Mock()
        request_context.meta.progressToken = "test_token"
        request_context.session = Mock()
        request_context.session.send_progress_notification = AsyncMock()
        request_context.request_id = "test_request"
        
        # Create context
        context = server.mcp.get_context()
        context._request_context = request_context
        context._fastmcp = server.mcp
        
        # Patch get_context
        server.mcp.get_context = Mock(return_value=context)

        # Start a test session
        start_result = await server.mcp.call_tool("start_application", {
            "application": "firefox",
            "mode": "vnc",
            "display": ":0"
        })

        # Extract session_id from start result
        start_result_dict = json.loads(start_result[0].text)

        # Stop the session
        stop_result = await server.mcp.call_tool("stop_session", {
            "session_id": start_result_dict["session_id"]
        })

        # Extract result from TextContent
        stop_result_dict = json.loads(stop_result[0].text)

        # Verify session was stopped
        assert stop_result_dict["status"] == "success"
        assert mock_process.terminate.called 