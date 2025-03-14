#!/usr/bin/env python3
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import tempfile

# Add the parent directory to the path so we can import the server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.kde_launcher.kde_launcher_server import KDELauncherServer, ValidationError, ApplicationError, DBusError

class TestKDELauncherServer(unittest.TestCase):
    """Test cases for the KDE Launcher server."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dbus objects
        self.mock_session_bus = MagicMock()
        self.mock_krunner_interface = MagicMock()
        self.mock_kwin_interface = MagicMock()
        
        # Mock dbus.SessionBus
        self.patcher_session_bus = patch('dbus.SessionBus', return_value=self.mock_session_bus)
        self.mock_dbus_session_bus = self.patcher_session_bus.start()
        
        # Override server's _get_krunner_interface and _get_kwin_interface methods
        self.patcher_krunner = patch.object(
            KDELauncherServer, 
            '_get_krunner_interface', 
            return_value=self.mock_krunner_interface
        )
        self.mock_get_krunner = self.patcher_krunner.start()
        
        self.patcher_kwin = patch.object(
            KDELauncherServer, 
            '_get_kwin_interface', 
            return_value=self.mock_kwin_interface
        )
        self.mock_get_kwin = self.patcher_kwin.start()
        
        # Initialize the server
        self.server = KDELauncherServer()
        
        # Mock server's mcp.run method to prevent actual server start
        self.server.mcp.run = MagicMock()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.patcher_session_bus.stop()
        self.patcher_krunner.stop()
        self.patcher_kwin.stop()
    
    def test_initialization(self):
        """Test server initialization."""
        self.assertEqual(self.server.mcp.name, "kde-launcher")
        self.assertIsNotNone(self.server.config)
        self.assertEqual(self.server.config["log_level"], "INFO")
    
    def test_validate_app_id(self):
        """Test validation of application IDs."""
        # Valid app IDs
        self.assertTrue(self.server._validate_app_id("firefox"))
        self.assertTrue(self.server._validate_app_id("org.kde.konsole"))
        self.assertTrue(self.server._validate_app_id("application with spaces"))
        
        # Invalid app IDs (containing dangerous characters)
        self.assertFalse(self.server._validate_app_id("firefox & rm -rf /"))
        self.assertFalse(self.server._validate_app_id("konsole; rm -rf /"))
        self.assertFalse(self.server._validate_app_id("app | rm -rf /"))
    
    def test_validate_action(self):
        """Test validation of window actions."""
        # Valid actions
        self.assertTrue(self.server._validate_action("focus"))
        self.assertTrue(self.server._validate_action("minimize"))
        self.assertTrue(self.server._validate_action("maximize"))
        self.assertTrue(self.server._validate_action("close"))
        
        # Invalid actions
        self.assertFalse(self.server._validate_action("invalid"))
        self.assertFalse(self.server._validate_action("kill"))
        self.assertFalse(self.server._validate_action(""))
    
    def test_sanitize_args(self):
        """Test sanitization of command-line arguments."""
        # Valid arguments
        args = ["--profile", "default", "--new-window", "https://example.com"]
        sanitized = self.server._sanitize_args(args)
        self.assertEqual(sanitized, args)
        
        # Arguments with dangerous characters
        dangerous_args = ["--profile", "default", "--exec='rm -rf /'", "$(rm -rf /)"]
        sanitized = self.server._sanitize_args(dangerous_args)
        self.assertEqual(sanitized, ["--profile", "default"])
        
        # Empty arguments
        self.assertEqual(self.server._sanitize_args([]), [])
        self.assertEqual(self.server._sanitize_args(None), [])
    
    def test_search_applications(self):
        """Test searching for applications via KRunner."""
        # Set up mock response
        mock_matches = [
            {
                'text': 'Firefox',
                'subtext': 'Web Browser',
                'data': 'firefox.desktop',
                'categoryRelevance': {'applications': 100}
            },
            {
                'text': 'Firefox Developer Edition',
                'subtext': 'Web Browser for Developers',
                'data': 'firefox-developer-edition.desktop',
                'categoryRelevance': {'applications': 90}
            }
        ]
        self.mock_krunner_interface.Match = MagicMock(return_value=mock_matches)
        
        # Get the search_applications tool from the server
        search_applications = None
        for name, tool in self.server.mcp.tools.items():
            if name == "search_applications":
                search_applications = tool
                break
        
        self.assertIsNotNone(search_applications, "search_applications tool should be registered")
        
        # Call the tool and verify results
        results = search_applications("firefox")
        
        # Verify KRunner.Match was called with the correct query
        self.mock_krunner_interface.Match.assert_called_once_with("firefox")
        
        # Verify results structure
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['name'], 'Firefox')
        self.assertEqual(results[0]['description'], 'Web Browser')
        self.assertEqual(results[0]['app_id'], 'firefox.desktop')
    
    def test_launch_application(self):
        """Test launching an application via KRunner."""
        # Mock KRunner.Run method
        self.mock_krunner_interface.Run = MagicMock()
        
        # Get the launch_application tool from the server
        launch_application = None
        for name, tool in self.server.mcp.tools.items():
            if name == "launch_application":
                launch_application = tool
                break
        
        self.assertIsNotNone(launch_application, "launch_application tool should be registered")
        
        # Call the tool and verify results
        result = launch_application("firefox.desktop", ["--new-window"])
        
        # Verify KRunner.Run was called with the correct app_id
        self.mock_krunner_interface.Run.assert_called_once_with("firefox.desktop")
        
        # Verify result structure
        self.assertTrue(result['success'])
        self.assertEqual(result['app_id'], "firefox.desktop")
        self.assertEqual(result['args'], ["--new-window"])
        
        # Test with invalid app_id
        with self.assertRaises(ValidationError):
            launch_application("firefox; rm -rf /")
    
    def test_list_running_applications(self):
        """Test listing running applications via KWin."""
        # Set up mock response
        mock_window_ids = [123, 456]
        mock_window_info = {
            123: {'caption': 'Firefox', 'resourceClass': 'firefox', 'desktop': 1},
            456: {'caption': 'Terminal', 'resourceClass': 'konsole', 'desktop': 1}
        }
        
        self.mock_kwin_interface.getWindowList = MagicMock(return_value=mock_window_ids)
        self.mock_kwin_interface.getWindowInfo = MagicMock(
            side_effect=lambda window_id: mock_window_info[window_id]
        )
        
        # Get the list_running_applications tool from the server
        list_running_applications = None
        for name, tool in self.server.mcp.tools.items():
            if name == "list_running_applications":
                list_running_applications = tool
                break
        
        self.assertIsNotNone(list_running_applications, "list_running_applications tool should be registered")
        
        # Call the tool and verify results
        results = list_running_applications()
        
        # Verify KWin methods were called
        self.mock_kwin_interface.getWindowList.assert_called_once()
        self.assertEqual(self.mock_kwin_interface.getWindowInfo.call_count, 2)
        
        # Verify results structure
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['window_id'], '123')
        self.assertEqual(results[0]['title'], 'Firefox')
        self.assertEqual(results[0]['class'], 'firefox')
        self.assertEqual(results[0]['desktop'], 1)
    
    def test_control_window(self):
        """Test controlling windows via KWin."""
        # Mock KWin methods
        self.mock_kwin_interface.activateWindow = MagicMock()
        self.mock_kwin_interface.minimizeWindow = MagicMock()
        self.mock_kwin_interface.maximizeWindow = MagicMock()
        self.mock_kwin_interface.closeWindow = MagicMock()
        
        # Get the control_window tool from the server
        control_window = None
        for name, tool in self.server.mcp.tools.items():
            if name == "control_window":
                control_window = tool
                break
        
        self.assertIsNotNone(control_window, "control_window tool should be registered")
        
        # Test focusing a window
        result = control_window("123", "focus")
        self.assertTrue(result)
        self.mock_kwin_interface.activateWindow.assert_called_once_with(123)
        
        # Test minimizing a window
        result = control_window("123", "minimize")
        self.assertTrue(result)
        self.mock_kwin_interface.minimizeWindow.assert_called_once_with(123)
        
        # Test maximizing a window
        result = control_window("123", "maximize")
        self.assertTrue(result)
        self.mock_kwin_interface.maximizeWindow.assert_called_once_with(123)
        
        # Test closing a window
        result = control_window("123", "close")
        self.assertTrue(result)
        self.mock_kwin_interface.closeWindow.assert_called_once_with(123)
        
        # Test with invalid action
        with self.assertRaises(ValidationError):
            control_window("123", "invalid_action")
        
        # Test with invalid window ID
        with self.assertRaises(ValidationError):
            control_window("invalid_id", "focus")
    
    def test_create_launcher(self):
        """Test creating a custom application launcher."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override desktop file path
            test_desktop_path = os.path.join(temp_dir, "test-app.desktop")
            
            # Mock os.path.expanduser to return our test path
            original_expanduser = os.path.expanduser
            def mock_expanduser(path):
                if path.startswith("~/.local/share/applications/"):
                    return test_desktop_path
                return original_expanduser(path)
            
            # Apply the mock
            with patch('os.path.expanduser', side_effect=mock_expanduser):
                # Get the create_launcher tool from the server
                create_launcher = None
                for name, tool in self.server.mcp.tools.items():
                    if name == "create_launcher":
                        create_launcher = tool
                        break
                
                self.assertIsNotNone(create_launcher, "create_launcher tool should be registered")
                
                # Call the tool and verify results
                result = create_launcher(
                    name="Test App",
                    command="/usr/bin/test-app",
                    icon="test-icon",
                    categories=["Development", "Utility"]
                )
                
                # Verify result
                self.assertTrue(result)
                
                # Verify desktop file was created with correct content
                self.assertTrue(os.path.exists(test_desktop_path))
                
                with open(test_desktop_path, 'r') as f:
                    content = f.read()
                    self.assertIn("[Desktop Entry]", content)
                    self.assertIn("Name=Test App", content)
                    self.assertIn("Exec=/usr/bin/test-app", content)
                    self.assertIn("Icon=test-icon", content)
                    self.assertIn("Categories=Development;Utility;", content)
                
                # Test with invalid command
                with self.assertRaises(ValidationError):
                    create_launcher(
                        name="Malicious App",
                        command="/usr/bin/app && rm -rf /",
                        icon="test-icon"
                    )

if __name__ == "__main__":
    unittest.main() 