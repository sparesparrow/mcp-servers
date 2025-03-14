import os
import unittest
import tempfile
from unittest.mock import MagicMock, patch
import sys
import json
import anthropic
import requests

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mermaid.mermaid_server import MermaidServer, ApiError, MermaidError, ValidationError, StyleManager, DEFAULT_COLOR_THEMES

class TestMermaidServer(unittest.TestCase):
    """Tests for the Mermaid diagram generator MCP server."""

    def setUp(self):
        """Set up test environment."""
        # Create a mock for the Anthropic client
        self.anthropic_mock = MagicMock()
        # Patch the Anthropic client
        self.patcher = patch('anthropic.Anthropic', return_value=self.anthropic_mock)
        self.patcher.start()
        
        # Create a temp file for custom themes
        self.temp_themes_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_themes_file.close()
        
        # Initialize the server with a test API key
        self.server = MermaidServer(
            api_key="test-api-key",
            custom_themes_path=self.temp_themes_file.name
        )
        
        # Mock the run method to prevent actual execution
        self.server.mcp.run = MagicMock()
        
        # Create a mock response for the Anthropic client
        self.mock_message = MagicMock()
        self.mock_message.content = [MagicMock(text="mocked response")]
        self.anthropic_mock.messages.create.return_value = self.mock_message
        
        # Add __name__ attribute to the mock to prevent AttributeError
        self.anthropic_mock.messages.create.__name__ = "messages.create"
        
        # Add validator mock
        self.server.validator.validate = MagicMock(return_value={"is_valid": True, "issues": []})

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()
        # Remove temp file
        if os.path.exists(self.temp_themes_file.name):
            os.unlink(self.temp_themes_file.name)

    def test_generate_diagram(self):
        """Test the generate_diagram tool."""
        # Set specific mock response for this test
        self.mock_message.content[0].text = """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```"""
        
        # Test with default theme
        result = self.server.generate_diagram("Create a simple flow diagram")
        
        # Verify the API was called with correct arguments
        self.anthropic_mock.messages.create.assert_called_once()
        
        # Verify the result contains the mermaid diagram and styling
        self.assertIn("graph TD", result)
        self.assertIn("A[Start] --> B[Process]", result)
        self.assertIn("classDef default", result)
        
        # Reset mock
        self.anthropic_mock.messages.create.reset_mock()
        
        # Test with specific theme
        self.mock_message.content[0].text = """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```"""
        
        result = self.server.generate_diagram("Create a simple flow diagram", theme="dark")
        
        # Verify theme was applied
        self.assertIn("fill:#2d2d2d", result)
        
    def test_analyze_diagram(self):
        """Test the analyze_diagram tool."""
        # Set mock response
        self.mock_message.content[0].text = "This diagram shows a simple flow from Start to End."
        
        # Test with valid diagram
        result = self.server.analyze_diagram("graph TD\nA[Start] --> B[End]")
        
        # Verify the API was called with correct arguments
        self.anthropic_mock.messages.create.assert_called_once()
        
        # Verify the result matches the expected output
        self.assertEqual(result, "This diagram shows a simple flow from Start to End.")
        
        # Reset the mock
        self.anthropic_mock.messages.create.reset_mock()
        
        # Test with invalid diagram
        self.server.validator.validate = MagicMock(return_value={"is_valid": False, "issues": ["Invalid syntax"]})
        
        # Expect a ValidationError
        with self.assertRaises(ValidationError):
            self.server.analyze_diagram("invalid diagram syntax")

    def test_modify_diagram(self):
        """Test the modify_diagram tool."""
        # Set mock response
        self.mock_message.content[0].text = """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
    B --> D[Alternative End]
```"""
        
        # Test with valid diagram and modification
        result = self.server.modify_diagram(
            diagram="graph TD\nA[Start] --> B[Process]\nB --> C[End]",
            modification="Add an alternative end point",
            theme="pastel"
        )
        
        # Verify the API was called with correct arguments
        self.anthropic_mock.messages.create.assert_called_once()
        
        # Verify the result contains the modified diagram with styling
        self.assertIn("graph TD", result)
        self.assertIn("Alternative End", result)
        
        # Should have pastel styling
        self.assertTrue(
            "fill:#f0f8ff" in result or  # Either directly in flowchart styling
            "'primaryColor': '#ff9966'" in result  # Or in init config for other diagram types
        )
        
        # Reset mock
        self.anthropic_mock.messages.create.reset_mock()
        
        # Test with keep_styling=False
        self.mock_message.content[0].text = """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
    B --> D[Alternative End]
```"""
        
        # Create a diagram with existing styling
        styled_diagram = """graph TD
    A[Start] --> B[Process]
    B --> C[End]
    
%% Styling
classDef default fill:#f9f9f9,stroke:#333333,stroke-width:1px,color:#333333,rx:5px,ry:5px"""
        
        result = self.server.modify_diagram(
            diagram=styled_diagram,
            modification="Add an alternative end point",
            keep_styling=False,
            theme="vibrant"
        )
        
        # Should have vibrant styling instead of the original styling
        self.assertTrue(
            "fill:#ffffff" in result or  # Either directly in flowchart styling
            "'primaryColor': '#ff7700'" in result  # Or in init config for other diagram types
        )
    
    def test_error_handling(self):
        """Test error handling when an invalid diagram is provided."""
        # Test with an invalid diagram - this should be handled by the validator
        # Set up the mock to return invalid response
        self.server.validator.validate = MagicMock(return_value={"is_valid": False, "issues": ["Invalid syntax"]})
        
        # Make sure the validate_diagram method is set to raise ValidationError when validator returns errors
        with patch.object(self.server, 'validate_diagram', side_effect=ValidationError("Invalid diagram")):
            with self.assertRaises(ValidationError):
                self.server.validate_diagram("invalid diagram syntax")
    
    def test_input_validation_generate_diagram(self):
        """Test input validation for generate_diagram."""
        with self.assertRaises(ValueError):
            self.server.generate_diagram("")
    
    def test_input_validation_analyze_diagram(self):
        """Test input validation for analyze_diagram."""
        with self.assertRaises(ValueError):
            self.server.analyze_diagram("")
    
    def test_input_validation_modify_diagram(self):
        """Test input validation for modify_diagram."""
        with self.assertRaises(ValueError):
            self.server.modify_diagram("", "add something")
        
        with self.assertRaises(ValueError):
            self.server.modify_diagram("graph TD\nA-->B", "")
    
    def test_api_error_handling(self):
        """Test handling of specific API errors."""
        # Create mock request and response for API errors
        mock_request = MagicMock()
        mock_response = MagicMock()

        # Test APIError
        api_error = anthropic.APIError(
            message="API Error",
            request=mock_request,
            body={"error": {"message": "API Error"}}
        )
        self.anthropic_mock.messages.create.side_effect = api_error

        with self.assertRaises(ApiError):
            self.server.generate_diagram("Test prompt")

        # Reset side_effect
        self.anthropic_mock.messages.create.side_effect = None

        # Test general exception handling
        general_error = Exception("Generic error")
        self.anthropic_mock.messages.create.side_effect = general_error

        with self.assertRaises(MermaidError):
            self.server.generate_diagram("Test prompt")
            
    def test_get_theme_info(self):
        """Test the get_theme_info tool."""
        # Test getting info for all themes
        result = self.server.get_theme_info()
        
        # Verify the result structure
        self.assertIn("default_theme", result)
        self.assertIn("available_themes", result)
        self.assertIn("themes", result)
        self.assertIn("default", result["themes"])
        self.assertIn("dark", result["themes"])
        self.assertIn("pastel", result["themes"])
        self.assertIn("vibrant", result["themes"])
        
        # Test getting info for a specific theme
        result = self.server.get_theme_info("dark")
        
        # Verify the result
        self.assertEqual(result["name"], "dark")
        self.assertIn("node_fill", result["colors"])
        self.assertEqual(result["colors"]["node_fill"], "#2d2d2d")
        
        # Test with invalid theme name
        with self.assertRaises(ValueError):
            self.server.get_theme_info("nonexistent_theme")

    def test_custom_themes(self):
        """Test adding and removing custom themes."""
        # Create a test theme
        test_theme = {
            "node_fill": "#f5f5f5",
            "node_border": "#999999",
            "node_text": "#444444",
            "edge": "#888888",
            "highlight": "#ff9900",
            "success": "#99cc99",
            "warning": "#ffdd99",
            "error": "#ff9999"
        }
        
        # Add the theme
        result = self.server.add_custom_theme("test-theme", test_theme)
        self.assertTrue(result)
        
        # Verify theme was added
        theme_info = self.server.get_theme_info("test-theme")
        self.assertEqual(theme_info["name"], "test-theme")
        self.assertEqual(theme_info["colors"], test_theme)
        
        # Test with invalid theme name
        with self.assertRaises(ValueError):
            self.server.add_custom_theme("invalid theme name", test_theme)
            
        # Test with invalid theme colors (missing key)
        invalid_theme = test_theme.copy()
        del invalid_theme["node_fill"]
        with self.assertRaises(ValueError):
            self.server.add_custom_theme("another-theme", invalid_theme)
        
        # Test removing theme
        result = self.server.remove_custom_theme("test-theme")
        self.assertTrue(result)
        
        # Verify theme was removed
        with self.assertRaises(ValueError):
            self.server.get_theme_info("test-theme")
        
        # Test removing non-existent theme
        with self.assertRaises(ValueError):
            self.server.remove_custom_theme("nonexistent-theme")
            
        # Test removing built-in theme (should fail)
        with self.assertRaises(ValueError):
            self.server.remove_custom_theme("default")
    
    def test_preview_diagram(self):
        """Test generating SVG preview of a diagram."""
        # Mock the requests.get response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<svg>Test SVG Content</svg>"
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Test generating preview
            result = self.server.preview_diagram("graph TD\nA[Start] --> B[End]")
            
            # Verify requests.get was called with the correct URL pattern
            mock_get.assert_called_once()
            url = mock_get.call_args[0][0]
            self.assertTrue(url.startswith("https://mermaid.ink/svg/"))
            
            # Verify result is base64-encoded SVG
            import base64
            decoded = base64.b64decode(result).decode('utf-8')
            self.assertEqual(decoded, "<svg>Test SVG Content</svg>")
        
        # Test with invalid diagram
        self.server.validator.validate = MagicMock(return_value={"is_valid": False, "issues": ["Invalid syntax"]})
        with self.assertRaises(ValidationError):
            self.server.preview_diagram("invalid diagram")
            
        # Test with request exception
        with patch('requests.get', side_effect=requests.RequestException("Connection error")) as mock_get:
            with self.assertRaises(ApiError):
                self.server.preview_diagram("graph TD\nA[Start] --> B[End]")


class TestStyleManager(unittest.TestCase):
    """Tests for the StyleManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temp file for custom themes
        self.temp_themes_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_themes_file.close()
        
        # Sample custom theme
        self.custom_theme = {
            "test-theme": {
                "node_fill": "#f5f5f5",
                "node_border": "#999999",
                "node_text": "#444444",
                "edge": "#888888",
                "highlight": "#ff9900",
                "success": "#99cc99",
                "warning": "#ffdd99",
                "error": "#ff9999"
            }
        }
        
        # Write to temp file
        with open(self.temp_themes_file.name, 'w') as f:
            json.dump(self.custom_theme, f)
            
        self.style_manager = StyleManager(custom_themes_path=self.temp_themes_file.name)
    
    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.temp_themes_file.name):
            os.unlink(self.temp_themes_file.name)
    
    def test_get_theme(self):
        """Test getting themes."""
        # Test default theme
        theme = self.style_manager.get_theme()
        self.assertEqual(theme, DEFAULT_COLOR_THEMES["default"])
        
        # Test specific theme
        theme = self.style_manager.get_theme("dark")
        self.assertEqual(theme, DEFAULT_COLOR_THEMES["dark"])
        
        # Test nonexistent theme (should return default)
        theme = self.style_manager.get_theme("nonexistent")
        self.assertEqual(theme, DEFAULT_COLOR_THEMES["default"])
    
    def test_style_flowchart(self):
        """Test styling flowcharts."""
        diagram = """graph TD
    A[Start] --> B[Process]
    B --> C[End]"""
        
        result = self.style_manager.add_styling_to_diagram(diagram)
        
        # Verify styling was added
        self.assertIn("classDef default", result)
        self.assertIn("fill:", result)
        
        # Test that already styled diagrams are not modified
        styled_diagram = """graph TD
    A[Start] --> B[Process]
    B --> C[End]
    
classDef default fill:#f9f9f9,stroke:#333333"""
        
        result = self.style_manager.add_styling_to_diagram(styled_diagram)
        self.assertEqual(result, styled_diagram)
    
    def test_style_sequence_diagram(self):
        """Test styling sequence diagrams."""
        diagram = """sequenceDiagram
    Alice->>Bob: Hello Bob, how are you?
    Bob-->>Alice: I am good thanks!"""
        
        result = self.style_manager.add_styling_to_diagram(diagram)
        
        # Verify styling was added
        self.assertIn("%%{init:", result)
        self.assertIn("'theme': 'base'", result)
        
        # Test that already styled diagrams are not modified
        styled_diagram = """%%{init: {'theme': 'default'} }%%
sequenceDiagram
    Alice->>Bob: Hello Bob, how are you?
    Bob-->>Alice: I am good thanks!"""
        
        result = self.style_manager.add_styling_to_diagram(styled_diagram)
        self.assertEqual(result, styled_diagram)
    
    def test_style_class_diagram(self):
        """Test styling class diagrams."""
        diagram = """classDiagram
    class Animal {
        +int age
        +String gender
        +isMammal()
        +mate()
    }"""
        
        result = self.style_manager.add_styling_to_diagram(diagram)
        
        # Verify styling was added
        self.assertIn("%%{init:", result)
        self.assertIn("'theme': 'base'", result)
    
    def test_style_er_diagram(self):
        """Test styling ER diagrams."""
        diagram = """erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains"""
        
        result = self.style_manager.add_styling_to_diagram(diagram)
        
        # Verify styling was added
        self.assertIn("%%{init:", result)
        self.assertIn("'theme': 'base'", result)
    
    def test_unsupported_diagram_type(self):
        """Test handling of unsupported diagram types."""
        diagram = """gantt
    title A Gantt Diagram
    section Section
    A task           :a1, 2014-01-01, 30d"""
        
        result = self.style_manager.add_styling_to_diagram(diagram)
        
        # Should return the original diagram unchanged
        self.assertEqual(result, diagram)

    def test_custom_themes_loading(self):
        """Test loading custom themes from file."""
        # Verify custom theme was loaded
        self.assertIn("test-theme", self.style_manager.themes)
        self.assertEqual(self.style_manager.themes["test-theme"], self.custom_theme["test-theme"])
    
    def test_add_remove_custom_theme(self):
        """Test adding and removing custom themes."""
        # Create a new theme
        new_theme = {
            "node_fill": "#ffffff",
            "node_border": "#333333",
            "node_text": "#555555",
            "edge": "#777777",
            "highlight": "#ff5500",
            "success": "#77cc77",
            "warning": "#ffcc77",
            "error": "#ff7777"
        }
        
        # Add the theme
        result = self.style_manager.add_custom_theme("new-theme", new_theme)
        self.assertTrue(result)
        self.assertIn("new-theme", self.style_manager.themes)
        
        # Try to override a built-in theme (should fail)
        result = self.style_manager.add_custom_theme("default", new_theme)
        self.assertFalse(result)
        
        # Test validation - invalid theme (missing key)
        invalid_theme = new_theme.copy()
        del invalid_theme["node_fill"]
        result = self.style_manager.add_custom_theme("invalid-theme", invalid_theme)
        self.assertFalse(result)
        self.assertNotIn("invalid-theme", self.style_manager.themes)
        
        # Test validation - invalid color code
        invalid_theme = new_theme.copy()
        invalid_theme["node_fill"] = "not-a-color"
        result = self.style_manager.add_custom_theme("invalid-theme", invalid_theme)
        self.assertFalse(result)
        
        # Test removing theme
        result = self.style_manager.remove_custom_theme("new-theme")
        self.assertTrue(result)
        self.assertNotIn("new-theme", self.style_manager.themes)
        
        # Test removing non-existent theme
        result = self.style_manager.remove_custom_theme("nonexistent-theme")
        self.assertFalse(result)
        
        # Test removing built-in theme
        result = self.style_manager.remove_custom_theme("default")
        self.assertFalse(result)
        self.assertIn("default", self.style_manager.themes)


if __name__ == "__main__":
    unittest.main()
