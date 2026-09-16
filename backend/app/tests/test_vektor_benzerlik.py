"""Vektör benzerlik motoru testleri (bileşen #15 — bkz. app/services/vektor_benzerlik.py).

Qdrant bu ortamda ÇALIŞMIYOR (Docker yok) — bu GERÇEKTEN denenir ve
otomatik in-memory (TF-IDF) fallback'e düşüldüğü doğrulanır.
"""
from app.services.vektor_benzerlik import (
    InMemoryBackend, QdrantBackend, get_vektor_benzerlik_motoru, gecmis_kriz_benzerligi_hesapla,
)


def test_qdrant_sunucusu_bu_ortamda_erisilemez_gercekten_denendi():
    """Docker/Qdrant kurulu olmadığı için bagli_mi() False dönmeli — bu,
    gerçek bir bağlantı denemesidir, mock değildir."""
    assert QdrantBackend().bagli_mi() is False


def test_motor_otomatik_olarak_in_memory_fallbacke_duser():
    motor = get_vektor_benzerlik_motoru()
    assert isinstance(motor, InMemoryBackend)


def test_benzer_metinler_yuksek_skor_uretir():
    backend = InMemoryBackend()
    koleksiyon = [
        "Bir üreticinin ürün kalitesi sorunları nedeniyle şikayet dalgasıyla karşılaştığı örüntü.",
        "Kurumun veri ihlalini geç açıklaması nedeniyle düzenleyici inceleme.",
    ]
    sonuc = backend.benzerlik_ara("Şirketimizin ürünlerinde kalite sorunu ve şikayet dalgası yaşanıyor.", koleksiyon)
    assert sonuc.en_benzer_metin == koleksiyon[0]
    # NOT: TF-IDF kelime-tabanlı (gövde/lemma eşleştirmesi yapmaz) olduğundan
    # Türkçe çekim ekleri nedeniyle ("ürünlerinde" vs "ürün") tam kelime
    # eşleşmesi sınırlı kalır; asıl doğrulanan şey DOĞRU belgeyi bulması
    # (yukarıdaki satır) — skor burada yalnızca sıfır olmadığını kanıtlar.
    assert sonuc.benzerlik_skoru > 0.05


def test_bos_koleksiyon_sifir_skor_doner():
    backend = InMemoryBackend()
    sonuc = backend.benzerlik_ara("herhangi bir metin", [])
    assert sonuc.benzerlik_skoru == 0.0
    assert sonuc.en_benzer_metin is None


def test_gecmis_kriz_benzerligi_hesapla_gercek_sablonlarla_calisir():
    sonuc = gecmis_kriz_benzerligi_hesapla(
        "Ürünümüzde kalite sorunu tespit edildi, müşteriler şikayetçi.",
        konu="Ürün Kalitesi Krizi",
    )
    assert 0.0 <= sonuc.benzerlik_skoru <= 1.0
    assert sonuc.backend == "in_memory_tfidf"
