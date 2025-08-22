"""
Intent Classifier for MEFAPEX Chatbot
======================================

Lightweight machine learning model for intent classification using TF-IDF and Logistic Regression.
Maps user messages to static_responses categories with confidence scores.

Features:
- TF-IDF vectorization for text features
- Logistic regression for classification
- Turkish language support with preprocessing
- Training data generation from static responses
- Model persistence and loading
- Confidence-based fallback
"""

import os
import json
import pickle
import logging
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np

# Machine learning imports
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    from sklearn.pipeline import Pipeline
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class IntentPrediction:
    """Intent prediction result with confidence score"""
    intent: str
    confidence: float
    category: str
    all_probabilities: Dict[str, float]

class TextPreprocessor:
    """Turkish text preprocessing for better intent classification"""
    
    def __init__(self):
        # Turkish character mappings
        self.turkish_char_map = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
        }
        
        # Turkish stopwords (basic set)
        self.stopwords = {
            'bir', 've', 'bu', 'da', 'de', 'ile', 'için', 'ki', 'mi', 'mu', 'mü',
            'ne', 'o', 'şu', 'ya', 'gibi', 'kadar', 'daha', 'en', 'çok', 'az',
            'var', 'yok', 'olan', 'olur', 'eder', 'etmek', 'olmak', 'yapmak'
        }
    
    def normalize_turkish(self, text: str) -> str:
        """Normalize Turkish characters to ASCII"""
        for tr_char, ascii_char in self.turkish_char_map.items():
            text = text.replace(tr_char, ascii_char)
        return text
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove special characters except Turkish ones
        text = re.sub(r'[^\w\sçğıöşüÇĞIÖŞÜ]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def remove_stopwords(self, text: str) -> str:
        """Remove Turkish stopwords"""
        words = text.split()
        filtered_words = [word for word in words if word not in self.stopwords]
        return ' '.join(filtered_words)
    
    def preprocess(self, text: str, remove_stopwords: bool = True) -> str:
        """Full preprocessing pipeline"""
        text = self.clean_text(text)
        if remove_stopwords:
            text = self.remove_stopwords(text)
        return text

class IntentClassifier:
    """
    Lightweight intent classifier using TF-IDF + Logistic Regression
    """
    
    def __init__(self, model_path: str = "models_cache/intent_classifier.pkl", 
                 static_responses_path: str = "content/static_responses.json"):
        self.model_path = model_path
        self.static_responses_path = static_responses_path
        self.preprocessor = TextPreprocessor()
        
        # Model components
        self.model = None
        self.vectorizer = None
        self.pipeline = None
        self.label_to_category = {}
        self.category_to_label = {}
        self.is_trained = False
        
        # Configuration
        self.confidence_threshold = 0.3  # Minimum confidence for prediction
        self.max_features = 1000  # TF-IDF max features
        self.random_state = 42
        
        # Ensure model directory exists
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Try to load existing model
        if os.path.exists(self.model_path):
            self.load_model()
        else:
            logger.info("No existing model found. Will train new model.")
    
    def generate_training_data(self) -> Tuple[List[str], List[str]]:
        """
        Generate training data from static responses and additional samples
        Returns: (texts, labels)
        """
        if not os.path.exists(self.static_responses_path):
            raise FileNotFoundError(f"Static responses file not found: {self.static_responses_path}")
        
        with open(self.static_responses_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        responses = data.get("responses", {})
        texts = []
        labels = []
        
        # Generate training samples from keywords and synthetic data
        for category, response_data in responses.items():
            if not isinstance(response_data, dict):
                continue
            
            keywords = response_data.get("keywords", [])
            
            # Add keywords as training samples
            for keyword in keywords:
                texts.append(keyword)
                labels.append(category)
            
            # Generate additional synthetic samples based on category
            synthetic_samples = self._generate_synthetic_samples(category, keywords)
            texts.extend(synthetic_samples)
            labels.extend([category] * len(synthetic_samples))
        
        # Add negative samples (for better discrimination)
        negative_samples = self._generate_negative_samples()
        texts.extend(negative_samples)
        labels.extend(['unknown'] * len(negative_samples))
        
        logger.info(f"Generated {len(texts)} training samples across {len(set(labels))} categories")
        return texts, labels
    
    def _generate_synthetic_samples(self, category: str, keywords: List[str]) -> List[str]:
        """Generate synthetic training samples for a category"""
        samples = []
        
        # Category-specific sample generation
        if category == "greetings":
            samples.extend([
                "merhaba size nasıl yardımcı olabilirim",
                "selam arkadaş",
                "günaydın efendim",
                "iyi akşamlar size",
                "nasıl gidiyorsun bugün",
                "ne haber neler oluyor",
                "selamlar herkese",
                "hello there",
                "hi how are you",
                "good morning everyone"
            ])
        
        elif category == "company_info":
            samples.extend([
                "mefapex firması ne yapıyor",
                "şirketiniz hakkında bilgi verir misiniz",
                "hangi alanlarda hizmet veriyorsunuz",
                "mefapex bilişim ne işi yapıyor",
                "firma olarak neler sunuyorsunuz",
                "şirket profili nedir",
                "hakkımızda bölümü",
                "what does mefapex do",
                "company information please",
                "tell me about your business",
                "mefapex hakkında",
                "şirket bilgisi",
                "firma hakkında",
                "ne iş yapıyorsunuz",
                "hangi sektörde",
                "business profile",
                "company profile",
                "about mefapex",
                "mefapex nedir",
                "şirket tanıtımı",
                "firma tanıtımı"
            ])
        
        elif category == "working_hours":
            samples.extend([
                "kaçta açıyorsunuz",
                "mesai saatleri nedir",
                "ne zaman müsaitsiniz",
                "çalışma programınız nasıl",
                "hangi saatlerde hizmet veriyorsunuz",
                "ofis saatleri",
                "iş günleri ve saatleri",
                "when are you open",
                "what time do you close",
                "business hours please"
            ])
        
        elif category == "support_types":
            samples.extend([
                "yardım alabilir miyim",
                "destek nasıl talep ederim",
                "problem yaşıyorum",
                "teknik sorun var",
                "sistem çalışmıyor",
                "hata alıyorum",
                "nasıl destek alabilirim",
                "sorun var",
                "arıza var",
                "çalışmıyor",
                "bozuk",
                "help me please",
                "technical support needed",
                "i have a problem",
                "support request",
                "need assistance",
                "teknik yardım",
                "destek lazım",
                "yardım lazım",
                "sorun çözümü",
                "teknik problem"
            ])
        
        elif category == "technology_info":
            samples.extend([
                "hangi teknolojileri kullanıyorsunuz",
                "yazılım geliştirme yapar mısınız",
                "programming dilleri neler",
                "teknoloji altyapınız",
                "yazılım projesi yapabilir misiniz",
                "kodlama konusunda",
                "development süreçleri",
                "what technologies do you use",
                "software development services",
                "programming capabilities",
                "hangi programlama dilleri",
                "yazılım teknolojileri",
                "teknoloji stack",
                "development tools",
                "coding languages",
                "framework neler",
                "teknoloji hizmetleri",
                "yazılım çözümleri",
                "teknoloji danışmanlığı",
                "sistem mimarisi"
            ])
        
        elif category == "thanks_goodbye":
            samples.extend([
                "çok teşekkür ederim",
                "sağolun yardımınız için",
                "görüşmek üzere",
                "iyi günler dilerim",
                "hoşça kalın",
                "şimdilik bu kadar",
                "thanks a lot",
                "goodbye see you later",
                "thank you very much"
            ])
        
        # Add variations with different phrasings
        for keyword in keywords[:3]:  # Use first 3 keywords
            samples.extend([
                f"{keyword} hakkında bilgi",
                f"{keyword} konusunda",
                f"{keyword} ile ilgili",
                f"{keyword} nedir",
                f"{keyword} nasıl"
            ])
        
        return samples
    
    def _generate_negative_samples(self) -> List[str]:
        """Generate negative samples for better discrimination"""
        return [
            "hava durumu nasıl",
            "futbol maçı ne zaman",
            "yemek tarifi ver",
            "film önerisi",
            "müzik dinlemek istiyorum",
            "alışveriş yapmak",
            "tatil planı",
            "spor haberleri",
            "news about politics",
            "cooking recipes",
            "weather forecast",
            "random nonsense text",
            "completely unrelated query"
        ]
    
    def train_model(self, retrain: bool = False) -> bool:
        """
        Train the intent classification model
        """
        if not SKLEARN_AVAILABLE:
            logger.error("Scikit-learn not available. Cannot train model.")
            return False
        
        if self.is_trained and not retrain:
            logger.info("Model already trained. Use retrain=True to force retrain.")
            return True
        
        try:
            logger.info("🔄 Training intent classification model...")
            
            # Generate training data
            texts, labels = self.generate_training_data()
            
            # Preprocess texts
            processed_texts = [self.preprocessor.preprocess(text) for text in texts]
            
            # Create label mappings
            unique_labels = list(set(labels))
            self.category_to_label = {cat: i for i, cat in enumerate(unique_labels)}
            self.label_to_category = {i: cat for cat, i in self.category_to_label.items()}
            
            # Convert labels to numbers
            numeric_labels = [self.category_to_label[label] for label in labels]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                processed_texts, numeric_labels, 
                test_size=0.2, random_state=self.random_state, 
                stratify=numeric_labels
            )
            
            # Create pipeline
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=self.max_features,
                    ngram_range=(1, 2),  # Unigrams and bigrams
                    lowercase=True,
                    stop_words=None,  # We handle stopwords in preprocessing
                    min_df=1,
                    max_df=0.95
                )),
                ('classifier', LogisticRegression(
                    random_state=self.random_state,
                    max_iter=1000,
                    class_weight='balanced'  # Handle imbalanced classes
                ))
            ])
            
            # Train model
            self.pipeline.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = self.pipeline.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"✅ Model trained successfully!")
            logger.info(f"📊 Training samples: {len(X_train)}")
            logger.info(f"📊 Test samples: {len(X_test)}")
            logger.info(f"📊 Accuracy: {accuracy:.3f}")
            logger.info(f"📊 Categories: {len(unique_labels)}")
            
            # Detailed classification report
            target_names = [self.label_to_category[i] for i in range(len(unique_labels))]
            report = classification_report(y_test, y_pred, target_names=target_names, output_dict=True)
            
            for category in target_names:
                if category in report:
                    precision = report[category]['precision']
                    recall = report[category]['recall']
                    f1 = report[category]['f1-score']
                    logger.info(f"📈 {category}: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}")
            
            self.is_trained = True
            
            # Save model
            self.save_model()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            return False
    
    def predict_intent(self, text: str) -> Optional[IntentPrediction]:
        """
        Predict intent for given text
        Returns IntentPrediction or None if confidence is too low
        """
        if not self.is_trained or not self.pipeline:
            logger.warning("Model not trained. Cannot predict intent.")
            return None
        
        try:
            # Preprocess text
            processed_text = self.preprocessor.preprocess(text)
            
            if not processed_text.strip():
                return None
            
            # Get prediction probabilities
            probabilities = self.pipeline.predict_proba([processed_text])[0]
            
            # Find best prediction
            best_idx = np.argmax(probabilities)
            best_confidence = probabilities[best_idx]
            best_category = self.label_to_category[best_idx]
            
            # Create probability dictionary
            all_probs = {
                self.label_to_category[i]: float(prob) 
                for i, prob in enumerate(probabilities)
            }
            
            # Check confidence threshold
            if best_confidence < self.confidence_threshold:
                logger.debug(f"Low confidence prediction: {best_category} ({best_confidence:.3f})")
                return None
            
            logger.debug(f"Intent prediction: {best_category} ({best_confidence:.3f})")
            
            return IntentPrediction(
                intent=best_category,
                confidence=float(best_confidence),
                category=best_category,
                all_probabilities=all_probs
            )
            
        except Exception as e:
            logger.error(f"Intent prediction failed: {e}")
            return None
    
    def save_model(self) -> bool:
        """Save trained model to disk"""
        if not self.is_trained or not self.pipeline:
            logger.warning("No trained model to save")
            return False
        
        try:
            model_data = {
                'pipeline': self.pipeline,
                'label_to_category': self.label_to_category,
                'category_to_label': self.category_to_label,
                'confidence_threshold': self.confidence_threshold,
                'is_trained': self.is_trained
            }
            
            joblib.dump(model_data, self.model_path)
            logger.info(f"✅ Model saved to {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save model: {e}")
            return False
    
    def load_model(self) -> bool:
        """Load trained model from disk"""
        if not os.path.exists(self.model_path):
            logger.info("No saved model found")
            return False
        
        try:
            model_data = joblib.load(self.model_path)
            
            self.pipeline = model_data['pipeline']
            self.label_to_category = model_data['label_to_category']
            self.category_to_label = model_data['category_to_label']
            self.confidence_threshold = model_data.get('confidence_threshold', 0.3)
            self.is_trained = model_data.get('is_trained', True)
            
            logger.info(f"✅ Model loaded from {self.model_path}")
            logger.info(f"📊 Categories: {len(self.label_to_category)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and statistics"""
        info = {
            'is_trained': self.is_trained,
            'model_path': self.model_path,
            'confidence_threshold': self.confidence_threshold,
            'sklearn_available': SKLEARN_AVAILABLE
        }
        
        if self.is_trained and self.pipeline:
            info.update({
                'categories': list(self.label_to_category.keys()),
                'num_categories': len(self.label_to_category),
                'max_features': self.max_features,
                'model_exists': os.path.exists(self.model_path)
            })
            
            # TF-IDF vectorizer info
            if hasattr(self.pipeline, 'named_steps') and 'tfidf' in self.pipeline.named_steps:
                tfidf = self.pipeline.named_steps['tfidf']
                info.update({
                    'vocabulary_size': len(tfidf.vocabulary_) if hasattr(tfidf, 'vocabulary_') else 0,
                    'ngram_range': getattr(tfidf, 'ngram_range', None)
                })
        
        return info
    
    def test_predictions(self, test_queries: List[str] = None) -> Dict:
        """Test the model with sample queries"""
        if test_queries is None:
            test_queries = [
                "merhaba nasılsınız",  # greetings
                "mefapex ne yapıyor",  # company_info
                "çalışma saatleri nedir",  # working_hours
                "yardıma ihtiyacım var",  # support_types
                "hangi teknolojileri kullanıyorsunuz",  # technology_info
                "teşekkür ederim",  # thanks_goodbye
                "hava durumu nasıl",  # should be unknown/low confidence
            ]
        
        results = {}
        
        for query in test_queries:
            prediction = self.predict_intent(query)
            if prediction:
                results[query] = {
                    'predicted_intent': prediction.intent,
                    'confidence': prediction.confidence,
                    'all_probabilities': prediction.all_probabilities
                }
            else:
                results[query] = {
                    'predicted_intent': 'unknown',
                    'confidence': 0.0,
                    'all_probabilities': {}
                }
        
        return results

# Global instance
intent_classifier = IntentClassifier()

# Auto-train on first import if no model exists
if not intent_classifier.is_trained:
    logger.info("🤖 Auto-training intent classifier...")
    intent_classifier.train_model()
