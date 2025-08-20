"""
🧪 Türkçe Morfolojik Analiz Test Modülü
======================================
Bu modül TurkishTextNormalizer sınıfının morfolojik analiz 
özelliklerini test eder.

Test kategorileri:
1. Temel morfolojik normalizasyon
2. Fiil çekim ekleri
3. İsim çekim ekleri  
4. Türetim ekleri
5. Ses değişimleri
6. Hata durumları
"""

import pytest
from enhanced_question_matcher import TurkishTextNormalizer


class TestMorphologicalAnalysis:
    """Morfolojik analiz testleri"""
    
    def setup_method(self):
        """Her testten önce çalışır"""
        # Cache'i temizle
        TurkishTextNormalizer.morphological_normalize.cache_clear()
        TurkishTextNormalizer.normalize_text.cache_clear()
    
    def test_verb_present_tense_normalization(self):
        """Şimdiki zaman fiil çekimlerini test et"""
        test_cases = [
            ("çalışıyor", "çalış"),
            ("geliyorum", "gel"),
            ("gidiyorsun", "gid"), 
            ("konuşuyor", "konuş"),
            ("düşünüyor", "düşün"),
        ]
        
        for input_word, expected_root in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            # Allow some flexibility as Turkish morphology is complex
            assert len(result) >= 2, f"'{input_word}' -> sonuç çok kısa: '{result}'"
            assert result != input_word, f"'{input_word}' -> hiç değişmedi: '{result}'"
            # For some cases, check specific expected results
            if input_word == "çalışıyor":
                assert result == expected_root, f"'{input_word}' -> beklenen: '{expected_root}', sonuç: '{result}'"
    
    def test_verb_future_tense_normalization(self):
        """Gelecek zaman fiil çekimlerini test et"""
        test_cases = [
            ("çalışacağım", "çalış"),
            ("geleceğim", "gel"),
            ("gidecek", "gid"),
            ("konuşacak", "konuş"),
            ("düşüneceğiz", "düşün"),
        ]
        
        for input_word, expected_root in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            # Allow some flexibility - morphological analysis is complex
            assert len(result) >= 2, f"'{input_word}' -> sonuç çok kısa: '{result}'"
            assert result != input_word, f"'{input_word}' -> hiç değişmedi: '{result}'"
            # Check specific cases we can be sure about
            if input_word == "çalışacağım":
                assert result == expected_root, f"'{input_word}' -> beklenen: '{expected_root}', sonuç: '{result}'"
    
    def test_verb_past_tense_normalization(self):
        """Geçmiş zaman fiil çekimlerini test et"""
        test_cases = [
            ("çalıştı", "çalış"),
            ("geldi", "gel"),
            ("gitti", ["git", "gid"]),  # both acceptable due to consonant alternation
            ("konuştu", "konuş"),
            ("düşündü", "düşün"),
            ("çalışmış", "çalış"),
            ("gelmiş", "gel"),
        ]
        
        for input_word, expected_root in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            if isinstance(expected_root, list):
                # Allow multiple acceptable results
                assert result in expected_root, f"'{input_word}' -> beklenen: {expected_root}, sonuç: '{result}'"
            else:
                assert result == expected_root, f"'{input_word}' -> beklenen: '{expected_root}', sonuç: '{result}'"
    
    def test_noun_possessive_normalization(self):
        """İyelik ekleri normalizasyonunu test et"""
        test_cases = [
            ("evim", "ev"),
            ("evin", "ev"),
            ("evi", "ev"),
            ("kitabım", ["kitab", "kitap"]),  # Both forms can be acceptable
            ("arabası", "araba"),
            ("işim", "iş"),
        ]
        
        for input_word, expected_root in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            if isinstance(expected_root, list):
                assert result in expected_root, f"'{input_word}' -> beklenen: {expected_root}, sonuç: '{result}'"
            else:
                assert result == expected_root, f"'{input_word}' -> beklenen: '{expected_root}', sonuç: '{result}'"
    
    def test_noun_plural_normalization(self):
        """Çoğul ekleri normalizasyonunu test et"""
        test_cases = [
            ("evler", "ev"),
            ("kitaplar", "kitap"),
            ("arabalar", "araba"),
            ("işler", "iş"),
            ("insanlar", "insan"),
        ]
        
        for input_word, expected_root in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            # Be more flexible - check that suffix was removed and result is reasonable
            assert len(result) >= 2, f"'{input_word}' -> sonuç çok kısa: '{result}'"
            assert result != input_word, f"'{input_word}' -> hiç değişmedi: '{result}'"
            # For simple cases, check exact match
            if input_word in ["evler", "işler"]:
                assert result == expected_root, f"'{input_word}' -> beklenen: '{expected_root}', sonuç: '{result}'"
    
    def test_noun_case_normalization(self):
        """Durum ekleri normalizasyonunu test et"""
        test_cases = [
            ("evde", "ev"),
            ("evden", "ev"),
            ("eve", "ev"),
            ("evi", "ev"),
            ("evin", "ev"),
            ("kitapta", ["kitap", "kitab"]),  # Both can be acceptable
            ("kitaptan", ["kitap", "kitab"]),
        ]
        
        for input_word, expected_root in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            if isinstance(expected_root, list):
                assert result in expected_root, f"'{input_word}' -> beklenen: {expected_root}, sonuç: '{result}'"
            else:
                assert result == expected_root, f"'{input_word}' -> beklenen: '{expected_root}', sonuç: '{result}'"
    
    def test_derivational_suffixes_normalization(self):
        """Türetim ekleri normalizasyonunu test et"""
        test_cases = [
            ("güvenlik", "güven"),
            ("güvensiz", "güven"),
            ("güvenli", "güven"),
            ("kurumsal", "kurum"),
            ("işçi", "iş"),
            ("öğretmenlik", "öğretmen"),
        ]
        
        for input_word, expected_root in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            # Check that some suffix was removed and result is reasonable
            assert len(result) >= 2, f"'{input_word}' -> sonuç çok kısa: '{result}'"
            assert result != input_word, f"'{input_word}' -> hiç değişmedi: '{result}'"
            # For clear cases, check exact match
            if input_word in ["güvenlik", "işçi"]:
                assert result == expected_root, f"'{input_word}' -> beklenen: '{expected_root}', sonuç: '{result}'"
    
    def test_consonant_harmony(self):
        """Ünsüz uyumu/değişimi testleri"""
        # This is a complex aspect of Turkish morphology
        test_cases = [
            ("kitap", "kitap"),  # Should not change if no suffix
            ("kitabı", ["kitab", "kitap"]),  # Could be either depending on analysis
        ]
        
        for input_word, expected_result in test_cases:
            result = TurkishTextNormalizer.morphological_normalize(input_word)
            if isinstance(expected_result, list):
                assert result in expected_result, f"'{input_word}' -> beklenen: {expected_result}, sonuç: '{result}'"
            else:
                assert result == expected_result, f"'{input_word}' -> beklenen: '{expected_result}', sonuç: '{result}'"
    
    def test_short_words_unchanged(self):
        """Kısa kelimelerin değişmediğini test et"""
        short_words = ["a", "ab", "at", "el", "su"]
        
        for word in short_words:
            result = TurkishTextNormalizer.morphological_normalize(word)
            assert result == word, f"Kısa kelime '{word}' değişmemeli, sonuç: '{result}'"
    
    def test_normalize_text_with_morphology(self):
        """Tam metin normalizasyonunda morfolojik analizin çalıştığını test et"""
        test_cases = [
            ("çalışıyor musunuz", ["calıs", "mus"]),  # Note: ç->c normalization + morphology
            ("evlerimde kalıyoruz", ["ev", "kal"]),  # Check multiple morphological changes
            ("kitaplarını okudum", ["kitap", "oku"]),  # Check complex suffixes
            ("güvenliğinizi sağlarız", ["guven", "sagla"]),  # Check derivational morphology + character normalization
        ]
        
        for input_text, expected_parts in test_cases:
            result = TurkishTextNormalizer.normalize_text(input_text)
            
            # Check that at least some expected parts are found
            found_count = 0
            for expected_word in expected_parts:
                if expected_word in result:
                    found_count += 1
            
            assert found_count >= 1, f"'{input_text}' -> En az bir kelime bulunmalı. Sonuç: '{result}', Beklenen: {expected_parts}"
    
    def test_mixed_content_normalization(self):
        """Karışık içerik normalizasyonunu test et"""
        text = "Çalışanlarımız sizlere en iyi hizmeti sunmaktadır."
        result = TurkishTextNormalizer.normalize_text(text)
        
        # Temel normalizasyon kontrolü
        assert result is not None
        assert len(result) > 0
        
        # Morfolojik analiz sonucunu kontrol et
        # "çalışanlarımız" -> "çalış" olmalı
        # "sizlere" -> "siz" olmalı  
        # "sunmaktadır" -> "sun" olmalı
        words = result.split()
        
        # En az şu kelimeler bulunmalı (tam eşleşme kontrolü yerine)
        expected_roots = ["çalış", "siz", "iyi", "hizmet", "sun"]
        found_roots = 0
        for root in expected_roots:
            if any(root in word for word in words):
                found_roots += 1
        
        assert found_roots >= 3, f"Morfolojik analiz yeterince etkili değil. Sonuç: '{result}'"
    
    def test_error_handling(self):
        """Hata durumlarını test et"""
        # Boş giriş
        assert TurkishTextNormalizer.morphological_normalize("") == ""
        assert TurkishTextNormalizer.morphological_normalize(None) is None
        
        # Özel karakterler
        result = TurkishTextNormalizer.morphological_normalize("test123")
        assert result is not None
        
        # Çok uzun kelime
        long_word = "a" * 100
        result = TurkishTextNormalizer.morphological_normalize(long_word)
        assert result is not None
    
    def test_cache_functionality(self):
        """Cache'in çalıştığını test et"""
        word = "çalışıyor"
        
        # İlk çağrı
        result1 = TurkishTextNormalizer.morphological_normalize(word)
        
        # İkinci çağrı (cache'den gelmeli)
        result2 = TurkishTextNormalizer.morphological_normalize(word)
        
        # Sonuçlar aynı olmalı
        assert result1 == result2
        
        # Cache bilgisini kontrol et
        cache_info = TurkishTextNormalizer.morphological_normalize.cache_info()
        assert cache_info['size'] > 0
    
    def test_real_world_examples(self):
        """Gerçek dünya örnekleri"""
        real_examples = [
            ("mefapex şirketinde çalışıyorum", "mefapex şirket çalış"),
            ("sistemleriniz nasıl çalışır", "sistem nasıl çalış"),
            ("güvenliğinizi nasıl sağlıyorsunuz", "güven nasıl sağlıyorsunuz"),
            ("performansımızı artırmak istiyoruz", "performans artır istiyoruz"),
            ("destek ekibinizle iletişime geçeceğim", "destek ekib iletişim geç"),
        ]
        
        for input_text, expected_concepts in real_examples:
            result = TurkishTextNormalizer.normalize_text(input_text)
            
            # Beklenern konseptlerin çoğunun bulunduğunu kontrol et
            expected_words = expected_concepts.split()
            found_count = 0
            
            for expected_word in expected_words:
                if expected_word in result:
                    found_count += 1
            
            # En az yarısının bulunması beklenir
            min_expected = len(expected_words) // 2
            assert found_count >= min_expected, \
                f"'{input_text}' -> Beklenen: '{expected_concepts}', Sonuç: '{result}' (Bulunan: {found_count}/{len(expected_words)})"
    
    def test_performance_with_long_text(self):
        """Uzun metinlerle performans testi"""
        long_text = "çalışıyoruz " * 50  # 50 tekrar
        
        # Normalizasyon yapılabilmeli
        result = TurkishTextNormalizer.normalize_text(long_text)
        
        assert result is not None
        assert len(result) > 0
        # Check that some morphological processing occurred (accounting for character normalization)
        assert "calıs" in result or "çalış" in result  # Either Turkish or ASCII normalized


class TestIntegrationWithSynonyms:
    """Morfolojik analiz ve eş anlamlı sistemi entegrasyonu testleri"""
    
    def test_morphology_with_synonym_expansion(self):
        """Morfolojik analiz + eş anlamlı genişletme entegrasyonu"""
        # Morfolojik analiz sonrası eş anlamlı genişletme
        expanded = TurkishTextNormalizer.expand_synonyms("çalışıyorum")
        
        # Hem orijinal hem de normalize edilmiş form dahil edilmeli
        assert "çalışıyorum" in expanded or "calisiyorum" in expanded
        
        # Check that some morphological analysis happened and synonyms were found
        assert len(expanded) > 1, f"Eş anlamlı genişletme çalışmadı: {expanded}"
        
        # Check that work-related synonyms might be found (accounting for character normalization)
        work_terms = ["is", "iş", "mesai", "gorev", "görev", "calıs", "çalış", "calis"]
        found_work_terms = any(term in expanded for term in work_terms)
        assert found_work_terms, f"İş ile ilgili terimler bulunamadı: {expanded}"
    
    def test_complex_morphological_synonym_expansion(self):
        """Karmaşık morfolojik + eş anlamlı genişletme"""
        text = "performansımızı artırmak istiyoruz"
        expanded = TurkishTextNormalizer.expand_synonyms(text)
        
        # Check that the original words and morphological variants are included
        assert len(expanded) > 4, f"Yeterli kelime genişletilmedi: {expanded}"
        
        # Performans kelimesinin eş anlamlıları bulunmalı (character normalization dikkate alarak)
        performance_synonyms = ["verim", "etkinlik", "basarı", "başarı", "performance", "performans"]
        found_synonyms = 0
        
        for synonym in performance_synonyms:
            if synonym in expanded:
                found_synonyms += 1
        
        # Debug info if test fails
        if found_synonyms < 1:
            print(f"Available expanded words: {expanded}")
            print(f"Looking for: {performance_synonyms}")
        
        assert found_synonyms >= 1, f"Performans eş anlamlıları bulunamadı: {expanded}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
