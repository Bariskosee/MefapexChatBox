"""
🚀 MEFAPEX Database Manager - Compatibility Layer
===============================================

This file maintains backward compatibility with the original database manager
while using the new modular architecture underneath.
"""

# Import the new modular database manager
from database import DatabaseManager
from database.manager import db_manager

# Export for backward compatibility
__all__ = ['DatabaseManager', 'db_manager']
