import json
from pathlib import Path
from typing import Dict, Any, Optional
import time
from dataclasses import dataclass, asdict
import socket
import psutil
import asyncio

from .exceptions import SessionError

@dataclass
class SessionInfo:
    """Information about an Xpra session."""
    session_id: str
    application: str
    display: str
    start_time: float
    mode: str
    port: int
    pid: Optional[int] = None
    status: str = "running"
    process: Optional[asyncio.subprocess.Process] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session info to dictionary."""
        data = asdict(self)
        # Remove process field as it's not JSON serializable
        data.pop("process", None)
        return data
    
    @property
    def is_running(self) -> bool:
        """Check if the session process is running."""
        return self.process is not None and self.process.returncode is None

class SessionManager:
    """Manages Xpra session persistence and state."""
    
    def __init__(self, storage_path: Path):
        """Initialize session manager with storage location."""
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, SessionInfo] = {}
        self._load_existing_sessions()
    
    def _load_existing_sessions(self):
        """Load existing session data from storage."""
        for session_file in self.storage_path.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    session_info = SessionInfo(**data)
                    # Only load if process is still running
                    if session_info.is_running:
                        self._sessions[session_info.session_id] = session_info
                    else:
                        # Clean up stale session file
                        session_file.unlink()
            except Exception as e:
                # Log but continue if a session file is corrupted
                print(f"Failed to load session {session_file}: {e}")
    
    def create_session(
        self,
        application: str,
        display: str,
        mode: str,
        port: int,
        pid: Optional[int] = None
    ) -> SessionInfo:
        """Create and store a new session."""
        session_id = f"{application}_{display}"
        
        if session_id in self._sessions:
            raise SessionError(f"Session {session_id} already exists")
        
        # Check if port is available
        if not self._is_port_available(port):
            raise SessionError(f"Port {port} is already in use")
        
        session_info = SessionInfo(
            session_id=session_id,
            application=application,
            display=display,
            start_time=time.time(),
            mode=mode,
            port=port,
            pid=pid
        )
        
        self._sessions[session_id] = session_info
        self._save_session(session_info)
        return session_info
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get information about a specific session."""
        session = self._sessions.get(session_id)
        if session and not session.is_running:
            self.remove_session(session_id)
            return None
        return session
    
    def list_sessions(self) -> Dict[str, SessionInfo]:
        """Get all active sessions."""
        # Remove any stopped sessions
        for session_id, session in list(self._sessions.items()):
            if not session.is_running:
                self.remove_session(session_id)
        return dict(self._sessions)
    
    def update_session_status(self, session_id: str, status: str):
        """Update the status of a session."""
        if session_id not in self._sessions:
            raise SessionError(f"Session {session_id} not found")
            
        session_info = self._sessions[session_id]
        session_info.status = status
        self._save_session(session_info)
    
    def remove_session(self, session_id: str):
        """Remove a session from storage."""
        if session_id not in self._sessions:
            raise SessionError(f"Session {session_id} not found")
            
        session_file = self.storage_path / f"{session_id}.json"
        try:
            session_file.unlink(missing_ok=True)
            del self._sessions[session_id]
        except Exception as e:
            raise SessionError(f"Failed to remove session {session_id}: {e}")
    
    def _save_session(self, session_info: SessionInfo):
        """Save session information to storage."""
        session_file = self.storage_path / f"{session_info.session_id}.json"
        try:
            with open(session_file, "w") as f:
                json.dump(session_info.to_dict(), f, indent=2)
        except Exception as e:
            raise SessionError(f"Failed to save session {session_info.session_id}: {e}")
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for use."""
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return True
        except socket.error:
            return False
    
    def cleanup_stale_sessions(self):
        """Remove sessions for processes that are no longer running."""
        for session_id, session in list(self._sessions.items()):
            if not session.is_running:
                self.remove_session(session_id) 