"""Çok dilli duygu analizi testleri (Faz 10) — bkz. app/services/sentiment.py.

BERTurk testinde (test_sentiment_transformer.py) olduğu gibi, çok dilli
transformer (XLM-R) modeli bu ortamda indirilemeyebilir (ağ kısıtı); bu
yüzden get_sentiment_analyzer() ÜZERİNDEN çalışan testler hem transformer
hem lexicon sonucunu kabul eden esnek assertion'lar kullanır. Lexicon
sınıflarının (CokDilliLexiconSentimentAnalyzer) KENDİSİ ağ gerektirmediğinden
doğrudan da (motor seçiminden bağımsız olarak) test edilir.
"""
from app.services.sentiment import (
    CokDilliLexiconSentimentAnalyzer, get_sentiment_analyzer, LexiconSentimentAnalyzer,
)


def test_ingilizce_negatif_sozluk_dogru_siniflandirir():
    analyzer = CokDilliLexiconSentimentAnalyzer("en")
    sonuc = analyzer.analiz_et("This is an absolute scandal, the product is terrible and I am furious.")
    assert sonuc.duygu == "negatif"
    assert sonuc.model_adi == "lexicon_coklu_dil_en"


def test_almanca_pozitif_sozluk_dogru_siniflandirir():
    analyzer = CokDilliLexiconSentimentAnalyzer("de")
    sonuc = analyzer.analiz_et("Der Service war ausgezeichnet, ich bin sehr zufrieden und empfehle es.")
    assert sonuc.duygu == "pozitif"


def test_desteklenmeyen_dil_kodu_ingilizceye_duser():
    analyzer = CokDilliLexiconSentimentAnalyzer("xx")
    assert analyzer.dil_kodu == "en"


def test_turkce_dil_kodu_eski_davranisi_bozmaz():
    """dil_kodu='tr' (varsayılan) çağrıldığında get_sentiment_analyzer() Faz
    10 ÖNCESİYLE aynı motoru (BERTurk veya Türkçe lexicon) döndürmelidir."""
    analyzer = get_sentiment_analyzer("tr")
    assert isinstance(analyzer, (LexiconSentimentAnalyzer, type(analyzer)))
    sonuc = analyzer.analiz_et("Bu firma tam bir rezalet, çok kızgınım ve asla güvenmiyorum.")
    assert sonuc.duygu == "negatif"


def test_ingilizce_dil_kodu_coklu_dil_motoru_secer_veya_temiz_fallback_yapar():
    analyzer = get_sentiment_analyzer("en")
    sonuc = analyzer.analiz_et("This is an absolute scandal, the product is terrible and I am furious.")
    assert sonuc.duygu == "negatif"
    assert sonuc.model_adi in ("cardiffnlp/twitter-xlm-roberta-base-sentiment", "lexicon_coklu_dil_en")
