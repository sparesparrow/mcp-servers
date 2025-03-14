"""
Configuration Manager for MCP Servers

Provides a centralized way to manage configuration across different MCP servers,
supporting multiple sources (environment variables, config files, command-line arguments)
with validation and sensible defaults.
"""

import os
import sys
import json
import yaml
import argparse
import logging
from typing import Dict, Any, Optional, Union, List, Type, get_type_hints, get_origin, get_args
from dataclasses import dataclass, field, asdict, is_dataclass
import re

logger = logging.getLogger('mcp.config')

@dataclass
class ServerConfig:
    """Base configuration for MCP servers."""
    server_id: str
    server_name: str
    server_description: str = "MCP Server"
    server_version: str = "1.0.0"
    
    # Router integration
    router_integration_enabled: bool = True
    router_url: str = "http://localhost:3000"
    router_health_check_interval: int = 60
    router_retry_interval: int = 5
    router_max_retries: int = 3
    
    # Server endpoints
    server_host: str = "localhost"
    server_port: int = 8000
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Security
    auth_enabled: bool = False
    auth_token: Optional[str] = None
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    
    # Cache
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    # Custom capabilities
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        return yaml.dump(self.to_dict())

class ConfigManager:
    """
    Configuration manager for MCP servers that loads configuration
    from multiple sources with priority order:
    1. Command-line arguments
    2. Environment variables
    3. Configuration file
    4. Default values
    """
    
    def __init__(
        self,
        config_class: Type[ServerConfig] = ServerConfig,
        env_prefix: str = "MCP",
        config_file_env_var: str = "MCP_CONFIG_FILE",
        default_config_paths: List[str] = None
    ):
        """
        Initialize the configuration manager.
        
        Args:
            config_class: Dataclass type for configuration
            env_prefix: Prefix for environment variables
            config_file_env_var: Environment variable for config file path
            default_config_paths: List of default paths to look for config file
        """
        self.config_class = config_class
        self.env_prefix = env_prefix
        self.config_file_env_var = config_file_env_var
        self.default_config_paths = default_config_paths or [
            "./config.json",
            "./config.yaml",
            "./config.yml",
            os.path.expanduser("~/.mcp/config.json"),
            os.path.expanduser("~/.mcp/config.yaml"),
            os.path.expanduser("~/.mcp/config.yml"),
            "/etc/mcp/config.json",
            "/etc/mcp/config.yaml",
            "/etc/mcp/config.yml"
        ]
        
        # Initialize configuration
        self.config = None
    
    def load_config(self, args: Optional[List[str]] = None) -> ServerConfig:
        """
        Load configuration from all sources.
        
        Args:
            args: Command-line arguments (uses sys.argv if None)
            
        Returns:
            Configuration object
        """
        # Create default configuration
        config_dict = self._create_default_config()
        
        # Load configuration from file
        config_dict = self._merge_config(config_dict, self._load_from_file())
        
        # Load configuration from environment variables
        config_dict = self._merge_config(config_dict, self._load_from_env())
        
        # Load configuration from command-line arguments
        config_dict = self._merge_config(config_dict, self._load_from_args(args))
        
        # Create configuration object
        self.config = self._create_config_object(config_dict)
        
        # Configure logging
        self._configure_logging()
        
        return self.config
    
    def get_config(self) -> ServerConfig:
        """
        Get the current configuration.
        
        Returns:
            Configuration object
        
        Raises:
            RuntimeError: If configuration is not loaded
        """
        if self.config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        
        return self.config
    
    def _create_default_config(self) -> Dict[str, Any]:
        """
        Create default configuration.
        
        Returns:
            Default configuration as dictionary
        """
        return asdict(self.config_class(
            server_id=f"mcp-server-{os.getpid()}",
            server_name="MCP Server"
        ))
    
    def _load_from_file(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration from file as dictionary
        """
        # Check environment variable for config file path
        config_path = os.environ.get(self.config_file_env_var)
        
        # If not set, check default paths
        if not config_path:
            for path in self.default_config_paths:
                if os.path.isfile(path):
                    config_path = path
                    break
        
        # If no config file found, return empty dictionary
        if not config_path or not os.path.isfile(config_path):
            return {}
        
        try:
            # Load configuration from file
            with open(config_path, 'r') as f:
                if config_path.endswith('.json'):
                    return json.load(f)
                elif config_path.endswith(('.yaml', '.yml')):
                    return yaml.safe_load(f)
                else:
                    logger.warning(f"Unknown configuration file format: {config_path}")
                    return {}
        except Exception as e:
            logger.warning(f"Error loading configuration from file {config_path}: {str(e)}")
            return {}
    
    def _load_from_env(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Returns:
            Configuration from environment variables as dictionary
        """
        config = {}
        
        # Get all environment variables with the prefix
        env_prefix = f"{self.env_prefix}_".upper()
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # Convert environment variable name to config key
                config_key = self._env_to_config_key(key[len(env_prefix):])
                
                # Parse value
                config_value = self._parse_value(value)
                
                # Set config value
                config = self._set_nested_key(config, config_key, config_value)
        
        return config
    
    def _load_from_args(self, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load configuration from command-line arguments.
        
        Args:
            args: Command-line arguments (uses sys.argv if None)
            
        Returns:
            Configuration from command-line arguments as dictionary
        """
        # Create argument parser
        parser = argparse.ArgumentParser(description=f"{self.config_class.__name__} Configuration")
        
        # Add arguments based on config class fields
        type_hints = get_type_hints(self.config_class)
        for field_name, field_type in type_hints.items():
            # Convert field name from snake_case to kebab-case for command-line arguments
            arg_name = f"--{field_name.replace('_', '-')}"
            
            # Determine argument type and default value
            arg_type = self._get_argument_type(field_type)
            
            # Add argument
            if field_type == bool or get_origin(field_type) is Union and bool in get_args(field_type):
                # For boolean flags
                parser.add_argument(
                    arg_name,
                    action='store_true',
                    help=f"{field_name} (boolean flag)"
                )
                negated_arg_name = f"--no-{field_name.replace('_', '-')}"
                parser.add_argument(
                    negated_arg_name,
                    action='store_false',
                    dest=field_name,
                    help=f"Disable {field_name} (boolean flag)"
                )
            elif get_origin(field_type) is list or get_origin(field_type) is List:
                # For list arguments
                parser.add_argument(
                    arg_name,
                    type=str,
                    nargs='+',
                    help=f"{field_name} (list of items)"
                )
            else:
                # For regular arguments
                parser.add_argument(
                    arg_name,
                    type=arg_type,
                    help=f"{field_name} ({self._get_type_name(field_type)})"
                )
        
        # Parse arguments
        parsed_args = parser.parse_args(args)
        
        # Convert to dictionary
        config = {}
        for key, value in vars(parsed_args).items():
            if value is not None:
                config = self._set_nested_key(config, key, value)
        
        return config
    
    def _create_config_object(self, config_dict: Dict[str, Any]) -> ServerConfig:
        """
        Create configuration object from dictionary.
        
        Args:
            config_dict: Configuration as dictionary
            
        Returns:
            Configuration object
        """
        return self.config_class(**config_dict)
    
    def _merge_config(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge configuration dictionaries.
        
        Args:
            base: Base configuration
            overlay: Overlay configuration that takes precedence
            
        Returns:
            Merged configuration
        """
        # Create a copy of the base configuration
        result = base.copy()
        
        # Merge overlay configuration
        for key, value in overlay.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                # Recursively merge nested dictionaries
                result[key] = self._merge_config(result[key], value)
            else:
                # Override base value with overlay value
                result[key] = value
        
        return result
    
    def _env_to_config_key(self, env_key: str) -> str:
        """
        Convert environment variable name to configuration key.
        
        Args:
            env_key: Environment variable name (without prefix)
            
        Returns:
            Configuration key
        """
        # Convert to lowercase
        key = env_key.lower()
        
        # Replace double underscores with dots for nested keys
        key = key.replace('__', '.')
        
        return key
    
    def _parse_value(self, value: str) -> Any:
        """
        Parse string value to appropriate type.
        
        Args:
            value: String value
            
        Returns:
            Parsed value
        """
        # Check for boolean values
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # Check for integer values
        try:
            return int(value)
        except ValueError:
            pass
        
        # Check for float values
        try:
            return float(value)
        except ValueError:
            pass
        
        # Check for list values (comma-separated)
        if ',' in value:
            return [self._parse_value(item.strip()) for item in value.split(',')]
        
        # Return as string
        return value
    
    def _get_argument_type(self, field_type: Type) -> Type:
        """
        Get argument type for command-line argument parser.
        
        Args:
            field_type: Field type
            
        Returns:
            Argument type
        """
        # Handle Union types (e.g., Optional)
        if get_origin(field_type) is Union:
            # Use the first non-None type
            for arg_type in get_args(field_type):
                if arg_type is not type(None):
                    return self._get_argument_type(arg_type)
        
        # Handle List types
        if get_origin(field_type) is list or get_origin(field_type) is List:
            # Use string for list items
            return str
        
        # Handle basic types
        if field_type is bool:
            return bool
        elif field_type is int:
            return int
        elif field_type is float:
            return float
        elif field_type is str:
            return str
        
        # Default to string
        return str
    
    def _get_type_name(self, field_type: Type) -> str:
        """
        Get human-readable type name.
        
        Args:
            field_type: Field type
            
        Returns:
            Type name
        """
        # Handle Union types (e.g., Optional)
        if get_origin(field_type) is Union:
            # Use the first non-None type
            types = []
            for arg_type in get_args(field_type):
                if arg_type is not type(None):
                    types.append(self._get_type_name(arg_type))
            
            if len(types) == 1:
                return f"Optional[{types[0]}]"
            else:
                return f"Union[{', '.join(types)}]"
        
        # Handle List types
        if get_origin(field_type) is list or get_origin(field_type) is List:
            if get_args(field_type):
                return f"List[{self._get_type_name(get_args(field_type)[0])}]"
            else:
                return "List"
        
        # Handle basic types
        return field_type.__name__
    
    def _set_nested_key(self, config: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """
        Set nested key in configuration dictionary.
        
        Args:
            config: Configuration dictionary
            key: Key to set (can be nested with dots)
            value: Value to set
            
        Returns:
            Updated configuration dictionary
        """
        # Handle nested keys (with dots)
        if '.' in key:
            parts = key.split('.', 1)
            parent_key = parts[0]
            child_key = parts[1]
            
            # Initialize parent if it doesn't exist
            if parent_key not in config:
                config[parent_key] = {}
            
            # Recursively set nested key
            config[parent_key] = self._set_nested_key(config[parent_key], child_key, value)
        else:
            # Set key directly
            config[key] = value
        
        return config
    
    def _configure_logging(self):
        """Configure logging based on configuration."""
        if not self.config:
            return
        
        # Configure root logger
        root_logger = logging.getLogger()
        
        # Set log level
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        root_logger.setLevel(log_level)
        
        # Add file handler if log file is specified
        if self.config.log_file:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(self.config.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Add file handler
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            root_logger.addHandler(file_handler)
        
        # Log configuration loading
        logger.info(f"Loaded configuration for {self.config.server_name} (ID: {self.config.server_id})")

def create_config_manager(
    config_class: Type[ServerConfig] = ServerConfig,
    env_prefix: str = "MCP",
    args: Optional[List[str]] = None
) -> ServerConfig:
    """
    Create and initialize a configuration manager.
    
    Args:
        config_class: Configuration class (must be a dataclass)
        env_prefix: Prefix for environment variables
        args: Command-line arguments (uses sys.argv if None)
        
    Returns:
        Loaded configuration
    
    Raises:
        TypeError: If config_class is not a dataclass
    """
    # Validate config class
    if not is_dataclass(config_class):
        raise TypeError(f"config_class must be a dataclass, got {type(config_class)}")
    
    # Create and initialize config manager
    manager = ConfigManager(config_class=config_class, env_prefix=env_prefix)
    config = manager.load_config(args=args)
    
    return config
