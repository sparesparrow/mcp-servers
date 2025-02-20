"""Session monitoring and notification handling."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Set
import psutil

from .session import SessionInfo
from .exceptions import SessionError

logger = logging.getLogger(__name__)

class SessionMonitor:
    """Monitors Xpra sessions and sends notifications about state changes."""
    
    def __init__(self, mcp_server):
        """Initialize session monitor.
        
        Args:
            mcp_server: The MCP server instance
        """
        self.mcp = mcp_server
        self._monitored_sessions: Dict[str, SessionInfo] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_monitoring = asyncio.Event()
    
    async def start(self):
        """Start session monitoring."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitor_sessions())
            logger.info("Session monitoring started")
    
    async def stop(self):
        """Stop session monitoring."""
        if self._monitoring_task:
            self._stop_monitoring.set()
            await self._monitoring_task
            self._monitoring_task = None
            logger.info("Session monitoring stopped")
    
    def add_session(self, session: SessionInfo):
        """Add a session to monitor."""
        self._monitored_sessions[session.session_id] = session
    
    def remove_session(self, session_id: str):
        """Remove a session from monitoring."""
        self._monitored_sessions.pop(session_id, None)
    
    async def _monitor_sessions(self):
        """Monitor sessions and send notifications about state changes."""
        while not self._stop_monitoring.is_set():
            try:
                for session_id, session in list(self._monitored_sessions.items()):
                    # Check process status
                    try:
                        process = psutil.Process(session.pid)
                        if not process.is_running():
                            await self._notify_session_change(session_id, "stopped")
                            self.remove_session(session_id)
                            continue
                        
                        # Check resource usage
                        cpu_percent = process.cpu_percent()
                        memory_info = process.memory_info()
                        
                        if cpu_percent > 90:  # High CPU usage
                            await self._notify_resource_warning(
                                session_id,
                                "high_cpu",
                                f"CPU usage at {cpu_percent}%"
                            )
                        
                        if memory_info.rss > 1024 * 1024 * 1024:  # >1GB RAM
                            await self._notify_resource_warning(
                                session_id,
                                "high_memory",
                                f"Memory usage at {memory_info.rss / (1024*1024):.1f}MB"
                            )
                            
                    except psutil.NoSuchProcess:
                        await self._notify_session_change(session_id, "stopped")
                        self.remove_session(session_id)
                    except Exception as e:
                        logger.error(f"Error monitoring session {session_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in session monitoring: {e}")
            
            await asyncio.sleep(5)  # Check every 5 seconds
    
    async def _notify_session_change(self, session_id: str, status: str):
        """Send a session state change notification."""
        try:
            notification = {
                "session_id": session_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            await self.mcp.send_notification(
                "notifications/sessions/status_changed",
                notification
            )
            logger.info(f"Session {session_id} status changed to {status}")
        except Exception as e:
            logger.error(f"Failed to send session notification: {e}")
    
    async def _notify_resource_warning(self, session_id: str, warning_type: str, message: str):
        """Send a resource warning notification."""
        try:
            notification = {
                "session_id": session_id,
                "type": warning_type,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            await self.mcp.send_notification(
                "notifications/sessions/resource_warning",
                notification
            )
            logger.warning(f"Resource warning for session {session_id}: {message}")
        except Exception as e:
            logger.error(f"Failed to send resource warning: {e}") 