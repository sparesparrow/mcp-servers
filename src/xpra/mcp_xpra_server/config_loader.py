import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .config import ServerConfig
from .exceptions import ConfigurationError

DEFAULT_CONFIG_PATHS = [
    "/etc/mcp-xpra-server/xpra.yaml",
    "~/.config/mcp-xpra-server/xpra.yaml",
    "./config/xpra.yaml"
]

def load_config(config_path: str) -> ServerConfig:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ServerConfig instance
        
    Raises:
        ConfigurationError: If configuration is invalid or cannot be loaded
    """
    try:
        with open(os.path.expanduser(config_path)) as f:
            config_data = yaml.safe_load(f)
            
        # Extract server settings
        server_config = config_data.get("server", {})
        
        # Extract logging settings
        logging_config = config_data.get("logging", {})
        log_dir = Path(os.path.expanduser(logging_config.get("directory", "~/.local/share/mcp-xpra-server/logs")))
        
        config = ServerConfig(
            log_dir=log_dir,
            default_bind_address=server_config.get("bind_address", "0.0.0.0"),
            default_vnc_port=server_config.get("vnc_port", 5900),
            default_html_port=server_config.get("html_port", 8080),
            min_memory_mb=server_config.get("min_memory_mb", 512)
        )
        
        # Validate configuration
        config.validate()
        return config
        
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Failed to parse configuration file: {e}")
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}")

def load_config_old(config_path: Optional[str] = None) -> ServerConfig:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file, or None to search default locations
        
    Returns:
        ServerConfig instance
        
    Raises:
        ConfigurationError: If configuration is invalid or cannot be loaded
    """
    # Find configuration file
    if config_path:
        config_file = Path(os.path.expanduser(config_path))
        if not config_file.is_file():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
    else:
        for path in DEFAULT_CONFIG_PATHS:
            config_file = Path(os.path.expanduser(path))
            if config_file.is_file():
                break
        else:
            # No config file found, use defaults
            return ServerConfig()
    
    try:
        # Load YAML configuration
        with open(config_file) as f:
            yaml_config = yaml.safe_load(f)
            
        # Extract server settings
        server_config = yaml_config.get("server", {})
        config = ServerConfig(
            log_dir=Path(os.path.expanduser(yaml_config.get("logging", {}).get("directory", ServerConfig.log_dir))),
            default_bind_address=server_config.get("bind_address", ServerConfig.default_bind_address),
            default_vnc_port=server_config.get("vnc_port", ServerConfig.default_vnc_port),
            default_html_port=server_config.get("html_port", ServerConfig.default_html_port),
            min_memory_mb=server_config.get("min_memory_mb", ServerConfig.min_memory_mb)
        )
        
        # Validate configuration
        config.validate()
        return config
        
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Failed to parse configuration file: {e}")
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") 