"""Tests for the MCP Prompt Manager server."""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch
from mcp.server import Server, TextContent
import mcp.types as types
from pydantic import AnyUrl

# Add the src directory to the Python path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from prompt_manager_server import PROMPT_TEMPLATES, handle_list_prompts, handle_get_prompt, handle_list_resources, handle_read_resource, handle_list_tools, handle_execute_tool

class TestPromptManager:
    """Test the MCP Prompt Manager server."""

    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test listing available prompts."""
        # Create a mock server
        server = MagicMock()
        
        # Call the handler
        result = await handle_list_prompts()
        
        # Check that we got the expected number of prompts
        assert len(result) == 3
        
        # Check that all expected prompts are present
        prompt_names = [prompt.name for prompt in result]
        assert "structured-analysis" in prompt_names
        assert "comparison" in prompt_names
        assert "step-by-step-guide" in prompt_names

    @pytest.mark.asyncio
    async def test_get_prompt_structured_analysis(self):
        """Test getting the structured analysis prompt."""
        # Call the handler with a valid prompt name and arguments
        result = await handle_get_prompt("structured-analysis", {"topic": "Artificial Intelligence"})
        
        # Check the result
        assert "Artificial Intelligence" in result.messages[0].content.text
        assert result.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_get_prompt_comparison(self):
        """Test getting the comparison prompt."""
        # Call the handler with a valid prompt name and arguments
        result = await handle_get_prompt("comparison", {"item1": "Python", "item2": "JavaScript"})
        
        # Check the result
        assert "Python" in result.messages[0].content.text
        assert "JavaScript" in result.messages[0].content.text
        assert result.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_get_prompt_step_by_step(self):
        """Test getting the step-by-step guide prompt."""
        # Call the handler with a valid prompt name and arguments
        result = await handle_get_prompt(
            "step-by-step-guide", 
            {
                "title": "Building an MCP Server",
                "overview": "A guide to building your first MCP server",
                "prerequisites": "Python knowledge",
                "tools_materials": "Python 3.9+, MCP library",
                "steps": "1. Install dependencies\n2. Create server structure\n3. Implement handlers",
                "troubleshooting": "Common issues and solutions",
                "resources": "Links to documentation",
                "summary": "You've built your first MCP server!"
            }
        )
        
        # Check the result
        assert "Building an MCP Server" in result.messages[0].content.text
        assert "A guide to building your first MCP server" in result.messages[0].content.text
        assert result.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_get_prompt_invalid(self):
        """Test getting an invalid prompt name."""
        # Call the handler with an invalid prompt name
        with pytest.raises(ValueError, match="Unknown prompt: nonexistent"):
            await handle_get_prompt("nonexistent", {})

    @pytest.mark.asyncio
    async def test_get_prompt_missing_arguments(self):
        """Test getting a prompt with missing required arguments."""
        # Call the handler with missing required arguments
        with pytest.raises(ValueError, match="Missing required argument: topic"):
            await handle_get_prompt("structured-analysis", {})

    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test listing available resources."""
        # Call the handler
        result = await handle_list_resources()
        
        # Check the result
        assert len(result) == 1
        assert result[0].name == "Prompt Templates Documentation"
        assert result[0].uri == AnyUrl("doc://prompt-templates/guide")

    @pytest.mark.asyncio
    async def test_read_resource_valid(self):
        """Test reading a valid resource."""
        # Call the handler with a valid URI
        result = await handle_read_resource(AnyUrl("doc://prompt-templates/guide"))
        
        # Check the result
        assert "Prompt Templates Guide" in result
        assert "Structured Analysis" in result
        assert "Comparison" in result
        assert "Step-by-Step Guide" in result

    @pytest.mark.asyncio
    async def test_read_resource_invalid_scheme(self):
        """Test reading a resource with an invalid scheme."""
        # Call the handler with an invalid scheme
        with pytest.raises(ValueError, match="Unsupported URI scheme: http"):
            await handle_read_resource(AnyUrl("http://example.com"))

    @pytest.mark.asyncio
    async def test_read_resource_invalid_path(self):
        """Test reading a resource with an invalid path."""
        # Call the handler with an invalid path
        with pytest.raises(ValueError, match="Unknown resource path: nonexistent"):
            await handle_read_resource(AnyUrl("doc://nonexistent"))

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools."""
        # Call the handler
        result = await handle_list_tools()
        
        # Check the result
        assert len(result) == 1
        assert result[0].name == "add_template"
        assert "Add a new prompt template" in result[0].description

    @pytest.mark.asyncio
    async def test_execute_tool_add_template(self):
        """Test executing the add_template tool."""
        # Parameters for the tool
        parameters = {
            "name": "test-template",
            "description": "A test template",
            "template": "This is a test template for {topic}."
        }
        
        # Call the handler
        result = await handle_execute_tool("add_template", parameters)
        
        # Check the result
        assert result["status"] == "success"
        assert "test-template" in result["message"]
        
        # Check that the template was added
        assert "test-template" in PROMPT_TEMPLATES
        assert PROMPT_TEMPLATES["test-template"] == "This is a test template for {topic}."

    @pytest.mark.asyncio
    async def test_execute_tool_add_template_missing_params(self):
        """Test executing the add_template tool with missing parameters."""
        # Call the handler with missing parameters
        with pytest.raises(ValueError, match="Template name and content are required"):
            await handle_execute_tool("add_template", {"name": "test"})

    @pytest.mark.asyncio
    async def test_execute_tool_invalid(self):
        """Test executing an invalid tool."""
        # Call the handler with an invalid tool name
        with pytest.raises(ValueError, match="Unknown tool: nonexistent"):
            await handle_execute_tool("nonexistent", {}) 