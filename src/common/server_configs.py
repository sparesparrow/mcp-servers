"""
Specialized Configuration Classes for MCP Servers

This module provides specialized configuration classes for various MCP servers
that extend the base ServerConfig class with server-specific configuration options.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from .config_manager import ServerConfig

@dataclass
class OrchestratorConfig(ServerConfig):
    """Configuration for the Code Diagram Orchestrator server."""
    
    # API Keys
    api_key: Optional[str] = None
    
    # Orchestration settings
    orchestration_timeout: int = 300  # seconds
    worker_timeout: int = 60  # seconds
    max_concurrent_workers: int = 5
    
    # Cache settings
    diagram_cache_ttl: int = 3600  # seconds
    analysis_cache_ttl: int = 3600  # seconds
    documentation_cache_ttl: int = 3600  # seconds
    
    # Debug settings
    debug_mode: bool = False
    trace_mode: bool = False
    
    # Default capabilities
    capabilities: List[str] = field(default_factory=lambda: [
        "code-analysis",
        "code-visualization",
        "documentation-generation",
        "diagram-generation"
    ])

@dataclass
class ProjectOrchestratorConfig(ServerConfig):
    """Configuration for the Project Orchestrator server."""
    
    # Project settings
    projects_dir: str = "./projects"
    templates_file: str = "./project_templates.json"
    component_templates_file: str = "./component_templates.json"
    
    # Output settings
    readme_template_file: Optional[str] = None
    
    # Design pattern detection
    pattern_detection_threshold: float = 0.7
    
    # Integration settings
    github_integration_enabled: bool = False
    github_token: Optional[str] = None
    
    # Default capabilities
    capabilities: List[str] = field(default_factory=lambda: [
        "project-orchestration",
        "project-template-application",
        "project-structure-generation",
        "mermaid-diagram-generation",
        "design-pattern-analysis"
    ])

@dataclass
class PromptsServerConfig(ServerConfig):
    """Configuration for the Prompts server."""
    
    # Storage settings
    prompts_dir: str = "./prompts"
    database_url: Optional[str] = None
    
    # Export/Import settings
    export_format: str = "json"
    allow_remote_imports: bool = False
    
    # Versioning
    enable_versioning: bool = True
    max_versions_to_keep: int = 10
    
    # Template settings
    template_extension: str = "mustache"
    template_variables_required: bool = True
    
    # Backup settings
    backup_enabled: bool = True
    backup_interval: int = 86400  # seconds (1 day)
    backup_dir: str = "./backups"
    max_backups_to_keep: int = 7
    
    # Default capabilities
    capabilities: List[str] = field(default_factory=lambda: [
        "prompt-management",
        "prompt-template-application",
        "prompt-versioning",
        "prompt-import-export"
    ])

@dataclass
class MemoryServerConfig(ServerConfig):
    """Configuration for the Memory server."""
    
    # Storage settings
    storage_type: str = "memory"  # Options: memory, file, database
    storage_file: Optional[str] = None
    database_url: Optional[str] = None
    
    # Memory settings
    max_entities: int = 1000
    max_relations: int = 5000
    max_observations_per_entity: int = 100
    
    # Embedding settings
    embedding_enabled: bool = False
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimensions: int = 1536
    
    # Search settings
    search_exact_match_boost: float = 2.0
    search_partial_match_boost: float = 1.0
    search_embedding_boost: float = 1.5
    search_max_results: int = 20
    
    # Default capabilities
    capabilities: List[str] = field(default_factory=lambda: [
        "knowledge-graph-management",
        "entity-storage",
        "relation-management",
        "graph-querying"
    ])

@dataclass
class FilesystemServerConfig(ServerConfig):
    """Configuration for the Filesystem server."""
    
    # File access settings
    allowed_directories: List[str] = field(default_factory=list)
    root_directory: Optional[str] = None
    virtual_root_enabled: bool = True
    
    # Security settings
    allow_write_operations: bool = True
    allow_execute_operations: bool = False
    allow_delete_operations: bool = True
    allowed_file_types: List[str] = field(default_factory=lambda: ["*"])
    
    # Monitoring
    monitor_file_changes: bool = False
    
    # Default capabilities
    capabilities: List[str] = field(default_factory=lambda: [
        "file-read",
        "file-write",
        "directory-listing",
        "file-search"
    ])

@dataclass
class RouterConnectorConfig(ServerConfig):
    """Configuration for the MCP Router connector."""
    
    # Router settings
    router_endpoints: Dict[str, str] = field(default_factory=lambda: {
        "register": "/api/mcp/capabilities/register",
        "unregister": "/api/mcp/capabilities/unregister",
        "health": "/api/mcp/capabilities/health/report",
        "find": "/api/mcp/capabilities/find",
        "servers": "/api/mcp/capabilities/servers"
    })
    
    # Connection settings
    connection_timeout: int = 10  # seconds
    response_timeout: int = 30  # seconds
    
    # Registration settings
    server_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Health check settings
    report_system_metrics: bool = True
    report_memory_usage: bool = True
    report_load_average: bool = True
    
    # Retry settings
    retry_delay_factor: float = 1.5  # Exponential backoff factor
    max_retry_delay: int = 60  # seconds
    
    # Default capabilities
    capabilities: List[str] = field(default_factory=lambda: [
        "mcp-routing",
        "capability-discovery",
        "health-monitoring"
    ])

# Configuration factory
def create_server_config(server_type: str, **kwargs) -> ServerConfig:
    """
    Create a server configuration of the specified type.
    
    Args:
        server_type: Type of server configuration to create
        **kwargs: Additional configuration parameters
        
    Returns:
        Server configuration
    
    Raises:
        ValueError: If server_type is not recognized
    """
    config_class_map = {
        "orchestrator": OrchestratorConfig,
        "project-orchestrator": ProjectOrchestratorConfig,
        "prompts": PromptsServerConfig,
        "memory": MemoryServerConfig,
        "filesystem": FilesystemServerConfig,
        "router-connector": RouterConnectorConfig,
        "default": ServerConfig
    }
    
    if server_type not in config_class_map:
        raise ValueError(f"Unknown server type: {server_type}")
    
    config_class = config_class_map[server_type]
    
    # Initialize config with server type
    kwargs["server_id"] = kwargs.get("server_id", f"mcp-{server_type}")
    kwargs["server_name"] = kwargs.get("server_name", f"MCP {server_type.replace('-', ' ').title()} Server")
    
    return config_class(**kwargs)
