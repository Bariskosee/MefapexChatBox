#!/usr/bin/env python3
"""
🇹🇷 MEFAPEX Turkish AI Model Performance Comparison
==================================================
Bu script farklı Türkçe AI modellerinin performansını karşılaştırır.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_model_performance(model_name: str, test_texts: List[str]) -> Dict[str, Any]:
    """Test a specific model's performance"""
    logger.info(f"🧪 Testing model: {model_name}")
    
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        start_time = time.time()
        
        # Load model
        model = SentenceTransformer(model_name)
        load_time = time.time() - start_time
        
        # Test embeddings
        embedding_times = []
        embeddings = []
        
        for text in test_texts:
            embed_start = time.time()
            embedding = model.encode([text])
            embed_time = time.time() - embed_start
            embedding_times.append(embed_time)
            embeddings.append(embedding)
        
        # Calculate stats
        avg_embedding_time = sum(embedding_times) / len(embedding_times)
        total_test_time = sum(embedding_times)
        
        # Memory usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
        except ImportError:
            memory_mb = "N/A"
        
        # Model size estimation
        try:
            param_count = sum(p.numel() for p in model.parameters())
            model_size_mb = param_count * 4 / (1024 * 1024)  # Rough estimation
        except:
            model_size_mb = "N/A"
        
        # Clean up
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return {
            "model_name": model_name,
            "load_time_seconds": round(load_time, 3),
            "avg_embedding_time_seconds": round(avg_embedding_time, 3),
            "total_test_time_seconds": round(total_test_time, 3),
            "memory_usage_mb": round(memory_mb, 2) if isinstance(memory_mb, (int, float)) else memory_mb,
            "estimated_model_size_mb": round(model_size_mb, 2) if isinstance(model_size_mb, (int, float)) else model_size_mb,
            "embedding_dimension": len(embeddings[0][0]) if embeddings else "N/A",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ Error testing {model_name}: {e}")
        return {
            "model_name": model_name,
            "status": "failed",
            "error": str(e)
        }

def compare_turkish_models():
    """Compare different Turkish and multilingual models"""
    logger.info("🇹🇷 Türkçe AI Model Performans Karşılaştırması Başlatılıyor...")
    
    # Test texts in Turkish
    test_texts = [
        "Fabrika çalışma saatleri nelerdir?",
        "İzin başvurusu nasıl yapılır?",
        "Güvenlik kuralları hakkında bilgi verir misiniz?",
        "Merhaba, nasıl yardımcı olabilirim?",
        "Vardiya değişiklikleri nasıl yapılır?",
        "Yemek molası ne zaman başlıyor?",
        "Acil durumlarda kimi aramam gerekiyor?",
        "Personel giriş çıkış saatleri nedir?",
        "Teknik destek için hangi numarayı aramalıyım?",
        "Proje yönetimi konusunda bilgi alabilir miyim?"
    ]
    
    # Models to test
    models_to_test = [
        # Turkish optimized models
        "emrecan/bert-base-turkish-cased-mean-nli-stsb-tr",
        
        # Multilingual models
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "sentence-transformers/LaBSE",
        
        # Smaller multilingual models
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        
        # English fallback (for comparison)
        "all-MiniLM-L6-v2",
        "all-mpnet-base-v2"
    ]
    
    results = []
    
    for model_name in models_to_test:
        logger.info(f"🔄 Testing: {model_name}")
        result = test_model_performance(model_name, test_texts)
        results.append(result)
        
        if result["status"] == "success":
            logger.info(f"✅ {model_name}: "
                       f"Load: {result['load_time_seconds']}s, "
                       f"Avg Embed: {result['avg_embedding_time_seconds']}s, "
                       f"Memory: {result['memory_usage_mb']}MB")
        else:
            logger.error(f"❌ {model_name}: {result.get('error', 'Unknown error')}")
        
        # Add delay between models to allow memory cleanup
        time.sleep(2)
    
    return results

def generate_report(results: List[Dict[str, Any]]):
    """Generate a detailed performance report"""
    logger.info("📊 Rapor oluşturuluyor...")
    
    # Filter successful results
    successful_results = [r for r in results if r["status"] == "success"]
    failed_results = [r for r in results if r["status"] == "failed"]
    
    # Sort by average embedding time
    successful_results.sort(key=lambda x: x["avg_embedding_time_seconds"])
    
    # Generate report
    report = {
        "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_models_tested": len(results),
        "successful_tests": len(successful_results),
        "failed_tests": len(failed_results),
        "results": results,
        "summary": {
            "fastest_model": successful_results[0]["model_name"] if successful_results else None,
            "slowest_model": successful_results[-1]["model_name"] if successful_results else None,
            "lowest_memory": min(successful_results, key=lambda x: x["memory_usage_mb"] if isinstance(x["memory_usage_mb"], (int, float)) else float('inf'))["model_name"] if successful_results else None,
            "highest_memory": max(successful_results, key=lambda x: x["memory_usage_mb"] if isinstance(x["memory_usage_mb"], (int, float)) else 0)["model_name"] if successful_results else None
        },
        "recommendations": []
    }
    
    # Add recommendations
    if successful_results:
        fastest = successful_results[0]
        report["recommendations"].append({
            "category": "En Hızlı",
            "model": fastest["model_name"],
            "reason": f"En düşük embedding süresi: {fastest['avg_embedding_time_seconds']}s"
        })
        
        # Find Turkish-specific model
        turkish_models = [r for r in successful_results if "turkish" in r["model_name"].lower()]
        if turkish_models:
            best_turkish = turkish_models[0]
            report["recommendations"].append({
                "category": "Türkçe Optimize",
                "model": best_turkish["model_name"],
                "reason": "Türkçe diline özel olarak eğitilmiş"
            })
        
        # Find balanced model
        for result in successful_results:
            if (isinstance(result["memory_usage_mb"], (int, float)) and 
                result["memory_usage_mb"] < 2000 and 
                result["avg_embedding_time_seconds"] < 0.1):
                report["recommendations"].append({
                    "category": "Dengeli Performans",
                    "model": result["model_name"],
                    "reason": f"İyi hız ({result['avg_embedding_time_seconds']}s) ve düşük bellek ({result['memory_usage_mb']}MB)"
                })
                break
    
    # Save report
    report_file = Path("turkish_model_performance_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📄 Detaylı rapor kaydedildi: {report_file}")
    
    return report

def print_summary(report: Dict[str, Any]):
    """Print a summary of the performance test"""
    print("\n" + "="*70)
    print("🇹🇷 TÜRKÇE AI MODEL PERFORMANS RAPORU")
    print("="*70)
    
    print(f"📅 Test Tarihi: {report['test_timestamp']}")
    print(f"🧪 Test Edilen Model Sayısı: {report['total_models_tested']}")
    print(f"✅ Başarılı Testler: {report['successful_tests']}")
    print(f"❌ Başarısız Testler: {report['failed_tests']}")
    
    print("\n📊 BAŞARILI MODELLER (Hız Sıralaması):")
    print("-" * 70)
    
    successful_results = [r for r in report["results"] if r["status"] == "success"]
    
    for i, result in enumerate(successful_results, 1):
        print(f"{i}. {result['model_name']}")
        print(f"   ⏱️  Yükleme: {result['load_time_seconds']}s | Embedding: {result['avg_embedding_time_seconds']}s")
        print(f"   💾 Bellek: {result['memory_usage_mb']}MB | Boyut: {result['embedding_dimension']}D")
        print()
    
    if report["recommendations"]:
        print("🎯 ÖNERİLER:")
        print("-" * 70)
        for rec in report["recommendations"]:
            print(f"🏆 {rec['category']}: {rec['model']}")
            print(f"   📝 {rec['reason']}")
            print()
    
    if len(successful_results) > 0:
        print("💡 SONUÇ:")
        print("-" * 70)
        print("Türkçe dil desteği için en iyi seçenekler:")
        
        # Find best Turkish model
        turkish_models = [r for r in successful_results if "turkish" in r["model_name"].lower()]
        if turkish_models:
            print(f"1. 🇹🇷 Türkçe Optimize: {turkish_models[0]['model_name']}")
        
        # Find best multilingual
        multilingual = [r for r in successful_results if "multilingual" in r["model_name"].lower()]
        if multilingual:
            print(f"2. 🌍 Çok Dilli: {multilingual[0]['model_name']}")
        
        # Fastest overall
        print(f"3. ⚡ En Hızlı: {successful_results[0]['model_name']}")
        
        print("\n🔧 Konfigürasyon önerisi:")
        print(f"TURKISH_SENTENCE_MODEL={turkish_models[0]['model_name'] if turkish_models else successful_results[0]['model_name']}")
        print(f"AI_PREFER_TURKISH_MODELS=true")
        print(f"AI_LANGUAGE_DETECTION=true")

def main():
    """Main function"""
    logger.info("🚀 Türkçe AI Model Performans Testi Başlatılıyor...")
    
    try:
        # Run comparison
        results = compare_turkish_models()
        
        # Generate report
        report = generate_report(results)
        
        # Print summary
        print_summary(report)
        
        logger.info("✅ Performans testi tamamlandı!")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Test kullanıcı tarafından iptal edildi")
    except Exception as e:
        logger.error(f"❌ Test sırasında hata: {e}")
        raise

if __name__ == "__main__":
    main()
