import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(debug: bool = False):
    """Configure logging for the xpra MCP server.
    
    Args:
        debug: Whether to enable debug logging
    """
    log_dir = Path.home() / ".local" / "share" / "mcp-xpra-server" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s',
        handlers=[
            RotatingFileHandler(
                log_dir / "xpra-server.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            ),
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    # Configure specific loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("subprocess").setLevel(logging.INFO)
    
    logger = logging.getLogger("xpra-mcp")
    logger.setLevel(log_level)
    return logger