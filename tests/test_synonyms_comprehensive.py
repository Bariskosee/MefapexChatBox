import pytest
import os
import json
import tempfile
from enhanced_question_matcher import TurkishTextNormalizer


class TestSynonymsLoader:
    """Eş anlamlı yükleyici testleri"""
    
    def setup_method(self):
        """Her testten önce çalışır"""
        # Önbelleği temizle
        TurkishTextNormalizer._synonyms = None
        TurkishTextNormalizer._synonyms_file_path = None
    
    def test_synonyms_loaded_from_json(self):
        """JSON dosyasından eş anlamlıların yüklendiğini test et"""
        # Yeni yükleme için önbelleği temizle
        TurkishTextNormalizer._synonyms = None
        
        # Eş anlamlıları yükle
        synonyms = TurkishTextNormalizer.load_synonyms()
        
        # Temel kontrollar
        assert isinstance(synonyms, dict)
        assert len(synonyms) > 0
        
        # Belirli kelimelerin varlığını kontrol et
        assert "çalışma" in synonyms
        assert "performans" in synonyms
        assert "sistem" in synonyms
        
        # Eş anlamlıların listeler olduğunu kontrol et
        assert isinstance(synonyms["çalışma"], list)
        assert len(synonyms["çalışma"]) > 0
    
    def test_expand_synonyms_functionality(self):
        """expand_synonyms fonksiyonunun doğru çalıştığını test et"""
        # "performans" kelimesinin eş anlamlılarını genişlet
        expanded = TurkishTextNormalizer.expand_synonyms("performans")
        
        # Orijinal kelime dahil edilmeli
        assert "performans" in expanded
        
        # Eş anlamlıları dahil edilmeli
        assert "verim" in expanded
        assert "etkinlik" in expanded
        
        # Set tipinde döndürülmeli
        assert isinstance(expanded, set)
    
    def test_expand_synonyms_multiple_words(self):
        """Birden fazla kelime için eş anlamlı genişletmeyi test et"""
        expanded = TurkishTextNormalizer.expand_synonyms("çalışma saat")
        
        # Orijinal kelimeler (normalleştirilmiş haliyle) dahil edilmeli
        # Normalizasyon işlemi Türkçe karakterleri temizlediği için "çalışma" -> "calisma" olur
        assert "calisma" in expanded or "çalışma" in expanded
        assert "saat" in expanded
        
        # Eş anlamlıları dahil edilmeli
        assert "is" in expanded or "iş" in expanded  # çalışma'nın eş anlamlısı
        assert "zaman" in expanded  # saat'in eş anlamlısı
    
    def test_synonyms_caching(self):
        """Eş anlamlıların önbelleğe alındığını test et"""
        # İlk yükleme
        synonyms1 = TurkishTextNormalizer.load_synonyms()
        
        # İkinci yükleme (önbellekten gelmeli)
        synonyms2 = TurkishTextNormalizer.load_synonyms()
        
        # Aynı nesne olmalı (önbellekten geldiği için)
        assert synonyms1 is synonyms2
    
    def test_reload_synonyms(self):
        """Eş anlamlıları yeniden yüklemeyi test et"""
        # İlk yükleme
        synonyms1 = TurkishTextNormalizer.load_synonyms()
        
        # Yeniden yükleme
        synonyms2 = TurkishTextNormalizer.reload_synonyms()
        
        # İçerik aynı olmalı ama farklı nesne olabilir
        assert synonyms1.keys() == synonyms2.keys()
    
    def test_get_synonyms_info(self):
        """Eş anlamlılar hakkında bilgi alma işlevini test et"""
        info = TurkishTextNormalizer.get_synonyms_info()
        
        # Bilgi yapısını kontrol et
        assert isinstance(info, dict)
        assert "total_words" in info
        assert "total_synonyms" in info
        assert "file_path" in info
        assert "using_fallback" in info
        
        # Değerlerin mantıklı olduğunu kontrol et
        assert info["total_words"] > 0
        assert info["total_synonyms"] > 0
        assert isinstance(info["using_fallback"], bool)
    
    def test_fallback_synonyms_on_missing_file(self):
        """Dosya bulunamadığında fallback eş anlamlıların kullanıldığını test et"""
        # Önbelleği temizle
        TurkishTextNormalizer._synonyms = None
        
        # Geçici olarak dosya yolunu değiştir
        original_file = TurkishTextNormalizer._synonyms_file_path
        
        try:
            # Var olmayan bir yol belirle
            TurkishTextNormalizer._synonyms_file_path = "/nonexistent/path/synonyms.json"
            
            # Eş anlamlıları yükle
            synonyms = TurkishTextNormalizer.load_synonyms()
            
            # Fallback eş anlamlıların yüklendiğini kontrol et
            assert synonyms is not None
            assert len(synonyms) > 0
            assert "çalışma" in synonyms  # Fallback'te bulunan bir kelime
            
        finally:
            # Özgün durumu geri yükle
            TurkishTextNormalizer._synonyms_file_path = original_file
            TurkishTextNormalizer._synonyms = None
    
    def test_backward_compatibility_synonyms_property(self):
        """Geriye uyumluluk için SYNONYMS özelliğini test et"""
        normalizer = TurkishTextNormalizer()
        
        # SYNONYMS özelliği çalışmalı
        synonyms = normalizer.SYNONYMS
        
        assert isinstance(synonyms, dict)
        assert len(synonyms) > 0
        assert "çalışma" in synonyms
    
    def test_memory_optimization_limits(self):
        """Bellek optimizasyonu sınırlarını test et"""
        # Çok uzun metin ile test
        long_text = " ".join(["kelime"] * 100)  # 100 kelimeli uzun metin
        
        expanded = TurkishTextNormalizer.expand_synonyms(long_text)
        
        # Sonuç boş olmamalı
        assert len(expanded) > 0
        assert "kelime" in expanded
    
    def test_empty_and_none_inputs(self):
        """Boş ve None girişleri için test"""
        # Boş string
        expanded_empty = TurkishTextNormalizer.expand_synonyms("")
        assert len(expanded_empty) == 0
        
        # Sadece boşluk
        expanded_space = TurkishTextNormalizer.expand_synonyms("   ")
        assert len(expanded_space) <= 1  # Sadece boşluk olabilir
    
    def test_case_insensitive_synonyms(self):
        """Büyük/küçük harf duyarsızlığını test et"""
        # Büyük harfle test
        expanded_upper = TurkishTextNormalizer.expand_synonyms("PERFORMANS")
        expanded_lower = TurkishTextNormalizer.expand_synonyms("performans")
        
        # Sonuçlar benzer olmalı (normalizasyon nedeniyle)
        assert len(expanded_upper) > 1
        assert len(expanded_lower) > 1


def test_json_file_structure():
    """JSON dosyasının yapısını test et"""
    # Dosya yolunu belirle
    current_dir = os.path.dirname(os.path.abspath(__file__))
    synonyms_path = os.path.join(current_dir, '..', 'content', 'synonyms.json')
    
    # Dosyanın var olduğunu kontrol et
    assert os.path.exists(synonyms_path), f"Synonyms dosyası bulunamadı: {synonyms_path}"
    
    # JSON formatının geçerli olduğunu kontrol et
    with open(synonyms_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Temel yapı kontrolü
    assert isinstance(data, dict)
    assert len(data) > 0
    
    # Her anahtar için değerlerin liste olduğunu kontrol et
    for key, values in data.items():
        assert isinstance(key, str), f"Anahtar string olmalı: {key}"
        assert isinstance(values, list), f"Değerler liste olmalı: {key}"
        assert len(values) > 0, f"Eş anlamlı listesi boş olmamalı: {key}"
        
        # Her eş anlamlının string olduğunu kontrol et
        for synonym in values:
            assert isinstance(synonym, str), f"Eş anlamlı string olmalı: {synonym} in {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
