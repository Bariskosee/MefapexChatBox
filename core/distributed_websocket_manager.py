"""
Distributed WebSocket manager for horizontal scaling
Supports multiple workers with Redis pub/sub for message broadcasting
"""
import asyncio
import json
import logging
import os
import uuid
from typing import Dict, Set, Optional, Any, List
from datetime import datetime
import weakref

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from core.session_store import (
    SessionStore, MessageBroker, SessionInfo,
    create_session_store, create_message_broker
)

logger = logging.getLogger(__name__)

class DistributedConnectionManager:
    """
    Distributed WebSocket connection manager supporting horizontal scaling
    Features:
    - Redis-based session persistence
    - Pub/sub message broadcasting across workers
    - Automatic failover and cleanup
    - Worker identification and load balancing
    """
    
    def __init__(self, redis_url: Optional[str] = None, worker_id: Optional[str] = None):
        # Worker identification
        self.worker_id = worker_id or f"worker-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        
        # Local connections (WebSocket objects are worker-specific)
        self.local_connections: Dict[str, WebSocket] = {}  # session_id -> websocket
        self.connection_sessions: Dict[WebSocket, str] = weakref.WeakKeyDictionary()  # websocket -> session_id
        
        # Distributed session store
        self.session_store: SessionStore = create_session_store(redis_url)
        self.message_broker: MessageBroker = create_message_broker(redis_url)
        
        # Local stats
        self.local_stats = {
            'worker_id': self.worker_id,
            'local_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'connections_opened': 0,
            'connections_closed': 0,
            'broadcast_messages_sent': 0,
            'broadcast_messages_received': 0
        }
        
        # Setup message broker subscriptions
        self._setup_message_subscriptions()
        
        logger.info(f"🌐 Distributed WebSocket Manager initialized - Worker: {self.worker_id}")
    
    def _setup_message_subscriptions(self):
        """Setup message broker subscriptions for different message types"""
        # Subscribe to broadcast messages
        asyncio.create_task(
            self.message_broker.subscribe_to_channel(
                "websocket:broadcast", 
                self._handle_broadcast_message
            )
        )
        
        # Subscribe to user-specific messages
        asyncio.create_task(
            self.message_broker.subscribe_to_channel(
                "websocket:user_message", 
                self._handle_user_message
            )
        )
        
        # Subscribe to worker coordination messages
        asyncio.create_task(
            self.message_broker.subscribe_to_channel(
                f"websocket:worker:{self.worker_id}", 
                self._handle_worker_message
            )
        )
    
    async def connect(self, websocket: WebSocket, user_id: str, username: str, metadata: Optional[Dict] = None):
        """
        Accept new WebSocket connection and register in distributed session store
        """
        await websocket.accept()
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session info
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            username=username,
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            worker_id=self.worker_id,
            metadata=metadata or {}
        )
        
        # Store in distributed session store
        success = await self.session_store.add_session(session_info)
        if not success:
            logger.error(f"Failed to store session for user {username}")
            await websocket.close(code=1011, reason="Session storage failed")
            return None
        
        # Store local connection mapping
        self.local_connections[session_id] = websocket
        self.connection_sessions[websocket] = session_id
        
        # Update local stats
        self.local_stats['local_connections'] += 1
        self.local_stats['connections_opened'] += 1
        
        logger.info(f"✅ User {username} ({user_id}) connected via WebSocket - Session: {session_id}")
        
        # Send welcome message
        await self.send_personal_message({
            'type': 'connection_established',
            'message': 'WebSocket connection established',
            'session_id': session_id,
            'worker_id': self.worker_id,
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)
        
        # Notify other workers about new connection
        await self._broadcast_worker_event('user_connected', {
            'user_id': user_id,
            'username': username,
            'session_id': session_id,
            'worker_id': self.worker_id
        })
        
        return session_id
    
    async def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection and cleanup distributed session
        """
        try:
            # Get session ID from local mapping
            session_id = self.connection_sessions.get(websocket)
            if not session_id:
                logger.warning("WebSocket disconnect without session ID")
                return
            
            # Get session info from distributed store
            session_info = await self.session_store.get_session(session_id)
            if session_info:
                user_id = session_info.user_id
                username = session_info.username
                
                # Remove from distributed session store
                await self.session_store.remove_session(session_id)
                
                # Remove from local mappings
                self.local_connections.pop(session_id, None)
                
                # Update local stats
                self.local_stats['local_connections'] -= 1
                self.local_stats['connections_closed'] += 1
                
                logger.info(f"❌ User {username} ({user_id}) disconnected - Session: {session_id}")
                
                # Notify other workers about disconnection
                await self._broadcast_worker_event('user_disconnected', {
                    'user_id': user_id,
                    'username': username,
                    'session_id': session_id,
                    'worker_id': self.worker_id
                })
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific WebSocket connection (local only)
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message))
                self.local_stats['messages_sent'] += 1
                
                # Update session activity in distributed store
                session_id = self.connection_sessions.get(websocket)
                if session_id:
                    await self.session_store.update_activity(session_id)
                    
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Connection likely closed, will be cleaned up by disconnect handler
    
    async def send_to_user(self, user_id: str, message: dict):
        """
        Send message to all connections of a specific user across all workers
        """
        # First try local connections
        local_sent = 0
        user_sessions = await self.session_store.get_user_sessions(user_id)
        
        for session in user_sessions:
            if session.worker_id == self.worker_id:
                # Local connection
                websocket = self.local_connections.get(session.session_id)
                if websocket:
                    await self.send_personal_message(message, websocket)
                    local_sent += 1
        
        # If user has sessions on other workers, broadcast via message broker
        remote_sessions = [s for s in user_sessions if s.worker_id != self.worker_id]
        if remote_sessions:
            await self.message_broker.publish_message("websocket:user_message", {
                'user_id': user_id,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'sender_worker': self.worker_id
            })
        
        logger.debug(f"Message sent to user {user_id}: {local_sent} local, {len(remote_sessions)} remote")
    
    async def broadcast_to_all(self, message: dict):
        """
        Broadcast message to all connected users across all workers
        """
        # Send to local connections
        disconnected_sessions = []
        
        for session_id, websocket in self.local_connections.items():
            try:
                await self.send_personal_message(message, websocket)
            except:
                disconnected_sessions.append(session_id)
        
        # Clean up disconnected local connections
        for session_id in disconnected_sessions:
            websocket = self.local_connections.get(session_id)
            if websocket:
                await self.disconnect(websocket)
        
        # Broadcast to other workers via message broker
        await self.message_broker.publish_message("websocket:broadcast", {
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'sender_worker': self.worker_id
        })
        
        self.local_stats['broadcast_messages_sent'] += 1
    
    async def _handle_broadcast_message(self, data: dict):
        """Handle broadcast message from message broker"""
        try:
            # Don't process our own broadcasts
            if data.get('sender_worker') == self.worker_id:
                return
            
            message = data['message']
            disconnected_sessions = []
            
            # Send to all local connections
            for session_id, websocket in self.local_connections.items():
                try:
                    await self.send_personal_message(message, websocket)
                except:
                    disconnected_sessions.append(session_id)
            
            # Clean up disconnected connections
            for session_id in disconnected_sessions:
                websocket = self.local_connections.get(session_id)
                if websocket:
                    await self.disconnect(websocket)
            
            self.local_stats['broadcast_messages_received'] += 1
            
        except Exception as e:
            logger.error(f"Error handling broadcast message: {e}")
    
    async def _handle_user_message(self, data: dict):
        """Handle user-specific message from message broker"""
        try:
            # Don't process our own messages
            if data.get('sender_worker') == self.worker_id:
                return
            
            user_id = data['user_id']
            message = data['message']
            
            # Find local sessions for this user
            user_sessions = await self.session_store.get_user_sessions(user_id)
            local_sessions = [s for s in user_sessions if s.worker_id == self.worker_id]
            
            # Send to local connections
            for session in local_sessions:
                websocket = self.local_connections.get(session.session_id)
                if websocket:
                    await self.send_personal_message(message, websocket)
            
            self.local_stats['messages_received'] += 1
            
        except Exception as e:
            logger.error(f"Error handling user message: {e}")
    
    async def _handle_worker_message(self, data: dict):
        """Handle worker-specific coordination messages"""
        try:
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Respond to health check
                await self.message_broker.publish_message(
                    f"websocket:worker:{data.get('sender_worker')}", 
                    {
                        'type': 'pong',
                        'worker_id': self.worker_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'stats': self.local_stats
                    }
                )
            
        except Exception as e:
            logger.error(f"Error handling worker message: {e}")
    
    async def _broadcast_worker_event(self, event_type: str, data: dict):
        """Broadcast worker events to coordination channel"""
        await self.message_broker.publish_message("websocket:worker_events", {
            'event_type': event_type,
            'worker_id': self.worker_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        })
    
    async def get_user_connections(self, user_id: str) -> List[SessionInfo]:
        """Get all active sessions for a user across all workers"""
        return await self.session_store.get_user_sessions(user_id)
    
    async def is_user_online(self, user_id: str) -> bool:
        """Check if user has any active connections across all workers"""
        sessions = await self.session_store.get_user_sessions(user_id)
        return len(sessions) > 0
    
    async def get_online_users(self) -> List[str]:
        """Get list of all online user IDs across all workers"""
        sessions = await self.session_store.get_all_sessions()
        user_ids = set(session.user_id for session in sessions)
        return list(user_ids)
    
    async def get_connection_stats(self) -> dict:
        """Get comprehensive connection statistics"""
        # Get distributed session stats
        all_sessions = await self.session_store.get_all_sessions()
        
        # Group by worker
        worker_stats = {}
        user_sessions = {}
        
        for session in all_sessions:
            # Worker stats
            if session.worker_id not in worker_stats:
                worker_stats[session.worker_id] = {
                    'session_count': 0,
                    'users': set()
                }
            worker_stats[session.worker_id]['session_count'] += 1
            worker_stats[session.worker_id]['users'].add(session.user_id)
            
            # User session details
            if session.user_id not in user_sessions:
                user_sessions[session.user_id] = []
            user_sessions[session.user_id].append({
                'session_id': session.session_id,
                'worker_id': session.worker_id,
                'connected_at': session.connected_at.isoformat(),
                'last_activity': session.last_activity.isoformat()
            })
        
        # Convert sets to counts for JSON serialization
        for worker_id in worker_stats:
            worker_stats[worker_id]['unique_users'] = len(worker_stats[worker_id]['users'])
            del worker_stats[worker_id]['users']
        
        return {
            'distributed_stats': {
                'total_sessions': len(all_sessions),
                'total_users': len(user_sessions),
                'total_workers': len(worker_stats),
                'worker_distribution': worker_stats
            },
            'local_stats': self.local_stats,
            'user_sessions': user_sessions
        }
    
    async def ping_all_connections(self):
        """Send ping to all connections across all workers"""
        ping_message = {
            'type': 'ping',
            'timestamp': datetime.utcnow().isoformat(),
            'worker_id': self.worker_id
        }
        
        await self.broadcast_to_all(ping_message)
        logger.debug("📡 Ping sent to all connections across all workers")
    
    async def cleanup_expired_sessions(self, ttl_seconds: int = 3600) -> int:
        """Clean up expired sessions across all workers"""
        return await self.session_store.cleanup_expired_sessions(ttl_seconds)
    
    async def health_check(self) -> dict:
        """Perform health check of the distributed system"""
        try:
            # Test session store
            test_session = SessionInfo(
                session_id=f"health_check_{self.worker_id}",
                user_id="health_check_user",
                username="health_check",
                connected_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                worker_id=self.worker_id
            )
            
            # Test add/get/remove cycle
            add_success = await self.session_store.add_session(test_session)
            get_result = await self.session_store.get_session(test_session.session_id)
            remove_success = await self.session_store.remove_session(test_session.session_id)
            
            # Test message broker
            test_message = {'test': True, 'timestamp': datetime.utcnow().isoformat()}
            broker_success = await self.message_broker.publish_message("websocket:health_check", test_message)
            
            return {
                'worker_id': self.worker_id,
                'session_store_healthy': add_success and get_result is not None and remove_success,
                'message_broker_healthy': broker_success,
                'local_connections': len(self.local_connections),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'worker_id': self.worker_id,
                'session_store_healthy': False,
                'message_broker_healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Clean shutdown of distributed manager"""
        logger.info(f"🔌 Shutting down Distributed WebSocket Manager - Worker: {self.worker_id}")
        
        # Close all local connections
        for websocket in list(self.local_connections.values()):
            try:
                await websocket.close(code=1001, reason="Server shutdown")
            except:
                pass
        
        # Clean up session store
        if hasattr(self.session_store, 'close'):
            await self.session_store.close()
        
        # Clean up message broker
        if hasattr(self.message_broker, 'close'):
            await self.message_broker.close()

# Factory function to create distributed connection manager
def create_distributed_websocket_manager(redis_url: Optional[str] = None, worker_id: Optional[str] = None) -> DistributedConnectionManager:
    """Create distributed WebSocket manager with appropriate backend"""
    return DistributedConnectionManager(redis_url=redis_url, worker_id=worker_id)
