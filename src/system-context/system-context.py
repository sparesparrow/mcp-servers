import os
import pwd
import subprocess
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import pyperclip
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ErrorResponse
import chromadb
from dotenv import load_dotenv
import re
import json

class SystemContextServer:
    def __init__(self, allowed_paths: List[str]):
        """Initialize the system context server with allowed paths."""
        load_dotenv()
        self.allowed_users = os.getenv("MCP_ALLOWED_USERS", "").split(",")
        self.vector_db = chromadb.PersistentClient(path="./mcp_context_db")
        
        current_user = pwd.getpwuid(os.getuid()).pw_name
        if current_user not in self.allowed_users:
            raise RuntimeError(f"User {current_user} not authorized")

        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self.mcp = FastMCP("system-context")
        self._setup_resources()
        self._setup_tools()

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if a path is within allowed directories."""
        path = path.resolve()
        allowed_patterns = [
            re.compile(p) for p in os.getenv("MCP_PATH_PATTERNS", "").split(",")
        ]
        return any(
            str(path).startswith(str(allowed_path))
            for allowed_path in self.allowed_paths
        ) or any(
            p.match(str(path)) for p in allowed_patterns
        )

    def _get_shell_history(self, limit: int = 100) -> str:
        """Get shell command history from various shell history files."""
        history_files = [
            os.path.expanduser("~/.bash_history"),
            os.path.expanduser("~/.zsh_history"),
            os.path.expanduser("~/.fish_history")
        ]
        
        history = []
        for hist_file in history_files:
            if os.path.exists(hist_file):
                try:
                    with open(hist_file, 'r', encoding='utf-8') as f:
                        history.extend(f.readlines()[-limit:])
                except Exception as e:
                    print(f"Error reading {hist_file}: {e}")
        
        return "\n".join(history[-limit:])

    def _get_clipboard_history(self) -> str:
        """Get current clipboard content."""
        try:
            return pyperclip.paste() or "Clipboard is empty"
        except Exception as e:
            return f"Unable to access clipboard: {e}"

    def _list_directory(self, path: str) -> str:
        """List directory contents with metadata."""
        try:
            path_obj = Path(path).resolve()
            if not self._is_path_allowed(path_obj):
                return f"Access denied to {path}"

            entries = []
            for entry in path_obj.iterdir():
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:]
                    })
                except Exception as e:
                    entries.append({
                        "name": entry.name,
                        "error": str(e)
                    })
            
            return "\n".join(f"{e['name']} ({e.get('type', 'unknown')}): "
                           f"Size: {e.get('size', 'N/A')}, "
                           f"Modified: {e.get('modified', 'N/A')}, "
                           f"Permissions: {e.get('permissions', 'N/A')}"
                           for e in entries)
        except Exception as e:
            return f"Error listing directory: {e}"

    def _read_file(self, path: str, max_size: int = 1024 * 1024) -> str:
        """Read file contents with size limit."""
        try:
            path_obj = Path(path).resolve()
            if not self._is_path_allowed(path_obj):
                return f"Access denied to {path}"

            if not path_obj.is_file():
                return f"Not a file: {path}"

            size = path_obj.stat().st_size
            if size > max_size:
                return f"File too large ({size} bytes). Maximum size is {max_size} bytes."

            with open(path_obj, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    def _setup_resources(self):
        """Set up MCP resources."""
        @self.mcp.resource("shell://history")
        def get_shell_history() -> str:
            """Get recent shell command history."""
            return self._get_shell_history()

        @self.mcp.resource("clipboard://current")
        def get_clipboard() -> str:
            """Get current clipboard content."""
            return self._get_clipboard_history()

        @self.mcp.resource("context://vector-db/collections/{collection_name}")
        def get_vector_db_collection(collection_name: str) -> chromadb.Collection:
            """Access a specific collection in the vector database."""
            return self.vector_db.get_or_create_collection(collection_name)

        @self.mcp.resource("file://{path}")
        def get_file_resource(path: str) -> TextContent | ErrorResponse:
            """Access a file or directory."""
            path_obj = Path(path).resolve()
            if not self._is_path_allowed(path_obj):
                return ErrorResponse(code=403, message=f"Access denied to {path}")

            if path_obj.is_file():
                try:
                    with open(path_obj, 'r', encoding='utf-8') as f:
                        return TextContent(content=f.read())
                except Exception as e:
                    return ErrorResponse(code=500, message=str(e))
            elif path_obj.is_dir():
                # Return directory listing as a structured object (e.g., JSON)
                entries = []
                for entry in path_obj.iterdir():
                    try:
                        stat = entry.stat()
                        entries.append({
                            "name": entry.name,
                            "type": "directory" if entry.is_dir() else "file",
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "permissions": oct(stat.st_mode)[-3:]
                        })
                    except Exception as e:
                        entries.append({
                            "name": entry.name,
                            "error": str(e)
                        })
                return TextContent(content=json.dumps(entries)) # Requires import json
            else:
                return ErrorResponse(code=404, message=f"Not found: {path}")

    def _setup_tools(self):
        """Set up MCP tools."""
        @self.mcp.tool()
        def list_directory(path: str) -> str:
            """List contents of a directory."""
            return self._list_directory(path)

        @self.mcp.tool()
        def read_file(path: str) -> str:
            """Read contents of a file."""
            return self._read_file(path)

        @self.mcp.tool()
        def search_history(pattern: str) -> str:
            """Search shell history for a pattern."""
            history = self._get_shell_history()
            matches = [line for line in history.split('\n') if pattern in line]
            return "\n".join(matches) if matches else "No matching commands found."

        def validate_access(func):
            def wrapper(*args, **kwargs):
                if not self._check_access():
                    return ErrorResponse(code=403, message="Access denied")
                return func(*args, **kwargs)
            return wrapper

        @self.mcp.tool()
        @validate_access
        def search_files(query: str, max_results: int = 5) -> str:
            """Semantic search across documents using vector DB"""
            results = self.vector_db.query(
                query_texts=[query],
                n_results=max_results
            )
            return "\n".join(results['documents'][0])

        @self.mcp.tool()
        @validate_access
        def monitor_directory(path: str) -> str:
            """Watch directory for changes and maintain knowledge graph"""
            if not self._is_path_allowed(Path(path)):
                return ErrorResponse(code=403, message="Path not allowed")
            
            # Implementation using watchdog library
            return self._setup_directory_monitor(path)

    def run(self):
        """Run the MCP server."""
        if os.getenv("MCP_REMOTE_ENABLED"):
            self._enable_remote_transport()
        if __name__ == "__main__":
            import asyncio
            asyncio.run(self.mcp.run())

# Example usage
if __name__ == "__main__":
    # List of allowed paths - customize these based on user needs
    ALLOWED_PATHS = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/projects"),
        # Add more allowed paths as needed
    ]
    
    server = SystemContextServer(ALLOWED_PATHS)
    server.run()
