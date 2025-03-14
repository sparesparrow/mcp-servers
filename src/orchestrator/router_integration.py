"""
Router Integration - Enhances the Code Diagram Orchestrator with MCP Router integration capabilities.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
import time
import threading
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('orchestrator.router_integration')

# Add src directory to path to import other modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class RouterIntegrationError(Exception):
    """Base exception class for router integration errors."""
    pass

class CapabilityRegistrationError(RouterIntegrationError):
    """Exception raised when capability registration fails."""
    pass

class RouterConnectionError(RouterIntegrationError):
    """Exception raised when connection to the router fails."""
    pass

class HealthCheckError(RouterIntegrationError):
    """Exception raised when health check fails."""
    pass

class RouterIntegration:
    """Integration with the MCP Router for capability registration and health checks."""
    
    def __init__(
        self,
        router_url: str = None,
        server_id: str = "code-diagram-orchestrator",
        capabilities: List[str] = None,
        health_check_interval: int = 60,
        retry_interval: int = 5,
        max_retries: int = 3
    ):
        """
        Initialize the router integration.
        
        Args:
            router_url: URL of the MCP Router
            server_id: Unique identifier for this server
            capabilities: List of capabilities this server provides
            health_check_interval: Interval in seconds for health checks
            retry_interval: Interval in seconds between retries
            max_retries: Maximum number of retries for operations
        """
        self.router_url = router_url or os.environ.get("MCP_ROUTER_URL", "http://localhost:3000")
        self.server_id = server_id
        self.capabilities = capabilities or [
            "code-analysis",
            "code-visualization",
            "documentation-generation",
            "diagram-generation"
        ]
        self.health_check_interval = health_check_interval
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        
        self.is_registered = False
        self.health_check_thread = None
        self.stop_health_check = threading.Event()
    
    def start(self):
        """Start the router integration."""
        self.register_capabilities()
        self.start_health_check()
    
    def stop(self):
        """Stop the router integration."""
        if self.health_check_thread:
            self.stop_health_check.set()
            self.health_check_thread.join(timeout=5)
        
        self.unregister_capabilities()
    
    def register_capabilities(self) -> None:
        """
        Register server capabilities with the router.
        
        Raises:
            CapabilityRegistrationError: If registration fails
        """
        registration_data = {
            "server_id": self.server_id,
            "capabilities": self.capabilities,
            "endpoints": {
                "base_url": self._get_server_url(),
                "health": "/health",
                "capabilities": "/capabilities"
            },
            "metadata": {
                "description": "MCP server for code analysis, visualization, and documentation",
                "version": "1.0.0"
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.router_url}/api/v1/capabilities/register",
                    json=registration_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully registered capabilities with router")
                    self.is_registered = True
                    return
                
                logger.warning(f"Failed to register capabilities: HTTP {response.status_code}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
            except requests.RequestException as e:
                logger.warning(f"Failed to connect to router: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
        
        raise CapabilityRegistrationError("Failed to register capabilities with router")
    
    def unregister_capabilities(self) -> None:
        """
        Unregister server capabilities from the router.
        
        This is called during graceful shutdown.
        """
        if not self.is_registered:
            return
        
        try:
            response = requests.post(
                f"{self.router_url}/api/v1/capabilities/unregister",
                json={"server_id": self.server_id},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully unregistered capabilities from router")
                self.is_registered = False
            else:
                logger.warning(f"Failed to unregister capabilities: HTTP {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Failed to connect to router for unregistration: {str(e)}")
    
    def start_health_check(self) -> None:
        """Start the health check thread."""
        if self.health_check_thread and self.health_check_thread.is_alive():
            return
        
        self.stop_health_check.clear()
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        logger.info(f"Started health check thread with interval of {self.health_check_interval} seconds")
    
    def _health_check_loop(self) -> None:
        """Health check loop that runs in a separate thread."""
        while not self.stop_health_check.is_set():
            try:
                self._report_health()
            except Exception as e:
                logger.error(f"Error in health check: {str(e)}")
            
            # Wait for the next check interval, but check stop flag every second
            for _ in range(self.health_check_interval):
                if self.stop_health_check.is_set():
                    break
                time.sleep(1)
    
    def _report_health(self) -> None:
        """
        Report health status to the router.
        
        Raises:
            HealthCheckError: If health check fails
        """
        health_data = {
            "server_id": self.server_id,
            "status": "healthy",
            "timestamp": int(time.time()),
            "details": {
                "uptime": self._get_uptime(),
                "load": self._get_system_load(),
                "memory_usage": self._get_memory_usage()
            }
        }
        
        try:
            response = requests.post(
                f"{self.router_url}/api/v1/health/report",
                json=health_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug(f"Successfully reported health status to router")
            else:
                logger.warning(f"Failed to report health status: HTTP {response.status_code}")
                
                # If the server is not registered, try to re-register
                if response.status_code == 404 and not self.is_registered:
                    logger.info("Attempting to re-register capabilities")
                    self.register_capabilities()
        except requests.RequestException as e:
            logger.warning(f"Failed to connect to router for health check: {str(e)}")
    
    def handle_capability_query(self) -> Dict[str, Any]:
        """
        Handle a request for capability information.
        
        This is called when the router queries for detailed capability information.
        
        Returns:
            Dict containing capability details
        """
        capability_details = {
            "server_id": self.server_id,
            "capabilities": self.capabilities,
            "tools": [
                {
                    "name": "analyze_and_visualize",
                    "description": "Analyze code against SOLID principles and generate a diagram",
                    "parameters": {
                        "code": {
                            "type": "string",
                            "description": "Code to analyze"
                        },
                        "principles": {
                            "type": "array",
                            "description": "Optional list of specific principles to check",
                            "items": {
                                "type": "string"
                            },
                            "required": False
                        }
                    },
                    "returns": {
                        "type": "object",
                        "description": "Analysis and diagram results"
                    }
                },
                {
                    "name": "generate_class_diagram",
                    "description": "Generate a class diagram from code",
                    "parameters": {
                        "code": {
                            "type": "string",
                            "description": "Code to generate diagram from"
                        }
                    },
                    "returns": {
                        "type": "string",
                        "description": "Mermaid diagram code"
                    }
                },
                {
                    "name": "create_documentation",
                    "description": "Create comprehensive documentation for code with analysis and diagrams",
                    "parameters": {
                        "code": {
                            "type": "string",
                            "description": "Code to document"
                        }
                    },
                    "returns": {
                        "type": "string",
                        "description": "Markdown documentation"
                    }
                },
                {
                    "name": "clear_cache",
                    "description": "Clear the server's response cache",
                    "parameters": {},
                    "returns": {
                        "type": "string",
                        "description": "Confirmation message"
                    }
                }
            ]
        }
        
        return capability_details
    
    def _get_server_url(self) -> str:
        """
        Get the server's own URL.
        
        Returns:
            Server URL
        """
        # In a real implementation, this would be more sophisticated
        # and would determine the actual URL the server is running on
        server_host = os.environ.get("MCP_SERVER_HOST", "localhost")
        server_port = os.environ.get("MCP_SERVER_PORT", "8000")
        return f"http://{server_host}:{server_port}"
    
    def _get_uptime(self) -> int:
        """
        Get server uptime in seconds.
        
        Returns:
            Uptime in seconds
        """
        # This is a placeholder - in a real implementation,
        # you'd get the actual server start time
        return 3600  # 1 hour
    
    def _get_system_load(self) -> float:
        """
        Get system load average.
        
        Returns:
            System load average
        """
        try:
            import os
            load = os.getloadavg()[0]
            return load
        except (AttributeError, OSError):
            # Fallback for systems that don't support getloadavg
            return 0.0
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """
        Get memory usage information.
        
        Returns:
            Dict with memory usage details
        """
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return {
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024)
            }
        except (ImportError, AttributeError):
            # Fallback if psutil is not available
            return {
                "rss_mb": 0.0,
                "vms_mb": 0.0
            }
