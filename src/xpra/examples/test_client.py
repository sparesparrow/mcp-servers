"""Example client script for testing the Xpra MCP server."""

from mcp.client import Client
import asyncio
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger("xpra-client")

async def test_server():
    """Test the Xpra MCP server functionality."""
    client = Client()  # Connects to localhost by default
    
    try:
        # Start Firefox in HTML5 mode
        logger.info("Starting Firefox in HTML5 mode...")
        start_result = await client.call(
            "xpra-server",
            "start_application",
            params={
                "application": "firefox",
                "mode": "html5",
                "display": ":0"
            }
        )
        logger.info(f"Start result: {json.dumps(start_result, indent=2)}")
        session_id = start_result["session_id"]
        
        # List active sessions
        logger.info("\nListing active sessions...")
        list_result = await client.call(
            "xpra-server",
            "list_sessions"
        )
        logger.info(f"Active sessions: {json.dumps(list_result, indent=2)}")
        
        # Wait to allow manual testing
        logger.info("\nSession is running. You can now:")
        logger.info(f"1. Connect to HTML5 interface at: {start_result.get('url', 'http://localhost:8080')}")
        logger.info("Waiting 30 seconds for manual testing...")
        await asyncio.sleep(30)
        
        # Stop the session
        logger.info(f"\nStopping session {session_id}...")
        stop_result = await client.call(
            "xpra-server",
            "stop_session",
            params={"session_id": session_id}
        )
        logger.info(f"Stop result: {json.dumps(stop_result, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

async def main():
    """Main entry point."""
    try:
        await test_server()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 