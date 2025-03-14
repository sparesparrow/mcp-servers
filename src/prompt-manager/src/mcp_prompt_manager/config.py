"""Configuration module for the MCP Prompt Manager server."""
import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger("mcp-prompt-manager.config")

# Default configuration
DEFAULT_CONFIG = {
    "server_name": "prompt-manager",
    "log_level": "INFO",
    "template_dir": None,  # If None, only built-in templates are used
    "persistence": False,  # Whether to save added templates to disk
    "persistence_file": None,  # Path to persistence file, if None uses default
}

class Config:
    """Configuration manager for the MCP Prompt Manager server."""
    
    def __init__(self):
        """Initialize with default configuration."""
        self._config = DEFAULT_CONFIG.copy()
        self._loaded = False
    
    def load(self, config_path: Optional[str] = None) -> None:
        """Load configuration from a JSON file."""
        if config_path is None:
            # Look for config in standard locations
            paths_to_try = [
                # Current directory
                Path.cwd() / "prompt_manager_config.json", 
                # User config directory
                Path.home() / ".config" / "mcp-prompt-manager" / "config.json",
                # System config directory (Linux/Mac)
                Path("/etc/mcp-prompt-manager/config.json"),
                # System config directory (Windows)
                Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "mcp-prompt-manager" / "config.json"
            ]
            
            for path in paths_to_try:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                
                # Update default config with user settings
                self._config.update(user_config)
                self._loaded = True
                logger.info(f"Loaded configuration from {config_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading configuration from {config_path}: {e}")
                # Continue with default config
        else:
            if config_path:
                logger.warning(f"Configuration file not found at {config_path}, using defaults")
            else:
                logger.info("No configuration file specified, using defaults")
                
        # Set up persistence file if needed
        if self._config["persistence"] and not self._config["persistence_file"]:
            # Default persistence file location
            persistence_dir = Path.home() / ".local" / "share" / "mcp-prompt-manager"
            os.makedirs(persistence_dir, exist_ok=True)
            self._config["persistence_file"] = str(persistence_dir / "templates.json")
    
    def from_env(self) -> None:
        """Load configuration from environment variables."""
        # Map of environment variables to config keys
        env_map = {
            "MCP_PROMPT_MANAGER_NAME": "server_name",
            "MCP_PROMPT_MANAGER_LOG_LEVEL": "log_level",
            "MCP_PROMPT_MANAGER_TEMPLATE_DIR": "template_dir",
            "MCP_PROMPT_MANAGER_PERSISTENCE": "persistence",
            "MCP_PROMPT_MANAGER_PERSISTENCE_FILE": "persistence_file",
        }
        
        for env_var, config_key in env_map.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert string boolean values
                if config_key == "persistence":
                    value = value.lower() in ("true", "yes", "1")
                
                self._config[config_key] = value
                logger.debug(f"Set {config_key} from environment: {value}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config[key] = value
        
    @property
    def server_name(self) -> str:
        """Get the server name."""
        return self._config["server_name"]
    
    @property
    def log_level(self) -> str:
        """Get the log level."""
        return self._config["log_level"]
    
    @property
    def template_dir(self) -> Optional[str]:
        """Get the template directory."""
        return self._config["template_dir"]
    
    @property
    def persistence(self) -> bool:
        """Check if persistence is enabled."""
        return self._config["persistence"]
    
    @property
    def persistence_file(self) -> Optional[str]:
        """Get the persistence file path."""
        return self._config["persistence_file"]
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self._config.copy()

# Global configuration instance
config = Config() 