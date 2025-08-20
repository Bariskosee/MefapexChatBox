import importlib
from enhanced_question_matcher import TurkishTextNormalizer


def test_synonyms_loaded_from_json():
    # Ensure a fresh load
    TurkishTextNormalizer._synonyms = None
    synonyms = TurkishTextNormalizer.load_synonyms()
    assert "çalışma" in synonyms
    assert "performans" in synonyms
    expanded = TurkishTextNormalizer.expand_synonyms("performans")
    assert "verim" in expanded
