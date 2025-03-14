"""
MCP Architecture Diagram Generator

Generates Mermaid diagram code to visualize the MCP server architecture and integration.
"""

import os
import sys
import json
import yaml
import logging
from typing import Dict, Any, List, Optional, Set, Union, Tuple
import inspect
import importlib
import re

# Import server configs for introspection
from .server_configs import (
    ServerConfig,
    OrchestratorConfig,
    ProjectOrchestratorConfig,
    PromptsServerConfig,
    MemoryServerConfig,
    FilesystemServerConfig,
    RouterConnectorConfig
)

logger = logging.getLogger('mcp.diagram')

class DiagramGenerator:
    """Generator for MCP architecture diagrams."""
    
    def __init__(self):
        """Initialize the diagram generator."""
        self.servers = {}
        self.connections = []
        self.capabilities = {}
    
    def add_server(self, server_id: str, server_type: str, capabilities: Optional[List[str]] = None):
        """
        Add a server to the diagram.
        
        Args:
            server_id: Server identifier
            server_type: Server type (e.g., 'orchestrator', 'prompts')
            capabilities: List of capabilities provided by the server
        """
        self.servers[server_id] = {
            'id': server_id,
            'type': server_type,
            'capabilities': capabilities or []
        }
        
        # Track capabilities
        for capability in capabilities or []:
            if capability not in self.capabilities:
                self.capabilities[capability] = []
            self.capabilities[capability].append(server_id)
    
    def add_connection(self, from_server: str, to_server: str, label: Optional[str] = None):
        """
        Add a connection between servers.
        
        Args:
            from_server: Source server identifier
            to_server: Target server identifier
            label: Optional connection label
        """
        self.connections.append({
            'from': from_server,
            'to': to_server,
            'label': label
        })
    
    def generate_architecture_diagram(self) -> str:
        """
        Generate a Mermaid diagram visualizing the MCP server architecture.
        
        Returns:
            Mermaid diagram code
        """
        diagram = ["```mermaid", "graph TD"]
        
        # Add servers
        for server_id, server in self.servers.items():
            display_name = server_id.replace('-', ' ').title()
            server_type = server['type'].replace('-', ' ').title()
            diagram.append(f"    {server_id}[\"{display_name}<br/><small>({server_type})</small>\"]")
        
        # Add MCP Router as central node
        diagram.append("    router([\"MCP Router\"])")
        diagram.append("    client([\"LLM Client\"])")
        
        # Add connections from servers to router
        for server_id in self.servers:
            label = "MCP Protocol"
            diagram.append(f"    {server_id} <-->|{label}| router")
        
        # Add connection from client to router
        diagram.append("    client <-->|MCP Protocol| router")
        
        # Add custom connections
        for connection in self.connections:
            from_server = connection['from']
            to_server = connection['to']
            label = connection.get('label', "")
            
            if label:
                diagram.append(f"    {from_server} -->|{label}| {to_server}")
            else:
                diagram.append(f"    {from_server} --> {to_server}")
        
        # Close diagram
        diagram.append("```")
        
        return "\n".join(diagram)
    
    def generate_capability_diagram(self) -> str:
        """
        Generate a Mermaid diagram visualizing the MCP server capabilities.
        
        Returns:
            Mermaid diagram code
        """
        diagram = ["```mermaid", "graph TD"]
        
        # Group servers by type
        server_types = {}
        for server_id, server in self.servers.items():
            server_type = server['type']
            if server_type not in server_types:
                server_types[server_type] = []
            server_types[server_type].append(server_id)
        
        # Add capability nodes
        for capability, server_ids in self.capabilities.items():
            capability_id = f"cap_{capability.replace('-', '_')}"
            capability_name = capability.replace('-', ' ').title()
            diagram.append(f"    {capability_id}[\"Capability:<br/>{capability_name}\"]")
        
        # Add server groups
        for server_type, server_ids in server_types.items():
            type_name = server_type.replace('-', ' ').title()
            
            # Start subgraph
            diagram.append(f"    subgraph {server_type} [\"MCP {type_name} Servers\"]")
            
            # Add servers
            for server_id in server_ids:
                display_name = server_id.replace('-', ' ').title()
                diagram.append(f"        {server_id}[\"{display_name}\"]")
            
            # End subgraph
            diagram.append("    end")
        
        # Add connections from servers to capabilities
        for server_id, server in self.servers.items():
            for capability in server['capabilities']:
                capability_id = f"cap_{capability.replace('-', '_')}"
                diagram.append(f"    {server_id} -->|provides| {capability_id}")
        
        # Close diagram
        diagram.append("```")
        
        return "\n".join(diagram)
    
    def generate_sequence_diagram(self, scenario: str) -> str:
        """
        Generate a Mermaid sequence diagram for a specific scenario.
        
        Args:
            scenario: Name of the scenario ('registration', 'health', 'discovery', or custom)
            
        Returns:
            Mermaid diagram code
        """
        diagram = ["```mermaid", "sequenceDiagram"]
        
        # Add participants
        diagram.append("    participant Client as LLM Client")
        diagram.append("    participant Router as MCP Router")
        
        # Add server participants
        server_participants = []
        for server_id in self.servers:
            display_name = server_id.replace('-', ' ').title()
            participant_id = f"Server{len(server_participants) + 1}"
            server_participants.append((participant_id, server_id, display_name))
            diagram.append(f"    participant {participant_id} as {display_name}")
        
        # Add sequence based on scenario
        if scenario == 'registration':
            # Server registration scenario
            for participant_id, server_id, display_name in server_participants:
                diagram.append(f"    {participant_id}->>Router: Register server and capabilities")
                diagram.append(f"    Router-->>Router: Store server information")
                diagram.append(f"    Router-->>Router: Index capabilities")
                diagram.append(f"    Router-->>+{participant_id}: Registration successful")
                
                # Health check loop
                diagram.append(f"    loop Every minute")
                diagram.append(f"        {participant_id}->>Router: Report health status")
                diagram.append(f"        Router-->>Router: Update server health")
                diagram.append(f"        Router-->>+{participant_id}: Health update successful")
                diagram.append(f"    end")
        
        elif scenario == 'health':
            # Health monitoring scenario
            diagram.append(f"    loop Every minute")
            for participant_id, server_id, display_name in server_participants:
                diagram.append(f"        {participant_id}->>Router: Report health status")
                diagram.append(f"        Router-->>Router: Update server health")
                diagram.append(f"        alt Healthy status")
                diagram.append(f"            Router-->>+{participant_id}: Health update successful")
                diagram.append(f"        else Unhealthy status")
                diagram.append(f"            Router-->>Router: Mark server as unavailable")
                diagram.append(f"            Router-->>+{participant_id}: Health update successful")
                diagram.append(f"        end")
            diagram.append(f"    end")
        
        elif scenario == 'discovery':
            # Capability discovery scenario
            diagram.append(f"    Client->>Router: Request servers with specific capabilities")
            diagram.append(f"    Router-->>Router: Find matching servers")
            diagram.append(f"    Router-->>+Client: Return matching servers")
            
            diagram.append(f"    Client->>Router: Get server details")
            diagram.append(f"    Router-->>+Client: Return server details")
            
            # Choose a random server for example
            if server_participants:
                participant_id, server_id, display_name = server_participants[0]
                diagram.append(f"    Client->>Router: Send request to {display_name}")
                diagram.append(f"    Router->>+{participant_id}: Forward request")
                diagram.append(f"    {participant_id}-->>-Router: Return result")
                diagram.append(f"    Router-->>-Client: Return result")
        
        elif scenario == 'failover':
            # Failover scenario
            if len(server_participants) >= 2:
                primary_id, primary_server_id, primary_name = server_participants[0]
                secondary_id, secondary_server_id, secondary_name = server_participants[1]
                
                diagram.append(f"    Client->>Router: Request servers with capability X")
                diagram.append(f"    Router-->>+Client: Return [{primary_name}, {secondary_name}]")
                
                diagram.append(f"    Client->>Router: Send request to {primary_name}")
                diagram.append(f"    Router->>+{primary_id}: Forward request")
                diagram.append(f"    Note over {primary_id}: Server becomes unresponsive")
                diagram.append(f"    Router-->>Router: Detect {primary_name} failure")
                diagram.append(f"    Router-->>Router: Mark {primary_name} as unavailable")
                
                diagram.append(f"    Router->>+{secondary_id}: Forward request (failover)")
                diagram.append(f"    {secondary_id}-->>-Router: Return result")
                diagram.append(f"    Router-->>-Client: Return result")
        
        elif scenario == 'cross_server':
            # Cross-server integration scenario
            if len(server_participants) >= 3:
                # Use the first three servers for example
                client_id, client_server_id, client_name = server_participants[0]
                orchest_id, orchest_server_id, orchest_name = server_participants[1]
                prompt_id, prompt_server_id, prompt_name = server_participants[2]
                
                diagram.append(f"    Client->>Router: Request operation requiring multiple capabilities")
                diagram.append(f"    Router->>+{orchest_id}: Forward main request")
                
                diagram.append(f"    {orchest_id}->>Router: Request servers with prompt capability")
                diagram.append(f"    Router-->>+{orchest_id}: Return [{prompt_name}]")
                
                diagram.append(f"    {orchest_id}->>Router: Send request to {prompt_name}")
                diagram.append(f"    Router->>+{prompt_id}: Forward request")
                diagram.append(f"    {prompt_id}-->>-Router: Return prompt template")
                diagram.append(f"    Router-->>-{orchest_id}: Return prompt template")
                
                diagram.append(f"    {orchest_id}-->>-Router: Return final result")
                diagram.append(f"    Router-->>-Client: Return final result")
        
        # Close diagram
        diagram.append("```")
        
        return "\n".join(diagram)
    
    def generate_class_diagram(self) -> str:
        """
        Generate a Mermaid class diagram of the MCP server configuration classes.
        
        Returns:
            Mermaid diagram code
        """
        diagram = ["```mermaid", "classDiagram"]
        
        # Define classes
        classes = [
            ServerConfig,
            OrchestratorConfig,
            ProjectOrchestratorConfig,
            PromptsServerConfig,
            MemoryServerConfig,
            FilesystemServerConfig,
            RouterConnectorConfig
        ]
        
        # Add class definitions and inheritance
        for cls in classes:
            class_name = cls.__name__
            
            # Get base classes (except object)
            base_classes = [base.__name__ for base in cls.__bases__ if base.__name__ != 'object']
            
            # Add class to diagram
            if base_classes:
                for base_class in base_classes:
                    diagram.append(f"    {base_class} <|-- {class_name}")
            
            # Add class fields from dataclass
            field_annotations = cls.__annotations__ if hasattr(cls, '__annotations__') else {}
            
            for field_name, field_type in field_annotations.items():
                # Format field type name
                type_name = self._format_type_name(field_type)
                
                # Add field to diagram
                diagram.append(f"    {class_name} : +{field_name} {type_name}")
        
        # Close diagram
        diagram.append("```")
        
        return "\n".join(diagram)
    
    def generate_deployment_diagram(self) -> str:
        """
        Generate a Mermaid deployment diagram for MCP servers.
        
        Returns:
            Mermaid diagram code
        """
        diagram = ["```mermaid", "graph TD"]
        
        # Define deployment environments
        environments = ["Development", "Staging", "Production"]
        
        # Define common components
        common_components = [
            ("DB", "Database"),
            ("Cache", "Redis Cache"),
            ("LLM", "LLM Service"),
            ("Client", "LLM Client")
        ]
        
        # Add subgraphs for each environment
        for env in environments:
            # Start subgraph
            env_id = env.lower()
            diagram.append(f"    subgraph {env_id} [\"{env} Environment\"]")
            
            # Add MCP Router
            diagram.append(f"        {env_id}_router([\"MCP Router\"])")
            
            # Add servers
            for server_id, server in self.servers.items():
                display_name = server_id.replace('-', ' ').title()
                diagram.append(f"        {env_id}_{server_id}[\"{display_name}\"]")
                
                # Connect to router
                diagram.append(f"        {env_id}_{server_id} <--> {env_id}_router")
            
            # Add common components
            for component_id, component_name in common_components:
                diagram.append(f"        {env_id}_{component_id}[\"📦 {component_name}\"]")
            
            # Connect client to router
            diagram.append(f"        {env_id}_Client <--> {env_id}_router")
            
            # End subgraph
            diagram.append("    end")
        
        # Add deployment pipeline connections
        diagram.append("    Development -->|Promote| Staging")
        diagram.append("    Staging -->|Promote| Production")
        
        # Close diagram
        diagram.append("```")
        
        return "\n".join(diagram)
    
    def generate_component_diagram(self) -> str:
        """
        Generate a Mermaid component diagram for MCP servers.
        
        Returns:
            Mermaid diagram code
        """
        diagram = ["```mermaid", "graph TD"]
        
        # Define MCP Router components
        diagram.append("    subgraph Router [\"MCP Router\"]")
        diagram.append("        router_api[\"API Layer\"]")
        diagram.append("        router_capability[\"Capability Manager\"]")
        diagram.append("        router_health[\"Health Monitor\"]")
        diagram.append("        router_security[\"Security Manager\"]")
        
        # Connect router components
        diagram.append("        router_api --> router_capability")
        diagram.append("        router_api --> router_health")
        diagram.append("        router_api --> router_security")
        diagram.append("    end")
        
        # Add server components for each server type
        for server_type in set(server['type'] for server in self.servers.values()):
            type_name = server_type.replace('-', ' ').title()
            type_id = server_type.replace('-', '_')
            
            # Start server subgraph
            diagram.append(f"    subgraph {type_id} [\"MCP {type_name} Server\"]")
            
            # Add common components
            diagram.append(f"        {type_id}_core[\"Core Service\"]")
            diagram.append(f"        {type_id}_api[\"API Layer\"]")
            diagram.append(f"        {type_id}_router_integration[\"Router Integration\"]")
            
            # Add specialized components based on server type
            if server_type == 'orchestrator':
                diagram.append(f"        {type_id}_workers[\"Worker Manager\"]")
                diagram.append(f"        {type_id}_diagram[\"Diagram Generator\"]")
                diagram.append(f"        {type_id}_analysis[\"Code Analysis\"]")
                
                # Connect specialized components
                diagram.append(f"        {type_id}_core --> {type_id}_workers")
                diagram.append(f"        {type_id}_core --> {type_id}_diagram")
                diagram.append(f"        {type_id}_core --> {type_id}_analysis")
            
            elif server_type == 'project-orchestrator':
                diagram.append(f"        {type_id}_templates[\"Template Manager\"]")
                diagram.append(f"        {type_id}_analyzer[\"Pattern Analyzer\"]")
                diagram.append(f"        {type_id}_generator[\"Project Generator\"]")
                
                # Connect specialized components
                diagram.append(f"        {type_id}_core --> {type_id}_templates")
                diagram.append(f"        {type_id}_core --> {type_id}_analyzer")
                diagram.append(f"        {type_id}_core --> {type_id}_generator")
            
            elif server_type == 'prompts':
                diagram.append(f"        {type_id}_storage[\"Prompt Storage\"]")
                diagram.append(f"        {type_id}_template[\"Template Engine\"]")
                diagram.append(f"        {type_id}_versioning[\"Version Control\"]")
                
                # Connect specialized components
                diagram.append(f"        {type_id}_core --> {type_id}_storage")
                diagram.append(f"        {type_id}_core --> {type_id}_template")
                diagram.append(f"        {type_id}_core --> {type_id}_versioning")
            
            # Connect common components
            diagram.append(f"        {type_id}_api --> {type_id}_core")
            diagram.append(f"        {type_id}_router_integration --> {type_id}_api")
            
            # End server subgraph
            diagram.append("    end")
            
            # Connect to router
            diagram.append(f"    {type_id}_router_integration <-->|MCP Protocol| router_api")
        
        # Add Client
        diagram.append("    Client([\"LLM Client\"])")
        diagram.append("    Client <-->|MCP Protocol| router_api")
        
        # Close diagram
        diagram.append("```")
        
        return "\n".join(diagram)
    
    def generate_comprehensive_documentation(self) -> str:
        """
        Generate comprehensive documentation with all diagram types.
        
        Returns:
            Markdown documentation with all diagrams
        """
        docs = ["# MCP Server Architecture Documentation"]
        
        # Add introduction
        docs.append("\n## Introduction")
        docs.append(
            "This document provides a comprehensive visual overview of the MCP (Model Context Protocol) "
            "server architecture and integration patterns. The diagrams illustrate how different MCP "
            "servers communicate with each other and with LLM clients through the MCP Router."
        )
        
        # Add architecture overview
        docs.append("\n## Architecture Overview")
        docs.append(
            "The following diagram shows the high-level architecture of the MCP ecosystem, "
            "including all servers and their connections to the MCP Router."
        )
        docs.append(self.generate_architecture_diagram())
        
        # Add capability diagram
        docs.append("\n## Capability Map")
        docs.append(
            "This diagram shows the capabilities provided by each MCP server, illustrating "
            "how different servers can provide overlapping or complementary capabilities."
        )
        docs.append(self.generate_capability_diagram())
        
        # Add component diagram
        docs.append("\n## Component Architecture")
        docs.append(
            "This diagram shows the internal components of each MCP server and the MCP Router, "
            "illustrating how they are structured and interact with each other."
        )
        docs.append(self.generate_component_diagram())
        
        # Add sequence diagrams
        docs.append("\n## Interaction Patterns")
        
        docs.append("\n### Server Registration Process")
        docs.append(
            "This sequence diagram illustrates how MCP servers register with the MCP Router "
            "and periodically report their health status."
        )
        docs.append(self.generate_sequence_diagram('registration'))
        
        docs.append("\n### Capability Discovery Process")
        docs.append(
            "This sequence diagram shows how clients discover and interact with MCP servers "
            "based on their capabilities through the MCP Router."
        )
        docs.append(self.generate_sequence_diagram('discovery'))
        
        docs.append("\n### Failover Handling")
        docs.append(
            "This sequence diagram demonstrates how the MCP Router handles server failures "
            "by automatically failing over to alternative servers with equivalent capabilities."
        )
        docs.append(self.generate_sequence_diagram('failover'))
        
        docs.append("\n### Cross-Server Integration")
        docs.append(
            "This sequence diagram shows how multiple MCP servers can work together to fulfill "
            "complex requests that require multiple capabilities."
        )
        docs.append(self.generate_sequence_diagram('cross_server'))
        
        # Add class diagram
        docs.append("\n## Configuration Classes")
        docs.append(
            "This class diagram shows the hierarchy of configuration classes used by different "
            "MCP servers, illustrating how they extend the base ServerConfig class."
        )
        docs.append(self.generate_class_diagram())
        
        # Add deployment diagram
        docs.append("\n## Deployment Model")
        docs.append(
            "This diagram illustrates how MCP servers can be deployed across different environments, "
            "from development to production, with a promotion pipeline."
        )
        docs.append(self.generate_deployment_diagram())
        
        # Add server configuration table
        docs.append("\n## Server Configuration Reference")
        docs.append(
            "This table provides a reference for the configuration options available for each MCP server type."
        )
        docs.append(self._generate_config_reference())
        
        # Add capability table
        docs.append("\n## Capability Reference")
        docs.append(
            "This table lists all capabilities provided by MCP servers and which servers implement each capability."
        )
        docs.append(self._generate_capability_reference())
        
        return "\n".join(docs)
    
    def _format_type_name(self, type_annotation: Any) -> str:
        """
        Format a type annotation into a readable string.
        
        Args:
            type_annotation: Type annotation
            
        Returns:
            Formatted type name
        """
        # Get the string representation of the type
        type_str = str(type_annotation)
        
        # Clean up the string
        type_str = type_str.replace('typing.', '')
        type_str = type_str.replace('NoneType', 'None')
        
        # Handle common typing patterns
        type_str = re.sub(r'Union\[([^,]+), NoneType\]', r'Optional[\1]', type_str)
        
        return type_str
    
    def _generate_config_reference(self) -> str:
        """
        Generate a reference table for server configurations.
        
        Returns:
            Markdown table of server configurations
        """
        # Define configuration classes to document
        config_classes = [
            ServerConfig,
            OrchestratorConfig,
            ProjectOrchestratorConfig,
            PromptsServerConfig,
            MemoryServerConfig,
            FilesystemServerConfig,
            RouterConnectorConfig
        ]
        
        # Start table
        table = [
            "| Server Type | Configuration Option | Type | Default Value | Description |",
            "| ----------- | -------------------- | ---- | ------------- | ----------- |"
        ]
        
        # Add rows for each configuration class
        for cls in config_classes:
            server_type = cls.__name__.replace('Config', '')
            
            # Get field annotations and defaults
            field_annotations = cls.__annotations__ if hasattr(cls, '__annotations__') else {}
            field_defaults = {}
            
            # Get default values
            for field_name in field_annotations:
                if hasattr(cls, field_name):
                    field_defaults[field_name] = getattr(cls, field_name)
            
            # Add rows for each field
            for field_name, field_type in field_annotations.items():
                # Format field type
                type_str = self._format_type_name(field_type)
                
                # Get default value
                default_value = field_defaults.get(field_name, "N/A")
                if isinstance(default_value, (list, dict)) and not default_value:
                    default_value = "Empty"
                elif default_value is None:
                    default_value = "None"
                elif isinstance(default_value, bool):
                    default_value = str(default_value)
                elif isinstance(default_value, (list, dict)):
                    default_value = f"{len(default_value)} items"
                
                # Add row to table
                table.append(f"| {server_type} | {field_name} | {type_str} | {default_value} | |")
        
        return "\n".join(table)
    
    def _generate_capability_reference(self) -> str:
        """
        Generate a reference table for capabilities.
        
        Returns:
            Markdown table of capabilities
        """
        # Start table
        table = [
            "| Capability | Description | Implementing Servers |",
            "| ---------- | ----------- | -------------------- |"
        ]
        
        # Add rows for each capability
        for capability, server_ids in self.capabilities.items():
            # Format capability name
            capability_name = capability.replace('-', ' ').title()
            
            # Get list of servers
            server_list = ", ".join(server_ids)
            
            # Add row to table
            table.append(f"| {capability_name} | | {server_list} |")
        
        return "\n".join(table)

# Function to create a diagram generator with standard MCP servers
def create_standard_diagram_generator() -> DiagramGenerator:
    """
    Create a DiagramGenerator pre-populated with standard MCP servers.
    
    Returns:
        Pre-populated DiagramGenerator
    """
    generator = DiagramGenerator()
    
    # Add standard servers
    generator.add_server(
        "code-diagram-orchestrator",
        "orchestrator",
        [
            "code-analysis",
            "code-visualization",
            "documentation-generation",
            "diagram-generation"
        ]
    )
    
    generator.add_server(
        "project-orchestrator",
        "project-orchestrator",
        [
            "project-orchestration",
            "project-template-application",
            "project-structure-generation",
            "mermaid-diagram-generation",
            "design-pattern-analysis"
        ]
    )
    
    generator.add_server(
        "prompt-manager",
        "prompts",
        [
            "prompt-management",
            "prompt-template-application",
            "prompt-versioning",
            "prompt-import-export"
        ]
    )
    
    generator.add_server(
        "memory-server",
        "memory",
        [
            "knowledge-graph-management",
            "entity-storage",
            "relation-management",
            "graph-querying"
        ]
    )
    
    generator.add_server(
        "filesystem-server",
        "filesystem",
        [
            "file-read",
            "file-write",
            "directory-listing",
            "file-search"
        ]
    )
    
    # Add server relationships
    generator.add_connection(
        "code-diagram-orchestrator",
        "prompt-manager",
        "Get templates"
    )
    
    generator.add_connection(
        "project-orchestrator",
        "prompt-manager",
        "Get templates"
    )
    
    generator.add_connection(
        "code-diagram-orchestrator",
        "filesystem-server",
        "Read/write files"
    )
    
    generator.add_connection(
        "project-orchestrator",
        "filesystem-server",
        "Read/write files"
    )
    
    return generator

if __name__ == "__main__":
    # Example usage
    generator = create_standard_diagram_generator()
    
    # Generate architecture diagram
    architecture_diagram = generator.generate_architecture_diagram()
    print(architecture_diagram)
    
    # Generate capability diagram
    capability_diagram = generator.generate_capability_diagram()
    print(capability_diagram)
    
    # Generate sequence diagram for registration scenario
    sequence_diagram = generator.generate_sequence_diagram('registration')
    print(sequence_diagram)
    
    # Generate class diagram
    class_diagram = generator.generate_class_diagram()
    print(class_diagram)
    
    # Generate component diagram
    component_diagram = generator.generate_component_diagram()
    print(component_diagram)
    
    # Generate deployment diagram
    deployment_diagram = generator.generate_deployment_diagram()
    print(deployment_diagram)
    
    # Generate comprehensive documentation
    documentation = generator.generate_comprehensive_documentation()
    
    # Write documentation to file
    with open('mcp_architecture.md', 'w') as f:
        f.write(documentation)
