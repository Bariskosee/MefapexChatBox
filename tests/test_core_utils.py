"""
Test for core utilities functions
"""
import pytest
from unittest.mock import Mock
from fastapi import Request
from core.utils import get_client_ip, get_user_agent, get_forwarded_proto, is_local_ip, sanitize_ip_for_logging


class TestGetClientIP:
    """Test get_client_ip function"""
    
    def test_x_forwarded_for_header(self):
        """Test IP extraction from X-Forwarded-For header"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {
            "X-Forwarded-For": "192.168.1.100, 10.0.0.1, 172.16.0.1"
        }
        mock_request.client = None
        
        result = get_client_ip(mock_request)
        assert result == "192.168.1.100"
    
    def test_x_real_ip_header(self):
        """Test IP extraction from X-Real-IP header"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Real-IP": "203.0.113.42"}
        mock_request.client = None
        
        result = get_client_ip(mock_request)
        assert result == "203.0.113.42"
    
    def test_cf_connecting_ip_header(self):
        """Test IP extraction from Cloudflare header"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"CF-Connecting-IP": "198.51.100.23"}
        mock_request.client = None
        
        result = get_client_ip(mock_request)
        assert result == "198.51.100.23"
    
    def test_direct_connection(self):
        """Test IP extraction from direct connection"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.50"
        
        result = get_client_ip(mock_request)
        assert result == "192.168.1.50"
    
    def test_fallback_to_localhost(self):
        """Test fallback when no IP can be determined"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = None
        
        result = get_client_ip(mock_request)
        assert result == "127.0.0.1"
    
    def test_header_priority(self):
        """Test that headers are prioritized correctly"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "203.0.113.2", 
            "CF-Connecting-IP": "203.0.113.3"
        }
        mock_request.client = Mock()
        mock_request.client.host = "203.0.113.4"
        
        result = get_client_ip(mock_request)
        # X-Forwarded-For should have highest priority
        assert result == "203.0.113.1"
    
    def test_invalid_ip_fallback(self):
        """Test handling of invalid IP addresses"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {
            "X-Forwarded-For": "invalid-ip",
            "X-Real-IP": "also-invalid"
        }
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        
        result = get_client_ip(mock_request)
        # Should fall back to client.host since headers are invalid
        assert result == "192.168.1.1"


class TestIsLocalIP:
    """Test is_local_ip function"""
    
    def test_localhost_ips(self):
        """Test localhost IP detection"""
        assert is_local_ip("127.0.0.1") is True
        assert is_local_ip("::1") is True
        assert is_local_ip("localhost") is True
    
    def test_private_ipv4_ranges(self):
        """Test private IPv4 range detection"""
        assert is_local_ip("10.0.0.1") is True
        assert is_local_ip("172.16.0.1") is True
        assert is_local_ip("192.168.1.1") is True
        assert is_local_ip("169.254.1.1") is True  # link-local
    
    def test_public_ips(self):
        """Test public IP detection"""
        assert is_local_ip("8.8.8.8") is False
        assert is_local_ip("203.0.113.1") is False
        assert is_local_ip("198.51.100.1") is False
    
    def test_ipv6_local(self):
        """Test IPv6 local address detection"""
        assert is_local_ip("fe80::1") is True
        assert is_local_ip("fc00::1") is True
        assert is_local_ip("fd00::1") is True


class TestSanitizeIP:
    """Test sanitize_ip_for_logging function"""
    
    def test_local_ip_passthrough(self):
        """Test that local IPs are not sanitized"""
        assert sanitize_ip_for_logging("127.0.0.1") == "127.0.0.1"
        assert sanitize_ip_for_logging("192.168.1.1") == "192.168.1.1"
        assert sanitize_ip_for_logging("10.0.0.1") == "10.0.0.1"
    
    def test_public_ipv4_sanitization(self):
        """Test IPv4 public IP sanitization"""
        assert sanitize_ip_for_logging("203.0.113.42") == "203.0.113.xxx"
        assert sanitize_ip_for_logging("8.8.8.8") == "8.8.8.xxx"
    
    def test_public_ipv6_sanitization(self):
        """Test IPv6 public IP sanitization"""
        assert sanitize_ip_for_logging("2001:db8::1") == "2001:db8::xxxx"
        assert sanitize_ip_for_logging("2001:db8:85a3::8a2e:370:7334") == "2001:db8:85a3::xxxx"


class TestGetUserAgent:
    """Test get_user_agent function"""
    
    def test_user_agent_present(self):
        """Test user agent extraction when present"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"User-Agent": "Mozilla/5.0 Test Browser"}
        
        result = get_user_agent(mock_request)
        assert result == "Mozilla/5.0 Test Browser"
    
    def test_user_agent_missing(self):
        """Test user agent fallback when missing"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        
        result = get_user_agent(mock_request)
        assert result == "unknown"


class TestGetForwardedProto:
    """Test get_forwarded_proto function"""
    
    def test_forwarded_proto_header(self):
        """Test protocol extraction from X-Forwarded-Proto"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Forwarded-Proto": "https"}
        mock_request.url.scheme = "http"
        
        result = get_forwarded_proto(mock_request)
        assert result == "https"
    
    def test_forwarded_ssl_header(self):
        """Test protocol extraction from X-Forwarded-Ssl"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Forwarded-Ssl": "on"}
        mock_request.url.scheme = "http"
        
        result = get_forwarded_proto(mock_request)
        assert result == "https"
    
    def test_fallback_to_request_scheme(self):
        """Test fallback to request scheme"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.url.scheme = "http"
        
        result = get_forwarded_proto(mock_request)
        assert result == "http"


if __name__ == "__main__":
    pytest.main([__file__])
