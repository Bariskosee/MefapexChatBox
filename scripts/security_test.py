#!/usr/bin/env python3
"""
🔒 MEFAPEX ChatBot - Security Test Suite
Bu script güvenlik önlemlerini test eder
"""

import asyncio
import aiohttp
import json
import time
import secrets
from typing import Dict, List, Optional

class SecurityTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, status: str, details: str = ""):
        """Test sonucunu logla"""
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        })
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status} {details}")
    
    async def test_rate_limiting(self):
        """Rate limiting testini çalıştır"""
        print("\n🚦 Testing Rate Limiting...")
        
        # Chat endpoint rate limiting test
        chat_url = f"{self.base_url}/chat"
        rapid_requests = []
        
        for i in range(25):  # Rate limit 20'den fazla istek gönder
            try:
                response = await self.session.post(
                    chat_url,
                    json={"message": f"Test message {i}"},
                    timeout=aiohttp.ClientTimeout(total=2)
                )
                rapid_requests.append(response.status)
            except asyncio.TimeoutError:
                rapid_requests.append(408)  # Timeout
            except Exception:
                rapid_requests.append(500)  # Server error
        
        rate_limited_count = sum(1 for status in rapid_requests if status == 429)
        
        if rate_limited_count > 0:
            self.log_result("Rate Limiting", "PASS", f"{rate_limited_count} requests rate limited")
        else:
            self.log_result("Rate Limiting", "FAIL", "No rate limiting detected")
    
    async def test_cors_headers(self):
        """CORS güvenliği testini çalıştır"""
        print("\n🌐 Testing CORS Security...")
        
        try:
            # OPTIONS request ile CORS header'larını kontrol et
            response = await self.session.options(
                f"{self.base_url}/health",
                headers={"Origin": "https://malicious-site.com"}
            )
            
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
            }
            
            # Wildcard (*) kontrolü
            origin_header = cors_headers.get("Access-Control-Allow-Origin", "")
            if origin_header == "*":
                self.log_result("CORS Wildcard", "FAIL", "Wildcard (*) origin detected")
            else:
                self.log_result("CORS Wildcard", "PASS", "No wildcard origin")
                
        except Exception as e:
            self.log_result("CORS Headers", "ERROR", str(e))
    
    async def test_security_headers(self):
        """Güvenlik header'larını test et"""
        print("\n🛡️ Testing Security Headers...")
        
        try:
            response = await self.session.get(f"{self.base_url}/health")
            headers = response.headers
            
            # Kritik güvenlik header'ları
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY", 
                "X-XSS-Protection": "1; mode=block",
                "Content-Security-Policy": True,  # Varlığını kontrol et
                "Referrer-Policy": True
            }
            
            for header, expected in security_headers.items():
                if header in headers:
                    if isinstance(expected, bool):
                        self.log_result(f"Security Header: {header}", "PASS", "Present")
                    elif headers[header] == expected:
                        self.log_result(f"Security Header: {header}", "PASS", headers[header])
                    else:
                        self.log_result(f"Security Header: {header}", "WARN", f"Got: {headers[header]}")
                else:
                    self.log_result(f"Security Header: {header}", "FAIL", "Missing")
                    
        except Exception as e:
            self.log_result("Security Headers", "ERROR", str(e))
    
    async def test_brute_force_protection(self):
        """Brute force korumasını test et"""
        print("\n🔐 Testing Brute Force Protection...")
        
        login_url = f"{self.base_url}/login"
        
        # 6 kez yanlış şifre dene (limit 5)
        failed_attempts = 0
        for i in range(7):
            try:
                response = await self.session.post(
                    login_url,
                    json={
                        "username": "testuser",
                        "password": f"wrongpassword{i}"
                    }
                )
                
                if response.status == 429:  # Too Many Requests
                    self.log_result("Brute Force Protection", "PASS", f"Blocked after {i} attempts")
                    return
                elif response.status == 401:
                    failed_attempts += 1
                    
            except Exception as e:
                self.log_result("Brute Force Protection", "ERROR", str(e))
                return
        
        if failed_attempts >= 6:
            self.log_result("Brute Force Protection", "FAIL", "No blocking detected")
    
    async def test_input_validation(self):
        """Input validation testini çalıştır"""
        print("\n🔍 Testing Input Validation...")
        
        chat_url = f"{self.base_url}/chat"
        
        # Test cases for malicious input
        malicious_inputs = [
            "<script>alert('xss')</script>",  # XSS
            "A" * 2000,  # Çok uzun mesaj
            "",  # Boş mesaj
            "<iframe src='evil.com'></iframe>",  # iframe injection
        ]
        
        for i, malicious_input in enumerate(malicious_inputs):
            try:
                response = await self.session.post(
                    chat_url,
                    json={"message": malicious_input}
                )
                
                if response.status == 400:
                    self.log_result(f"Input Validation {i+1}", "PASS", "Rejected malicious input")
                elif response.status == 200:
                    # Response içeriğini kontrol et
                    text = await response.text()
                    if malicious_input in text and "<script>" in malicious_input:
                        self.log_result(f"Input Validation {i+1}", "FAIL", "XSS vulnerability detected")
                    else:
                        self.log_result(f"Input Validation {i+1}", "PASS", "Input sanitized")
                else:
                    self.log_result(f"Input Validation {i+1}", "WARN", f"Status: {response.status}")
                    
            except Exception as e:
                self.log_result(f"Input Validation {i+1}", "ERROR", str(e))
    
    async def test_authentication_security(self):
        """Authentication güvenliğini test et"""
        print("\n🔑 Testing Authentication Security...")
        
        # Test 1: Weak password rejection
        register_url = f"{self.base_url}/register"
        weak_passwords = ["123", "password", "12345678"]
        
        for password in weak_passwords:
            try:
                response = await self.session.post(
                    register_url,
                    json={
                        "username": f"testuser_{secrets.token_hex(4)}",
                        "email": f"test_{secrets.token_hex(4)}@example.com",
                        "password": password
                    }
                )
                
                if response.status == 400:
                    self.log_result("Weak Password Rejection", "PASS", f"Rejected: {password}")
                else:
                    self.log_result("Weak Password Rejection", "FAIL", f"Accepted: {password}")
                    
            except Exception as e:
                self.log_result("Weak Password Rejection", "ERROR", str(e))
    
    async def test_info_disclosure(self):
        """Bilgi sızıntısı testini çalıştır"""
        print("\n📄 Testing Information Disclosure...")
        
        # Test 1: Docs endpoint (production'da kapalı olmalı)
        docs_endpoints = ["/docs", "/redoc", "/openapi.json"]
        
        for endpoint in docs_endpoints:
            try:
                response = await self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status == 404:
                    self.log_result(f"Docs Endpoint {endpoint}", "PASS", "Not accessible")
                elif response.status == 200:
                    self.log_result(f"Docs Endpoint {endpoint}", "WARN", "Accessible (dev mode?)")
                else:
                    self.log_result(f"Docs Endpoint {endpoint}", "INFO", f"Status: {response.status}")
                    
            except Exception as e:
                self.log_result(f"Docs Endpoint {endpoint}", "ERROR", str(e))
    
    async def run_all_tests(self):
        """Tüm güvenlik testlerini çalıştır"""
        print("🔒 MEFAPEX Security Test Suite Starting...")
        print(f"Target: {self.base_url}")
        print("=" * 60)
        
        # Test suite
        test_methods = [
            self.test_cors_headers,
            self.test_security_headers,
            self.test_rate_limiting,
            self.test_brute_force_protection,
            self.test_input_validation,
            self.test_authentication_security,
            self.test_info_disclosure
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                print(f"❌ Test {test_method.__name__} failed: {e}")
        
        # Sonuçları özetle
        print("\n" + "=" * 60)
        print("🔒 SECURITY TEST SUMMARY")
        print("=" * 60)
        
        pass_count = sum(1 for r in self.results if r["status"] == "PASS")
        fail_count = sum(1 for r in self.results if r["status"] == "FAIL")
        warn_count = sum(1 for r in self.results if r["status"] == "WARN")
        error_count = sum(1 for r in self.results if r["status"] == "ERROR")
        
        print(f"✅ PASSED: {pass_count}")
        print(f"❌ FAILED: {fail_count}")
        print(f"⚠️  WARNINGS: {warn_count}")
        print(f"🔥 ERRORS: {error_count}")
        
        if fail_count == 0 and error_count == 0:
            print("\n🎉 SECURITY STATUS: GOOD")
        elif fail_count > 0:
            print("\n🚨 SECURITY STATUS: NEEDS ATTENTION")
        else:
            print("\n⚠️  SECURITY STATUS: CHECK WARNINGS")
        
        return self.results

async def main():
    """Ana test fonksiyonu"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MEFAPEX Security Test Suite")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to test")
    args = parser.parse_args()
    
    async with SecurityTester(args.url) as tester:
        results = await tester.run_all_tests()
        
        # JSON raporu oluştur
        with open("security_test_report.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Detailed report saved to: security_test_report.json")

if __name__ == "__main__":
    asyncio.run(main())
