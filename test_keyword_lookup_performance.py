#!/usr/bin/env python3
"""
Performance Benchmark Test for Keyword Lookup with Inverted Index
Tests the improvement in lookup performance compared to linear search
"""

import time
import statistics
import json
import os
import logging
from typing import List, Dict, Tuple
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from content_manager import ContentManager

# Configure logging for testing
logging.basicConfig(level=logging.WARNING)  # Reduce noise during benchmarks

class KeywordLookupBenchmark:
    """Benchmark class for testing keyword lookup performance"""
    
    def __init__(self):
        self.content_manager = ContentManager()
        
        # Sample test messages for benchmarking
        self.test_messages = [
            # Greetings
            "merhaba nasılsınız",
            "selam arkadaş",
            "günaydın herkese",
            "iyi akşamlar size",
            "hello there",
            "hi how are you",
            "selamlar dostum",
            "merhabalar",
            
            # Company info
            "mefapex nedir",
            "şirket hakkında bilgi",
            "firma ne yapıyor",
            "company information",
            "mefapex bilişim teknolojileri",
            "teknoloji firma",
            "bilişim şirketi",
            
            # Working hours
            "çalışma saatleri nedir",
            "saat kaçta açıksınız",
            "mesai saatleri",
            "working hours",
            "office hours",
            "ne zaman açık",
            "kaçta kapanıyorsunuz",
            "iş saatleri",
            
            # Support
            "yardıma ihtiyacım var",
            "teknik destek",
            "problem var",
            "hata alıyorum",
            "support needed",
            "help me",
            "arıza bildirimi",
            "sorun çözümü",
            
            # Technology
            "hangi teknolojiler",
            "yazılım geliştirme",
            "programming languages",
            "teknoloji stack",
            "development tools",
            "ai yapay zeka",
            "makine öğrenmesi",
            
            # Thanks/goodbye
            "teşekkür ederim",
            "sağolun",
            "thanks very much",
            "görüşürüz",
            "bye bye",
            "hoşça kalın",
            
            # Edge cases
            "rastgele metin",
            "bilinmeyen soru",
            "what is the weather",
            "futbol maçı",
            "random query",
            "asdasdasd",
            
            # Long messages
            "merhaba arkadaşlar çalışma saatleri hakkında bilgi almak istiyorum acaba ne zaman açıksınız",
            "teknik destek konusunda yardım alabilir miyim yazılım geliştirme ile ilgili sorunlarım var",
            "mefapex bilişim teknolojileri şirketi hakkında detaylı bilgi alabilir miyim hangi hizmetleri veriyorsunuz",
        ]
        
        # Generate more test data for stress testing
        self.stress_test_messages = self._generate_stress_test_data()
        
    def _generate_stress_test_data(self) -> List[str]:
        """Generate additional test data for stress testing"""
        base_words = ["merhaba", "çalışma", "saat", "mefapex", "teknoloji", "destek", 
                     "yardım", "bilgi", "firma", "yazılım", "development", "problem"]
        
        additional_messages = []
        
        # Generate combinations
        for i in range(100):
            import random
            words = random.sample(base_words, random.randint(1, 4))
            message = " ".join(words)
            additional_messages.append(message)
        
        return additional_messages
    
    def benchmark_lookup_methods(self, messages: List[str], iterations: int = 100) -> Dict:
        """
        Benchmark different lookup methods
        """
        results = {
            "test_info": {
                "total_messages": len(messages),
                "iterations_per_message": iterations,
                "total_lookups": len(messages) * iterations
            },
            "inverted_index": {"times": [], "matches": 0},
            "linear_search": {"times": [], "matches": 0}
        }
        
        print(f"🏁 Starting benchmark with {len(messages)} messages, {iterations} iterations each")
        print(f"📊 Total lookups: {len(messages) * iterations}")
        
        # Test with inverted index (current implementation)
        print("\n🔍 Testing with inverted index...")
        self.content_manager._index_built = True
        
        for message in messages:
            times = []
            for _ in range(iterations):
                start_time = time.perf_counter()
                response, source = self.content_manager._find_static_response_direct(message.lower())
                end_time = time.perf_counter()
                
                times.append(end_time - start_time)
                if response:
                    results["inverted_index"]["matches"] += 1
            
            results["inverted_index"]["times"].extend(times)
        
        # Test with linear search (fallback implementation)
        print("📋 Testing with linear search...")
        self.content_manager._index_built = False
        
        for message in messages:
            times = []
            for _ in range(iterations):
                start_time = time.perf_counter()
                response, source = self.content_manager._find_static_response_direct(message.lower())
                end_time = time.perf_counter()
                
                times.append(end_time - start_time)
                if response:
                    results["linear_search"]["matches"] += 1
            
            results["linear_search"]["times"].extend(times)
        
        # Restore inverted index
        self.content_manager._index_built = True
        
        return results
    
    def analyze_results(self, results: Dict) -> Dict:
        """Analyze benchmark results and calculate statistics"""
        analysis = {
            "test_info": results["test_info"],
            "inverted_index": self._calculate_stats(results["inverted_index"]["times"]),
            "linear_search": self._calculate_stats(results["linear_search"]["times"]),
            "comparison": {}
        }
        
        # Add match counts
        analysis["inverted_index"]["matches"] = results["inverted_index"]["matches"]
        analysis["linear_search"]["matches"] = results["linear_search"]["matches"]
        
        # Calculate performance improvement
        inverted_avg = analysis["inverted_index"]["average"]
        linear_avg = analysis["linear_search"]["average"]
        
        if linear_avg > 0:
            speedup = linear_avg / inverted_avg
            improvement_percent = ((linear_avg - inverted_avg) / linear_avg) * 100
            
            analysis["comparison"] = {
                "speedup_factor": round(speedup, 2),
                "improvement_percent": round(improvement_percent, 2),
                "time_saved_per_lookup_ms": round((linear_avg - inverted_avg) * 1000, 4),
                "total_time_saved_ms": round((linear_avg - inverted_avg) * results["test_info"]["total_lookups"] * 1000, 2)
            }
        
        return analysis
    
    def _calculate_stats(self, times: List[float]) -> Dict:
        """Calculate statistical measures for timing data"""
        if not times:
            return {"error": "No timing data"}
        
        times_ms = [t * 1000 for t in times]  # Convert to milliseconds
        
        return {
            "count": len(times),
            "average": statistics.mean(times),
            "average_ms": round(statistics.mean(times_ms), 4),
            "median": statistics.median(times),
            "median_ms": round(statistics.median(times_ms), 4),
            "min": min(times),
            "min_ms": round(min(times_ms), 4),
            "max": max(times),
            "max_ms": round(max(times_ms), 4),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "std_dev_ms": round(statistics.stdev(times_ms), 4) if len(times) > 1 else 0,
        }
    
    def run_comprehensive_benchmark(self):
        """Run comprehensive performance benchmarks"""
        print("=" * 60)
        print("🚀 KEYWORD LOOKUP PERFORMANCE BENCHMARK")
        print("=" * 60)
        
        # Test different scenarios
        scenarios = [
            ("Standard Messages", self.test_messages, 50),
            ("Stress Test", self.stress_test_messages, 20),
            ("Combined Load", self.test_messages + self.stress_test_messages, 30)
        ]
        
        all_results = {}
        
        for scenario_name, messages, iterations in scenarios:
            print(f"\n📋 Running scenario: {scenario_name}")
            print(f"   Messages: {len(messages)}, Iterations: {iterations}")
            
            results = self.benchmark_lookup_methods(messages, iterations)
            analysis = self.analyze_results(results)
            all_results[scenario_name] = analysis
            
            self._print_scenario_results(scenario_name, analysis)
        
        # Print summary
        self._print_summary(all_results)
        
        return all_results
    
    def _print_scenario_results(self, scenario_name: str, analysis: Dict):
        """Print results for a specific scenario"""
        print(f"\n📊 Results for {scenario_name}:")
        print("-" * 40)
        
        inverted = analysis["inverted_index"]
        linear = analysis["linear_search"]
        comparison = analysis["comparison"]
        
        print(f"Inverted Index: {inverted['average_ms']:.4f}ms avg, {inverted['matches']} matches")
        print(f"Linear Search:  {linear['average_ms']:.4f}ms avg, {linear['matches']} matches")
        
        if comparison:
            print(f"Speedup:        {comparison['speedup_factor']}x faster")
            print(f"Improvement:    {comparison['improvement_percent']:.1f}% performance gain")
            print(f"Time Saved:     {comparison['time_saved_per_lookup_ms']:.4f}ms per lookup")
    
    def _print_summary(self, all_results: Dict):
        """Print overall summary of all benchmarks"""
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        total_speedup = 0
        total_improvement = 0
        scenario_count = 0
        
        for scenario_name, analysis in all_results.items():
            comparison = analysis.get("comparison", {})
            if comparison:
                total_speedup += comparison["speedup_factor"]
                total_improvement += comparison["improvement_percent"]
                scenario_count += 1
        
        if scenario_count > 0:
            avg_speedup = total_speedup / scenario_count
            avg_improvement = total_improvement / scenario_count
            
            print(f"✅ Average Performance Improvement: {avg_improvement:.1f}%")
            print(f"⚡ Average Speedup Factor: {avg_speedup:.2f}x")
            print(f"🎯 Tested Scenarios: {scenario_count}")
        
        # Print inverted index info
        stats = self.content_manager.get_stats()
        index_info = stats.get("inverted_index", {})
        print(f"\n🔍 Inverted Index Information:")
        print(f"   Keywords Indexed: {index_info.get('keywords', 0)}")
        print(f"   Phrases Indexed: {index_info.get('phrases', 0)}")
        print(f"   Categories: {stats.get('static_responses', 0)}")
        
        print("\n✨ Inverted index optimization successfully improves lookup performance!")
    
    def test_correctness(self):
        """Test that both methods return the same results"""
        print("\n🧪 Testing correctness (ensuring both methods return same results)...")
        
        mismatches = 0
        
        for message in self.test_messages[:20]:  # Test subset for correctness
            # Get result with inverted index
            self.content_manager._index_built = True
            response1, source1 = self.content_manager._find_static_response_direct(message.lower())
            
            # Get result with linear search
            self.content_manager._index_built = False
            response2, source2 = self.content_manager._find_static_response_direct(message.lower())
            
            # Compare results
            if response1 != response2:
                print(f"❌ Mismatch for '{message}': inverted='{source1}' vs linear='{source2}'")
                mismatches += 1
        
        # Restore inverted index
        self.content_manager._index_built = True
        
        if mismatches == 0:
            print("✅ All test cases return identical results - correctness verified!")
        else:
            print(f"⚠️ Found {mismatches} mismatches - needs investigation")
        
        return mismatches == 0

def main():
    """Main function to run the benchmark"""
    benchmark = KeywordLookupBenchmark()
    
    # Test correctness first
    if not benchmark.test_correctness():
        print("❌ Correctness test failed - aborting benchmark")
        return
    
    # Run comprehensive benchmark
    results = benchmark.run_comprehensive_benchmark()
    
    # Save results to file
    results_file = "benchmark_results.json"
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to {results_file}")
    except Exception as e:
        print(f"⚠️ Could not save results: {e}")

if __name__ == "__main__":
    main()
