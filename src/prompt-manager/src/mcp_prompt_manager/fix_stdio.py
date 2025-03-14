"""
This module provides a compatibility function for running an MCP server with stdio.
It supports multiple versions of the MCP package.
"""

import sys
import asyncio
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

logger = logging.getLogger("mcp-prompt-manager")

async def run_server_with_stdio(server: Server, options: InitializationOptions):
    """
    Run an MCP server with stdio, compatible with multiple versions of the MCP package.
    This handles different APIs across MCP versions.
    
    Args:
        server: The MCP server instance
        options: The initialization options
    """
    try:
        # Try method 1: Use stdlib stdio (newer MCP versions)
        import mcp.server.stdio
        
        logger.info("Using MCP stdio module...")
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options)
            
    except (ImportError, AttributeError):
        try:
            # Try method 2: Direct stdio serve method (some MCP versions)
            logger.info("Using direct stdio_serve method...")
            await server.stdio_serve(options)
            
        except AttributeError:
            # Method 3: Manual setup with stdin/stdout (fallback for all versions)
            logger.info("Using manual stdin/stdout setup...")
            
            # Configure stdin/stdout for binary data
            sys.stdin.reconfigure(encoding=None)
            sys.stdout.reconfigure(encoding=None)
            
            # Create streams
            stdin_reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(stdin_reader)
            await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
            
            w_transport, w_protocol = await asyncio.get_event_loop().connect_write_pipe(
                asyncio.streams.FlowControlMixin, sys.stdout
            )
            stdout_writer = asyncio.StreamWriter(w_transport, w_protocol, None, asyncio.get_event_loop())
            
            # Run the server with the manual streams
            await server.run(stdin_reader, stdout_writer, options)
