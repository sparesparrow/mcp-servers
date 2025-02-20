from dataclasses import dataclass
from typing import Optional
import os
from pathlib import Path

from .exceptions import ConfigurationError

@dataclass
class ServerConfig:
    """Configuration for the Xpra MCP server."""
    log_dir: Path = Path.home() / ".local/share/mcp-xpra-server/logs"
    default_bind_address: str = "0.0.0.0"
    default_vnc_port: int = 5900
    default_html_port: int = 8080
    min_memory_mb: int = 512
    
    def __post_init__(self):
        """Convert string paths to Path objects and ensure directories exist."""
        if isinstance(self.log_dir, str):
            self.log_dir = Path(self.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """Validate configuration values."""
        if not (1024 <= self.default_vnc_port <= 65535):
            raise ConfigurationError(f"Invalid VNC port: {self.default_vnc_port}")
            
        if not (1024 <= self.default_html_port <= 65535):
            raise ConfigurationError(f"Invalid HTML port: {self.default_html_port}")
            
        if not isinstance(self.default_bind_address, str):
            raise ConfigurationError(f"Invalid bind address type: {type(self.default_bind_address)}")
            
        if self.min_memory_mb < 256:
            raise ConfigurationError(f"Minimum memory requirement too low: {self.min_memory_mb}MB") 