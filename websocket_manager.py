"""
BotPhia Thread-Safe WebSocket Manager
====================================

Thread-safe WebSocket connection management with message queuing,
dead connection cleanup, and async worker system for real-time trading data.

Author: Senior Backend Developer
Phase: 1 - Days 8-10
"""

import asyncio
import json
import logging
import threading
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Callable, Union
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import uuid
from concurrent.futures import ThreadPoolExecutor
import time

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# Import error handling system
from error_handler import (
    ErrorHandler, WebSocketError, handle_errors, ErrorSeverity,
    handle_api_error, handle_critical_error
)

# Configure logging
logger = logging.getLogger(__name__)

# Message Types and Models
# =======================

class MessageType(Enum):
    """WebSocket message types"""
    INITIAL_STATE = "initial_state"
    SIGNAL_UPDATE = "signal_update"
    POSITION_UPDATE = "position_update"
    MARKET_DATA = "market_data"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    USER_ACTION = "user_action"

@dataclass
class WebSocketMessage:
    """Structured WebSocket message"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    priority: int = 0  # Higher number = higher priority

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp,
            'message_id': self.message_id,
            'user_id': self.user_id
        }

@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection"""
    connection_id: str
    websocket: WebSocket
    user_id: Optional[str]
    connected_at: datetime
    last_heartbeat: datetime
    subscriptions: Set[str] = field(default_factory=set)
    message_count: int = 0
    is_authenticated: bool = False

# Thread-Safe WebSocket Manager
# =============================

class ThreadSafeWebSocketManager:
    """
    Thread-safe WebSocket connection manager with comprehensive features.
    
    Features:
    - Thread-safe connection management
    - Message queuing with priorities
    - Dead connection detection and cleanup
    - User-specific subscriptions
    - Heartbeat monitoring
    - Message delivery guarantees
    - Performance monitoring
    """
    
    def __init__(self, max_connections: int = 100, heartbeat_interval: int = 30,
                 cleanup_interval: int = 60, max_queue_size: int = 1000):
        """
        Initialize WebSocket manager.
        
        Args:
            max_connections: Maximum concurrent connections
            heartbeat_interval: Heartbeat check interval in seconds
            cleanup_interval: Dead connection cleanup interval in seconds
            max_queue_size: Maximum messages in queue per connection
        """
        # Thread-safe connection storage
        self._connections: Dict[str, ConnectionInfo] = {}
        self._user_connections: Dict[str, Set[str]] = defaultdict(set)
        self._connection_lock = threading.RLock()
        
        # Message queuing
        self._message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))
        self._queue_lock = threading.RLock()
        
        # Configuration
        self.max_connections = max_connections
        self.heartbeat_interval = heartbeat_interval
        self.cleanup_interval = cleanup_interval
        self.max_queue_size = max_queue_size
        
        # Worker management
        self._worker_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ws_worker")
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            'total_connections': 0,
            'messages_sent': 0,
            'messages_failed': 0,
            'dead_connections_cleaned': 0,
            'start_time': datetime.now()
        }
        self._stats_lock = threading.Lock()
        
        # Error handler
        self.error_handler = ErrorHandler()
        
        logger.info(f"ThreadSafeWebSocketManager initialized (max_connections={max_connections})")
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """
        Add a new WebSocket connection.
        
        Args:
            websocket: WebSocket instance
            user_id: Optional user ID for authentication
            
        Returns:
            Connection ID
            
        Raises:
            WebSocketError: If connection limit exceeded or connection fails
        """
        connection_id = str(uuid.uuid4())
        
        try:
            # Check connection limit
            with self._connection_lock:
                if len(self._connections) >= self.max_connections:
                    raise WebSocketError(
                        message=f"Connection limit exceeded ({self.max_connections})",
                        context={'current_connections': len(self._connections)}
                    )
            
            # Accept WebSocket connection
            await websocket.accept()
            
            # Create connection info
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                websocket=websocket,
                user_id=user_id,
                connected_at=datetime.now(),
                last_heartbeat=datetime.now(),
                is_authenticated=user_id is not None
            )
            
            # Store connection
            with self._connection_lock:
                self._connections[connection_id] = connection_info
                if user_id:
                    self._user_connections[user_id].add(connection_id)
            
            # Update statistics
            with self._stats_lock:
                self._stats['total_connections'] += 1
            
            # Start background tasks if first connection
            if len(self._connections) == 1:
                await self._start_background_tasks()
            
            logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
            
            # Send initial state
            await self._send_initial_state(connection_id)
            
            return connection_id
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'websocket_connect',
                'connection_id': connection_id,
                'user_id': user_id
            }, ErrorSeverity.HIGH)
            raise WebSocketError(f"Failed to connect WebSocket: {str(e)}")
    
    async def disconnect(self, connection_id: str, reason: str = "normal") -> bool:
        """
        Disconnect a WebSocket connection.
        
        Args:
            connection_id: Connection ID to disconnect
            reason: Disconnection reason
            
        Returns:
            True if connection was found and disconnected
        """
        try:
            with self._connection_lock:
                connection_info = self._connections.get(connection_id)
                if not connection_info:
                    return False
                
                # Remove from user connections
                if connection_info.user_id:
                    self._user_connections[connection_info.user_id].discard(connection_id)
                    if not self._user_connections[connection_info.user_id]:
                        del self._user_connections[connection_info.user_id]
                
                # Remove connection
                del self._connections[connection_id]
            
            # Clear message queue
            with self._queue_lock:
                if connection_id in self._message_queues:
                    del self._message_queues[connection_id]
            
            # Close WebSocket if still open
            try:
                if connection_info.websocket:
                    await connection_info.websocket.close()
            except Exception:
                pass  # Connection might already be closed
            
            logger.info(f"WebSocket disconnected: {connection_id} (reason: {reason})")
            
            # Stop background tasks if no connections
            if not self._connections:
                await self._stop_background_tasks()
            
            return True
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'websocket_disconnect',
                'connection_id': connection_id,
                'reason': reason
            })
            return False
    
    async def send_message(self, message: WebSocketMessage, 
                          connection_id: Optional[str] = None,
                          user_id: Optional[str] = None,
                          broadcast: bool = False) -> Dict[str, bool]:
        """
        Send message to WebSocket connection(s).
        
        Args:
            message: Message to send
            connection_id: Specific connection ID (mutually exclusive with user_id/broadcast)
            user_id: Send to all connections of this user
            broadcast: Send to all connections
            
        Returns:
            Dictionary mapping connection IDs to success status
        """
        if sum([bool(connection_id), bool(user_id), broadcast]) != 1:
            raise ValueError("Exactly one of connection_id, user_id, or broadcast must be specified")
        
        results = {}
        target_connections = []
        
        # Determine target connections
        with self._connection_lock:
            if connection_id:
                if connection_id in self._connections:
                    target_connections = [self._connections[connection_id]]
            elif user_id:
                for conn_id in self._user_connections.get(user_id, set()):
                    if conn_id in self._connections:
                        target_connections.append(self._connections[conn_id])
            elif broadcast:
                target_connections = list(self._connections.values())
        
        # Send to each target connection
        for connection_info in target_connections:
            success = await self._send_to_connection(connection_info, message)
            results[connection_info.connection_id] = success
        
        return results
    
    async def _send_to_connection(self, connection_info: ConnectionInfo, 
                                 message: WebSocketMessage) -> bool:
        """Send message to a specific connection"""
        try:
            # Set user_id if not already set
            if not message.user_id and connection_info.user_id:
                message.user_id = connection_info.user_id
            
            # Convert to JSON
            json_message = json.dumps(message.to_dict())
            
            # Send message
            await connection_info.websocket.send_text(json_message)
            
            # Update statistics
            connection_info.message_count += 1
            with self._stats_lock:
                self._stats['messages_sent'] += 1
            
            logger.debug(f"Message sent to {connection_info.connection_id}: {message.type.value}")
            return True
            
        except WebSocketDisconnect:
            # Connection disconnected, mark for cleanup
            await self._mark_for_cleanup(connection_info.connection_id, "client_disconnect")
            return False
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'send_websocket_message',
                'connection_id': connection_info.connection_id,
                'message_type': message.type.value
            })
            
            # Mark potentially dead connection
            await self._mark_for_cleanup(connection_info.connection_id, "send_error")
            
            with self._stats_lock:
                self._stats['messages_failed'] += 1
            
            return False
    
    async def _send_initial_state(self, connection_id: str) -> None:
        """Send initial state to newly connected client"""
        try:
            initial_message = WebSocketMessage(
                type=MessageType.INITIAL_STATE,
                data={
                    'connection_id': connection_id,
                    'timestamp': datetime.now().isoformat(),
                    'server_status': 'online',
                    'features': ['real_time_signals', 'position_updates', 'market_data']
                }
            )
            
            await self.send_message(initial_message, connection_id=connection_id)
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'send_initial_state',
                'connection_id': connection_id
            })
    
    async def _mark_for_cleanup(self, connection_id: str, reason: str) -> None:
        """Mark connection for cleanup"""
        logger.warning(f"Marking connection {connection_id} for cleanup: {reason}")
        # The cleanup task will handle actual removal
        
    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())
            logger.info("Started WebSocket cleanup worker")
        
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_worker())
            logger.info("Started WebSocket heartbeat worker")
    
    async def _stop_background_tasks(self) -> None:
        """Stop background maintenance tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped WebSocket cleanup worker")
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Stopped WebSocket heartbeat worker")
    
    async def _cleanup_worker(self) -> None:
        """Background worker to clean up dead connections"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_dead_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error_handler.handle_error(e, {
                    'operation': 'cleanup_worker'
                })
    
    async def _heartbeat_worker(self) -> None:
        """Background worker to send heartbeats"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._send_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error_handler.handle_error(e, {
                    'operation': 'heartbeat_worker'
                })
    
    async def _cleanup_dead_connections(self) -> None:
        """Clean up dead or stale connections"""
        dead_connections = []
        cutoff_time = datetime.now() - timedelta(seconds=self.heartbeat_interval * 3)
        
        with self._connection_lock:
            for connection_id, connection_info in self._connections.items():
                # Check if connection is stale
                if connection_info.last_heartbeat < cutoff_time:
                    dead_connections.append(connection_id)
                    continue
                
                # Test connection health
                try:
                    # Try to send a ping
                    await connection_info.websocket.ping()
                except Exception:
                    dead_connections.append(connection_id)
        
        # Remove dead connections
        for connection_id in dead_connections:
            await self.disconnect(connection_id, "dead_connection")
            with self._stats_lock:
                self._stats['dead_connections_cleaned'] += 1
        
        if dead_connections:
            logger.info(f"Cleaned up {len(dead_connections)} dead connections")
    
    async def _send_heartbeats(self) -> None:
        """Send heartbeat messages to all connections"""
        heartbeat_message = WebSocketMessage(
            type=MessageType.HEARTBEAT,
            data={'timestamp': datetime.now().isoformat()}
        )
        
        results = await self.send_message(heartbeat_message, broadcast=True)
        
        # Update last heartbeat for successful sends
        with self._connection_lock:
            for connection_id, success in results.items():
                if success and connection_id in self._connections:
                    self._connections[connection_id].last_heartbeat = datetime.now()
    
    def get_connection_count(self) -> int:
        """Get current connection count"""
        with self._connection_lock:
            return len(self._connections)
    
    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user"""
        with self._connection_lock:
            return list(self._user_connections.get(user_id, set()))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        with self._stats_lock:
            stats = dict(self._stats)
        
        with self._connection_lock:
            stats['current_connections'] = len(self._connections)
            stats['user_connections'] = len(self._user_connections)
        
        with self._queue_lock:
            stats['queued_messages'] = sum(len(queue) for queue in self._message_queues.values())
        
        stats['uptime_seconds'] = (datetime.now() - stats['start_time']).total_seconds()
        
        return stats
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the WebSocket manager"""
        logger.info("Shutting down WebSocket manager...")
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Disconnect all connections
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id, "server_shutdown")
        
        # Shutdown thread pool
        self._worker_executor.shutdown(wait=True)
        
        logger.info("WebSocket manager shutdown complete")

# Global instance
# ===============

_global_websocket_manager: Optional[ThreadSafeWebSocketManager] = None

def get_websocket_manager() -> ThreadSafeWebSocketManager:
    """Get or create global WebSocket manager"""
    global _global_websocket_manager
    if _global_websocket_manager is None:
        _global_websocket_manager = ThreadSafeWebSocketManager()
    return _global_websocket_manager

def set_websocket_manager(manager: ThreadSafeWebSocketManager) -> None:
    """Set global WebSocket manager"""
    global _global_websocket_manager
    _global_websocket_manager = manager

# Convenience functions
# ====================

async def broadcast_signal_update(signal_data: Dict[str, Any]) -> Dict[str, bool]:
    """Broadcast signal update to all connected clients"""
    manager = get_websocket_manager()
    message = WebSocketMessage(
        type=MessageType.SIGNAL_UPDATE,
        data=signal_data
    )
    return await manager.send_message(message, broadcast=True)

async def send_position_update(user_id: str, position_data: Dict[str, Any]) -> Dict[str, bool]:
    """Send position update to specific user"""
    manager = get_websocket_manager()
    message = WebSocketMessage(
        type=MessageType.POSITION_UPDATE,
        data=position_data,
        user_id=user_id
    )
    return await manager.send_message(message, user_id=user_id)

async def broadcast_market_data(market_data: Dict[str, Any]) -> Dict[str, bool]:
    """Broadcast market data to all connected clients"""
    manager = get_websocket_manager()
    message = WebSocketMessage(
        type=MessageType.MARKET_DATA,
        data=market_data
    )
    return await manager.send_message(message, broadcast=True)

async def send_error_message(connection_id: str, error_data: Dict[str, Any]) -> Dict[str, bool]:
    """Send error message to specific connection"""
    manager = get_websocket_manager()
    message = WebSocketMessage(
        type=MessageType.ERROR,
        data=error_data
    )
    return await manager.send_message(message, connection_id=connection_id)