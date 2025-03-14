"""Template management module for the MCP Prompt Manager server."""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .config import config

# Configure logging
logger = logging.getLogger("mcp-prompt-manager.templates")

# Built-in templates
BUILTIN_TEMPLATES = {
    "structured-analysis": """
# Structured Analysis Framework

Please analyze the following topic using a structured approach:

## Topic: {topic}

Complete the following analysis framework:

1. **Overview**
   - Brief summary of the topic
   - Key historical context or background

2. **Core Components**
   - Primary elements or principles
   - How these components interact

3. **Benefits & Advantages**
   - Main benefits
   - Comparative advantages over alternatives

4. **Challenges & Limitations**
   - Current challenges
   - Inherent limitations

5. **Current Trends**
   - Recent developments
   - Emerging patterns

6. **Future Outlook**
   - Predicted developments
   - Potential disruptions

7. **Practical Applications**
   - Real-world use cases
   - Implementation considerations

8. **Conclusion**
   - Summary of key points
   - Final assessment
""",

    "comparison": """
# Comparative Analysis Framework

Please provide a detailed comparison between these items:

## Items to Compare: {item1} vs {item2}

Please analyze using the following comparative framework:

1. **Overview**
   - Brief description of {item1}
   - Brief description of {item2}
   - Historical context for both

2. **Key Characteristics**
   - Primary features of {item1}
   - Primary features of {item2}
   - Distinguishing attributes

3. **Strengths & Weaknesses**
   - {item1} strengths
   - {item1} weaknesses
   - {item2} strengths
   - {item2} weaknesses

4. **Use Cases**
   - Ideal scenarios for {item1}
   - Ideal scenarios for {item2}
   - Overlap in applications

5. **Performance Metrics**
   - How {item1} performs on key metrics
   - How {item2} performs on key metrics
   - Direct comparison of results

6. **Cost & Resource Considerations**
   - Resource requirements for {item1}
   - Resource requirements for {item2}
   - Cost-benefit analysis

7. **Future Outlook**
   - Development trajectory for {item1}
   - Development trajectory for {item2}
   - Predicted competitive advantage

8. **Recommendation**
   - Scenarios where {item1} is preferable
   - Scenarios where {item2} is preferable
   - Overall assessment
""",

    "step-by-step-guide": """
# Step-by-Step Guide: {title}

## Overview
{overview}

## Prerequisites
- Required knowledge: {prerequisites}
- Required tools/materials: {tools_materials}

## Detailed Steps

{steps}

## Common Issues and Troubleshooting
{troubleshooting}

## Additional Resources
{resources}

## Summary
{summary}
"""
}

# Template metadata for the built-in templates
TEMPLATE_METADATA = {
    "structured-analysis": {
        "description": "A framework for structured analysis of a single topic",
        "arguments": [
            {
                "name": "topic",
                "description": "The topic to analyze",
                "required": True,
            }
        ],
    },
    "comparison": {
        "description": "A framework for comparing two items or concepts",
        "arguments": [
            {
                "name": "item1",
                "description": "First item to compare",
                "required": True,
            },
            {
                "name": "item2",
                "description": "Second item to compare",
                "required": True,
            }
        ],
    },
    "step-by-step-guide": {
        "description": "A template for creating detailed step-by-step guides",
        "arguments": [
            {
                "name": "title",
                "description": "Title of the guide",
                "required": True,
            },
            {
                "name": "overview",
                "description": "Brief overview of the guide",
                "required": True,
            },
            {
                "name": "prerequisites",
                "description": "Knowledge prerequisites",
                "required": False,
            },
            {
                "name": "tools_materials",
                "description": "Required tools and materials",
                "required": False,
            },
            {
                "name": "steps",
                "description": "The main steps (can be plain text, will be formatted)",
                "required": True,
            },
            {
                "name": "troubleshooting",
                "description": "Common issues and troubleshooting tips",
                "required": False,
            },
            {
                "name": "resources",
                "description": "Additional resources",
                "required": False,
            },
            {
                "name": "summary",
                "description": "Brief summary",
                "required": False,
            },
        ],
    }
}

class TemplateManager:
    """Manages prompt templates with optional persistence."""
    
    def __init__(self):
        """Initialize the template manager."""
        self._templates = BUILTIN_TEMPLATES.copy()
        self._metadata = TEMPLATE_METADATA.copy()
        self._custom_templates = {}
        self._custom_metadata = {}
        
    def load_templates(self) -> None:
        """Load templates from configured sources."""
        # Load from directory if specified
        if config.template_dir and os.path.isdir(config.template_dir):
            self._load_from_directory(config.template_dir)
        
        # Load persisted templates if enabled
        if config.persistence and config.persistence_file:
            self._load_from_persistence_file()
    
    def _load_from_directory(self, directory: str) -> None:
        """Load templates from a directory."""
        template_dir = Path(directory)
        try:
            # Look for a metadata.json file
            metadata_file = template_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    all_metadata = json.load(f)
            else:
                all_metadata = {}
            
            # Load individual template files
            for template_file in template_dir.glob("*.md"):
                template_name = template_file.stem
                try:
                    with open(template_file, 'r') as f:
                        template_content = f.read()
                    
                    self._custom_templates[template_name] = template_content
                    
                    # Add metadata if available, otherwise create basic metadata
                    if template_name in all_metadata:
                        self._custom_metadata[template_name] = all_metadata[template_name]
                    else:
                        # Extract placeholder names from template content
                        import re
                        placeholders = re.findall(r'{([^{}]*)}', template_content)
                        arguments = [
                            {
                                "name": placeholder,
                                "description": f"Value for {placeholder}",
                                "required": True
                            }
                            for placeholder in set(placeholders)
                        ]
                        
                        self._custom_metadata[template_name] = {
                            "description": f"Custom template: {template_name}",
                            "arguments": arguments
                        }
                    
                    logger.info(f"Loaded template {template_name} from {template_file}")
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}")
            
            # Merge with built-in templates (custom templates take precedence)
            self._templates.update(self._custom_templates)
            self._metadata.update(self._custom_metadata)
            
        except Exception as e:
            logger.error(f"Error loading templates from directory {directory}: {e}")
    
    def _load_from_persistence_file(self) -> None:
        """Load persisted templates."""
        persistence_file = Path(config.persistence_file)
        if not persistence_file.exists():
            return
        
        try:
            with open(persistence_file, 'r') as f:
                data = json.load(f)
            
            # Load templates and metadata
            persisted_templates = data.get("templates", {})
            persisted_metadata = data.get("metadata", {})
            
            # Merge with custom templates (persisted templates take precedence)
            self._custom_templates.update(persisted_templates)
            self._custom_metadata.update(persisted_metadata)
            
            # Merge with all templates
            self._templates.update(self._custom_templates)
            self._metadata.update(self._custom_metadata)
            
            logger.info(f"Loaded {len(persisted_templates)} templates from {persistence_file}")
        except Exception as e:
            logger.error(f"Error loading persisted templates from {persistence_file}: {e}")
    
    def save_templates(self) -> None:
        """Save custom templates if persistence is enabled."""
        if not config.persistence or not config.persistence_file:
            return
        
        try:
            persistence_file = Path(config.persistence_file)
            persistence_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "templates": self._custom_templates,
                "metadata": self._custom_metadata
            }
            
            with open(persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self._custom_templates)} custom templates to {persistence_file}")
        except Exception as e:
            logger.error(f"Error saving templates to {persistence_file}: {e}")
    
    def add_template(self, name: str, template: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a new template."""
        if not metadata:
            # Extract placeholder names from template content
            import re
            placeholders = re.findall(r'{([^{}]*)}', template)
            arguments = [
                {
                    "name": placeholder,
                    "description": f"Value for {placeholder}",
                    "required": True
                }
                for placeholder in set(placeholders)
            ]
            
            metadata = {
                "description": f"Custom template: {name}",
                "arguments": arguments
            }
        
        # Add to custom templates
        self._custom_templates[name] = template
        self._custom_metadata[name] = metadata
        
        # Add to active templates
        self._templates[name] = template
        self._metadata[name] = metadata
        
        # Save if persistence is enabled
        if config.persistence:
            self.save_templates()
    
    def get_template(self, name: str) -> Optional[str]:
        """Get a template by name."""
        return self._templates.get(name)
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get template metadata by name."""
        return self._metadata.get(name)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with metadata."""
        return [
            {
                "name": name,
                "description": self._metadata.get(name, {}).get("description", ""),
                "arguments": self._metadata.get(name, {}).get("arguments", []),
                "builtin": name in BUILTIN_TEMPLATES
            }
            for name in self._templates.keys()
        ]
    
    def remove_template(self, name: str) -> bool:
        """Remove a custom template."""
        if name in BUILTIN_TEMPLATES:
            logger.warning(f"Cannot remove built-in template: {name}")
            return False
        
        if name in self._custom_templates:
            del self._custom_templates[name]
            del self._custom_metadata[name]
            
            # Remove from active templates
            if name in self._templates:
                del self._templates[name]
            if name in self._metadata:
                del self._metadata[name]
            
            # Save if persistence is enabled
            if config.persistence:
                self.save_templates()
            
            return True
        
        return False

# Global template manager instance
template_manager = TemplateManager() 