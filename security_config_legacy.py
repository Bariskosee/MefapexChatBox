"""
🔒 MEFAPEX Security Configuration
Enhanced security settings and validation functions
"""

import os
import re
import logging
from typing import List, Dict, Set
from datetime import datetime
from core.configuration import get_config

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Centralized security configuration for MEFAPEX"""
    
    def __init__(self):
        self.environment = get_config().environment.value
        self.is_production = self.environment == "production"
        
        # 🚨 DEMO USER SECURITY SETTINGS
        self.demo_user_enabled = self._get_demo_user_setting()
        self.demo_password = get_config().security.demo_password
        
        # 🔒 PASSWORD SECURITY SETTINGS
        self.min_password_length = int(get_config().security.min_password_length)
        self.max_password_length = int(get_config().security.max_password_length)
        self.require_uppercase = os.getenv("REQUIRE_UPPERCASE", "true").lower() == "true"
        self.require_lowercase = os.getenv("REQUIRE_LOWERCASE", "true").lower() == "true"
        self.require_numbers = os.getenv("REQUIRE_NUMBERS", "true").lower() == "true"
        self.require_special_chars = os.getenv("REQUIRE_SPECIAL_CHARS", "true").lower() == "true"
        
        # 🛡️ INPUT VALIDATION SETTINGS
        self.max_message_length = int(get_config().validation.max_message_length)
        self.min_message_length = int(get_config().validation.min_message_length)
        self.max_username_length = int(get_config().validation.max_username_length)
        self.min_username_length = int(get_config().validation.min_username_length)
        
        # 🚦 RATE LIMITING SETTINGS
        self.max_requests_per_minute = int(get_config().rate_limit.requests_per_minute)
        self.max_chat_requests_per_minute = int(get_config().rate_limit.chat_requests_per_minute)
        self.max_login_attempts = int(get_config().security.max_login_attempts)
        self.block_duration_minutes = int(get_config().security.block_duration_minutes)
        
        # 🔐 JWT SETTINGS
        self.access_token_expire_minutes = int(get_config().security.access_token_expire_minutes)
        self.jwt_algorithm = "HS256"
        
        # 🌐 CORS SETTINGS
        self.allowed_origins = self._parse_cors_origins()
        self.allowed_hosts = self._parse_allowed_hosts()
        
        # 🛡️ XSS PROTECTION PATTERNS
        self.xss_patterns = self._get_xss_patterns()
        
        # 🔒 SQL INJECTION PATTERNS
        self.sql_injection_patterns = self._get_sql_injection_patterns()
        
        # 📝 PROHIBITED USERNAMES
        self.prohibited_usernames = {
            "admin", "root", "system", "api", "test", 
            "administrator", "superuser", "user", "guest", 
            "null", "undefined", "console", "debug"
        }
        
        # ⚠️ SECURITY AUDIT
        self._audit_security_settings()
    
    def _get_demo_user_setting(self) -> bool:
        """Determine if demo user should be enabled with security checks"""
        demo_enabled = get_config().security.demo_user_enabled
        
        if self.is_production and demo_enabled:
            force_demo = os.getenv("FORCE_DEMO_IN_PRODUCTION", "false").lower() == "true"
            if not force_demo:
                logger.error("🚨 SECURITY: Demo user disabled in production for security")
                return False
            else:
                logger.warning("⚠️ SECURITY WARNING: Demo user forced enabled in production!")
                return True
        
        return demo_enabled
    
    def _parse_cors_origins(self) -> List[str]:
        """Parse and validate CORS origins"""
        origins_env = get_config().server.allowed_origins
        origins = origins_env if isinstance(origins_env, list) else [origins_env]
        
        validated_origins = []
        for origin in origins:
            if origin == "*":
                if self.is_production:
                    logger.error(f"🚨 SECURITY: Wildcard CORS origin rejected in production: {origin}")
                    continue
                else:
                    logger.warning(f"⚠️ CORS: Wildcard origin allowed in development: {origin}")
            
            if origin.startswith(("http://", "https://")) or origin == "*":
                validated_origins.append(origin)
            else:
                logger.error(f"🚨 SECURITY: Invalid CORS origin format rejected: {origin}")
        
        if not validated_origins:
            # Fallback to safe defaults
            validated_origins = [
                "http://localhost:3000", 
                "http://localhost:8000", 
                "http://127.0.0.1:8000"
            ]
            logger.warning(f"⚠️ CORS: Using fallback origins: {validated_origins}")
        
        return validated_origins
    
    def _parse_allowed_hosts(self) -> List[str]:
        """Parse and validate allowed hosts"""
        hosts_env = get_config().server.allowed_hosts
        hosts = hosts_env if isinstance(hosts_env, list) else [hosts_env]
        
        if not hosts:
            hosts = ["localhost", "127.0.0.1"]
        
        return hosts
    
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
    
    def _audit_security_settings(self):
        """Audit current security settings and log warnings"""
        logger.info(f"🔒 Security Config Audit for {self.environment} environment:")
        
        # Demo user audit
        if self.demo_user_enabled:
            if self.is_production:
                logger.error("🚨 CRITICAL: Demo user enabled in production!")
            else:
                logger.info("ℹ️ Demo user enabled (development mode)")
        
        # Password policy audit
        if self.min_password_length < 8:
            logger.warning(f"⚠️ Weak password policy: min length {self.min_password_length}")
        
        # CORS audit
        if "*" in self.allowed_origins and self.is_production:
            logger.error("🚨 CRITICAL: Wildcard CORS in production!")
        
        logger.info(f"✅ Security audit completed")

class InputValidator:
    """Input validation and sanitization utilities"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
    
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

# Global security configuration instance
security_config = SecurityConfig()
input_validator = InputValidator(security_config)
