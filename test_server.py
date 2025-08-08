#!/usr/bin/env python3
"""
Basit test server'ı - ana server çalışmıyor mu diye kontrol için
"""
import uvicorn
from fastapi import FastAPI
import sys
import os

# Ana dizini ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI()

@app.get("/")
def test_root():
    return {"message": "Test server çalışıyor!"}

@app.get("/health")
def health():
    return {"status": "OK", "message": "Test server sağlıklı"}

if __name__ == "__main__":
    print("🧪 Test server başlatılıyor...")
    print("📍 http://127.0.0.1:8001")
    uvicorn.run(app, host="127.0.0.1", port=8001)
