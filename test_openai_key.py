#!/usr/bin/env python3
"""
Test script to verify OpenAI API key is working
"""

import os
from dotenv import load_dotenv
import openai

def test_openai_api():
    """Test if OpenAI API key is valid"""
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "your_actual_openai_api_key_here":
        print("❌ OpenAI API key not set!")
        print("Please edit the .env file and add your real API key.")
        return False
    
    if not api_key.startswith("sk-"):
        print("❌ Invalid API key format!")
        print("OpenAI API keys should start with 'sk-'")
        return False
    
    try:
        # Test the API key
        openai.api_key = api_key
        
        # Try a simple API call
        response = openai.models.list()
        
        print("✅ OpenAI API key is working!")
        print(f"🔑 Key: {api_key[:7]}...{api_key[-4:]}")
        print(f"📊 Available models: {len(response.data)}")
        
        # Check if GPT-3.5-turbo is available
        models = [model.id for model in response.data]
        if "gpt-3.5-turbo" in models:
            print("✅ GPT-3.5 Turbo is available")
        else:
            print("⚠️  GPT-3.5 Turbo not found in available models")
            
        return True
        
    except Exception as e:
        print(f"❌ API key test failed: {str(e)}")
        print("Please check your API key and try again.")
        return False

if __name__ == "__main__":
    print("🧪 Testing OpenAI API Key...")
    print("=" * 40)
    
    success = test_openai_api()
    
    if success:
        print("\n🎉 Ready to run the MEFAPEX chatbot!")
    else:
        print("\n🔧 Please fix the API key issue first.")
