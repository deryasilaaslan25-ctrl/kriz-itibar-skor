"""Benford Kanunu bot testi (bot_detection.py) ve istatistiksel doğrulama
modeli (risk_scoring.dogrulama_modeli_hesapla) testleri."""
import random

from app.services.bot_detection import benford_sapma_skoru, kombine_bot_skoru, BENFORD_MIN_GOZLEM
from app.services.risk_scoring import dogrulama_modeli_hesapla


def test_yetersiz_veri_none_doner():
    skor, aciklama = benford_sapma_skoru([1, 2, 3])
    assert skor is None
    assert "yetersiz" in aciklama.lower()


def test_organik_benford_uyumlu_seri_dusuk_skor():
    """Gerçek dünya verilerini taklit eden log-normal dağılımlı bir seri,
    Benford Kanunu'na yaklaşık uyar -> düşük sapma skoru beklenir."""
    random.seed(42)
    # Log-normal dağılım organik sosyal medya etkileşim sayılarını iyi taklit eder
    # ve Benford Kanunu'na tabidir (birçok doğal ölçüm süreci için geçerlidir).
    seri = [max(1, int(random.lognormvariate(4, 2))) for _ in range(500)]
    skor, aciklama = benford_sapma_skoru(seri)
    assert skor is not None
    assert skor < 0.9  # kesin bir eşik değil ama uyumlu seri yüksek skor üretmemeli


def test_koordineli_sabit_seri_yuksek_skor():
    """Hepsi aynı/çok benzer sayıda etkileşime sahip (koordineli bot ağı emaresi)
    bir seri, Benford dağılımından güçlü biçimde sapmalı -> yüksek skor."""
    seri = [50] * 200  # hepsi "5" ile başlıyor -> Benford'un beklediği dağılımdan tamamen sapar
    skor, aciklama = benford_sapma_skoru(seri)
    assert skor is not None
    assert skor > 0.9


def test_kombine_bot_skoru_veri_yoksa_sadece_heuristic():
    skor, detay = kombine_bot_skoru(0.4, None)
    assert skor == 0.4
    assert detay["benford_skor"] is None


def test_kombine_bot_skoru_iki_sinyali_birlestirir():
    seri = [50] * 200
    skor, detay = kombine_bot_skoru(0.2, seri)
    assert detay["benford_skor"] is not None
    assert skor > 0.2  # Benford güçlü sapma sinyali verdiği için kombine skor yükselmeli


def test_dogrulama_modeli_tum_sinyaller_sifirken_dusuk_skor():
    sonuc = dogrulama_modeli_hesapla(0.0, 0.0, 0.0, 0.0)
    assert sonuc["skor"] < 20


def test_dogrulama_modeli_tum_sinyaller_maksimumken_yuksek_skor():
    sonuc = dogrulama_modeli_hesapla(3.0, 1.0, 1.0, 1.0)
    assert sonuc["skor"] > 90


def test_dogrulama_modeli_bot_anomali_none_sifir_kabul_edilir():
    sonuc_none = dogrulama_modeli_hesapla(1.0, 0.5, 0.5, None)
    sonuc_sifir = dogrulama_modeli_hesapla(1.0, 0.5, 0.5, 0.0)
    assert sonuc_none["skor"] == sonuc_sifir["skor"]
