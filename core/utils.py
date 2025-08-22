"""
🛠️ Core Utilities
Centralized utility functions for common operations across the application
"""

import logging
from typing import Optional
from fastapi import Request

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request with proper fallback handling.
    
    Handles proxy headers and various deployment scenarios including:
    - Direct connections
    - Reverse proxy setups (nginx, Apache)
    - Load balancers
    - CDN services (Cloudflare, etc.)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Client IP address, fallback to "127.0.0.1" if unable to determine
    """
    try:
        # Priority 1: X-Forwarded-For header (most common for proxies)
        # Format: "client_ip, proxy1_ip, proxy2_ip"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first (leftmost) IP which is the original client
            client_ip = forwarded_for.split(',')[0].strip()
            if client_ip and _is_valid_ip(client_ip):
                return client_ip
        
        # Priority 2: X-Real-IP header (nginx real_ip module)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip and _is_valid_ip(real_ip):
            return real_ip.strip()
        
        # Priority 3: X-Forwarded-Host header
        forwarded_host = request.headers.get("X-Forwarded-Host")
        if forwarded_host and _is_valid_ip(forwarded_host):
            return forwarded_host.strip()
        
        # Priority 4: CF-Connecting-IP header (Cloudflare)
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip and _is_valid_ip(cf_ip):
            return cf_ip.strip()
        
        # Priority 5: X-Client-IP header (some proxies)
        client_ip_header = request.headers.get("X-Client-IP")
        if client_ip_header and _is_valid_ip(client_ip_header):
            return client_ip_header.strip()
        
        # Priority 6: Direct connection (request.client.host)
        if request.client and hasattr(request.client, 'host') and request.client.host:
            client_ip = request.client.host
            if _is_valid_ip(client_ip):
                return client_ip
        
        # Fallback: localhost
        logger.debug("Unable to determine client IP, using fallback")
        return "127.0.0.1"
        
    except Exception as e:
        logger.warning(f"Error extracting client IP: {e}")
        return "127.0.0.1"


def _is_valid_ip(ip: str) -> bool:
    """
    Basic validation to check if the string looks like a valid IP address.
    
    Args:
        ip: IP address string to validate
        
    Returns:
        bool: True if the IP looks valid, False otherwise
    """
    if not ip:
        return False
    
    # Remove common non-IP characters that might be present
    ip = ip.strip()
    
    # Basic format check - should look like an IP
    if not ip.replace('.', '').replace(':', '').replace('[', '').replace(']', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '').replace('a', '').replace('b', '').replace('c', '').replace('d', '').replace('e', '').replace('f', '').replace('A', '').replace('B', '').replace('C', '').replace('D', '').replace('E', '').replace('F', ''):
        pass
    else:
        return False
    
    # IPv4 validation
    if '.' in ip and ':' not in ip:
        parts = ip.split('.')
        if len(parts) == 4:
            try:
                for part in parts:
                    num = int(part)
                    if not (0 <= num <= 255):
                        return False
                return True
            except ValueError:
                return False
    
    # IPv6 validation (basic)
    if ':' in ip:
        # Remove brackets if present (e.g., [::1])
        ip = ip.strip('[]')
        # Basic IPv6 check - should have colons and valid hex characters
        if '::' in ip or (ip.count(':') >= 2 and all(c in '0123456789abcdefABCDEF:' for c in ip)):
            return True
    
    return False


def get_user_agent(request: Request) -> str:
    """
    Extract User-Agent string from request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: User-Agent string, fallback to "unknown" if not present
    """
    return request.headers.get("User-Agent", "unknown")


def get_forwarded_proto(request: Request) -> str:
    """
    Extract protocol (http/https) from request, considering proxy headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Protocol ("http" or "https")
    """
    # Check X-Forwarded-Proto header first (proxy/load balancer)
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto:
        return forwarded_proto.lower().strip()
    
    # Check X-Forwarded-Ssl header
    forwarded_ssl = request.headers.get("X-Forwarded-Ssl")
    if forwarded_ssl and forwarded_ssl.lower() in ("on", "true", "1"):
        return "https"
    
    # Fallback to request scheme
    return request.url.scheme


def is_local_ip(ip: str) -> bool:
    """
    Check if IP address is a local/private address.
    
    Args:
        ip: IP address string
        
    Returns:
        bool: True if IP is local/private, False otherwise
    """
    if not ip or ip == "127.0.0.1" or ip == "::1" or ip == "localhost":
        return True
    
    # IPv4 private ranges
    if '.' in ip and ':' not in ip:
        try:
            parts = [int(p) for p in ip.split('.')]
            if len(parts) == 4:
                # 10.0.0.0/8
                if parts[0] == 10:
                    return True
                # 172.16.0.0/12
                if parts[0] == 172 and 16 <= parts[1] <= 31:
                    return True
                # 192.168.0.0/16
                if parts[0] == 192 and parts[1] == 168:
                    return True
                # 169.254.0.0/16 (link-local)
                if parts[0] == 169 and parts[1] == 254:
                    return True
        except (ValueError, IndexError):
            pass
    
    # IPv6 local addresses (basic check)
    if ':' in ip:
        ip_lower = ip.lower()
        if ip_lower.startswith(('::1', 'fe80:', 'fc00:', 'fd00:')):
            return True
    
    return False


def sanitize_ip_for_logging(ip: str) -> str:
    """
    Sanitize IP address for safe logging (GDPR compliance).
    
    Args:
        ip: IP address string
        
    Returns:
        str: Sanitized IP address suitable for logging
    """
    if not ip or is_local_ip(ip):
        return ip
    
    # IPv4: Replace last octet with 'xxx'
    if '.' in ip and ':' not in ip:
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    
    # IPv6: Replace last 64 bits with 'xxxx'
    if ':' in ip:
        if '::' in ip:
            return ip.split('::')[0] + '::xxxx'
        else:
            parts = ip.split(':')
            if len(parts) >= 4:
                return ':'.join(parts[:4]) + ':xxxx'
    
    return "xxx.xxx.xxx.xxx"


def get_request_info(request: Request) -> dict:
    """
    Extract comprehensive request information for logging and monitoring.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        dict: Request information including IP, user agent, protocol, etc.
    """
    return {
        "client_ip": get_client_ip(request),
        "user_agent": get_user_agent(request),
        "protocol": get_forwarded_proto(request),
        "method": request.method,
        "path": request.url.path,
        "query_params": str(request.query_params) if request.query_params else None,
        "host": request.headers.get("Host"),
        "referer": request.headers.get("Referer"),
        "is_local": is_local_ip(get_client_ip(request))
    }
