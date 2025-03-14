import os
import unittest
from unittest.mock import MagicMock, patch
import sys
import json
import anthropic
from typing import List, Optional
import logging
import pytest
from src.solid.solid_server import SolidServer, ApiError, SolidError, SolidPrinciple, RateLimitError

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestSolidServer(unittest.TestCase):
    """Tests for the SOLID principles analyzer MCP server."""

    def setUp(self):
        """Set up test environment."""
        # Create a mock for the Anthropic client
        self.anthropic_mock = MagicMock()
        # Patch the Anthropic client
        self.patcher = patch('anthropic.Anthropic', return_value=self.anthropic_mock)
        self.patcher.start()
        
        # Initialize the server with a test API key
        self.server = SolidServer(api_key="test-api-key")
        
        # Mock the run method to prevent actual execution
        self.server.mcp.run = MagicMock()
        
        # Create a mock response for the Anthropic client
        self.mock_message = MagicMock()
        self.mock_message.content = [MagicMock(text="mocked response")]
        self.anthropic_mock.messages.create.return_value = self.mock_message
        
        # Add __name__ attribute to the mock to prevent AttributeError
        self.anthropic_mock.messages.create.__name__ = "messages.create"

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

    def test_analyze_code(self):
        """Test the analyze_code tool."""
        # Set specific mock response for this test
        self.mock_message.content[0].text = """
# SOLID Analysis

## Single Responsibility Principle
- Violation: Class handles database connection, business logic, and UI rendering
- Recommendation: Split into separate classes

## Open/Closed Principle
- Compliant: Uses inheritance appropriately
"""
        self.anthropic_mock.messages.create.return_value = self.mock_message

        # Test code
        test_code = """
class UserManager:
    def __init__(self, db_connection):
        self.db = db_connection

    def create_user(self, username, email):
        # Database logic
        self.db.execute("INSERT INTO users VALUES (?, ?)", (username, email))

    def render_user_profile(self, user_id):
        # UI rendering logic
        user = self.db.query("SELECT * FROM users WHERE id = ?", user_id)
        return f"<div class='profile'>{user.username}</div>"
"""

        # Access the tool directly through the class
        result = self.server.analyze_code(test_code)
        
        # Verify the result contains expected analysis
        self.assertIn("Single Responsibility Principle", result)
        self.assertIn("Violation", result)
        
        # Verify the API was called with the correct parameters
        self.anthropic_mock.messages.create.assert_called_once()
        call_kwargs = self.anthropic_mock.messages.create.call_args[1]
        self.assertIn("Analyze this code", call_kwargs['messages'][0]['content'])
        self.assertIn(test_code, call_kwargs['messages'][0]['content'])

    def test_analyze_code_with_specific_principles(self):
        """Test the analyze_code tool with specific principles."""
        # Set mock response
        self.mock_message.content[0].text = "SRP Analysis: Class has too many responsibilities"
        self.anthropic_mock.messages.create.return_value = self.mock_message

        # Test code
        test_code = "class UserManager: pass"

        # Access the tool with specific principles
        result = self.server.analyze_code(test_code, principles=[SolidPrinciple.SRP.value])
        
        # Verify the result
        self.assertEqual(result, "SRP Analysis: Class has too many responsibilities")
        
        # Verify the API was called with the correct parameters
        self.anthropic_mock.messages.create.assert_called_once()
        call_kwargs = self.anthropic_mock.messages.create.call_args[1]
        self.assertIn("Single Responsibility Principle", call_kwargs['messages'][0]['content'])

    def test_suggest_improvements(self):
        """Test the suggest_improvements tool."""
        # Set mock response
        self.mock_message.content[0].text = """
# Improved Code

```python
class UserRepository:
    def __init__(self, db_connection):
        self.db = db_connection

    def create_user(self, username, email):
        self.db.execute("INSERT INTO users VALUES (?, ?)", (username, email))

class UserProfileRenderer:
    def render_user_profile(self, user):
        return f"<div class='profile'>{user.username}</div>"
```

This separates the responsibilities into distinct classes.
"""
        self.anthropic_mock.messages.create.return_value = self.mock_message

        # Test inputs
        test_code = "class UserManager: pass"
        test_analysis = "SRP Violation: Class has too many responsibilities"

        # Access the tool
        result = self.server.suggest_improvements(test_code, test_analysis)
        
        # Verify the result contains improved code
        self.assertIn("UserRepository", result)
        self.assertIn("UserProfileRenderer", result)
        
        # Verify the API was called with the correct parameters
        self.anthropic_mock.messages.create.assert_called_once()
        call_kwargs = self.anthropic_mock.messages.create.call_args[1]
        self.assertIn("Original code", call_kwargs['messages'][0]['content'])
        self.assertIn(test_code, call_kwargs['messages'][0]['content'])
        self.assertIn(test_analysis, call_kwargs['messages'][0]['content'])

    def test_check_compliance(self):
        """Test the check_compliance tool."""
        # Set mock response
        self.mock_message.content[0].text = "LSP Analysis: Derived class properly extends base class functionality"
        self.anthropic_mock.messages.create.return_value = self.mock_message

        # Test inputs
        test_code = """
class Bird:
    def fly(self): pass

class Eagle(Bird):
    def fly(self): pass
"""
        test_principle = SolidPrinciple.LSP.value

        # Access the tool
        result = self.server.check_compliance(test_code, test_principle)
        
        # Verify the result
        self.assertEqual(result, "LSP Analysis: Derived class properly extends base class functionality")
        
        # Verify the API was called with the correct parameters
        self.anthropic_mock.messages.create.assert_called_once()
        call_kwargs = self.anthropic_mock.messages.create.call_args[1]
        self.assertIn("Assess this code's compliance", call_kwargs['messages'][0]['content'])
        self.assertIn(test_principle, call_kwargs['messages'][0]['content'])

    def test_generate_tests(self):
        """Test the generate_tests tool."""
        # Set mock response
        self.mock_message.content[0].text = """
```python
import unittest

class TestUserManager(unittest.TestCase):
    def test_single_responsibility(self):
        # Test that UserManager only has user management methods
        user_manager = UserManager()
        methods = [method for method in dir(user_manager) if callable(getattr(user_manager, method)) and not method.startswith('__')]
        self.assertTrue(all(method.startswith('manage_') for method in methods))
```
"""
        self.anthropic_mock.messages.create.return_value = self.mock_message

        # Test inputs
        test_code = "class UserManager: pass"
        test_analysis = "SRP Analysis: Class has focused responsibilities"

        # Access the tool
        result = self.server.generate_tests(test_code, test_analysis)
        
        # Verify the result contains test code
        self.assertIn("import unittest", result)
        self.assertIn("TestUserManager", result)
        
        # Verify the API was called with the correct parameters
        self.anthropic_mock.messages.create.assert_called_once()
        call_kwargs = self.anthropic_mock.messages.create.call_args[1]
        self.assertIn("Generate tests", call_kwargs['messages'][0]['content'])
        self.assertIn(test_code, call_kwargs['messages'][0]['content'])
        self.assertIn(test_analysis, call_kwargs['messages'][0]['content'])

    def test_input_validation_analyze_code(self):
        """Test input validation for analyze_code."""
        with self.assertRaises(ValueError):
            self.server.analyze_code("")

    def test_input_validation_suggest_improvements(self):
        """Test input validation for suggest_improvements."""
        with self.assertRaises(ValueError):
            self.server.suggest_improvements("", "analysis")
            
        with self.assertRaises(ValueError):
            self.server.suggest_improvements("code", "")

    def test_input_validation_check_compliance(self):
        """Test input validation for check_compliance."""
        with self.assertRaises(ValueError):
            self.server.check_compliance("", "principle")
            
        with self.assertRaises(ValueError):
            self.server.check_compliance("code", "")

    def test_input_validation_generate_tests(self):
        """Test input validation for generate_tests."""
        with self.assertRaises(ValueError):
            self.server.generate_tests("", "analysis")
            
        with self.assertRaises(ValueError):
            self.server.generate_tests("code", "")

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
            self.server.analyze_code("test code")

        # Reset side_effect
        self.anthropic_mock.messages.create.side_effect = None

        # Test general exception handling
        general_error = Exception("Generic error")
        self.anthropic_mock.messages.create.side_effect = general_error

        with self.assertRaises(SolidError):
            self.server.analyze_code("test code")

        # Reset side_effect
        self.anthropic_mock.messages.create.side_effect = None

        # Test rate limit error (use anthropic.APIError with rate limit message)
        rate_limit_error = anthropic.APIError(
            message="Rate limit exceeded",
            request=mock_request,
            body={"error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}}
        )
        self.anthropic_mock.messages.create.side_effect = rate_limit_error

        with self.assertRaises(ApiError):
            self.server.analyze_code("test code")

if __name__ == '__main__':
    unittest.main()
