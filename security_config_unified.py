"""
🔒 MEFAPEX Security Configuration - UNIFIED VERSION
=================================================
Security settings using unified configuration system
"""

import re
import logging
from typing import List, Dict, Set
from datetime import datetime
from core.configuration import get_config

logger = logging.getLogger(__name__)

# Get unified configuration
config = get_config()

class SecurityConfigWrapper:
    """
    Wrapper around unified configuration for legacy compatibility
    """
    
    def __init__(self):
        self.config = config
        self.environment = config.environment.value
        self.is_production = config.is_production()
        
        # Security settings from unified config
        self.demo_user_enabled = config.security.demo_user_enabled
        self.demo_password = config.security.demo_password
        self.min_password_length = config.security.min_password_length
        self.max_password_length = config.security.max_password_length
        self.require_uppercase = config.security.require_uppercase
        self.require_lowercase = config.security.require_lowercase
        self.require_numbers = config.security.require_numbers
        self.require_special_chars = config.security.require_special_chars
        
        # Input validation
        self.max_message_length = config.validation.max_message_length
        self.min_message_length = config.validation.min_message_length
        self.max_username_length = config.validation.max_username_length
        self.min_username_length = config.validation.min_username_length
        
        # Rate limiting
        self.max_requests_per_minute = config.rate_limit.requests_per_minute
        self.max_chat_requests_per_minute = config.rate_limit.chat_requests_per_minute
        self.max_login_attempts = config.security.max_login_attempts
        self.block_duration_minutes = config.security.block_duration_minutes
        
        # JWT settings
        self.access_token_expire_minutes = config.security.access_token_expire_minutes
        self.jwt_algorithm = config.security.jwt_algorithm
        
        # CORS and host settings
        self.allowed_origins = config.server.allowed_origins
        self.allowed_hosts = config.server.allowed_hosts
        
        # Security patterns
        self.xss_patterns = self._get_xss_patterns()
        self.sql_injection_patterns = self._get_sql_injection_patterns()
        self.prohibited_usernames = {
            "admin", "root", "system", "api", "test", 
            "administrator", "superuser", "user", "guest", 
            "null", "undefined", "console", "debug"
        }
    
    def _get_xss_patterns(self) -> List[str]:
        """Get XSS attack patterns for detection"""
        return [
            '<script', '</script>', '<iframe', '</iframe>', 
            '<object', '</object>', '<embed', '</embed>',
            '<svg', '</svg>', '<link', '<meta',
            'javascript:', 'vbscript:', 'data:text/html',
            'onload=', 'onclick=', 'onerror=', 'onmouseover=',
            'onfocus=', 'onblur=', 'onchange=', 'onsubmit=',
            'expression(', 'eval(', 'alert(', 'confirm(',
            'prompt(', 'document.', 'window.', 'location.',
            'navigator.', 'history.', 'screen.', 'parent.',
            'top.', 'self.', 'frames.', 'content.',
            'opener.', 'localStorage.', 'sessionStorage.',
            'indexedDB.', 'webkitStorageInfo.', 'mozStorageInfo.'
        ]
    
    def _get_sql_injection_patterns(self) -> List[str]:
        """Get SQL injection attack patterns for detection"""
        return [
            "'; drop table", "'; delete from", "'; update ",
            "'; insert into", "'; alter table", "'; create ",
            "union select", "union all select", "or 1=1", 
            "and 1=1", "' or '1'='1", "' and '1'='1",
            "' or 1=1 --", "' and 1=1 --", "' or true --",
            "exec(", "execute(", "sp_", "xp_", "master..",
            "information_schema", "sysobjects", "syscolumns",
            "pg_tables", "mysql.user",
            "' having 1=1 --", "' group by ", "' order by ",
            "waitfor delay", "benchmark(", "sleep(",
            "load_file(", "into outfile", "into dumpfile",
            "/*", "*/", "--", "#", "||", "&&"
        ]

class InputValidator:
    """Input validation and sanitization utilities"""
    
    def __init__(self, security_config: SecurityConfigWrapper):
        self.config = security_config
    
    def validate_password(self, password: str) -> tuple[bool, str]:
        """Validate password strength according to policy"""
        if not isinstance(password, str):
            return False, "Password must be a string"
        
        if len(password) < self.config.min_password_length:
            return False, f"Password must be at least {self.config.min_password_length} characters long"
        
        if len(password) > self.config.max_password_length:
            return False, f"Password must be less than {self.config.max_password_length} characters long"
        
        if self.config.require_uppercase and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if self.config.require_lowercase and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if self.config.require_numbers and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        if self.config.require_special_chars:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                return False, "Password must contain at least one special character"
        
        return True, "Password is strong"
    
    def validate_username(self, username: str) -> tuple[bool, str]:
        """Validate username according to policy"""
        if not isinstance(username, str):
            return False, "Username must be a string"
        
        username = username.strip()
        
        if len(username) < self.config.min_username_length:
            return False, f"Username must be at least {self.config.min_username_length} characters long"
        
        if len(username) > self.config.max_username_length:
            return False, f"Username must be less than {self.config.max_username_length} characters long"
        
        # Check prohibited usernames
        if username.lower() in self.config.prohibited_usernames:
            return False, "Username not allowed"
        
        # Check for valid characters (alphanumeric, underscore, hyphen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        return True, "Username is valid"
    
    def validate_message(self, message: str) -> tuple[bool, str]:
        """Validate chat message for security and length"""
        if not isinstance(message, str):
            return False, "Message must be a string"
        
        message = message.strip()
        
        if not message:
            return False, "Message cannot be empty"
        
        if len(message) < self.config.min_message_length:
            return False, f"Message must be at least {self.config.min_message_length} characters long"
        
        if len(message) > self.config.max_message_length:
            return False, f"Message must be less than {self.config.max_message_length} characters long"
        
        return True, "Message is valid"
    
    def detect_xss_attempt(self, text: str) -> tuple[bool, str]:
        """Detect potential XSS attacks in text"""
        if not isinstance(text, str):
            return False, ""
        
        text_lower = text.lower()
        
        for pattern in self.config.xss_patterns:
            if pattern in text_lower:
                logger.warning(f"🚨 XSS pattern detected: {pattern}")
                return True, pattern
        
        return False, ""
    
    def detect_sql_injection(self, text: str) -> tuple[bool, str]:
        """Detect potential SQL injection attempts in text"""
        if not isinstance(text, str):
            return False, ""
        
        text_lower = text.lower()
        
        for pattern in self.config.sql_injection_patterns:
            if pattern in text_lower:
                logger.warning(f"🚨 SQL injection pattern detected: {pattern}")
                return True, pattern
        
        return False, ""
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input for safe processing"""
        if not isinstance(text, str):
            return ""
        
        import html
        # HTML escape for XSS protection
        sanitized = html.escape(text)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized

# Global instances for backward compatibility
security_config = SecurityConfigWrapper()
input_validator = InputValidator(security_config)
