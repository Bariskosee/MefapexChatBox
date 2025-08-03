# Test Script for MEFAPEX Chatbot
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_MESSAGES = [
    "Fabrika çalışma saatleri nelerdir?",
    "İzin başvurusu nasıl yapılır?",
    "Güvenlik kuralları nelerdir?",
    "Vardiya değişiklikleri nasıl yapılır?",
    "Güncel üretim çıktısı nedir?",
    "Yemek saatleri nedir?",
    "Makine arızası nasıl bildirilir?",
    "Kalite kontrol prosedürleri nelerdir?"
]

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        print(f"✅ Health check: {data}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_login():
    """Test login endpoint"""
    print("\n🔐 Testing login...")
    try:
        # Test valid login
        response = requests.post(f"{BASE_URL}/login", json={
            "username": "demo",
            "password": "1234"
        })
        data = response.json()
        print(f"✅ Valid login: {data}")
        
        # Test invalid login
        response = requests.post(f"{BASE_URL}/login", json={
            "username": "wrong",
            "password": "wrong"
        })
        data = response.json()
        print(f"✅ Invalid login: {data}")
        
        return True
    except Exception as e:
        print(f"❌ Login test failed: {e}")
        return False

def test_chat():
    """Test chat endpoint with various messages"""
    print("\n💬 Testing chat endpoint...")
    
    for i, message in enumerate(TEST_MESSAGES, 1):
        try:
            print(f"\n{i}. Testing: '{message}'")
            
            start_time = time.time()
            response = requests.post(f"{BASE_URL}/chat", json={
                "message": message
            })
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                response_time = round((end_time - start_time) * 1000)
                print(f"   ✅ Response ({response_time}ms): {data['response'][:100]}...")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        # Small delay between requests
        time.sleep(1)

def test_performance():
    """Test response time performance"""
    print("\n⚡ Testing performance...")
    
    test_message = "Çalışma saatleri nelerdir?"
    response_times = []
    
    for i in range(5):
        try:
            start_time = time.time()
            response = requests.post(f"{BASE_URL}/chat", json={
                "message": test_message
            })
            end_time = time.time()
            
            if response.status_code == 200:
                response_time = (end_time - start_time) * 1000
                response_times.append(response_time)
                print(f"   Test {i+1}: {response_time:.0f}ms")
            
        except Exception as e:
            print(f"   ❌ Test {i+1} failed: {e}")
        
        time.sleep(0.5)
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        print(f"\n📊 Performance Summary:")
        print(f"   Average: {avg_time:.0f}ms")
        print(f"   Fastest: {min_time:.0f}ms")
        print(f"   Slowest: {max_time:.0f}ms")

def main():
    """Run all tests"""
    print("🧪 MEFAPEX Chatbot Test Suite")
    print("=" * 50)
    
    # Test health
    if not test_health():
        print("❌ Server is not running. Please start the application first.")
        return
    
    # Test login
    test_login()
    
    # Test chat
    test_chat()
    
    # Test performance
    test_performance()
    
    print("\n" + "=" * 50)
    print("🎉 Test suite completed!")

if __name__ == "__main__":
    main()
