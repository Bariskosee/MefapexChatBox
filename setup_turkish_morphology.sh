#!/bin/bash
"""
Setup script for Turkish morphological analysis
Installs spaCy and Turkish language model
"""

echo "🇹🇷 Setting up Turkish Morphological Analysis for MEFAPEX ChatBox"
echo "=================================================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python first."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip first."
    exit 1
fi

echo "📦 Installing spaCy..."
pip3 install spacy>=3.7.0

echo "📥 Downloading Turkish language model..."
python3 -m spacy download tr_core_news_sm

# Verify installation
echo "✅ Verifying installation..."
python3 -c "
import spacy
try:
    nlp = spacy.load('tr_core_news_sm')
    print('✅ Turkish spaCy model loaded successfully!')
    
    # Test basic functionality
    doc = nlp('Çalışanların sistem erişimi için yardım gerekiyor.')
    print(f'✅ Processed {len(doc)} tokens')
    for token in doc[:3]:
        print(f'   {token.text} → {token.lemma_}')
    
except Exception as e:
    print(f'❌ Error loading Turkish model: {e}')
    print('⚠️  Will use fallback morphological analysis')
"

echo ""
echo "🎉 Setup completed!"
echo ""
echo "📝 Next steps:"
echo "1. Test the morphological analysis: python3 test_turkish_morphology.py"
echo "2. Start the MEFAPEX server to see improvements in action"
echo "3. Try Turkish queries with morphological variations"
echo ""
echo "🔧 Features added:"
echo "- Turkish lemmatization with spaCy"
echo "- Morphological analysis for better matching"
echo "- Expanded synonyms with lemmas"
echo "- Improved pattern recognition for Turkish"
