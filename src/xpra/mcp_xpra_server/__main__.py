"""Main entry point for the MCP Xpra server."""

import sys
import logging
import argparse
from pathlib import Path

from .server import XpraServer
from .config_loader import load_config
from .exceptions import XpraError
from .utils.logging import setup_logging

def main():
    """Main entry point for the Xpra MCP server."""
    parser = argparse.ArgumentParser(description="Xpra MCP Server")
    parser.add_argument("--config", 
                      help="Path to configuration file",
                      default=str(Path.home() / ".config/mcp-xpra-server/xpra.yaml"))
    parser.add_argument("--debug",
                      help="Enable debug logging",
                      action="store_true")
    args = parser.parse_args()

    try:
        # Set up logging
        logger = setup_logging(debug=args.debug)
        logger.info("Starting MCP Xpra server...")

        # Load configuration
        config = load_config(args.config)
        
        # Start server
        server = XpraServer(config=config)
        server.run()
        
    except XpraError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 