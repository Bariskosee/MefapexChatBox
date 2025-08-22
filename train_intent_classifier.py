#!/usr/bin/env python3
"""
Intent Classifier Training Script
=================================

Script to train, evaluate, and manage the intent classification model for MEFAPEX Chatbot.

Usage:
    python train_intent_classifier.py [OPTIONS]

Options:
    --train         Train a new model
    --retrain       Force retrain existing model
    --test          Test model with sample queries
    --evaluate      Detailed model evaluation
    --info          Show model information
    --install-deps  Install required dependencies
"""

import os
import sys
import argparse
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def install_dependencies():
    """Install required machine learning dependencies"""
    logger.info("📦 Installing required dependencies...")
    
    try:
        import subprocess
        
        # List of required packages
        packages = [
            'scikit-learn>=1.0.0',
            'numpy>=1.21.0',
            'joblib>=1.1.0'
        ]
        
        for package in packages:
            logger.info(f"Installing {package}...")
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', package
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ {package} installed successfully")
            else:
                logger.error(f"❌ Failed to install {package}: {result.stderr}")
                return False
        
        logger.info("✅ All dependencies installed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Dependency installation failed: {e}")
        return False

def check_dependencies() -> bool:
    """Check if required dependencies are available"""
    try:
        import sklearn
        import numpy
        import joblib
        logger.info("✅ All dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {e}")
        logger.info("💡 Run with --install-deps to install required packages")
        return False

def train_model(retrain: bool = False):
    """Train the intent classification model"""
    logger.info("🔄 Starting model training...")
    
    try:
        from intent_classifier import intent_classifier
        
        success = intent_classifier.train_model(retrain=retrain)
        
        if success:
            logger.info("✅ Model training completed successfully!")
            
            # Show model info
            info = intent_classifier.get_model_info()
            logger.info(f"📊 Model Info:")
            logger.info(f"   Categories: {info.get('num_categories', 0)}")
            logger.info(f"   Vocabulary Size: {info.get('vocabulary_size', 0)}")
            logger.info(f"   Confidence Threshold: {info.get('confidence_threshold', 0.3)}")
            
        else:
            logger.error("❌ Model training failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Training error: {e}")
        return False
    
    return True

def test_model():
    """Test model with sample queries"""
    logger.info("🧪 Testing model with sample queries...")
    
    try:
        from intent_classifier import intent_classifier
        
        if not intent_classifier.is_trained:
            logger.error("❌ Model not trained! Run --train first.")
            return False
        
        # Test queries for each category
        test_queries = [
            # Greetings
            "merhaba nasılsınız",
            "selam arkadaş",
            "günaydın efendim",
            "hello there",
            
            # Company info
            "mefapex ne yapıyor",
            "şirketiniz hakkında bilgi",
            "firma olarak neler sunuyorsunuz",
            "company information",
            
            # Working hours
            "çalışma saatleri nedir",
            "kaçta açıyorsunuz",
            "mesai saatleri",
            "working hours",
            
            # Support types
            "yardıma ihtiyacım var",
            "teknik destek",
            "problem yaşıyorum",
            "help me please",
            
            # Technology info
            "hangi teknolojileri kullanıyorsunuz",
            "yazılım geliştirme",
            "programming languages",
            "development services",
            
            # Thanks/goodbye
            "teşekkür ederim",
            "sağolun",
            "goodbye",
            "thanks a lot",
            
            # Unknown/irrelevant
            "hava durumu nasıl",
            "futbol maçı",
            "random text here",
            "completely unrelated query"
        ]
        
        results = intent_classifier.test_predictions(test_queries)
        
        # Group results by predicted intent
        intent_groups = {}
        for query, result in results.items():
            intent = result['predicted_intent']
            if intent not in intent_groups:
                intent_groups[intent] = []
            intent_groups[intent].append((query, result))
        
        # Display results
        logger.info("\n📋 Test Results by Intent:")
        logger.info("=" * 60)
        
        for intent, queries in intent_groups.items():
            logger.info(f"\n🎯 Intent: {intent.upper()}")
            logger.info("-" * 40)
            
            for query, result in queries:
                confidence = result['confidence']
                status = "✅" if confidence > 0.3 else "⚠️"
                logger.info(f"{status} \"{query}\" -> {confidence:.3f}")
        
        # Summary statistics
        total_queries = len(results)
        confident_predictions = sum(1 for r in results.values() if r['confidence'] > 0.3)
        success_rate = (confident_predictions / total_queries) * 100
        
        logger.info(f"\n📊 Summary:")
        logger.info(f"   Total queries: {total_queries}")
        logger.info(f"   Confident predictions: {confident_predictions}")
        logger.info(f"   Success rate: {success_rate:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Testing error: {e}")
        return False

def evaluate_model():
    """Detailed model evaluation"""
    logger.info("📈 Performing detailed model evaluation...")
    
    try:
        from intent_classifier import intent_classifier
        
        if not intent_classifier.is_trained:
            logger.error("❌ Model not trained! Run --train first.")
            return False
        
        # Model info
        info = intent_classifier.get_model_info()
        
        logger.info("\n🔍 Model Information:")
        logger.info("=" * 50)
        for key, value in info.items():
            logger.info(f"   {key}: {value}")
        
        # Test with comprehensive dataset
        comprehensive_tests = {
            "greetings": [
                "merhaba", "selam", "günaydın", "iyi akşamlar", "nasılsın",
                "hello", "hi", "good morning", "hey there"
            ],
            "company_info": [
                "mefapex nedir", "şirket hakkında", "firma bilgisi", "ne yapıyorsunuz",
                "company info", "about your business", "what do you do"
            ],
            "working_hours": [
                "çalışma saatleri", "kaçta açık", "mesai saati", "ne zaman müsait",
                "working hours", "business hours", "when open"
            ],
            "support_types": [
                "yardım", "destek", "problem", "sorun", "teknik yardım",
                "help", "support", "assistance", "technical help"
            ],
            "technology_info": [
                "teknoloji", "yazılım", "programming", "development", "kod",
                "software", "technology stack", "programming languages"
            ],
            "thanks_goodbye": [
                "teşekkür", "sağol", "görüşürüz", "hoşça kal",
                "thanks", "thank you", "goodbye", "see you"
            ]
        }
        
        category_scores = {}
        
        for expected_category, queries in comprehensive_tests.items():
            correct = 0
            total = len(queries)
            
            for query in queries:
                prediction = intent_classifier.predict_intent(query)
                if prediction and prediction.intent == expected_category:
                    correct += 1
            
            accuracy = (correct / total) * 100
            category_scores[expected_category] = {
                'correct': correct,
                'total': total,
                'accuracy': accuracy
            }
        
        logger.info("\n📊 Category-wise Accuracy:")
        logger.info("=" * 50)
        
        overall_correct = 0
        overall_total = 0
        
        for category, scores in category_scores.items():
            correct = scores['correct']
            total = scores['total']
            accuracy = scores['accuracy']
            
            status = "✅" if accuracy >= 70 else "⚠️" if accuracy >= 50 else "❌"
            logger.info(f"{status} {category}: {correct}/{total} ({accuracy:.1f}%)")
            
            overall_correct += correct
            overall_total += total
        
        overall_accuracy = (overall_correct / overall_total) * 100
        
        logger.info(f"\n🎯 Overall Accuracy: {overall_correct}/{overall_total} ({overall_accuracy:.1f}%)")
        
        # Performance recommendations
        logger.info(f"\n💡 Performance Analysis:")
        if overall_accuracy >= 80:
            logger.info("✅ Excellent performance! Model is working well.")
        elif overall_accuracy >= 70:
            logger.info("👍 Good performance. Consider fine-tuning for better results.")
        elif overall_accuracy >= 60:
            logger.info("⚠️ Moderate performance. May need more training data or feature engineering.")
        else:
            logger.info("❌ Poor performance. Consider retraining with more diverse data.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Evaluation error: {e}")
        return False

def show_model_info():
    """Show model information"""
    logger.info("ℹ️ Model Information:")
    
    try:
        from intent_classifier import intent_classifier
        
        info = intent_classifier.get_model_info()
        
        logger.info("\n📋 Current Model Status:")
        logger.info("=" * 40)
        for key, value in info.items():
            logger.info(f"   {key}: {value}")
        
        if intent_classifier.is_trained:
            logger.info(f"\n✅ Model is trained and ready!")
        else:
            logger.info(f"\n❌ Model is not trained. Run --train to train the model.")
            
    except Exception as e:
        logger.error(f"❌ Error getting model info: {e}")

def main():
    """Main script function"""
    parser = argparse.ArgumentParser(
        description="Intent Classifier Training and Management Script"
    )
    
    parser.add_argument('--train', action='store_true',
                       help='Train a new model')
    parser.add_argument('--retrain', action='store_true',
                       help='Force retrain existing model')
    parser.add_argument('--test', action='store_true',
                       help='Test model with sample queries')
    parser.add_argument('--evaluate', action='store_true',
                       help='Detailed model evaluation')
    parser.add_argument('--info', action='store_true',
                       help='Show model information')
    parser.add_argument('--install-deps', action='store_true',
                       help='Install required dependencies')
    
    args = parser.parse_args()
    
    # Show help if no arguments
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    logger.info("🤖 MEFAPEX Intent Classifier Training Script")
    logger.info("=" * 50)
    
    # Install dependencies
    if args.install_deps:
        if install_dependencies():
            logger.info("✅ Dependencies installed. You can now train the model.")
        else:
            logger.error("❌ Failed to install dependencies.")
        return
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Execute requested actions
    success = True
    
    if args.train or args.retrain:
        success = train_model(retrain=args.retrain)
        if not success:
            return
    
    if args.test:
        success = test_model()
        if not success:
            return
    
    if args.evaluate:
        success = evaluate_model()
        if not success:
            return
    
    if args.info:
        show_model_info()
    
    logger.info("\n✅ Script completed successfully!")

if __name__ == "__main__":
    main()
