#!/usr/bin/env python3
"""
Comprehensive Test Suite for MEFAPEX Hybrid Relevance Detection System
======================================================================

This script demonstrates the hybrid approach for detecting irrelevant questions
and providing intelligent contextual responses.
"""

import asyncio
import time
import logging
from typing import List, Dict
from content_manager import ContentManager
from hybrid_relevance_detector import HybridRelevanceDetector, RelevanceLevel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class HybridSystemTester:
    """Comprehensive test suite for the hybrid relevance detection system"""
    
    def __init__(self):
        self.content_manager = ContentManager()
        self.relevance_detector = HybridRelevanceDetector("MEFAPEX Bilişim Teknolojileri")
        
    def test_categories(self) -> Dict:
        """
        Test different categories of questions
        """
        test_cases = {
            "clearly_relevant": [
                "MEFAPEX fabrikasında çalışma saatleri nedir?",
                "Yazılım geliştirme projeleri hakkında bilgi",
                "Teknik destek nasıl alabilirim?",
                "Güvenlik kuralları nelerdir?",
                "Personel izin başvurusu nasıl yapılır?",
                "Sistem entegrasyonu hizmetleri",
                "Üretim hattında kalite kontrol"
            ],
            "clearly_irrelevant": [
                "En iyi pizza tarifi nedir?",
                "Sevgilimle nasıl barışabilirim?",
                "Hangi film izlemeliyim bugün?",
                "Bugün hava durumu nasıl?",
                "Kilo vermek için ne yapmalıyım?",
                "Hangi müzik türü dinlemeliyim?",
                "Tatil için nereye gitsem?"
            ],
            "edge_cases": [
                "Bugün ne yapsam?",
                "Yardım eder misin?",
                "Nasılsın?",
                "Merhaba",
                "İş yerinde yemek nasıl?",
                "Çalışanlar için eğlence aktivitesi var mı?",
                "Şirkette spor salonu var mı?"
            ]
        }
        
        results = {}
        
        for category, messages in test_cases.items():
            print(f"\n🧪 Testing {category.upper().replace('_', ' ')}:")
            print("=" * 60)
            
            category_results = []
            
            for message in messages:
                start_time = time.time()
                response, source = self.content_manager.find_response(message)
                end_time = time.time()
                
                processing_time = (end_time - start_time) * 1000
                
                result = {
                    "message": message,
                    "source": source,
                    "processing_time_ms": processing_time,
                    "response_preview": response[:100] + "..." if len(response) > 100 else response
                }
                
                category_results.append(result)
                
                # Display result
                if source == "irrelevant":
                    emoji = "🚫"
                    status = "IRRELEVANT"
                elif source == "static":
                    emoji = "📋"
                    status = "STATIC"
                elif source.startswith("cache_"):
                    emoji = "⚡"
                    status = "CACHED"
                else:
                    emoji = "🤖"
                    status = "AI/DEFAULT"
                
                print(f"{emoji} {message}")
                print(f"   Status: {status} | Time: {processing_time:.1f}ms")
                print(f"   Preview: {result['response_preview']}")
                print()
            
            results[category] = category_results
        
        return results
    
    async def performance_analysis(self) -> Dict:
        """
        Analyze performance of different detection methods
        """
        print("\n⚡ PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        # Test performance with different types of questions
        performance_tests = [
            ("Keyword Filter Fast", "MEFAPEX yazılım geliştirme"),
            ("Pattern Match Fast", "pizza tarifi ver"),
            ("Domain Analysis", "fabrika üretim süreci"),
            ("Semantic Analysis", "iş yerinde motivasyon"),
            ("AI Classification", "gelecek planları nasıl olmalı")
        ]
        
        results = {}
        
        for test_name, message in performance_tests:
            times = []
            
            # Run multiple times for average
            for _ in range(5):
                start_time = time.time()
                result = await self.relevance_detector.classify(message)
                end_time = time.time()
                times.append((end_time - start_time) * 1000)
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            results[test_name] = {
                "message": message,
                "avg_time_ms": avg_time,
                "min_time_ms": min_time,
                "max_time_ms": max_time,
                "method": result.method.value,
                "confidence": result.confidence
            }
            
            print(f"📊 {test_name}:")
            print(f"   Message: {message}")
            print(f"   Average: {avg_time:.1f}ms | Min: {min_time:.1f}ms | Max: {max_time:.1f}ms")
            print(f"   Method: {result.method.value} | Confidence: {result.confidence:.3f}")
            print()
        
        return results
    
    def accuracy_test(self) -> Dict:
        """
        Test accuracy of relevance detection
        """
        print("\n🎯 ACCURACY TEST")
        print("=" * 60)
        
        # Ground truth test cases
        test_cases = [
            # (message, expected_relevant, description)
            ("MEFAPEX hizmetleri nelerdir?", True, "Company services"),
            ("Yazılım projesi fiyatları", True, "Software pricing"),
            ("Pizza tarifi istiyorum", False, "Cooking recipe"),
            ("Sevgili bulma tavsiyeleri", False, "Dating advice"),
            ("Film önerisi ver", False, "Movie recommendation"),
            ("Teknik destek gerekiyor", True, "Technical support"),
            ("Fabrika güvenlik kuralları", True, "Safety rules"),
            ("Bugün ne pişirsem", False, "Cooking question"),
            ("Çalışma saatleri", True, "Work hours"),
            ("Hava durumu", False, "Weather")
        ]
        
        correct_predictions = 0
        total_predictions = len(test_cases)
        detailed_results = []
        
        for message, expected_relevant, description in test_cases:
            response, source = self.content_manager.find_response(message)
            
            # Determine if system classified as relevant
            predicted_relevant = source != "irrelevant"
            
            is_correct = predicted_relevant == expected_relevant
            if is_correct:
                correct_predictions += 1
            
            result = {
                "message": message,
                "description": description,
                "expected": "Relevant" if expected_relevant else "Irrelevant",
                "predicted": "Relevant" if predicted_relevant else "Irrelevant",
                "source": source,
                "correct": is_correct
            }
            
            detailed_results.append(result)
            
            # Display result
            status_emoji = "✅" if is_correct else "❌"
            expected_emoji = "✅" if expected_relevant else "❌"
            predicted_emoji = "✅" if predicted_relevant else "❌"
            
            print(f"{status_emoji} {message}")
            print(f"   Expected: {expected_emoji} | Predicted: {predicted_emoji} | Source: {source}")
            print(f"   Description: {description}")
            print()
        
        accuracy = correct_predictions / total_predictions
        
        print(f"📊 ACCURACY SUMMARY:")
        print(f"   Correct: {correct_predictions}/{total_predictions}")
        print(f"   Accuracy: {accuracy:.1%}")
        
        return {
            "accuracy": accuracy,
            "correct_predictions": correct_predictions,
            "total_predictions": total_predictions,
            "detailed_results": detailed_results
        }
    
    def response_quality_test(self) -> Dict:
        """
        Test quality of generated responses for irrelevant questions
        """
        print("\n💬 RESPONSE QUALITY TEST")
        print("=" * 60)
        
        irrelevant_questions = [
            "En iyi pizza tarifi nedir?",
            "Sevgilimle nasıl barışabilirim?", 
            "Hangi film izlemeliyim?",
            "Bugün hava durumu nasıl?",
            "Kilo vermek için tavsiye",
            "Tatil planı yapıyorum yardım et"
        ]
        
        quality_results = []
        
        for question in irrelevant_questions:
            response, source = self.content_manager.find_response(question)
            
            # Analyze response quality
            quality_metrics = {
                "has_mefapex_branding": "MEFAPEX" in response,
                "has_helpful_alternatives": any(alt in response.lower() for alt in 
                                              ["yardımcı olabilirim", "help you with", "instead"]),
                "appropriate_tone": any(tone in response for tone in ["😊", "🤖", "💼"]),
                "provides_redirect": "iş" in response.lower() or "work" in response.lower(),
                "response_length": len(response),
                "is_contextual": source == "irrelevant"
            }
            
            quality_score = sum([
                quality_metrics["has_mefapex_branding"],
                quality_metrics["has_helpful_alternatives"], 
                quality_metrics["appropriate_tone"],
                quality_metrics["provides_redirect"],
                quality_metrics["response_length"] > 100,
                quality_metrics["is_contextual"]
            ]) / 6
            
            result = {
                "question": question,
                "source": source,
                "quality_score": quality_score,
                "metrics": quality_metrics,
                "response_preview": response[:200] + "..." if len(response) > 200 else response
            }
            
            quality_results.append(result)
            
            # Display result
            stars = "⭐" * int(quality_score * 5)
            print(f"❓ {question}")
            print(f"   Quality: {stars} ({quality_score:.1%})")
            print(f"   Source: {source}")
            print(f"   Preview: {result['response_preview']}")
            print()
        
        avg_quality = sum(r["quality_score"] for r in quality_results) / len(quality_results)
        
        print(f"📊 QUALITY SUMMARY:")
        print(f"   Average Quality: {'⭐' * int(avg_quality * 5)} ({avg_quality:.1%})")
        
        return {
            "average_quality": avg_quality,
            "detailed_results": quality_results
        }
    
    def integration_test(self) -> Dict:
        """
        Test integration between components
        """
        print("\n🔧 INTEGRATION TEST")
        print("=" * 60)
        
        # Test content manager stats
        stats = self.content_manager.get_stats()
        
        print("📊 Content Manager Stats:")
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for subkey, subvalue in value.items():
                    print(f"     {subkey}: {subvalue}")
            else:
                print(f"   {key}: {value}")
        
        return stats

async def main():
    """Run comprehensive test suite"""
    print("🧪 MEFAPEX Hybrid Relevance Detection System")
    print("=" * 80)
    print("Testing hybrid approach for detecting irrelevant questions")
    print("and providing intelligent contextual responses.")
    print("=" * 80)
    
    tester = HybridSystemTester()
    
    # Run all tests
    test_results = {}
    
    print("\n🚀 Starting comprehensive test suite...")
    
    # 1. Category tests
    test_results["categories"] = tester.test_categories()
    
    # 2. Performance analysis
    test_results["performance"] = await tester.performance_analysis()
    
    # 3. Accuracy test
    test_results["accuracy"] = tester.accuracy_test()
    
    # 4. Response quality test
    test_results["quality"] = tester.response_quality_test()
    
    # 5. Integration test
    test_results["integration"] = tester.integration_test()
    
    # Summary
    print("\n🎉 TEST SUITE COMPLETED")
    print("=" * 80)
    
    accuracy = test_results["accuracy"]["accuracy"]
    quality = test_results["quality"]["average_quality"]
    avg_performance = sum(p["avg_time_ms"] for p in test_results["performance"].values()) / len(test_results["performance"])
    
    print(f"📊 OVERALL RESULTS:")
    print(f"   Accuracy: {accuracy:.1%}")
    print(f"   Response Quality: {'⭐' * int(quality * 5)} ({quality:.1%})")
    print(f"   Average Performance: {avg_performance:.1f}ms")
    
    # Final grade
    overall_score = (accuracy + quality) / 2
    if overall_score >= 0.9:
        grade = "🏆 EXCELLENT"
    elif overall_score >= 0.8:
        grade = "🥇 VERY GOOD"
    elif overall_score >= 0.7:
        grade = "🥈 GOOD"
    elif overall_score >= 0.6:
        grade = "🥉 FAIR"
    else:
        grade = "❌ NEEDS IMPROVEMENT"
    
    print(f"   Overall Grade: {grade} ({overall_score:.1%})")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(main())
