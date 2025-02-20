"""Test configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path

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