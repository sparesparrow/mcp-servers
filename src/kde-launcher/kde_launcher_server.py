#!/usr/bin/env python3
import os
import sys
import logging
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Union
from functools import lru_cache

# Import FastMCP framework
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('kde-launcher-server')

# Import D-Bus interface - with error handling if not available
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    logger.warning("D-Bus Python bindings not found. Some functionality may be limited.")
    DBUS_AVAILABLE = False

# Custom exceptions for the KDE Launcher server
class KDELauncherError(Exception):
    """Base exception class for KDE Launcher server errors."""
    pass

class DBusError(KDELauncherError):
    """Exception raised for D-Bus communication errors."""
    pass

class ApplicationError(KDELauncherError):
    """Exception raised for application-related errors."""
    pass

class ValidationError(KDELauncherError):
    """Exception raised when input validation fails."""
    pass

class KDELauncherServer:
    """MCP server for launching and managing KDE Plasma desktop applications."""
    
    def __init__(self, **config):
        """Initialize the KDE Launcher server with configuration.
        
        Args:
            config: Optional configuration parameters
        """
        self.mcp = FastMCP("kde-launcher")
        
        # Load configuration
        self._load_config(config)
        
        # Initialize D-Bus connection if available
        self._initialize_dbus()
        
        # Register tools
        self.setup_tools()
        
        logger.info("KDE Launcher server initialized")
    
    def _load_config(self, config: Dict[str, Any]) -> None:
        """Load configuration from parameters or environment variables.
        
        Args:
            config: Configuration dictionary
        """
        # Default configuration
        self.config = {
            "log_level": "INFO",
            "krunner_timeout": 5000,  # KRunner search timeout in ms
            "desktop_file_dirs": [
                "/usr/share/applications",
                "~/.local/share/applications"
            ]
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Update with environment variables
        if os.environ.get("KDE_LAUNCHER_LOG_LEVEL"):
            self.config["log_level"] = os.environ.get("KDE_LAUNCHER_LOG_LEVEL")
        
        if os.environ.get("KDE_LAUNCHER_KRUNNER_TIMEOUT"):
            try:
                self.config["krunner_timeout"] = int(os.environ.get("KDE_LAUNCHER_KRUNNER_TIMEOUT"))
            except ValueError:
                logger.warning("Invalid KRunner timeout in environment variable, using default")
        
        # Set log level
        logger.setLevel(getattr(logging, self.config["log_level"].upper()))
    
    def _initialize_dbus(self) -> None:
        """Initialize D-Bus connections for interacting with KDE services."""
        if not DBUS_AVAILABLE:
            logger.warning("D-Bus support not available, running in limited mode")
            return
        
        try:
            # Initialize D-Bus mainloop
            DBusGMainLoop(set_as_default=True)
            
            # Get session bus
            self.session_bus = dbus.SessionBus()
            
            # Initialize KRunner interface
            self.krunner_interface = self._get_krunner_interface()
            
            # Initialize KWin interface for window management
            self.kwin_interface = self._get_kwin_interface()
            
            logger.info("D-Bus interfaces initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize D-Bus interfaces: {str(e)}")
            self.session_bus = None
            self.krunner_interface = None
            self.kwin_interface = None
    
    def _get_krunner_interface(self) -> Optional[dbus.Interface]:
        """Get the KRunner D-Bus interface.
        
        Returns:
            KRunner D-Bus interface or None if not available
        """
        if not self.session_bus:
            return None
        
        try:
            krunner_object = self.session_bus.get_object(
                'org.kde.krunner',
                '/PlasmaRunnerManager'
            )
            return dbus.Interface(krunner_object, 'org.kde.krunner.App')
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to get KRunner interface: {str(e)}")
            return None
    
    def _get_kwin_interface(self) -> Optional[dbus.Interface]:
        """Get the KWin D-Bus interface.
        
        Returns:
            KWin D-Bus interface or None if not available
        """
        if not self.session_bus:
            return None
        
        try:
            kwin_object = self.session_bus.get_object(
                'org.kde.KWin',
                '/KWin'
            )
            return dbus.Interface(kwin_object, 'org.kde.KWin')
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to get KWin interface: {str(e)}")
            return None
    
    def _validate_app_id(self, app_id: str) -> bool:
        """Validate application ID to prevent command injection.
        
        Args:
            app_id: Application ID to validate
            
        Returns:
            True if application ID is valid, False otherwise
        """
        # Basic validation to prevent command injection
        invalid_chars = ['&', ';', '|', '>', '<', '$', '`', '\\', '"', "'"]
        if any(char in app_id for char in invalid_chars):
            return False
        
        return True
    
    def _validate_action(self, action: str) -> bool:
        """Validate window action.
        
        Args:
            action: Window action to validate
            
        Returns:
            True if action is valid, False otherwise
        """
        valid_actions = ["focus", "minimize", "maximize", "close"]
        return action in valid_actions
    
    def _sanitize_args(self, args: List[str]) -> List[str]:
        """Sanitize command-line arguments.
        
        Args:
            args: List of arguments to sanitize
            
        Returns:
            Sanitized list of arguments
        """
        if not args:
            return []
        
        # Basic sanitization to prevent command injection
        sanitized_args = []
        for arg in args:
            # Remove potentially dangerous characters
            invalid_chars = ['&', ';', '|', '$', '`']
            if any(char in arg for char in invalid_chars):
                continue
            
            sanitized_args.append(arg)
        
        return sanitized_args
    
    def setup_tools(self) -> None:
        """Register tools with the MCP server."""
        @self.mcp.tool()
        def search_applications(query: str) -> List[Dict[str, str]]:
            """Search for applications matching a query string.
            
            Args:
                query: Search query string
                
            Returns:
                List of matching applications with name, description, and application ID
            """
            logger.info(f"Searching for applications matching query: {query}")
            
            if not DBUS_AVAILABLE or not self.krunner_interface:
                # Fallback to desktop file search if D-Bus is not available
                return self._search_desktop_files(query)
            
            try:
                # Use KRunner to search for applications
                matches = self.krunner_interface.Match(query)
                
                # Filter for application matches only
                app_matches = []
                for match in matches:
                    if match['categoryRelevance'].get('applications', 0) > 0:
                        app_matches.append({
                            'name': str(match['text']),
                            'description': str(match.get('subtext', '')),
                            'app_id': str(match['data'])
                        })
                
                logger.info(f"Found {len(app_matches)} matching applications")
                return app_matches
            except dbus.exceptions.DBusException as e:
                logger.error(f"D-Bus error in search_applications: {str(e)}")
                raise DBusError(f"Failed to search applications: {str(e)}")
        
        @self.mcp.tool()
        def launch_application(app_id: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
            """Launch an application with optional command-line arguments.
            
            Args:
                app_id: Application ID or executable name
                args: Optional list of command-line arguments
                
            Returns:
                Status and process information
            """
            logger.info(f"Launching application: {app_id}")
            
            # Validate app_id to prevent command injection
            if not self._validate_app_id(app_id):
                raise ValidationError("Invalid application ID")
            
            # Sanitize arguments
            sanitized_args = self._sanitize_args(args) if args else []
            
            if not DBUS_AVAILABLE or not self.krunner_interface:
                # Fallback to subprocess if D-Bus is not available
                return self._launch_app_subprocess(app_id, sanitized_args)
            
            try:
                # Use KRunner to launch the application
                self.krunner_interface.Run(app_id)
                
                return {
                    'success': True,
                    'app_id': app_id,
                    'args': sanitized_args if sanitized_args else []
                }
            except dbus.exceptions.DBusException as e:
                logger.error(f"D-Bus error in launch_application: {str(e)}")
                
                # Try fallback to subprocess
                logger.info("Trying fallback launch method")
                return self._launch_app_subprocess(app_id, sanitized_args)
        
        @self.mcp.tool()
        def list_running_applications() -> List[Dict[str, Any]]:
            """Get information about currently running applications.
            
            Returns:
                List of running applications with window IDs and titles
            """
            logger.info("Listing running applications")
            
            if not DBUS_AVAILABLE or not self.kwin_interface:
                logger.warning("Cannot list running applications: D-Bus or KWin interface not available")
                return []
            
            try:
                # Get list of windows from KWin
                window_ids = self.kwin_interface.getWindowList()
                
                running_apps = []
                for window_id in window_ids:
                    properties = self.kwin_interface.getWindowInfo(window_id)
                    
                    running_apps.append({
                        'window_id': str(window_id),
                        'title': str(properties.get('caption', 'Unknown')),
                        'class': str(properties.get('resourceClass', 'Unknown')),
                        'desktop': int(properties.get('desktop', 0))
                    })
                
                logger.info(f"Found {len(running_apps)} running applications")
                return running_apps
            except dbus.exceptions.DBusException as e:
                logger.error(f"D-Bus error in list_running_applications: {str(e)}")
                raise DBusError(f"Failed to list running applications: {str(e)}")
        
        @self.mcp.tool()
        def control_window(window_id: str, action: str) -> bool:
            """Control an application window (focus, minimize, maximize, close).
            
            Args:
                window_id: Window ID
                action: Control action ("focus", "minimize", "maximize", "close")
                
            Returns:
                True if action was successful, False otherwise
            """
            logger.info(f"Controlling window {window_id}: {action}")
            
            # Validate action
            if not self._validate_action(action):
                raise ValidationError(f"Invalid action: {action}")
            
            if not DBUS_AVAILABLE or not self.kwin_interface:
                logger.warning("Cannot control window: D-Bus or KWin interface not available")
                return False
            
            try:
                window_id_int = int(window_id)
            except ValueError:
                raise ValidationError(f"Invalid window ID: {window_id}")
            
            try:
                # Perform window action
                if action == "focus":
                    self.kwin_interface.activateWindow(window_id_int)
                elif action == "minimize":
                    self.kwin_interface.minimizeWindow(window_id_int)
                elif action == "maximize":
                    self.kwin_interface.maximizeWindow(window_id_int)
                elif action == "close":
                    self.kwin_interface.closeWindow(window_id_int)
                
                return True
            except dbus.exceptions.DBusException as e:
                logger.error(f"D-Bus error in control_window: {str(e)}")
                raise DBusError(f"Failed to control window: {str(e)}")
        
        @self.mcp.tool()
        def create_launcher(name: str, command: str, icon: Optional[str] = None, 
                           categories: Optional[List[str]] = None) -> bool:
            """Create a custom application launcher for frequent use.
            
            Args:
                name: Launcher name
                command: Command to execute
                icon: Optional icon name
                categories: Optional categories for the launcher
                
            Returns:
                True if launcher was created, False otherwise
            """
            logger.info(f"Creating launcher: {name}")
            
            # Validate name and command
            if not name or not command:
                raise ValidationError("Launcher name and command are required")
            
            # Sanitize command to prevent security issues
            invalid_chars = ['&', ';', '|', '$', '`', '\\']
            if any(char in command for char in invalid_chars):
                raise ValidationError("Invalid command - contains potentially unsafe characters")
            
            # Create desktop file content
            desktop_file_content = [
                "[Desktop Entry]",
                f"Name={name}",
                f"Exec={command}",
                "Type=Application",
                "Terminal=false",
            ]
            
            if icon:
                desktop_file_content.append(f"Icon={icon}")
            
            if categories:
                desktop_file_content.append(f"Categories={';'.join(categories)};")
            
            # Create desktop file in user's local applications directory
            desktop_file_path = os.path.expanduser(f"~/.local/share/applications/{name.lower().replace(' ', '-')}.desktop")
            
            try:
                # Create directories if they don't exist
                os.makedirs(os.path.dirname(desktop_file_path), exist_ok=True)
                
                # Write desktop file
                with open(desktop_file_path, 'w') as f:
                    f.write('\n'.join(desktop_file_content))
                
                # Make desktop file executable
                os.chmod(desktop_file_path, 0o755)
                
                logger.info(f"Created launcher: {desktop_file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to create launcher: {str(e)}")
                raise ApplicationError(f"Failed to create launcher: {str(e)}")
    
    def _search_desktop_files(self, query: str) -> List[Dict[str, str]]:
        """Search for applications in desktop files.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching applications
        """
        matches = []
        query_lower = query.lower()
        
        # Expand desktop file directories
        desktop_dirs = [os.path.expanduser(d) for d in self.config["desktop_file_dirs"]]
        
        for directory in desktop_dirs:
            if not os.path.exists(directory):
                continue
            
            for filename in os.listdir(directory):
                if not filename.endswith('.desktop'):
                    continue
                
                path = os.path.join(directory, filename)
                
                try:
                    # Parse desktop file
                    app_info = {}
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Basic parsing of desktop file
                        for line in content.splitlines():
                            if '=' in line:
                                key, value = line.split('=', 1)
                                if key == 'Name':
                                    app_info['name'] = value
                                elif key == 'Comment':
                                    app_info['description'] = value
                                elif key == 'Exec':
                                    app_info['exec'] = value
                    
                    # Check if app matches query
                    if 'name' in app_info and query_lower in app_info['name'].lower():
                        matches.append({
                            'name': app_info.get('name', 'Unknown'),
                            'description': app_info.get('description', ''),
                            'app_id': path
                        })
                except Exception as e:
                    logger.warning(f"Error parsing desktop file {path}: {str(e)}")
        
        logger.info(f"Found {len(matches)} matching applications in desktop files")
        return matches
    
    def _launch_app_subprocess(self, app_id: str, args: List[str]) -> Dict[str, Any]:
        """Launch application using subprocess.
        
        Args:
            app_id: Application ID or executable name
            args: Command-line arguments
            
        Returns:
            Status and process information
        """
        try:
            # Check if app_id is a path to a desktop file
            if app_id.endswith('.desktop'):
                # Parse desktop file to get the Exec line
                with open(app_id, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('Exec='):
                            command = line[5:].strip()
                            # Remove field codes (%f, %F, etc.)
                            command = command.split('%')[0].strip()
                            break
                    else:
                        raise ApplicationError(f"No Exec line found in desktop file: {app_id}")
                
                # Launch application with arguments
                if args:
                    command = f"{command} {' '.join(args)}"
                
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            else:
                # Launch application by name/command
                process = subprocess.Popen(
                    [app_id] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            
            # Wait a bit to check for immediate failure
            try:
                return_code = process.wait(timeout=0.5)
                if return_code != 0:
                    stderr = process.stderr.read().decode('utf-8')
                    raise ApplicationError(f"Application exited with non-zero status: {stderr}")
            except subprocess.TimeoutExpired:
                # Process is still running, which is good
                pass
            
            return {
                'success': True,
                'app_id': app_id,
                'args': args,
                'pid': process.pid
            }
        except Exception as e:
            logger.error(f"Failed to launch application: {str(e)}")
            raise ApplicationError(f"Failed to launch application: {str(e)}")
    
    def run(self) -> None:
        """Run the KDE Launcher server."""
        if DBUS_AVAILABLE:
            # Set up D-Bus main loop
            self.loop = GLib.MainLoop()
            
            # Set up a thread for the GLib main loop
            import threading
            dbus_thread = threading.Thread(target=self.loop.run)
            dbus_thread.daemon = True
            dbus_thread.start()
        
        logger.info("Starting KDE Launcher server")
        self.mcp.run()

def main() -> None:
    """Entry point for the KDE Launcher server."""
    try:
        server = KDELauncherServer()
        server.run()
    except Exception as e:
        logger.error(f"Failed to start KDE Launcher server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 