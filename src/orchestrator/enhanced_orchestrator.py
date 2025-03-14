"""
Enhanced Code Diagram Orchestrator - Integrates with MCP Router for improved functionality.
"""

from code_diagram_orchestrator import CodeDiagramOrchestrator, logger
from router_integration import RouterIntegration
import os
import sys
import signal
import argparse
from typing import Optional
import logging

class EnhancedOrchestrator(CodeDiagramOrchestrator):
    """Enhanced Code Diagram Orchestrator with MCP Router integration."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl: int = 3600,
        calls_per_minute: int = 15,
        router_url: Optional[str] = None,
        server_id: str = "code-diagram-orchestrator",
        enable_router_integration: bool = True
    ):
        """
        Initialize the enhanced orchestrator.
        
        Args:
            api_key: Anthropic API key
            cache_ttl: Cache time-to-live in seconds
            calls_per_minute: API rate limit
            router_url: URL of the MCP Router
            server_id: Unique identifier for this server
            enable_router_integration: Whether to enable router integration
        """
        # Initialize the base orchestrator
        super().__init__(api_key=api_key, cache_ttl=cache_ttl, calls_per_minute=calls_per_minute)
        
        # Initialize router integration if enabled
        self.enable_router_integration = enable_router_integration
        if enable_router_integration:
            self.router_integration = RouterIntegration(
                router_url=router_url,
                server_id=server_id,
                capabilities=[
                    "code-analysis",
                    "code-visualization",
                    "documentation-generation",
                    "diagram-generation"
                ]
            )
        else:
            self.router_integration = None
        
        # Add FastMCP routes for router integration
        self.setup_router_integration_routes()
    
    def setup_router_integration_routes(self):
        """Set up FastMCP routes for router integration."""
        
        @self.mcp.resource("health")
        def health_check():
            """Health check endpoint for the MCP Router."""
            return {
                "status": "healthy",
                "server_id": self.router_integration.server_id if self.router_integration else "code-diagram-orchestrator",
                "timestamp": int(__import__("time").time())
            }
        
        @self.mcp.resource("capabilities")
        def get_capabilities():
            """Get detailed capability information."""
            if self.router_integration:
                return self.router_integration.handle_capability_query()
            else:
                # Basic capability info if router integration is disabled
                return {
                    "server_id": "code-diagram-orchestrator",
                    "capabilities": [
                        "code-analysis",
                        "code-visualization",
                        "documentation-generation", 
                        "diagram-generation"
                    ]
                }
    
    def run(self):
        """Run the MCP server with router integration."""
        logger.info("Starting Enhanced Code Diagram Orchestrator MCP server")
        
        # Set up signal handlers for graceful shutdown
        self.setup_signal_handlers()
        
        # Start router integration if enabled
        if self.enable_router_integration and self.router_integration:
            try:
                logger.info("Starting router integration")
                self.router_integration.start()
            except Exception as e:
                logger.error(f"Failed to start router integration: {str(e)}")
                logger.info("Continuing without router integration")
        
        # Run the MCP server
        self.mcp.run()
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    
    def shutdown(self):
        """Perform graceful shutdown."""
        logger.info("Shutting down Enhanced Code Diagram Orchestrator")
        
        # Stop router integration if enabled
        if self.enable_router_integration and self.router_integration:
            try:
                logger.info("Stopping router integration")
                self.router_integration.stop()
            except Exception as e:
                logger.error(f"Error during router integration shutdown: {str(e)}")
        
        logger.info("Shutdown complete")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Enhanced Code Diagram Orchestrator")
    parser.add_argument(
        "--router-url",
        help="URL of the MCP Router",
        default=os.environ.get("MCP_ROUTER_URL", "http://localhost:3000")
    )
    parser.add_argument(
        "--server-id",
        help="Unique identifier for this server",
        default=os.environ.get("MCP_SERVER_ID", "code-diagram-orchestrator")
    )
    parser.add_argument(
        "--disable-router-integration",
        help="Disable integration with MCP Router",
        action="store_true"
    )
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("LOG_LEVEL", "INFO")
    )
    parser.add_argument(
        "--cache-ttl",
        help="Cache time-to-live in seconds",
        type=int,
        default=int(os.environ.get("CACHE_TTL", "3600"))
    )
    parser.add_argument(
        "--calls-per-minute",
        help="API rate limit (calls per minute)",
        type=int,
        default=int(os.environ.get("CALLS_PER_MINUTE", "15"))
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY environment variable not set.")
        logger.warning("The server will fail to process requests without a valid API key.")
    
    # Create and run the enhanced orchestrator
    server = EnhancedOrchestrator(
        api_key=api_key,
        cache_ttl=args.cache_ttl,
        calls_per_minute=args.calls_per_minute,
        router_url=args.router_url,
        server_id=args.server_id,
        enable_router_integration=not args.disable_router_integration
    )
    
    server.run()

if __name__ == "__main__":
    main()
