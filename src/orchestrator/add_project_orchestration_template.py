#!/usr/bin/env python3
"""
Script to add a project orchestration template to the prompt manager.
This script adds a project_orchestration template that uses templates from
/home/sparrow/projects/mcp-project-orchestrator.
"""
import json
import os
import sys
from pathlib import Path
import json

# Define the template storage location (matching the Docker volume mount point)
TEMPLATES_FILE = Path("/home/sparrow/mcp/data/prompts/templates.json")

# Ensure the directory exists
TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)

# Load existing templates if file exists
if TEMPLATES_FILE.exists():
    with open(TEMPLATES_FILE, "r") as f:
        try:
            templates = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {TEMPLATES_FILE} contains invalid JSON. Creating new templates list.")
            templates = []
else:
    templates = []

# Read the project templates from the orchestrator
PROJECT_TEMPLATES_FILE = Path("/home/sparrow/projects/mcp-project-orchestrator/project_templates.json")
PROJECT_ORCHESTRATION_FILE = Path("/home/sparrow/projects/mcp-project-orchestrator/project_orchestration.json")

if not PROJECT_TEMPLATES_FILE.exists():
    print(f"Error: Project templates file not found at {PROJECT_TEMPLATES_FILE}")
    sys.exit(1)

if not PROJECT_ORCHESTRATION_FILE.exists():
    print(f"Error: Project orchestration file not found at {PROJECT_ORCHESTRATION_FILE}")
    sys.exit(1)

# Load project templates
with open(PROJECT_TEMPLATES_FILE, "r") as f:
    project_templates = json.load(f)

# Load project orchestration
with open(PROJECT_ORCHESTRATION_FILE, "r") as f:
    project_orchestration = json.load(f)

# Create the project orchestration template
project_orchestration_template = {
    "name": "project_orchestration",
    "description": "Orchestrate the creation of a new project based on a selected template, creating initial codebase and implementation plan.",
    "template": """
You are an AI assistant specializing in guiding users through software project implementation using systematic approaches and design patterns. 
Your goal is to orchestrate the development project from an idea that is provided by the user.

Execute the following steps:
1. Extract key information from the user's query and decide on relevant context - files, MCP tools or prompts.
2. Determine which known design patterns and SW architecture abstraction concepts cover the logic behind the user's idea.
3. Select one of the project templates from the catalogue below and apply it by creating a new directory in the common SW projects directory and copying in the contents of the selected template's data folder.
4. Create Project Documentation - Describe SW Architecture, Components and Modules, their relationships, interfaces, communication protocols, technologies used, dependencies, installation, build, run and test commands.
5. Prepare File Structure and visualize directory tree of the project.
6. Decide in which order files should be implemented, how features should be tested, and how components should be built and deployed.

## Project Templates
{{project_templates}}

## Project Orchestration
{{project_orchestration}}

## User's Project Idea
{{project_idea}}
""",
    "arguments": [
        {
            "name": "project_templates",
            "description": "JSON data with available project templates",
            "required": True
        },
        {
            "name": "project_orchestration",
            "description": "JSON data with project orchestration workflow",
            "required": True
        },
        {
            "name": "project_idea",
            "description": "The user's project idea description",
            "required": True
        }
    ]
}

# Check if the template already exists and update it, or add it if it doesn't
template_exists = False
for i, template in enumerate(templates):
    if template.get("name") == project_orchestration_template["name"]:
        templates[i] = project_orchestration_template
        template_exists = True
        break

if not template_exists:
    templates.append(project_orchestration_template)

# Save the updated templates
with open(TEMPLATES_FILE, "w") as f:
    json.dump(templates, f, indent=2)

print(f"Successfully added/updated project_orchestration template to {TEMPLATES_FILE}")
print(f"Total templates: {len(templates)}") 