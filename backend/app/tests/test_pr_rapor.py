"""Kurumsal Kriz Müdahale Raporu (PDF) testleri — bkz. app/services/pr_rapor.py."""
from app.services.llm_advisor import SCCTKuralMotoru, SorumlulukSeviyesi
from app.services.pr_rapor import generate_academic_pr_report, create_pdf_report


def _ornek_rapor():
    motor = SCCTKuralMotoru()
    oneri = motor.strateji_belirle(
        toplam_risk_skoru=82, sorumluluk_seviyesi=SorumlulukSeviyesi.YUKSEK,
        bot_aktivitesi_baskin=False, sahte_haber_riski_yuksek=False,
    )
    return generate_academic_pr_report(
        oneri=oneri, kurum_adi="Anadolu Gıda A.Ş.", kriz_baslik="Ürün Kalitesi Krizi",
        kriz_konusu="Ürün Kalitesi Krizi", risk_skoru=82.0, risk_seviyesi="Kritik Risk",
    )


def test_rapor_dort_katmani_da_icerir():
    rapor = _ornek_rapor()
    assert rapor.teorik_teshis
    assert len(rapor.operasyonel_plan) == 3  # Altın Saatler / 12. Saat / 24-72. Saat
    assert len(rapor.kanal_taslaklari) == 4  # basın / sosyal medya / iç iletişim / call-center
    assert len(rapor.paydas_haritasi) >= 4


def test_operasyonel_plan_zaman_araliklari_dogru():
    rapor = _ornek_rapor()
    zamanlar = [a.zaman_araligi for a in rapor.operasyonel_plan]
    assert "İlk 2 Saat (Altın Saatler)" in zamanlar
    assert "12. Saat" in zamanlar
    assert "24-72. Saat" in zamanlar


def test_pdf_gercekten_uretilir_veya_temiz_fallback_verir():
    rapor = _ornek_rapor()
    pdf_bytes = create_pdf_report(rapor)
    assert len(pdf_bytes) > 100
    # Ya gerçek bir PDF (%PDF sihirli baytlarıyla başlar) ya da (WeasyPrint'in
    # Windows sistem kütüphaneleri eksikse) düz-metin HTML fallback'i olmalı —
    # her iki durumda da rapor içeriği KAYBOLMAMALI.
    assert pdf_bytes.startswith(b"%PDF") or b"Kurumsal Kriz" in pdf_bytes or "Kurumsal Kriz".encode("utf-8") in pdf_bytes
