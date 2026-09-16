"""ABSA (5 akademik boyut) testleri — bkz. app/services/absa.py.

Bu dosyadaki testler transformers/mDeBERTa modelini İNDİRMEDEN çalışır
(KeywordAbsaAnalyzer fallback'i doğrudan test edilir); modelin gerçekten
indirilip çalıştırıldığı doğrulama app/tests/test_sentiment_transformer.py
ve Faz 4 canlı doğrulama adımında yapılır.
"""
from app.services.absa import (
    cumlelere_ayir, KeywordAbsaAnalyzer, analiz_et, ABSA_BOYUTLARI,
)


def test_cumlelere_ayirma_temel():
    metin = "Ürün çok kaliteli. Ama müşteri hizmetleri hiç ilgilenmedi!"
    cumleler = cumlelere_ayir(metin)
    assert len(cumleler) == 2
    assert cumleler[0].startswith("Ürün")
    assert cumleler[1].startswith("Ama")


def test_bos_metin_bos_liste_doner():
    assert cumlelere_ayir("") == []
    assert cumlelere_ayir("   ") == []


def test_bes_akademik_boyut_tanimli():
    assert len(ABSA_BOYUTLARI) == 5
    beklenen = {"urun_hizmet_degeri", "yanit_verebilirlik", "inovasyon", "yonetisim_etik", "sosyal_sorumluluk"}
    assert set(ABSA_BOYUTLARI.keys()) == beklenen
    for boyut, tanim in ABSA_BOYUTLARI.items():
        assert "akademik_kaynak" in tanim and tanim["akademik_kaynak"]


def test_coklu_boyut_tek_metinden_cikarilir():
    """Document 121'in kilit ABSA örneği: tek bir metin BİRDEN FAZLA
    akademik boyuta atanabilmeli (ürün kalitesi olumlu + müşteri hizmetleri olumsuz)."""
    metin = "Ürün gerçekten harika ve kaliteli. Ama müşteri hizmetleri hiç yanıt vermedi, çok kızgınım."
    sonuc = KeywordAbsaAnalyzer().analiz_et(metin)
    assert "urun_hizmet_degeri" in sonuc.boyut_skorlari
    assert "yanit_verebilirlik" in sonuc.boyut_skorlari
    # Ürün kalitesi cümlesi pozitif, müşteri hizmetleri cümlesi negatif olmalı
    assert sonuc.boyut_skorlari["urun_hizmet_degeri"] > 0
    assert sonuc.boyut_skorlari["yanit_verebilirlik"] < 0


def test_yonetisim_etik_boyutu_tespit_edilir():
    metin = "Şirketin fiyatlandırma politikası hiç şeffaf değil, tüketiciyi kandırıyorlar."
    sonuc = KeywordAbsaAnalyzer().analiz_et(metin)
    assert "yonetisim_etik" in sonuc.boyut_skorlari


def test_analiz_et_giris_noktasi_asla_cokmez():
    """Üst düzey analiz_et() fonksiyonu (zero-shot dener, hata olursa fallback)
    her koşulda bir AbsaSonucu döndürmeli, exception fırlatmamalı."""
    sonuc = analiz_et("Kargo çok geç geldi, teslimat berbat.")
    assert sonuc.yontem in ("zero_shot_nli_mdeberta", "anahtar_kelime_fallback")
    assert isinstance(sonuc.boyut_skorlari, dict)
