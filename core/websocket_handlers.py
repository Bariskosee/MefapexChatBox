"""
🔌 WebSocket Handlers
====================
WebSocket connection management and message handling
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.websockets import WebSocketState

from auth_service import get_auth_service
from database_manager import db_manager
from model_manager import model_manager
from content_manager import ContentManager
from memory_monitor import MemoryMonitor
from core.configuration import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Initialize components
try:
    content_manager = ContentManager()
except ImportError:
    content_manager = None
    logger.warning("ContentManager not available")

try:
    memory_monitor = MemoryMonitor()
except ImportError:
    memory_monitor = None
    logger.warning("MemoryMonitor not available")

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        self.connection_metadata: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None) -> bool:
        """Accept and register a WebSocket connection"""
        try:
            await websocket.accept()
            
            async with self._lock:
                self.active_connections[connection_id] = websocket
                
                if user_id:
                    # If user already has a connection, disconnect the old one
                    if user_id in self.user_connections:
                        old_connection_id = self.user_connections[user_id]
                        await self._disconnect_internal(old_connection_id, notify=True)
                    
                    self.user_connections[user_id] = connection_id
                
                self.connection_metadata[connection_id] = {
                    "user_id": user_id,
                    "connected_at": datetime.now(),
                    "message_count": 0
                }
            
            logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
            
            # Send welcome message
            await self.send_message(connection_id, {
                "type": "connection_status",
                "status": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self, connection_id: str, notify: bool = False):
        """Disconnect a WebSocket connection"""
        async with self._lock:
            await self._disconnect_internal(connection_id, notify)
    
    async def _disconnect_internal(self, connection_id: str, notify: bool = False):
        """Internal disconnect logic (called with lock held)"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            
            # Send disconnect notification if requested and connection is open
            if notify and websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json({
                        "type": "connection_status",
                        "status": "disconnected",
                        "reason": "new_connection"
                    })
                except:
                    pass  # Connection might already be closed
            
            # Close the connection
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close()
            except:
                pass  # Connection might already be closed
            
            # Remove from tracking
            del self.active_connections[connection_id]
            
            # Remove user mapping
            metadata = self.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")
            if user_id and user_id in self.user_connections:
                if self.user_connections[user_id] == connection_id:
                    del self.user_connections[user_id]
            
            # Remove metadata
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id} (user: {user_id})")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific connection"""
        if connection_id not in self.active_connections:
            return False
        
        websocket = self.active_connections[connection_id]
        
        if websocket.client_state != WebSocketState.CONNECTED:
            await self.disconnect(connection_id)
            return False
        
        try:
            await websocket.send_json(message)
            
            # Update message count
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["message_count"] += 1
            
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific user"""
        if user_id not in self.user_connections:
            return False
        
        connection_id = self.user_connections[user_id]
        return await self.send_message(connection_id, message)
    
    async def broadcast(self, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            if exclude_connection and connection_id == exclude_connection:
                continue
            
            success = await self.send_message(connection_id, message)
            if not success:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about active connections"""
        return {
            "total_connections": len(self.active_connections),
            "authenticated_users": len(self.user_connections),
            "connections": [
                {
                    "connection_id": conn_id,
                    "user_id": metadata.get("user_id"),
                    "connected_at": metadata.get("connected_at").isoformat() if metadata.get("connected_at") else None,
                    "message_count": metadata.get("message_count", 0)
                }
                for conn_id, metadata in self.connection_metadata.items()
            ]
        }

# Global connection manager instance
manager = ConnectionManager()

class WebSocketHandlers:
    """
    WebSocket endpoint handlers
    """
    
    @staticmethod
    async def websocket_endpoint(websocket: WebSocket, connection_id: str):
        """Main WebSocket endpoint"""
        user_id = None
        
        try:
            # Connect to WebSocket
            await manager.connect(websocket, connection_id)
            
            while True:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                await WebSocketHandlers._handle_message(connection_id, message_data, websocket)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally: {connection_id}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {connection_id}: {e}")
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            await manager.disconnect(connection_id)
    
    @staticmethod
    async def websocket_chat(websocket: WebSocket):
        """Chat-specific WebSocket endpoint"""
        connection_id = f"chat_{datetime.now().timestamp()}"
        
        try:
            await manager.connect(websocket, connection_id)
            
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle chat-specific messages
                await WebSocketHandlers._handle_chat_message(connection_id, message_data, websocket)
                
        except WebSocketDisconnect:
            logger.info(f"Chat WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"Chat WebSocket error: {e}")
        finally:
            await manager.disconnect(connection_id)
    
    @staticmethod
    async def websocket_admin(websocket: WebSocket):
        """Admin-specific WebSocket endpoint"""
        connection_id = f"admin_{datetime.now().timestamp()}"
        
        try:
            await manager.connect(websocket, connection_id)
            
            # Send admin connection info
            await manager.send_message(connection_id, {
                "type": "admin_connected",
                "connection_info": manager.get_connection_info()
            })
            
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle admin-specific messages
                await WebSocketHandlers._handle_admin_message(connection_id, message_data)
                
        except WebSocketDisconnect:
            logger.info(f"Admin WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"Admin WebSocket error: {e}")
        finally:
            await manager.disconnect(connection_id)
    
    @staticmethod
    async def _handle_message(connection_id: str, message_data: Dict, websocket: WebSocket):
        """Handle general WebSocket messages"""
        message_type = message_data.get("type", "unknown")
        
        try:
            if message_type == "auth":
                await WebSocketHandlers._handle_auth(connection_id, message_data)
            elif message_type == "chat":
                await WebSocketHandlers._handle_chat(connection_id, message_data)
            elif message_type == "ping":
                await manager.send_message(connection_id, {"type": "pong", "timestamp": datetime.now().isoformat()})
            elif message_type == "get_history":
                await WebSocketHandlers._handle_get_history(connection_id, message_data)
            elif message_type == "system_info":
                await WebSocketHandlers._handle_system_info(connection_id)
            else:
                await manager.send_message(connection_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "Message processing failed"
            })
    
    @staticmethod
    async def _handle_auth(connection_id: str, message_data: Dict):
        """Handle authentication"""
        try:
            token = message_data.get("token")
            if not token:
                await manager.send_message(connection_id, {
                    "type": "auth_error",
                    "message": "Token required"
                })
                return
            
            # Verify token
            auth_service = get_auth_service()
            if not auth_service:
                await manager.send_message(connection_id, {
                    "type": "auth_error",
                    "message": "Authentication service not available"
                })
                return
            
            payload = auth_service.verify_access_token(token)
            if payload:
                user_id = payload.get("sub")
                
                # Update connection with user ID
                if connection_id in manager.connection_metadata:
                    manager.connection_metadata[connection_id]["user_id"] = user_id
                    manager.user_connections[user_id] = connection_id
                
                await manager.send_message(connection_id, {
                    "type": "auth_success",
                    "user_id": user_id,
                    "message": "Authentication successful"
                })
            else:
                await manager.send_message(connection_id, {
                    "type": "auth_error",
                    "message": "Invalid token"
                })
                
        except Exception as e:
            logger.error(f"Auth error: {e}")
            await manager.send_message(connection_id, {
                "type": "auth_error",
                "message": "Authentication failed"
            })
    
    @staticmethod
    async def _handle_chat(connection_id: str, message_data: Dict):
        """Handle chat messages"""
        try:
            message = message_data.get("message", "").strip()
            if not message:
                await manager.send_message(connection_id, {
                    "type": "error",
                    "message": "Message cannot be empty"
                })
                return
            
            # Get user ID if authenticated
            metadata = manager.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id", "anonymous")
            
            # Process message
            response = await WebSocketHandlers._process_chat_message(message, user_id)
            
            # Send response
            await manager.send_message(connection_id, {
                "type": "chat_response",
                "message": response,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            })
            
            # Save to database if user is authenticated
            if user_id != "anonymous" and hasattr(db_manager, 'add_message'):
                try:
                    session_id = db_manager.get_or_create_session(user_id)
                    db_manager.add_message(
                        session_id=session_id,
                        user_id=user_id,
                        user_message=message,
                        bot_response=response,
                        source="websocket"
                    )
                except Exception as e:
                    logger.error(f"Database save error: {e}")
            
        except Exception as e:
            logger.error(f"Chat handling error: {e}")
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "Chat processing failed"
            })
    
    @staticmethod
    async def _handle_chat_message(connection_id: str, message_data: Dict, websocket: WebSocket):
        """Handle chat-specific WebSocket messages"""
        await WebSocketHandlers._handle_chat(connection_id, message_data)
    
    @staticmethod
    async def _handle_admin_message(connection_id: str, message_data: Dict):
        """Handle admin-specific messages"""
        try:
            command = message_data.get("command")
            
            if command == "get_connections":
                await manager.send_message(connection_id, {
                    "type": "connection_info",
                    "data": manager.get_connection_info()
                })
            elif command == "get_system_status":
                await WebSocketHandlers._handle_system_info(connection_id)
            elif command == "broadcast":
                broadcast_message = message_data.get("message", {})
                await manager.broadcast(broadcast_message, exclude_connection=connection_id)
                await manager.send_message(connection_id, {
                    "type": "broadcast_sent",
                    "message": "Message broadcasted to all connections"
                })
            else:
                await manager.send_message(connection_id, {
                    "type": "error",
                    "message": f"Unknown admin command: {command}"
                })
                
        except Exception as e:
            logger.error(f"Admin message error: {e}")
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "Admin command failed"
            })
    
    @staticmethod
    async def _handle_get_history(connection_id: str, message_data: Dict):
        """Handle chat history requests"""
        try:
            metadata = manager.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")
            
            if not user_id:
                await manager.send_message(connection_id, {
                    "type": "error",
                    "message": "Authentication required for history"
                })
                return
            
            # Get chat history
            limit = message_data.get("limit", 50)
            history = []
            
            if hasattr(db_manager, 'get_chat_history'):
                history = db_manager.get_chat_history(user_id, limit=limit)
            
            await manager.send_message(connection_id, {
                "type": "chat_history",
                "history": history,
                "user_id": user_id
            })
            
        except Exception as e:
            logger.error(f"History request error: {e}")
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "Failed to get chat history"
            })
    
    @staticmethod
    async def _handle_system_info(connection_id: str):
        """Handle system information requests"""
        try:
            system_info = {
                "timestamp": datetime.now().isoformat(),
                "connections": manager.get_connection_info(),
                "memory": memory_monitor.get_memory_status() if memory_monitor else {"status": "unavailable"},
                "database": db_manager.health_check() if hasattr(db_manager, 'health_check') else {"status": "unknown"},
                "models": {
                    "loaded": bool(hasattr(model_manager, '_sentence_model') and model_manager._sentence_model),
                    "memory_usage": model_manager.get_memory_usage() if hasattr(model_manager, 'get_memory_usage') else {}
                }
            }
            
            await manager.send_message(connection_id, {
                "type": "system_info",
                "data": system_info
            })
            
        except Exception as e:
            logger.error(f"System info error: {e}")
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "Failed to get system information"
            })
    
    @staticmethod
    async def _process_chat_message(message: str, user_id: str) -> str:
        """Process chat message with AI models"""
        try:
            # First try content manager for quick responses
            if content_manager:
                response, response_type = content_manager.find_response(message)
                if response and response_type in ["exact", "contains"]:
                    return response
            
            # Try AI model for complex responses
            if hasattr(model_manager, 'generate_response'):
                ai_response = await model_manager.generate_response(message, user_id)
                if ai_response:
                    return ai_response
            
            # Fallback to content manager
            if content_manager:
                response, _ = content_manager.find_response(message)
                if response:
                    return response
            
            # Final fallback
            return "Üzgünüm, şu anda bu soruya cevap veremiyorum. Lütfen daha sonra tekrar deneyin."
            
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            return "Sistem geçici olarak müsait değil. Lütfen daha sonra tekrar deneyin."
