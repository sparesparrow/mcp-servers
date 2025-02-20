"""MCP server for managing Xpra sessions."""

import argparse
import logging
import sys
from pathlib import Path

from .version import __version__
from .server import XpraServer
from .config_loader import load_config
from .exceptions import XpraError

def main():
    """Main entry point for the Xpra MCP server."""
    parser = argparse.ArgumentParser(description="Xpra MCP Server")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Ensure log directory exists
        config.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Start server
        server = XpraServer(config=config)
        server.run()
        
    except XpraError as e:
        logging.error(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()