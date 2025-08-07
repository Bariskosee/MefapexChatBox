#!/usr/bin/env python3
"""
Performance monitoring script for MEFAPEX AI Assistant
Monitors system resources, cache performance, and response times
"""

import asyncio
import aiohttp
import psutil
import time
import json
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Comprehensive performance monitoring for MEFAPEX AI Assistant
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.metrics_history = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_system_health(self) -> Dict:
        """Check overall system health"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "unhealthy", "status_code": response.status}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_system_status(self) -> Dict:
        """Get detailed system status"""
        try:
            async with self.session.get(f"{self.base_url}/system/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status code: {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_cache_performance(self) -> Dict:
        """Get cache performance metrics"""
        try:
            async with self.session.get(f"{self.base_url}/performance/cache") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status code: {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_database_performance(self) -> Dict:
        """Get database performance metrics"""
        try:
            async with self.session.get(f"{self.base_url}/performance/database") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status code: {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_websocket_performance(self) -> Dict:
        """Get WebSocket performance metrics"""
        try:
            async with self.session.get(f"{self.base_url}/performance/websockets") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status code: {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def test_chat_response_time(self, message: str = "Hello") -> Dict:
        """Test chat response time"""
        start_time = time.time()
        
        try:
            payload = {"message": message}
            async with self.session.post(f"{self.base_url}/chat", json=payload) as response:
                end_time = time.time()
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "response_time_ms": round((end_time - start_time) * 1000, 2),
                        "source": result.get("source", "unknown"),
                        "response_length": len(result.get("response", ""))
                    }
                else:
                    return {
                        "success": False,
                        "response_time_ms": round((end_time - start_time) * 1000, 2),
                        "status_code": response.status
                    }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "response_time_ms": round((end_time - start_time) * 1000, 2),
                "error": str(e)
            }
    
    def get_system_resources(self) -> Dict:
        """Get current system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "used_gb": round(memory_used_gb, 2),
                    "total_gb": round(memory_total_gb, 2),
                    "percent": memory_percent
                },
                "disk": {
                    "used_gb": round(disk_used_gb, 2),
                    "total_gb": round(disk_total_gb, 2),
                    "percent": round(disk_percent, 2)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def run_comprehensive_check(self) -> Dict:
        """Run comprehensive performance check"""
        timestamp = datetime.utcnow().isoformat()
        
        # Gather all metrics
        results = {
            "timestamp": timestamp,
            "system_resources": self.get_system_resources(),
            "health_check": await self.check_system_health(),
            "system_status": await self.get_system_status(),
            "cache_performance": await self.get_cache_performance(),
            "database_performance": await self.get_database_performance(),
            "websocket_performance": await self.get_websocket_performance(),
            "response_time_test": await self.test_chat_response_time()
        }
        
        # Store in history
        self.metrics_history.append(results)
        
        # Keep only last 100 measurements
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return results
    
    async def run_load_test(self, num_requests: int = 10, concurrent: int = 3) -> Dict:
        """Run basic load test"""
        logger.info(f"Starting load test: {num_requests} requests, {concurrent} concurrent")
        
        start_time = time.time()
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrent)
        
        async def single_request(request_id: int):
            async with semaphore:
                return await self.test_chat_response_time(f"Test message {request_id}")
        
        # Run concurrent requests
        tasks = [single_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_requests = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
        
        response_times = [r["response_time_ms"] for r in successful_requests]
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "total_time_seconds": round(end_time - start_time, 2),
            "requests_per_second": round(num_requests / (end_time - start_time), 2),
            "response_times": {
                "min_ms": min(response_times) if response_times else 0,
                "max_ms": max(response_times) if response_times else 0,
                "avg_ms": round(sum(response_times) / len(response_times), 2) if response_times else 0
            },
            "failures": failed_requests[:5]  # First 5 failures for debugging
        }
    
    def print_summary(self, results: Dict):
        """Print formatted performance summary"""
        print("\n" + "="*60)
        print("🔍 MEFAPEX AI ASSISTANT PERFORMANCE REPORT")
        print("="*60)
        print(f"⏰ Timestamp: {results['timestamp']}")
        
        # System Resources
        if "system_resources" in results:
            sys_res = results["system_resources"]
            print(f"\n💻 SYSTEM RESOURCES:")
            print(f"   CPU: {sys_res.get('cpu', {}).get('percent', 'N/A')}% ({sys_res.get('cpu', {}).get('count', 'N/A')} cores)")
            print(f"   Memory: {sys_res.get('memory', {}).get('percent', 'N/A')}% ({sys_res.get('memory', {}).get('used_gb', 'N/A')}/{sys_res.get('memory', {}).get('total_gb', 'N/A')} GB)")
            print(f"   Disk: {sys_res.get('disk', {}).get('percent', 'N/A')}% ({sys_res.get('disk', {}).get('used_gb', 'N/A')}/{sys_res.get('disk', {}).get('total_gb', 'N/A')} GB)")
        
        # Health Check
        health = results.get("health_check", {})
        status = health.get("status", "unknown")
        print(f"\n❤️  HEALTH STATUS: {status.upper()}")
        
        # Cache Performance
        if "cache_performance" in results:
            cache = results["cache_performance"].get("response_cache", {})
            print(f"\n🗄️  CACHE PERFORMANCE:")
            print(f"   Hit Rate: {cache.get('hit_rate', 'N/A')}%")
            print(f"   Size: {cache.get('size', 'N/A')}/{cache.get('max_size', 'N/A')} entries")
            print(f"   Memory: {cache.get('memory_usage_mb', 'N/A')} MB")
        
        # Response Time
        if "response_time_test" in results:
            rt = results["response_time_test"]
            print(f"\n⚡ RESPONSE TIME:")
            print(f"   Test: {'✅ PASS' if rt.get('success') else '❌ FAIL'}")
            print(f"   Time: {rt.get('response_time_ms', 'N/A')} ms")
            print(f"   Source: {rt.get('source', 'N/A')}")
        
        # Database
        if "database_performance" in results:
            db = results["database_performance"]
            print(f"\n🗃️  DATABASE:")
            print(f"   Users: {db.get('users', 'N/A')}")
            print(f"   Messages: {db.get('messages', 'N/A')}")
            print(f"   Active Connections: {db.get('pool_active_connections', 'N/A')}/{db.get('pool_max_connections', 'N/A')}")
        
        # WebSocket
        if "websocket_performance" in results:
            ws = results["websocket_performance"]
            print(f"\n🔌 WEBSOCKETS:")
            print(f"   Active Connections: {ws.get('total_connections', 'N/A')}")
            print(f"   Active Users: {ws.get('active_users', 'N/A')}")
            print(f"   Messages Sent: {ws.get('messages_sent', 'N/A')}")
        
        print("\n" + "="*60)

async def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MEFAPEX AI Assistant Performance Monitor")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--load-test", action="store_true", help="Run load test")
    parser.add_argument("--requests", type=int, default=10, help="Number of requests for load test")
    parser.add_argument("--concurrent", type=int, default=3, help="Concurrent requests for load test")
    parser.add_argument("--continuous", action="store_true", help="Continuous monitoring (every 30 seconds)")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    async with PerformanceMonitor(args.url) as monitor:
        if args.load_test:
            print(f"🚀 Running load test: {args.requests} requests, {args.concurrent} concurrent")
            load_results = await monitor.run_load_test(args.requests, args.concurrent)
            print("\n📊 LOAD TEST RESULTS:")
            print(json.dumps(load_results, indent=2))
        
        elif args.continuous:
            print("🔄 Starting continuous monitoring (Ctrl+C to stop)")
            try:
                while True:
                    results = await monitor.run_comprehensive_check()
                    monitor.print_summary(results)
                    
                    if args.output:
                        with open(args.output, 'w') as f:
                            json.dump(monitor.metrics_history, f, indent=2)
                    
                    await asyncio.sleep(30)  # Wait 30 seconds
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
        
        else:
            # Single comprehensive check
            results = await monitor.run_comprehensive_check()
            monitor.print_summary(results)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n💾 Results saved to {args.output}")

if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("❌ psutil not installed. Run: pip install psutil")
        exit(1)
    
    try:
        import aiohttp
    except ImportError:
        print("❌ aiohttp not installed. Run: pip install aiohttp")
        exit(1)
    
    asyncio.run(main())
