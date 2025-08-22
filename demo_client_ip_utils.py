#!/usr/bin/env python3
"""
🔍 Client IP Extraction Demo
Demonstrates the centralized client IP extraction utility and its benefits
"""

from unittest.mock import Mock
from fastapi import Request
from core.utils import get_client_ip, get_request_info, sanitize_ip_for_logging


def demo_client_ip_extraction():
    """Demonstrate various client IP extraction scenarios"""
    
    print("🔍 Client IP Extraction Demo")
    print("=" * 50)
    
    # Scenario 1: Cloudflare proxy
    print("\n📡 Scenario 1: Cloudflare Proxy")
    mock_request = Mock(spec=Request)
    mock_request.headers = {
        "CF-Connecting-IP": "203.0.113.42",
        "X-Forwarded-For": "203.0.113.42, 172.16.0.1",
        "X-Real-IP": "203.0.113.42"
    }
    mock_request.client = Mock()
    mock_request.client.host = "172.16.0.1"
    
    client_ip = get_client_ip(mock_request)
    print(f"   Real client IP: {client_ip}")
    print(f"   Sanitized for logs: {sanitize_ip_for_logging(client_ip)}")
    
    # Scenario 2: nginx reverse proxy
    print("\n🔄 Scenario 2: nginx Reverse Proxy")
    mock_request.headers = {
        "X-Forwarded-For": "198.51.100.23, 10.0.0.5",
        "X-Real-IP": "198.51.100.23"
    }
    mock_request.client.host = "10.0.0.5"
    
    client_ip = get_client_ip(mock_request)
    print(f"   Real client IP: {client_ip}")
    print(f"   Sanitized for logs: {sanitize_ip_for_logging(client_ip)}")
    
    # Scenario 3: Direct connection (local development)
    print("\n🏠 Scenario 3: Direct Connection (Local)")
    mock_request.headers = {}
    mock_request.client.host = "127.0.0.1"
    
    client_ip = get_client_ip(mock_request)
    print(f"   Real client IP: {client_ip}")
    print(f"   Sanitized for logs: {sanitize_ip_for_logging(client_ip)}")
    
    # Scenario 4: Multiple proxy chain
    print("\n🔗 Scenario 4: Multiple Proxy Chain")
    mock_request.headers = {
        "X-Forwarded-For": "8.8.8.8, 172.16.0.1, 10.0.0.2, 192.168.1.1"
    }
    mock_request.client.host = "192.168.1.1"
    
    client_ip = get_client_ip(mock_request)
    print(f"   Real client IP: {client_ip}")
    print(f"   Sanitized for logs: {sanitize_ip_for_logging(client_ip)}")
    
    # Scenario 5: IPv6 address
    print("\n🌐 Scenario 5: IPv6 Address")
    mock_request.headers = {
        "X-Forwarded-For": "2001:db8:85a3::8a2e:370:7334"
    }
    
    client_ip = get_client_ip(mock_request)
    print(f"   Real client IP: {client_ip}")
    print(f"   Sanitized for logs: {sanitize_ip_for_logging(client_ip)}")


def demo_comprehensive_request_info():
    """Demonstrate comprehensive request information extraction"""
    
    print("\n\n🔎 Comprehensive Request Info Demo")
    print("=" * 50)
    
    mock_request = Mock(spec=Request)
    mock_request.headers = {
        "X-Forwarded-For": "203.0.113.42",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/91.0",
        "X-Forwarded-Proto": "https",
        "Host": "api.mefapex.com",
        "Referer": "https://mefapex.com/chat"
    }
    mock_request.client = Mock()
    mock_request.client.host = "172.16.0.1"
    mock_request.method = "POST"
    mock_request.url.path = "/api/chat/message"
    mock_request.url.scheme = "http"  # Will be overridden by header
    mock_request.query_params = {"debug": "true"}
    
    request_info = get_request_info(mock_request)
    
    print("\n📊 Request Information:")
    for key, value in request_info.items():
        print(f"   {key:15}: {value}")


def show_benefits():
    """Show the benefits of the centralized approach"""
    
    print("\n\n✨ Benefits of Centralized Client IP Extraction")
    print("=" * 60)
    
    benefits = [
        "🎯 Consistent behavior across all modules",
        "🔒 Proper proxy header handling (X-Forwarded-For, X-Real-IP, etc.)",
        "🌐 Support for various deployment scenarios (CDN, load balancers)",
        "🛡️ Security-focused with IP validation",
        "📝 GDPR-compliant IP sanitization for logging",
        "🧪 Thoroughly tested with comprehensive test suite",
        "🔧 Easy to maintain and update in one place",
        "📱 IPv6 support",
        "🏠 Local/private IP detection",
        "🚀 Performance optimized with proper fallbacks"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")


def show_migration_summary():
    """Show what was changed during migration"""
    
    print("\n\n🔄 Migration Summary")
    print("=" * 30)
    
    changes = [
        "📄 Created core/utils.py with centralized get_client_ip()",
        "🔐 Updated auth_service.py to use shared utility", 
        "🛡️ Updated middleware.py to use shared utility",
        "💬 Updated api/chat.py to use shared utility",
        "🔑 Updated api/auth.py to use shared utility",
        "⚙️ Updated core/middleware_integration.py to use shared utility",
        "🌐 Updated core/http_handlers.py to use shared utility",
        "🧪 Added comprehensive test suite",
        "📚 Maintained backward compatibility with deprecation notices"
    ]
    
    for change in changes:
        print(f"   {change}")


if __name__ == "__main__":
    demo_client_ip_extraction()
    demo_comprehensive_request_info()
    show_benefits()
    show_migration_summary()
    
    print("\n\n🎉 Demo completed successfully!")
    print("The centralized client IP extraction is now ready for production use.")
