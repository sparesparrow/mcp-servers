#!/usr/bin/env python3
"""
Script to test the project orchestration template in the prompt manager.
"""
import json
import os
import sys
from pathlib import Path
import json

# Define the template storage location (matching the Docker volume mount point)
TEMPLATES_FILE = Path("/home/sparrow/mcp/data/prompts/templates.json")

if not TEMPLATES_FILE.exists():
    print(f"Error: Templates file not found at {TEMPLATES_FILE}")
    sys.exit(1)

# Load existing templates
with open(TEMPLATES_FILE, "r") as f:
    try:
        templates = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: {TEMPLATES_FILE} contains invalid JSON.")
        sys.exit(1)

# Look for the project_orchestration template
found = False
for template in templates:
    if template.get("name") == "project_orchestration":
        found = True
        print("Found project_orchestration template:")
        print(f"  Description: {template.get('description')}")
        print(f"  Arguments: {len(template.get('arguments', []))}")
        for arg in template.get("arguments", []):
            print(f"    - {arg.get('name')}: {arg.get('description')}")
        print("Template successfully installed and configured!")
        break

if not found:
    print("Error: project_orchestration template not found in the templates file.")
    sys.exit(1)

# Verify project template files also exist
PROJECT_TEMPLATES_FILE = Path("/home/sparrow/projects/mcp-project-orchestrator/project_templates.json")
PROJECT_ORCHESTRATION_FILE = Path("/home/sparrow/projects/mcp-project-orchestrator/project_orchestration.json")

if not PROJECT_TEMPLATES_FILE.exists():
    print(f"Warning: Project templates file not found at {PROJECT_TEMPLATES_FILE}")
    print("The template will not work correctly without this file.")
else:
    print(f"Project templates file found at {PROJECT_TEMPLATES_FILE}")

if not PROJECT_ORCHESTRATION_FILE.exists():
    print(f"Warning: Project orchestration file not found at {PROJECT_ORCHESTRATION_FILE}")
    print("The template will not work correctly without this file.")
else:
    print(f"Project orchestration file found at {PROJECT_ORCHESTRATION_FILE}")

print("\nInstallation complete! You can now use the project_orchestration template with the prompt-manager.")
print("\nTo use the template in Cursor, you need to:")
print("1. Restart Cursor to load the updated configuration")
print("2. Use the prompt-manager-py tool with add_template")
print("3. Provide the required arguments: project_templates, project_orchestration, and project_idea") 