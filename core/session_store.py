"""
Distributed session store abstraction for WebSocket management
Supports horizontal scaling with Redis pub/sub and multiple workers
"""
import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SessionInfo:
    """Session information data class"""
    session_id: str
    user_id: str
    username: str
    connected_at: datetime
    last_activity: datetime
    worker_id: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['connected_at'] = self.connected_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SessionInfo':
        """Create from dictionary"""
        # Convert ISO strings back to datetime objects
        data['connected_at'] = datetime.fromisoformat(data['connected_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        return cls(**data)

class SessionStore(ABC):
    """Abstract base class for session storage"""
    
    @abstractmethod
    async def add_session(self, session_info: SessionInfo) -> bool:
        """Add a new session"""
        pass
    
    @abstractmethod
    async def remove_session(self, session_id: str) -> bool:
        """Remove a session"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        pass
    
    @abstractmethod
    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """Get all sessions for a user"""
        pass
    
    @abstractmethod
    async def get_all_sessions(self) -> List[SessionInfo]:
        """Get all active sessions"""
        pass
    
    @abstractmethod
    async def update_activity(self, session_id: str) -> bool:
        """Update last activity timestamp"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, ttl_seconds: int = 3600) -> int:
        """Clean up expired sessions"""
        pass

class MessageBroker(ABC):
    """Abstract base class for message broadcasting"""
    
    @abstractmethod
    async def publish_message(self, channel: str, message: dict) -> bool:
        """Publish message to a channel"""
        pass
    
    @abstractmethod
    async def subscribe_to_channel(self, channel: str, callback) -> None:
        """Subscribe to a channel"""
        pass
    
    @abstractmethod
    async def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a channel"""
        pass

class InMemorySessionStore(SessionStore):
    """In-memory session store for development/single worker"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionInfo] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
    
    async def add_session(self, session_info: SessionInfo) -> bool:
        """Add a new session"""
        try:
            self.sessions[session_info.session_id] = session_info
            
            if session_info.user_id not in self.user_sessions:
                self.user_sessions[session_info.user_id] = set()
            self.user_sessions[session_info.user_id].add(session_info.session_id)
            
            return True
        except Exception as e:
            logger.error(f"Error adding session: {e}")
            return False
    
    async def remove_session(self, session_id: str) -> bool:
        """Remove a session"""
        try:
            session = self.sessions.pop(session_id, None)
            if session:
                user_sessions = self.user_sessions.get(session.user_id, set())
                user_sessions.discard(session_id)
                if not user_sessions:
                    self.user_sessions.pop(session.user_id, None)
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        return self.sessions.get(session_id)
    
    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """Get all sessions for a user"""
        session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]
    
    async def get_all_sessions(self) -> List[SessionInfo]:
        """Get all active sessions"""
        return list(self.sessions.values())
    
    async def update_activity(self, session_id: str) -> bool:
        """Update last activity timestamp"""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.utcnow()
            return True
        return False
    
    async def cleanup_expired_sessions(self, ttl_seconds: int = 3600) -> int:
        """Clean up expired sessions"""
        cutoff = datetime.utcnow() - timedelta(seconds=ttl_seconds)
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if session.last_activity < cutoff
        ]
        
        for session_id in expired_sessions:
            await self.remove_session(session_id)
        
        return len(expired_sessions)

class InMemoryMessageBroker(MessageBroker):
    """In-memory message broker for development/single worker"""
    
    def __init__(self):
        self.subscribers: Dict[str, List] = {}
    
    async def publish_message(self, channel: str, message: dict) -> bool:
        """Publish message to a channel"""
        try:
            callbacks = self.subscribers.get(channel, [])
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Error in message callback: {e}")
            return True
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
    
    async def subscribe_to_channel(self, channel: str, callback) -> None:
        """Subscribe to a channel"""
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)
    
    async def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a channel"""
        self.subscribers.pop(channel, None)

class RedisSessionStore(SessionStore):
    """Redis-based session store for distributed deployment"""
    
    def __init__(self, redis_url: str, key_prefix: str = "ws_session:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.user_key_prefix = f"{key_prefix}user:"
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
    
    async def add_session(self, session_info: SessionInfo) -> bool:
        """Add a new session"""
        try:
            r = await self._get_redis()
            session_key = f"{self.key_prefix}{session_info.session_id}"
            user_key = f"{self.user_key_prefix}{session_info.user_id}"
            
            # Store session data
            session_data = json.dumps(session_info.to_dict())
            
            # Use pipeline for atomic operations
            async with r.pipeline() as pipe:
                # Store session
                await pipe.setex(session_key, 3600, session_data)  # 1 hour TTL
                # Add to user's session set
                await pipe.sadd(user_key, session_info.session_id)
                await pipe.expire(user_key, 3600)  # 1 hour TTL
                await pipe.execute()
            
            return True
        except Exception as e:
            logger.error(f"Error adding session to Redis: {e}")
            return False
    
    async def remove_session(self, session_id: str) -> bool:
        """Remove a session"""
        try:
            r = await self._get_redis()
            session_key = f"{self.key_prefix}{session_id}"
            
            # Get session to find user_id
            session_data = await r.get(session_key)
            if not session_data:
                return False
            
            session_info = SessionInfo.from_dict(json.loads(session_data))
            user_key = f"{self.user_key_prefix}{session_info.user_id}"
            
            # Use pipeline for atomic operations
            async with r.pipeline() as pipe:
                await pipe.delete(session_key)
                await pipe.srem(user_key, session_id)
                await pipe.execute()
            
            return True
        except Exception as e:
            logger.error(f"Error removing session from Redis: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        try:
            r = await self._get_redis()
            session_key = f"{self.key_prefix}{session_id}"
            session_data = await r.get(session_key)
            
            if session_data:
                return SessionInfo.from_dict(json.loads(session_data))
            return None
        except Exception as e:
            logger.error(f"Error getting session from Redis: {e}")
            return None
    
    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """Get all sessions for a user"""
        try:
            r = await self._get_redis()
            user_key = f"{self.user_key_prefix}{user_id}"
            session_ids = await r.smembers(user_key)
            
            sessions = []
            for session_id in session_ids:
                session = await self.get_session(session_id)
                if session:
                    sessions.append(session)
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting user sessions from Redis: {e}")
            return []
    
    async def get_all_sessions(self) -> List[SessionInfo]:
        """Get all active sessions"""
        try:
            r = await self._get_redis()
            session_keys = await r.keys(f"{self.key_prefix}*")
            
            sessions = []
            for key in session_keys:
                if not key.startswith(f"{self.user_key_prefix}"):  # Skip user index keys
                    session_data = await r.get(key)
                    if session_data:
                        try:
                            session = SessionInfo.from_dict(json.loads(session_data))
                            sessions.append(session)
                        except Exception as e:
                            logger.error(f"Error parsing session data: {e}")
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting all sessions from Redis: {e}")
            return []
    
    async def update_activity(self, session_id: str) -> bool:
        """Update last activity timestamp"""
        try:
            session = await self.get_session(session_id)
            if session:
                session.last_activity = datetime.utcnow()
                return await self.add_session(session)  # Re-add with updated timestamp
            return False
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False
    
    async def cleanup_expired_sessions(self, ttl_seconds: int = 3600) -> int:
        """Clean up expired sessions (Redis TTL handles this automatically)"""
        # Redis TTL handles cleanup automatically, but we can manually check
        try:
            cutoff = datetime.utcnow() - timedelta(seconds=ttl_seconds)
            all_sessions = await self.get_all_sessions()
            expired_count = 0
            
            for session in all_sessions:
                if session.last_activity < cutoff:
                    await self.remove_session(session.session_id)
                    expired_count += 1
            
            return expired_count
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0

class RedisMessageBroker(MessageBroker):
    """Redis-based message broker for distributed deployment"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscribers: Dict[str, List] = {}
        self._listen_task: Optional[asyncio.Task] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    async def close(self):
        """Close Redis connections"""
        if self._listen_task:
            self._listen_task.cancel()
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
    
    async def publish_message(self, channel: str, message: dict) -> bool:
        """Publish message to Redis channel"""
        try:
            r = await self._get_redis()
            message_json = json.dumps(message)
            await r.publish(channel, message_json)
            return True
        except Exception as e:
            logger.error(f"Error publishing message to Redis: {e}")
            return False
    
    async def subscribe_to_channel(self, channel: str, callback) -> None:
        """Subscribe to Redis channel"""
        try:
            r = await self._get_redis()
            
            if self._pubsub is None:
                self._pubsub = r.pubsub()
                self._listen_task = asyncio.create_task(self._listen_for_messages())
            
            # Add callback to subscribers
            if channel not in self._subscribers:
                self._subscribers[channel] = []
                # Subscribe to Redis channel
                await self._pubsub.subscribe(channel)
            
            self._subscribers[channel].append(callback)
            
        except Exception as e:
            logger.error(f"Error subscribing to Redis channel: {e}")
    
    async def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from Redis channel"""
        try:
            if self._pubsub and channel in self._subscribers:
                await self._pubsub.unsubscribe(channel)
                del self._subscribers[channel]
        except Exception as e:
            logger.error(f"Error unsubscribing from Redis channel: {e}")
    
    async def _listen_for_messages(self):
        """Listen for Redis pub/sub messages"""
        try:
            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data = json.loads(message['data'])
                    
                    # Call all subscribers for this channel
                    callbacks = self._subscribers.get(channel, [])
                    for callback in callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
                        except Exception as e:
                            logger.error(f"Error in Redis message callback: {e}")
        except asyncio.CancelledError:
            logger.info("Redis message listener cancelled")
        except Exception as e:
            logger.error(f"Error in Redis message listener: {e}")

def create_session_store(redis_url: Optional[str] = None) -> SessionStore:
    """Factory function to create appropriate session store"""
    if redis_url:
        return RedisSessionStore(redis_url)
    else:
        return InMemorySessionStore()

def create_message_broker(redis_url: Optional[str] = None) -> MessageBroker:
    """Factory function to create appropriate message broker"""
    if redis_url:
        return RedisMessageBroker(redis_url)
    else:
        return InMemoryMessageBroker()
