"""
🔌 Advanced WebSocket Service
High-performance real-time communication with connection pooling and message queuing
"""

import json
import asyncio
import logging
import time
from typing import Dict, Set, Optional, Any, List, Callable
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid
from enum import Enum
import weakref

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """WebSocket message types"""
    CHAT = "chat"
    TYPING = "typing"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    SYSTEM = "system"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    BROADCAST = "broadcast"

@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime = None
    sender_id: str = None
    room_id: str = None
    message_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "sender_id": self.sender_id,
            "room_id": self.room_id,
            "message_id": self.message_id
        }

@dataclass
class ConnectionInfo:
    """WebSocket connection information"""
    connection_id: str
    websocket: WebSocket
    user_id: str = None
    room_id: str = "general"
    connected_at: datetime = None
    last_heartbeat: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.connected_at is None:
            self.connected_at = datetime.now()
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now()
        if self.metadata is None:
            self.metadata = {}

class WebSocketManager:
    """Advanced WebSocket connection manager"""
    
    def __init__(self, heartbeat_interval: int = 30, message_history_size: int = 100):
        self.heartbeat_interval = heartbeat_interval
        self.message_history_size = message_history_size
        
        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.room_connections: Dict[str, Set[str]] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Message handling
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.message_history: Dict[str, List[WebSocketMessage]] = {}
        self.pending_messages: Dict[str, List[WebSocketMessage]] = {}
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "current_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "rooms_active": 0,
            "errors": 0
        }
        
        # Background tasks
        self._heartbeat_task = None
        self._cleanup_task = None
        self._running = False
        
        logger.info(f"🔌 WebSocketManager initialized (heartbeat={heartbeat_interval}s)")
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        if self._running:
            return
        
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("🚀 WebSocket background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background maintenance tasks"""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 WebSocket background tasks stopped")
    
    async def connect(self, websocket: WebSocket, user_id: str = None, room_id: str = "general") -> str:
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        connection_info = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            room_id=room_id
        )
        
        # Store connection
        self.connections[connection_id] = connection_info
        
        # Add to room
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        self.room_connections[room_id].add(connection_id)
        
        # Add to user connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        # Update stats
        self.stats["total_connections"] += 1
        self.stats["current_connections"] = len(self.connections)
        self.stats["rooms_active"] = len(self.room_connections)
        
        # Send pending messages if any
        await self._send_pending_messages(connection_id)
        
        # Notify room about new user
        if user_id:
            await self._broadcast_to_room(room_id, WebSocketMessage(
                type=MessageType.USER_JOINED,
                data={"user_id": user_id, "room_id": room_id},
                sender_id=user_id,
                room_id=room_id
            ), exclude_connection=connection_id)
        
        logger.info(f"👋 WebSocket connected: {connection_id} (user: {user_id}, room: {room_id})")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        
        # Remove from room
        if connection_info.room_id in self.room_connections:
            self.room_connections[connection_info.room_id].discard(connection_id)
            if not self.room_connections[connection_info.room_id]:
                del self.room_connections[connection_info.room_id]
        
        # Remove from user connections
        if connection_info.user_id and connection_info.user_id in self.user_connections:
            self.user_connections[connection_info.user_id].discard(connection_id)
            if not self.user_connections[connection_info.user_id]:
                del self.user_connections[connection_info.user_id]
        
        # Notify room about user leaving
        if connection_info.user_id:
            await self._broadcast_to_room(connection_info.room_id, WebSocketMessage(
                type=MessageType.USER_LEFT,
                data={"user_id": connection_info.user_id, "room_id": connection_info.room_id},
                sender_id=connection_info.user_id,
                room_id=connection_info.room_id
            ), exclude_connection=connection_id)
        
        # Remove connection
        del self.connections[connection_id]
        
        # Update stats
        self.stats["current_connections"] = len(self.connections)
        self.stats["rooms_active"] = len(self.room_connections)
        
        logger.info(f"👋 WebSocket disconnected: {connection_id}")
    
    async def send_message(self, connection_id: str, message: WebSocketMessage) -> bool:
        """Send message to specific connection"""
        if connection_id not in self.connections:
            logger.warning(f"Connection not found: {connection_id}")
            return False
        
        connection_info = self.connections[connection_id]
        
        try:
            await connection_info.websocket.send_text(json.dumps(message.to_dict()))
            self.stats["messages_sent"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            self.stats["errors"] += 1
            # Connection might be broken, remove it
            await self.disconnect(connection_id)
            return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> int:
        """Send message to all connections of a user"""
        if user_id not in self.user_connections:
            # Store as pending message
            if user_id not in self.pending_messages:
                self.pending_messages[user_id] = []
            self.pending_messages[user_id].append(message)
            
            # Limit pending messages
            if len(self.pending_messages[user_id]) > self.message_history_size:
                self.pending_messages[user_id] = self.pending_messages[user_id][-self.message_history_size:]
            
            return 0
        
        sent_count = 0
        connection_ids = list(self.user_connections[user_id])
        
        for connection_id in connection_ids:
            if await self.send_message(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_room(self, room_id: str, message: WebSocketMessage, exclude_user: str = None) -> int:
        """Broadcast message to all connections in a room"""
        return await self._broadcast_to_room(room_id, message, exclude_user=exclude_user)
    
    async def _broadcast_to_room(self, room_id: str, message: WebSocketMessage, 
                                exclude_connection: str = None, exclude_user: str = None) -> int:
        """Internal broadcast method"""
        if room_id not in self.room_connections:
            return 0
        
        # Store message in room history
        if room_id not in self.message_history:
            self.message_history[room_id] = []
        
        self.message_history[room_id].append(message)
        
        # Limit history size
        if len(self.message_history[room_id]) > self.message_history_size:
            self.message_history[room_id] = self.message_history[room_id][-self.message_history_size:]
        
        sent_count = 0
        connection_ids = list(self.room_connections[room_id])
        
        for connection_id in connection_ids:
            if connection_id == exclude_connection:
                continue
            
            connection_info = self.connections.get(connection_id)
            if connection_info and exclude_user and connection_info.user_id == exclude_user:
                continue
            
            if await self.send_message(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_all(self, message: WebSocketMessage) -> int:
        """Broadcast message to all connected clients"""
        sent_count = 0
        connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            if await self.send_message(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def handle_message(self, connection_id: str, raw_message: str):
        """Handle incoming WebSocket message"""
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        self.stats["messages_received"] += 1
        
        try:
            # Parse message
            message_data = json.loads(raw_message)
            message_type = MessageType(message_data.get("type", "chat"))
            
            message = WebSocketMessage(
                type=message_type,
                data=message_data.get("data", {}),
                sender_id=connection_info.user_id,
                room_id=connection_info.room_id
            )
            
            # Update heartbeat
            connection_info.last_heartbeat = datetime.now()
            
            # Handle specific message types
            if message_type == MessageType.HEARTBEAT:
                await self.send_message(connection_id, WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    data={"status": "alive", "server_time": datetime.now().isoformat()}
                ))
                return
            
            # Call registered handlers
            if message_type in self.message_handlers:
                for handler in self.message_handlers[message_type]:
                    try:
                        await handler(connection_id, message)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")
            
            # Default: broadcast to room
            if message_type == MessageType.CHAT:
                await self._broadcast_to_room(
                    connection_info.room_id, 
                    message, 
                    exclude_connection=connection_id
                )
            
        except json.JSONDecodeError:
            await self.send_message(connection_id, WebSocketMessage(
                type=MessageType.ERROR,
                data={"error": "Invalid JSON format"}
            ))
        except ValueError as e:
            await self.send_message(connection_id, WebSocketMessage(
                type=MessageType.ERROR,
                data={"error": f"Invalid message type: {e}"}
            ))
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            self.stats["errors"] += 1
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register handler for specific message type"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        logger.info(f"📝 Registered handler for {message_type.value}")
    
    async def _send_pending_messages(self, connection_id: str):
        """Send pending messages to newly connected user"""
        connection_info = self.connections.get(connection_id)
        if not connection_info or not connection_info.user_id:
            return
        
        user_id = connection_info.user_id
        if user_id in self.pending_messages:
            for message in self.pending_messages[user_id]:
                await self.send_message(connection_id, message)
            
            # Clear pending messages
            del self.pending_messages[user_id]
            logger.info(f"📨 Sent {len(self.pending_messages[user_id])} pending messages to {user_id}")
    
    async def _heartbeat_loop(self):
        """Background heartbeat checking"""
        while self._running:
            try:
                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(seconds=self.heartbeat_interval * 2)
                
                # Check for timed out connections
                timed_out_connections = []
                for connection_id, connection_info in self.connections.items():
                    if connection_info.last_heartbeat < timeout_threshold:
                        timed_out_connections.append(connection_id)
                
                # Disconnect timed out connections
                for connection_id in timed_out_connections:
                    logger.warning(f"Connection timeout: {connection_id}")
                    await self.disconnect(connection_id)
                
                # Send heartbeat to active connections
                for connection_id in list(self.connections.keys()):
                    await self.send_message(connection_id, WebSocketMessage(
                        type=MessageType.HEARTBEAT,
                        data={"server_time": current_time.isoformat()}
                    ))
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _cleanup_loop(self):
        """Background cleanup of old data"""
        while self._running:
            try:
                current_time = datetime.now()
                cleanup_threshold = current_time - timedelta(hours=24)
                
                # Clean old message history
                for room_id, messages in self.message_history.items():
                    self.message_history[room_id] = [
                        msg for msg in messages 
                        if msg.timestamp > cleanup_threshold
                    ]
                
                # Clean old pending messages
                for user_id, messages in list(self.pending_messages.items()):
                    self.pending_messages[user_id] = [
                        msg for msg in messages 
                        if msg.timestamp > cleanup_threshold
                    ]
                    
                    # Remove empty pending message lists
                    if not self.pending_messages[user_id]:
                        del self.pending_messages[user_id]
                
                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """Get information about a room"""
        if room_id not in self.room_connections:
            return {"room_id": room_id, "connection_count": 0, "users": []}
        
        connection_ids = self.room_connections[room_id]
        users = []
        
        for connection_id in connection_ids:
            connection_info = self.connections.get(connection_id)
            if connection_info and connection_info.user_id:
                users.append({
                    "user_id": connection_info.user_id,
                    "connected_at": connection_info.connected_at.isoformat(),
                    "last_heartbeat": connection_info.last_heartbeat.isoformat()
                })
        
        return {
            "room_id": room_id,
            "connection_count": len(connection_ids),
            "user_count": len(set(u["user_id"] for u in users)),
            "users": users
        }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            **self.stats,
            "rooms": {
                room_id: {
                    "connections": len(connections),
                    "users": len(set(
                        self.connections[conn_id].user_id 
                        for conn_id in connections 
                        if conn_id in self.connections and self.connections[conn_id].user_id
                    ))
                }
                for room_id, connections in self.room_connections.items()
            },
            "pending_messages": {
                user_id: len(messages)
                for user_id, messages in self.pending_messages.items()
            }
        }
    
    def get_message_history(self, room_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get message history for a room"""
        if room_id not in self.message_history:
            return []
        
        messages = self.message_history[room_id]
        if limit:
            messages = messages[-limit:]
        
        return [msg.to_dict() for msg in messages]

# Global WebSocket manager instance
websocket_manager = None

def init_websocket_manager(heartbeat_interval: int = 30, message_history_size: int = 100):
    """Initialize global WebSocket manager"""
    global websocket_manager
    websocket_manager = WebSocketManager(heartbeat_interval, message_history_size)
    return websocket_manager

def get_websocket_manager() -> WebSocketManager:
    """Get global WebSocket manager instance"""
    global websocket_manager
    if websocket_manager is None:
        websocket_manager = WebSocketManager()
    return websocket_manager
