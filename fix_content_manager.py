#!/usr/bin/env python3
"""
Fix content_manager.py to work with new modular database system
"""

import re

# Read the current content_manager.py
with open('/Users/bariskose/Downloads/MefapexChatBox-main/content_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing content_manager.py database calls...")

# Replace patterns
replacements = [
    # Replace _get_connection and _put_connection pattern
    (
        r'conn = db_manager\._get_connection\(\)\s+cursor = conn\.cursor\(\)',
        'cursor = db_manager.connection_service.get_connection().cursor()'
    ),
    (
        r'db_manager\._put_connection\(conn\)',
        '# Connection handled by context manager'
    ),
    # Replace direct connection usage
    (
        r'conn\.commit\(\)',
        '# Auto-commit handled by execute_query'
    ),
    (
        r'conn\.rollback\(\)',
        '# Auto-rollback handled by execute_query'
    )
]

# Apply replacements
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Manual fixes for specific patterns that need context managers
fixes = [
    # Fix _ensure_dynamic_table_exists method
    (
        '''    def _ensure_dynamic_table_exists(self):
        """Ensure dynamic_responses table exists in PostgreSQL"""
        try:
            from database_manager import db_manager
            
            cursor = db_manager.connection_service.get_connection().cursor()
            
            # Create dynamic_responses table if it doesn't exist
            cursor.execute('''',
        '''    def _ensure_dynamic_table_exists(self):
        """Ensure dynamic_responses table exists in PostgreSQL"""
        try:
            from database_manager import db_manager
            
            # Use the new modular database interface
            db_manager.connection_service.execute_query('''
    ),
    # Fix add_dynamic_response method
    (
        '''            cursor = db_manager.connection_service.get_connection().cursor()
            
            # Insert the new response
            cursor.execute(''',
        '''            # Use the new modular database interface
            db_manager.connection_service.execute_query('''
    ),
    # Fix get_all_dynamic_responses method  
    (
        '''            cursor = db_manager.connection_service.get_connection().cursor()
            
            cursor.execute(''',
        '''            # Use the new modular database interface
            results = db_manager.connection_service.execute_query('''
    ),
    # Fix update_dynamic_response method
    (
        '''            cursor = db_manager.connection_service.get_connection().cursor()
            
            cursor.execute(''',
        '''            # Use the new modular database interface
            db_manager.connection_service.execute_query('''
    ),
    # Fix delete_dynamic_response method
    (
        '''            cursor = db_manager.connection_service.get_connection().cursor()
            
            cursor.execute(''',
        '''            # Use the new modular database interface
            db_manager.connection_service.execute_query('''
    )
]

for old_text, new_text in fixes:
    content = content.replace(old_text, new_text)

print("✅ Applied database call fixes")

# Write the fixed content back
with open('/Users/bariskose/Downloads/MefapexChatBox-main/content_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed content_manager.py database integration")
print("🔍 The content_manager now uses the new modular database system")
