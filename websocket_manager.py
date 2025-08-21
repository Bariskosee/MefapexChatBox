"""
WebSocket manager for real-time communication in MEFAPEX AI Assistant
Replaces HTTP polling with efficient WebSocket connections
Now supports distributed deployment with Redis pub/sub for horizontal scaling
"""
import asyncio
import json
import logging
import os
import uuid
from typing import Dict, Set, Optional, Any
from datetime import datetime
import weakref

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from core.distributed_websocket_manager import create_distributed_websocket_manager

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections for real-time chat communication
    Features:
    - User-based connection tracking
    - Broadcast capabilities
    - Connection state management
    - Automatic cleanup of disconnected clients
    """
    
    def __init__(self):
        # Active connections per user
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = weakref.WeakKeyDictionary()
        
        # Global stats
        self.stats = {
            'total_connections': 0,
            'active_users': 0,
            'messages_sent': 0,
            'connections_opened': 0,
            'connections_closed': 0
        }
        
        logger.info("🔌 WebSocket ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, user_id: str, username: str):
        """
        Accept new WebSocket connection and register user
        """
        await websocket.accept()
        
        # Initialize user connections set if needed
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        # Add connection to user's set
        self.active_connections[user_id].add(websocket)
        
        # Store connection metadata
        self.connection_info[websocket] = {
            'user_id': user_id,
            'username': username,
            'connected_at': datetime.utcnow(),
            'session_id': str(uuid.uuid4()),
            'last_activity': datetime.utcnow()
        }
        
        # Update stats
        self.stats['total_connections'] += 1
        self.stats['connections_opened'] += 1
        self.stats['active_users'] = len(self.active_connections)
        
        logger.info(f"✅ User {username} ({user_id}) connected via WebSocket")
        
        # Send welcome message
        await self.send_personal_message({
            'type': 'connection_established',
            'message': 'WebSocket connection established',
            'session_id': self.connection_info[websocket]['session_id'],
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection and cleanup
        """
        try:
            # Get connection info before cleanup
            conn_info = self.connection_info.get(websocket)
            if conn_info:
                user_id = conn_info['user_id']
                username = conn_info['username']
                
                # Remove from active connections
                if user_id in self.active_connections:
                    self.active_connections[user_id].discard(websocket)
                    
                    # Remove user entry if no more connections
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]
                
                # Update stats
                self.stats['total_connections'] -= 1
                self.stats['connections_closed'] += 1
                self.stats['active_users'] = len(self.active_connections)
                
                logger.info(f"❌ User {username} ({user_id}) disconnected from WebSocket")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific WebSocket connection
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message))
                self.stats['messages_sent'] += 1
                
                # Update last activity
                if websocket in self.connection_info:
                    self.connection_info[websocket]['last_activity'] = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Connection likely closed, will be cleaned up by disconnect handler
    
    async def send_to_user(self, user_id: str, message: dict):
        """
        Send message to all connections of a specific user
        """
        if user_id in self.active_connections:
            disconnected_connections = []
            
            for websocket in self.active_connections[user_id].copy():
                try:
                    await self.send_personal_message(message, websocket)
                except:
                    disconnected_connections.append(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected_connections:
                self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """
        Broadcast message to all connected users
        """
        disconnected_connections = []
        
        for user_connections in self.active_connections.values():
            for websocket in user_connections.copy():
                try:
                    await self.send_personal_message(message, websocket)
                except:
                    disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            self.disconnect(websocket)
    
    def get_user_connections(self, user_id: str) -> Set[WebSocket]:
        """
        Get all active connections for a user
        """
        return self.active_connections.get(user_id, set())
    
    def is_user_online(self, user_id: str) -> bool:
        """
        Check if user has any active connections
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_online_users(self) -> list:
        """
        Get list of all online user IDs
        """
        return list(self.active_connections.keys())
    
    def get_connection_stats(self) -> dict:
        """
        Get connection statistics
        """
        active_connections_detail = {}
        for user_id, connections in self.active_connections.items():
            active_connections_detail[user_id] = {
                'connection_count': len(connections),
                'connections': [
                    {
                        'session_id': self.connection_info.get(ws, {}).get('session_id', 'unknown'),
                        'connected_at': self.connection_info.get(ws, {}).get('connected_at', 'unknown'),
                        'last_activity': self.connection_info.get(ws, {}).get('last_activity', 'unknown')
                    }
                    for ws in connections
                ]
            }
        
        return {
            **self.stats,
            'active_connections_detail': active_connections_detail
        }
    
    async def ping_all_connections(self):
        """
        Send ping to all connections to check status
        """
        ping_message = {
            'type': 'ping',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_all(ping_message)
        logger.debug("📡 Ping sent to all connections")

# Initialize the appropriate connection manager based on configuration
def _get_connection_manager():
    """Get connection manager instance based on configuration"""
    try:
        from config import config
        
        # Check if Redis is configured for distributed mode
        redis_url = getattr(config, 'REDIS_URL', None)
        distributed_enabled = getattr(config, 'DISTRIBUTED_WEBSOCKET_ENABLED', True)
        
        if distributed_enabled and redis_url and redis_url != "redis://localhost:6379/0":
            # Use distributed manager with Redis
            worker_id = getattr(config, 'WORKER_ID', None) or getattr(config, 'NODE_ID', None)
            return create_distributed_websocket_manager(redis_url=redis_url, worker_id=worker_id)
        else:
            # Fallback to legacy in-memory manager for development
            logger.info("Using legacy in-memory WebSocket manager (development mode)")
            return ConnectionManager()
            
    except ImportError:
        # Fallback if config is not available
        logger.warning("Config not available, using legacy WebSocket manager")
        return ConnectionManager()
    except Exception as e:
        logger.error(f"Error initializing WebSocket manager: {e}, falling back to legacy")
        return ConnectionManager()

# Global connection manager instance - will be distributed if Redis is configured
websocket_manager = _get_connection_manager()

class WebSocketMessageHandler:
    """
    Handle different types of WebSocket messages
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def handle_message(self, websocket: WebSocket, message_data: dict):
        """
        Route message to appropriate handler based on message type
        """
        message_type = message_data.get('type', 'unknown')
        
        handlers = {
            'chat_message': self.handle_chat_message,
            'typing_start': self.handle_typing_start,
            'typing_stop': self.handle_typing_stop,
            'ping': self.handle_ping,
            'get_history': self.handle_get_history,
            'clear_history': self.handle_clear_history
        }
        
        handler = handlers.get(message_type, self.handle_unknown_message)
        await handler(websocket, message_data)
    
    async def handle_chat_message(self, websocket: WebSocket, message_data: dict):
        """
        Handle chat message from client
        This will be implemented in the main FastAPI app
        """
        # This is a placeholder - actual implementation will be in main.py
        # where we have access to the AI models and database
        pass
    
    async def handle_typing_start(self, websocket: WebSocket, message_data: dict):
        """
        Handle typing indicator start
        """
        conn_info = self.connection_manager.connection_info.get(websocket)
        if conn_info:
            # Could broadcast typing status to other users in future
            await self.connection_manager.send_personal_message({
                'type': 'typing_acknowledged',
                'status': 'started'
            }, websocket)
    
    async def handle_typing_stop(self, websocket: WebSocket, message_data: dict):
        """
        Handle typing indicator stop
        """
        conn_info = self.connection_manager.connection_info.get(websocket)
        if conn_info:
            await self.connection_manager.send_personal_message({
                'type': 'typing_acknowledged',
                'status': 'stopped'
            }, websocket)
    
    async def handle_ping(self, websocket: WebSocket, message_data: dict):
        """
        Handle ping message
        """
        await self.connection_manager.send_personal_message({
            'type': 'pong',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)
    
    async def handle_get_history(self, websocket: WebSocket, message_data: dict):
        """
        Handle request for chat history
        """
        try:
            from database.manager import db_manager
            
            # Get user info from websocket connection
            user_info = getattr(websocket, 'user_info', None)
            if not user_info:
                await self.connection_manager.send_personal_message({
                    'type': 'error',
                    'message': 'User not authenticated',
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)
                return
            
            user_id = user_info.get('user_id')
            limit = message_data.get('limit', 20)
            
            # Get chat history from PostgreSQL
            history = db_manager.get_chat_history(user_id, limit)
            
            await self.connection_manager.send_personal_message({
                'type': 'history',
                'data': {
                    'messages': history,
                    'count': len(history)
                },
                'timestamp': datetime.utcnow().isoformat()
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'message': 'Failed to retrieve chat history',
                'timestamp': datetime.utcnow().isoformat()
            }, websocket)
    
    async def handle_clear_history(self, websocket: WebSocket, message_data: dict):
        """
        Handle request to clear chat history
        """
        try:
            from database.manager import db_manager
            
            # Get user info from websocket connection
            user_info = getattr(websocket, 'user_info', None)
            if not user_info:
                await self.connection_manager.send_personal_message({
                    'type': 'error',
                    'message': 'User not authenticated',
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)
                return
            
            user_id = user_info.get('user_id')
            
            # Clear chat history from PostgreSQL
            success = db_manager.clear_chat_history(user_id)
            
            if success:
                await self.connection_manager.send_personal_message({
                    'type': 'history_cleared',
                    'message': 'Chat history cleared successfully',
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)
            else:
                await self.connection_manager.send_personal_message({
                    'type': 'error',
                    'message': 'Failed to clear chat history',
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)
                
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'message': 'Failed to clear chat history',
                'timestamp': datetime.utcnow().isoformat()
            }, websocket)
    
    async def handle_unknown_message(self, websocket: WebSocket, message_data: dict):
        """
        Handle unknown message types
        """
        await self.connection_manager.send_personal_message({
            'type': 'error',
            'message': f"Unknown message type: {message_data.get('type', 'undefined')}",
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

# Global message handler
message_handler = WebSocketMessageHandler(websocket_manager)
