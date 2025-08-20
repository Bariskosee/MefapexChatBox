#!/usr/bin/env python3
"""
🔍 MEFAPEX Eş Anlamlı Sözlüğü Demo
==================================
Yeni eş anlamlı sistemi için demo script
"""

from enhanced_question_matcher import TurkishTextNormalizer
import json


def main():
    print("🚀 MEFAPEX Eş Anlamlı Sözlüğü Demo")
    print("=" * 50)
    
    # Sözlük bilgilerini göster
    info = TurkishTextNormalizer.get_synonyms_info()
    print(f"📊 Sözlük Bilgileri:")
    print(f"  • Toplam kelime sayısı: {info['total_words']}")
    print(f"  • Toplam eş anlamlı sayısı: {info['total_synonyms']}")
    print(f"  • Dosya yolu: {info['file_path']}")
    print(f"  • Fallback kullanılıyor: {'Evet' if info['using_fallback'] else 'Hayır'}")
    print()
    
    # Test kelimeleri
    test_words = [
        "performans",
        "çalışma saat",
        "sistem hata",
        "destek yardım",
        "MEFAPEX",
        "güvenlik",
        "backup yedek"
    ]
    
    print("🔍 Eş Anlamlı Genişletme Testleri:")
    print("-" * 40)
    
    for word in test_words:
        expanded = TurkishTextNormalizer.expand_synonyms(word)
        print(f"📝 '{word}' →")
        print(f"   Genişletilmiş: {sorted(expanded)}")
        print(f"   Toplam: {len(expanded)} kelime")
        print()
    
    # Etkileşimli test
    print("🎯 Etkileşimli Test:")
    print("-" * 20)
    print("Bir kelime veya cümle girin (çıkmak için 'q'):")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ['q', 'quit', 'çık', 'exit']:
                break
            
            if user_input:
                expanded = TurkishTextNormalizer.expand_synonyms(user_input)
                print(f"🔍 Genişletilmiş: {sorted(expanded)}")
                print(f"📊 Toplam: {len(expanded)} kelime")
        
        except KeyboardInterrupt:
            break
    
    print("\n👋 Demo tamamlandı!")


if __name__ == "__main__":
    main()
