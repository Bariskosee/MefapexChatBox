"""
🔌 Enhanced Async WebSocket Manager with Memory Leak Prevention
Proper connection lifecycle management and resource cleanup
"""

import asyncio
import json
import logging
import time
import weakref
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
import uuid

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """WebSocket connection information"""
    websocket: WebSocket
    user_id: str
    username: str
    connected_at: datetime
    last_activity: datetime
    message_count: int = 0
    is_active: bool = True

@dataclass
class WebSocketStats:
    """WebSocket performance statistics"""
    total_connections: int = 0
    active_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    connection_errors: int = 0
    cleanup_operations: int = 0
    memory_cleanups: int = 0

class AsyncWebSocketManager:
    """
    🔌 High-performance WebSocket manager with memory leak prevention
    - Proper connection lifecycle management
    - Automatic stale connection cleanup
    - Memory-efficient connection tracking
    - Heartbeat mechanism for connection health
    """
    
    def __init__(self, cleanup_interval: int = 300, heartbeat_interval: int = 30):
        # Use WeakSet for automatic garbage collection of dead connections
        self._connections: Dict[str, ConnectionInfo] = {}
        self._user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        
        # Connection management
        self._connection_lock = asyncio.Lock()
        self._stats = WebSocketStats()
        
        # Cleanup configuration
        self.cleanup_interval = cleanup_interval  # 5 minutes
        self.heartbeat_interval = heartbeat_interval  # 30 seconds
        self.max_idle_time = timedelta(minutes=15)  # Max idle before cleanup
        self.max_connections_per_user = 5  # Prevent connection spam
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"🔌 AsyncWebSocketManager initialized with {cleanup_interval}s cleanup interval")
    
    async def start_background_tasks(self):
        """Start background cleanup and heartbeat tasks"""
        if self._running:
            return
            
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info("🔄 WebSocket background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        self._running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 WebSocket background tasks stopped")
    
    async def connect(self, websocket: WebSocket, user_id: str, username: str) -> str:
        """
        🔗 Connect a new WebSocket with proper lifecycle management
        """
        try:
            await websocket.accept()
            
            async with self._connection_lock:
                # Generate unique connection ID
                connection_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
                
                # Check connection limits per user
                user_connections = self._user_connections.get(user_id, set())
                if len(user_connections) >= self.max_connections_per_user:
                    # Remove oldest connection for this user
                    oldest_conn_id = min(
                        user_connections,
                        key=lambda cid: self._connections[cid].connected_at
                    )
                    await self._force_disconnect(oldest_conn_id, "Connection limit exceeded")
                
                # Create connection info
                connection_info = ConnectionInfo(
                    websocket=websocket,
                    user_id=user_id,
                    username=username,
                    connected_at=datetime.utcnow(),
                    last_activity=datetime.utcnow()
                )
                
                # Store connection
                self._connections[connection_id] = connection_info
                
                # Update user connections mapping
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = set()
                self._user_connections[user_id].add(connection_id)
                
                # Update stats
                self._stats.total_connections += 1
                self._stats.active_connections += 1
                
                logger.info(f"🔗 WebSocket connected: {username} ({connection_id})")
                
                # Send welcome message
                await self.send_personal_message({
                    'type': 'connection_established',
                    'connection_id': connection_id,
                    'message': f'Connected as {username}',
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)
                
                # Start background tasks if not running
                if not self._running:
                    await self.start_background_tasks()
                
                return connection_id
                
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            self._stats.connection_errors += 1
            raise
    
    async def disconnect(self, websocket: WebSocket, reason: str = "Normal disconnect"):
        """
        🔌 Properly disconnect a WebSocket connection
        """
        try:
            async with self._connection_lock:
                # Find connection by websocket
                connection_id = None
                for cid, conn_info in self._connections.items():
                    if conn_info.websocket == websocket:
                        connection_id = cid
                        break
                
                if connection_id:
                    await self._remove_connection(connection_id, reason)
                else:
                    logger.warning("⚠️ Attempted to disconnect unknown WebSocket")
                    
        except Exception as e:
            logger.error(f"❌ WebSocket disconnect error: {e}")
    
    async def _remove_connection(self, connection_id: str, reason: str = "Cleanup"):
        """
        🗑️ Remove connection and cleanup resources
        """
        try:
            if connection_id not in self._connections:
                return
            
            connection_info = self._connections[connection_id]
            user_id = connection_info.user_id
            
            # Mark as inactive
            connection_info.is_active = False
            
            # Try to close websocket gracefully
            try:
                if connection_info.websocket.client_state.name == "CONNECTED":
                    await connection_info.websocket.close(code=1000, reason=reason)
            except Exception as e:
                logger.debug(f"⚠️ WebSocket close error: {e}")
            
            # Remove from connections
            del self._connections[connection_id]
            
            # Update user connections mapping
            if user_id in self._user_connections:
                self._user_connections[user_id].discard(connection_id)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]
            
            # Update stats
            self._stats.active_connections = max(0, self._stats.active_connections - 1)
            
            logger.info(f"🗑️ Connection removed: {connection_info.username} ({connection_id}) - {reason}")
            
        except Exception as e:
            logger.error(f"❌ Connection removal error: {e}")
    
    async def _force_disconnect(self, connection_id: str, reason: str):
        """Force disconnect a specific connection"""
        await self._remove_connection(connection_id, reason)
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        📤 Send message to specific WebSocket connection
        """
        try:
            message_json = json.dumps(message)
            await websocket.send_text(message_json)
            
            # Update activity timestamp
            async with self._connection_lock:
                for conn_info in self._connections.values():
                    if conn_info.websocket == websocket:
                        conn_info.last_activity = datetime.utcnow()
                        conn_info.message_count += 1
                        break
            
            self._stats.messages_sent += 1
            
        except WebSocketDisconnect:
            logger.info(f"🔌 WebSocket disconnected during message send")
            await self.disconnect(websocket, "Disconnected during send")
        except Exception as e:
            logger.error(f"❌ Failed to send personal message: {e}")
            await self.disconnect(websocket, f"Send error: {str(e)}")
    
    async def send_user_message(self, message: Dict[str, Any], user_id: str):
        """
        📢 Send message to all connections of a specific user
        """
        try:
            async with self._connection_lock:
                user_connections = self._user_connections.get(user_id, set()).copy()
            
            if not user_connections:
                logger.debug(f"No active connections for user {user_id}")
                return
            
            # Send to all user connections
            send_tasks = []
            for connection_id in user_connections:
                if connection_id in self._connections:
                    conn_info = self._connections[connection_id]
                    if conn_info.is_active:
                        task = self.send_personal_message(message, conn_info.websocket)
                        send_tasks.append(task)
            
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"❌ Failed to send user message: {e}")
    
    async def broadcast_message(self, message: Dict[str, Any], exclude_user: Optional[str] = None):
        """
        📡 Broadcast message to all active connections
        """
        try:
            async with self._connection_lock:
                connections_to_send = []
                for conn_info in self._connections.values():
                    if (conn_info.is_active and 
                        (exclude_user is None or conn_info.user_id != exclude_user)):
                        connections_to_send.append(conn_info.websocket)
            
            if not connections_to_send:
                return
            
            # Send to all connections
            send_tasks = [
                self.send_personal_message(message, websocket)
                for websocket in connections_to_send
            ]
            
            await asyncio.gather(*send_tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Failed to broadcast message: {e}")
    
    async def _cleanup_loop(self):
        """
        🧹 Background cleanup loop for stale connections
        """
        logger.info("🧹 WebSocket cleanup loop started")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_stale_connections()
                
            except asyncio.CancelledError:
                logger.info("🛑 Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Cleanup loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _cleanup_stale_connections(self):
        """
        🧹 Clean up stale and inactive connections
        """
        try:
            current_time = datetime.utcnow()
            stale_connections = []
            
            async with self._connection_lock:
                for connection_id, conn_info in self._connections.items():
                    # Check if connection is stale
                    idle_time = current_time - conn_info.last_activity
                    
                    if (idle_time > self.max_idle_time or 
                        not conn_info.is_active or
                        conn_info.websocket.client_state.name != "CONNECTED"):
                        stale_connections.append(connection_id)
            
            # Remove stale connections
            for connection_id in stale_connections:
                await self._remove_connection(connection_id, "Stale connection cleanup")
            
            if stale_connections:
                self._stats.cleanup_operations += 1
                self._stats.memory_cleanups += len(stale_connections)
                logger.info(f"🧹 Cleaned up {len(stale_connections)} stale connections")
                
        except Exception as e:
            logger.error(f"❌ Stale connection cleanup error: {e}")
    
    async def _heartbeat_loop(self):
        """
        💓 Background heartbeat loop to check connection health
        """
        logger.info("💓 WebSocket heartbeat loop started")
        
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._send_heartbeat()
                
            except asyncio.CancelledError:
                logger.info("🛑 Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Heartbeat loop error: {e}")
                await asyncio.sleep(5)
    
    async def _send_heartbeat(self):
        """
        💓 Send heartbeat to all active connections
        """
        try:
            heartbeat_message = {
                'type': 'heartbeat',
                'timestamp': datetime.utcnow().isoformat(),
                'server_time': time.time()
            }
            
            async with self._connection_lock:
                active_connections = [
                    conn_info.websocket 
                    for conn_info in self._connections.values() 
                    if conn_info.is_active
                ]
            
            if active_connections:
                # Send heartbeat to all connections
                heartbeat_tasks = [
                    self.send_personal_message(heartbeat_message, websocket)
                    for websocket in active_connections
                ]
                
                results = await asyncio.gather(*heartbeat_tasks, return_exceptions=True)
                
                # Count failures
                failures = sum(1 for result in results if isinstance(result, Exception))
                if failures > 0:
                    logger.debug(f"💓 Heartbeat: {failures} failures out of {len(active_connections)} connections")
                    
        except Exception as e:
            logger.error(f"❌ Heartbeat error: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        📊 Get WebSocket connection statistics
        """
        return {
            "total_connections": self._stats.total_connections,
            "active_connections": self._stats.active_connections,
            "messages_sent": self._stats.messages_sent,
            "messages_received": self._stats.messages_received,
            "connection_errors": self._stats.connection_errors,
            "cleanup_operations": self._stats.cleanup_operations,
            "memory_cleanups": self._stats.memory_cleanups,
            "unique_users": len(self._user_connections),
            "connections_per_user": {
                user_id: len(connections) 
                for user_id, connections in self._user_connections.items()
            } if len(self._user_connections) <= 10 else {"note": "Too many users to display"},
            "background_tasks_running": self._running
        }
    
    async def get_connection_details(self) -> List[Dict[str, Any]]:
        """
        📋 Get detailed connection information
        """
        async with self._connection_lock:
            details = []
            for connection_id, conn_info in self._connections.items():
                details.append({
                    "connection_id": connection_id,
                    "user_id": conn_info.user_id,
                    "username": conn_info.username,
                    "connected_at": conn_info.connected_at.isoformat(),
                    "last_activity": conn_info.last_activity.isoformat(),
                    "message_count": conn_info.message_count,
                    "is_active": conn_info.is_active,
                    "idle_time_seconds": (datetime.utcnow() - conn_info.last_activity).total_seconds()
                })
        
        return details
    
    async def force_cleanup_user(self, user_id: str, reason: str = "Admin cleanup"):
        """
        🧹 Force cleanup all connections for a specific user
        """
        async with self._connection_lock:
            user_connections = self._user_connections.get(user_id, set()).copy()
        
        for connection_id in user_connections:
            await self._remove_connection(connection_id, reason)
        
        logger.info(f"🧹 Force cleaned up {len(user_connections)} connections for user {user_id}")
    
    async def shutdown(self):
        """
        🔐 Shutdown WebSocket manager and cleanup all resources
        """
        logger.info("🔐 Shutting down AsyncWebSocketManager...")
        
        # Stop background tasks
        await self.stop_background_tasks()
        
        # Close all connections
        async with self._connection_lock:
            connection_ids = list(self._connections.keys())
        
        for connection_id in connection_ids:
            await self._remove_connection(connection_id, "Server shutdown")
        
        # Clear all data structures
        self._connections.clear()
        self._user_connections.clear()
        
        logger.info("✅ AsyncWebSocketManager shutdown complete")

# Global instance
async_websocket_manager = AsyncWebSocketManager()

# Compatibility functions for existing code
async def connect_websocket(websocket: WebSocket, user_id: str, username: str) -> str:
    """Connect WebSocket using async manager"""
    return await async_websocket_manager.connect(websocket, user_id, username)

async def disconnect_websocket(websocket: WebSocket, reason: str = "Normal disconnect"):
    """Disconnect WebSocket using async manager"""
    await async_websocket_manager.disconnect(websocket, reason)

async def send_websocket_message(message: Dict[str, Any], websocket: WebSocket):
    """Send message via WebSocket using async manager"""
    await async_websocket_manager.send_personal_message(message, websocket)
