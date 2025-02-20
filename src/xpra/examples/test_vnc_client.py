"""Example client script for testing the Xpra MCP server in VNC mode."""

from mcp.client import Client
import asyncio
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger("xpra-vnc-client")

async def test_vnc():
    """Test the Xpra MCP server VNC functionality."""
    client = Client()  # Connects to localhost by default
    
    try:
        # Configure firewall for VNC
        logger.info("Configuring firewall for VNC...")
        firewall_result = await client.call(
            "xpra-server",
            "configure_firewall",
            params={"mode": "vnc"}
        )
        logger.info(f"Firewall configuration: {json.dumps(firewall_result, indent=2)}")
        
        # Start Firefox in VNC mode
        logger.info("\nStarting Firefox in VNC mode...")
        start_result = await client.call(
            "xpra-server",
            "start_application",
            params={
                "application": "firefox",
                "mode": "vnc",
                "display": ":0",
                "enable_encryption": True
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
        logger.info(f"1. Connect your VNC client to: {start_result.get('host', 'localhost')}:{start_result.get('port', 5900)}")
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
        await test_vnc()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 