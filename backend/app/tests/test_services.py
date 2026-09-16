from app.services.sentiment import LexiconSentimentAnalyzer
from app.services.bot_detection import HeuristicBotClassifier, BotSinyalleri
from app.services.anomaly_detection import tespit_et, AnomalyMethod
from app.services.source_credibility import guven_puani_hesapla
from app.services.topic_modeling import KeywordTopicModel


def test_negatif_duygu_tespiti():
    analyzer = LexiconSentimentAnalyzer()
    sonuc = analyzer.analiz_et("Bu firma tam bir rezalet, çok kızgınım ve asla güvenmiyorum.")
    assert sonuc.duygu == "negatif"


def test_pozitif_duygu_tespiti():
    analyzer = LexiconSentimentAnalyzer()
    sonuc = analyzer.analiz_et("Hizmet gerçekten harika ve mükemmeldi, teşekkürler, tavsiye ederim.")
    assert sonuc.duygu == "pozitif"


def test_notr_duygu_tespiti():
    analyzer = LexiconSentimentAnalyzer()
    sonuc = analyzer.analiz_et("Ürün yarın kargoya verilecek.")
    assert sonuc.duygu == "nötr"


def test_bot_skoru_yuksek_risk():
    classifier = HeuristicBotClassifier()
    skor = classifier.skorla(BotSinyalleri(
        hesap_yasi_gun=2, son_24s_paylasim_sayisi=150,
        tekrarlayan_icerik_orani=0.9, hashtag_yogunlugu=12,
    ))
    assert skor > 0.6


def test_bot_skoru_dusuk_risk():
    classifier = HeuristicBotClassifier()
    skor = classifier.skorla(BotSinyalleri(
        hesap_yasi_gun=1000, son_24s_paylasim_sayisi=3,
        tekrarlayan_icerik_orani=0.0, hashtag_yogunlugu=0.5,
    ))
    assert skor < 0.35


def test_anomali_tespiti_ani_yukselis():
    normal_seri = [10, 11, 9, 10, 12, 11, 10, 9, 11, 10]
    anomalili_seri = normal_seri + [95]  # ani sıçrama
    sonuc = tespit_et(anomalili_seri, yontem=AnomalyMethod.ISOLATION_FOREST)
    assert sonuc["son_nokta_anomali_mi"] is True


def test_kaynak_guven_puani_ulusal_gazete():
    assert guven_puani_hesapla("ulusal_gazete") == 1.00


def test_kaynak_guven_puani_anonim():
    assert guven_puani_hesapla("anonim") == 0.20


def test_konu_modelleme_veri_ihlali():
    model = KeywordTopicModel()
    konu = model.konu_belirle("Şirketin veri sızıntısı ve kvkk ihlali gündemde.")
    # NOT: kategori adı jüri eleştirisi üzerine 6'dan ~20 kategoriye çıkarılırken
    # "Veri İhlali Krizi" -> "Veri İhlali / Siber Güvenlik Krizi" olarak genişletildi
    # (bkz. topic_modeling.py KONU_ANAHTAR_KELIMELER); bu test o zaman güncellenmemişti.
    assert konu == "Veri İhlali / Siber Güvenlik Krizi"
