from app.services.risk_scoring import RiskGirdisi, hesapla, risk_seviyesi_belirle


def _dusuk_girdi(**overrides) -> RiskGirdisi:
    taban = dict(
        negatif_icerik_orani=0.1, onceki_saat_hacim=100, guncel_saat_hacim=105,
        ortalama_yorum_yayilma_hizi=2, haber_kaynagi_sayisi=0, paylasim_sayisi=50,
        dogrulanmis_hesap_sayisi=0, toplam_icerik_sayisi=100,
        duygu_yogunlugu_ortalama=0.05, bot_skoru_ortalama=0.05,
        platform_agirlik_ortalama=0.3, hesap_guven_puani_ortalama=0.9,
        anahtar_kelime_yogunlugu=0.02, haber_guvenilirlik_ortalama=0.9,
        cografi_yayilim_genislik=0.1, icerik_benzerlik_orani=0.02,
        influencer_erisim_skoru=0.02, gorsel_icerik_orani=0.05,
        sahte_haber_riski_ortalama=0.02, gecmis_kriz_benzerlik_skoru=0.02,
    )
    taban.update(overrides)
    return RiskGirdisi(**taban)


def _kritik_girdi(**overrides) -> RiskGirdisi:
    taban = dict(
        negatif_icerik_orani=0.95, onceki_saat_hacim=100, guncel_saat_hacim=500,
        ortalama_yorum_yayilma_hizi=80, haber_kaynagi_sayisi=15, paylasim_sayisi=10000,
        dogrulanmis_hesap_sayisi=40, toplam_icerik_sayisi=50,
        duygu_yogunlugu_ortalama=0.9, bot_skoru_ortalama=0.8,
        platform_agirlik_ortalama=0.95, hesap_guven_puani_ortalama=0.15,
        anahtar_kelime_yogunlugu=0.9, haber_guvenilirlik_ortalama=0.9,
        cografi_yayilim_genislik=0.9, icerik_benzerlik_orani=0.7,
        influencer_erisim_skoru=0.85, gorsel_icerik_orani=0.6,
        sahte_haber_riski_ortalama=0.5, gecmis_kriz_benzerlik_skoru=0.6,
    )
    taban.update(overrides)
    return RiskGirdisi(**taban)


def test_dusuk_risk_senaryosu():
    sonuc = hesapla(_dusuk_girdi())
    assert sonuc.toplam_skor < 25
    assert sonuc.risk_seviyesi == "Düşük Risk"


def test_kritik_risk_senaryosu():
    sonuc = hesapla(_kritik_girdi())
    assert sonuc.toplam_skor > 75
    assert sonuc.risk_seviyesi == "Kritik Risk"


def test_16_bilesenin_tamami_raporlanir():
    sonuc = hesapla(_kritik_girdi())
    assert len(sonuc.bilesenler) == 16
    assert "guvenilir_kaynak_teyidi" in sonuc.destekleyici_sinyaller
    assert sonuc.en_yuksek_katki_sirasi[0] in sonuc.bilesenler


def test_skor_toplami_100u_gecmez():
    girdi = _kritik_girdi(
        negatif_icerik_orani=10, onceki_saat_hacim=1, guncel_saat_hacim=100000,
        ortalama_yorum_yayilma_hizi=100000, haber_kaynagi_sayisi=1000, paylasim_sayisi=10_000_000,
        dogrulanmis_hesap_sayisi=1000, toplam_icerik_sayisi=1000,
    )
    sonuc = hesapla(girdi)
    assert sonuc.toplam_skor <= 100


def test_risk_seviyesi_sinirlari():
    assert risk_seviyesi_belirle(0) == "Düşük Risk"
    assert risk_seviyesi_belirle(25) == "Düşük Risk"
    assert risk_seviyesi_belirle(26) == "Orta Risk"
    assert risk_seviyesi_belirle(50) == "Orta Risk"
    assert risk_seviyesi_belirle(51) == "Yüksek Risk"
    assert risk_seviyesi_belirle(75) == "Yüksek Risk"
    assert risk_seviyesi_belirle(76) == "Kritik Risk"
    assert risk_seviyesi_belirle(100) == "Kritik Risk"
