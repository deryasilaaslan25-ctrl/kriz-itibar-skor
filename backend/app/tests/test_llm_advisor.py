from app.services.llm_advisor import (
    SCCTKuralMotoru, SorumlulukSeviyesi, SCCTStratejisi, LLMOneriMotoru,
    SCCTAltTaktik, ALT_TAKTIK_BILGISI,
)


def test_bot_ve_sahte_haber_baskinsa_inkar_stratejisi_onerilir():
    motor = SCCTKuralMotoru()
    oneri = motor.strateji_belirle(
        toplam_risk_skoru=80, sorumluluk_seviyesi=SorumlulukSeviyesi.DUSUK,
        bot_aktivitesi_baskin=True, sahte_haber_riski_yuksek=True,
    )
    assert oneri.strateji == SCCTStratejisi.INKAR
    assert oneri.ilk_mudahale_suresi_saat <= 6


def test_yuksek_sorumluluk_yeniden_insa_onerir():
    motor = SCCTKuralMotoru()
    oneri = motor.strateji_belirle(
        toplam_risk_skoru=90, sorumluluk_seviyesi=SorumlulukSeviyesi.YUKSEK,
        bot_aktivitesi_baskin=False, sahte_haber_riski_yuksek=False,
    )
    assert oneri.strateji == SCCTStratejisi.YENIDEN_INSA
    assert len(oneri.somut_adimlar) >= 3


def test_dusuk_risk_guclendirme_onerir():
    motor = SCCTKuralMotoru()
    oneri = motor.strateji_belirle(
        toplam_risk_skoru=10, sorumluluk_seviyesi=SorumlulukSeviyesi.DUSUK,
        bot_aktivitesi_baskin=False, sahte_haber_riski_yuksek=False,
    )
    assert oneri.strateji == SCCTStratejisi.GUCLENDIRME


def test_tam_18_alt_taktik_tanimli():
    assert len(SCCTAltTaktik) == 18
    assert len(ALT_TAKTIK_BILGISI) == 18
    for taktik in SCCTAltTaktik:
        assert taktik in ALT_TAKTIK_BILGISI
        assert ALT_TAKTIK_BILGISI[taktik].akademik_kaynak  # her taktiğin bir kaynağı olmalı


def test_spesifik_strateji_ve_alternatifler_doludur():
    motor = SCCTKuralMotoru()
    oneri = motor.strateji_belirle(
        toplam_risk_skoru=90, sorumluluk_seviyesi=SorumlulukSeviyesi.YUKSEK,
        bot_aktivitesi_baskin=False, sahte_haber_riski_yuksek=False,
    )
    assert oneri.spesifik_strateji is not None
    assert ALT_TAKTIK_BILGISI[oneri.spesifik_strateji].durus == SCCTStratejisi.YENIDEN_INSA
    assert len(oneri.alternatif_stratejiler) >= 1


def test_dusuk_risk_altinda_yildirimi_calma_alternatif_olarak_onerilir():
    """Document 121: 'Stealing Thunder' krizin henüz kritik olmadığı erken
    aşamada HER ZAMAN bir alternatif olarak sunulmalı (sistemin erken uyarı misyonu)."""
    motor = SCCTKuralMotoru()
    oneri = motor.strateji_belirle(
        toplam_risk_skoru=60, sorumluluk_seviyesi=SorumlulukSeviyesi.ORTA,
        bot_aktivitesi_baskin=False, sahte_haber_riski_yuksek=False,
    )
    assert SCCTAltTaktik.YILDIRIMI_CALMA in oneri.alternatif_stratejiler


def test_kritik_risk_uzerinde_yildirimi_calma_onerilmez():
    motor = SCCTKuralMotoru()
    oneri = motor.strateji_belirle(
        toplam_risk_skoru=95, sorumluluk_seviyesi=SorumlulukSeviyesi.YUKSEK,
        bot_aktivitesi_baskin=False, sahte_haber_riski_yuksek=False,
    )
    assert SCCTAltTaktik.YILDIRIMI_CALMA not in oneri.alternatif_stratejiler


def test_llm_motoru_api_anahtari_yoksa_graceful_degrade_eder():
    motor = LLMOneriMotoru()
    motor.api_key = None
    assert motor.aktif_mi() is False
    kural_motoru = SCCTKuralMotoru()
    oneri = kural_motoru.strateji_belirle(60, SorumlulukSeviyesi.ORTA, False, False)
    sonuc = motor.oneri_uret(oneri, {})
    assert sonuc.llm_destekli is False
    assert sonuc.strateji == oneri.strateji
