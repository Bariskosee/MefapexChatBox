"""
👤 User Repository for MEFAPEX Chat System
==========================================

Data access layer for user management operations.
"""

import logging
from typing import List, Optional, Dict, Any
from ..models.user import User
from ..services.connection_service import connection_service

logger = logging.getLogger(__name__)


class UserRepository:
    """
    User data access repository
    
    Handles all database operations related to users including
    authentication, registration, and user management.
    """

    def __init__(self):
        self.connection_service = connection_service

    def create_user(self, user: User) -> User:
        """
        Create a new user in the database
        
        Args:
            user: User object to create
            
        Returns:
            Created user with database ID
        """
        query = """
            INSERT INTO users (user_id, username, email, password_hash, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id, created_at
        """
        
        try:
            result = self.connection_service.execute_query(
                query,
                (user.user_id, user.username, user.email, user.password_hash, user.is_active),
                fetch_one=True
            )
            
            if result:
                user.user_id = str(result['user_id'])
                user.created_at = result['created_at']
                
                logger.info(f"✅ User created: {user.username} (ID: {user.user_id})")
                return user
            else:
                raise RuntimeError("Failed to create user - no result returned")
                
        except Exception as e:
            logger.error(f"❌ Failed to create user {user.username}: {e}")
            raise

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username
        
        Args:
            username: Username to search for
            
        Returns:
            User object or None if not found
        """
        query = """
            SELECT user_id, username, email, password_hash, 
                   created_at, last_login, is_active, preferences
            FROM users 
            WHERE username = %s
        """
        
        try:
            result = self.connection_service.execute_query(
                query, (username,), fetch_one=True
            )
            
            if result:
                return User.from_dict(dict(result))
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get user by username {username}: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by user_id
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User object or None if not found
        """
        query = """
            SELECT user_id, username, email, password_hash,
                   created_at, last_login, is_active, preferences
            FROM users 
            WHERE user_id = %s
        """
        
        try:
            result = self.connection_service.execute_query(
                query, (user_id,), fetch_one=True
            )
            
            if result:
                return User.from_dict(dict(result))
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get user by ID {user_id}: {e}")
            return None

    def update_user(self, user: User) -> bool:
        """
        Update user information
        
        Args:
            user: User object with updated information
            
        Returns:
            True if update successful, False otherwise
        """
        query = """
            UPDATE users 
            SET username = %s, email = %s, password_hash = %s,
                updated_at = CURRENT_TIMESTAMP, last_login = %s, is_active = %s,
                preferences = %s
            WHERE user_id = %s
        """
        
        try:
            rows_affected = self.connection_service.execute_query(
                query,
                (user.username, user.email, user.password_hash,
                 user.last_login, user.is_active, user.preferences, user.user_id),
                fetch_all=False
            )
            
            success = rows_affected > 0
            if success:
                logger.info(f"✅ User updated: {user.username}")
            else:
                logger.warning(f"⚠️ No user found to update: {user.user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to update user {user.username}: {e}")
            return False

    def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User ID to update
            
        Returns:
            True if update successful, False otherwise
        """
        query = """
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        
        try:
            rows_affected = self.connection_service.execute_query(
                query, (user_id,), fetch_all=False
            )
            
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update last login for user {user_id}: {e}")
            return False

    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user account
        
        Args:
            user_id: User ID to deactivate
            
        Returns:
            True if deactivation successful, False otherwise
        """
        query = """
            UPDATE users 
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        
        try:
            rows_affected = self.connection_service.execute_query(
                query, (user_id,), fetch_all=False
            )
            
            success = rows_affected > 0
            if success:
                logger.info(f"✅ User deactivated: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to deactivate user {user_id}: {e}")
            return False

    def get_all_users(self, active_only: bool = True) -> List[User]:
        """
        Get all users from the database
        
        Args:
            active_only: If True, return only active users
            
        Returns:
            List of User objects
        """
        query = """
            SELECT user_id, username, email, password_hash,
                   created_at, last_login, is_active, preferences
            FROM users
        """
        
        if active_only:
            query += " WHERE is_active = TRUE"
            
        query += " ORDER BY created_at DESC"
        
        try:
            results = self.connection_service.execute_query(query)
            return [User.from_dict(dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Failed to get all users: {e}")
            return []

    def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics
        
        Returns:
            Dictionary with user statistics
        """
        queries = {
            'total_users': "SELECT COUNT(*) as count FROM users",
            'active_users': "SELECT COUNT(*) as count FROM users WHERE is_active = TRUE",
            'recent_users': """
                SELECT COUNT(*) as count FROM users 
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
            """
        }
        
        stats = {}
        
        for stat_name, query in queries.items():
            try:
                result = self.connection_service.execute_query(query, fetch_one=True)
                stats[stat_name] = result['count'] if result else 0
            except Exception as e:
                logger.error(f"❌ Failed to get {stat_name}: {e}")
                stats[stat_name] = 0
        
        return stats

    def user_exists(self, username: str = None, email: str = None) -> bool:
        """
        Check if user exists by username or email
        
        Args:
            username: Username to check
            email: Email to check
            
        Returns:
            True if user exists, False otherwise
        """
        if not username and not email:
            return False
            
        conditions = []
        params = []
        
        if username:
            conditions.append("username = %s")
            params.append(username)
            
        if email:
            conditions.append("email = %s")
            params.append(email)
        
        query = f"SELECT 1 FROM users WHERE {' OR '.join(conditions)} LIMIT 1"
        
        try:
            result = self.connection_service.execute_query(
                query, params, fetch_one=True
            )
            return result is not None
            
        except Exception as e:
            logger.error(f"❌ Failed to check user existence: {e}")
            return False


# Create singleton instance
user_repository = UserRepository()
