#!/usr/bin/env python3
"""
Simple runner script for the prompt-manager MCP server.
"""
import asyncio
from src.prompt_manager_server import serve

if __name__ == "__main__":
    asyncio.run(serve()) 