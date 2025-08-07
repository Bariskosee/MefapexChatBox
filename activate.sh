#!/bin/bash

# MEFAPEX Chatbot - Virtual Environment Activation Script

echo "🐍 Activating Python virtual environment..."

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 Python: $(python --version)"
echo "📍 Location: $(which python)"

# Show installed packages
echo ""
echo "📚 Key packages installed:"
python -c "
import pkg_resources
packages = ['fastapi', 'uvicorn', 'openai', 'qdrant-client', 'python-dotenv', 'mysql-connector-python', 'numpy', 'requests']
for package in packages:
    try:
        version = pkg_resources.get_distribution(package).version
        print(f'  ✅ {package}: {version}')
    except:
        print(f'  ❌ {package}: Not found')
"

echo ""
echo "🚀 Ready to run MEFAPEX Chatbot!"
echo "   To start the application: python main.py"
echo "   To load embeddings: python embedding_loader.py"
echo "   To run tests: python test_chatbot.py"
echo ""

# Start an interactive shell with the virtual environment
exec "$SHELL"
