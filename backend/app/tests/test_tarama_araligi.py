"""Adaptif tarama aralığı testleri — bkz. app/services/tarama_araligi.py."""
from app.services.tarama_araligi import hesapla, MIN_TARAMA_ARALIGI_DK, MAX_TARAMA_ARALIGI_DK


def test_adaptif_kapaliyken_sabit_aralik_korunur():
    sonuc = hesapla(temel_aralik_dk=15, z_hacim=5.0, adaptif_aktif=False)
    assert sonuc.aralik_dk == 15


def test_yuksek_anomalide_aralik_daralir():
    durgun = hesapla(temel_aralik_dk=30, z_hacim=0.0)
    anomali = hesapla(temel_aralik_dk=30, z_hacim=4.0)
    assert anomali.aralik_dk < durgun.aralik_dk


def test_alt_sinir_asilmaz():
    sonuc = hesapla(temel_aralik_dk=30, z_hacim=1000.0)
    assert sonuc.aralik_dk >= MIN_TARAMA_ARALIGI_DK


def test_ust_sinir_asilmaz():
    sonuc = hesapla(temel_aralik_dk=1000, z_hacim=0.0)
    assert sonuc.aralik_dk <= MAX_TARAMA_ARALIGI_DK


def test_negatif_z_pozitif_z_ile_ayni_davranir():
    """Negatif Z (hacim düşüşü) tarama sıklığını ARTIRMAMALI — yalnızca
    pozitif anomaliler (hacim artışı) sıklaştırma tetikler."""
    negatif = hesapla(temel_aralik_dk=20, z_hacim=-5.0)
    sifir = hesapla(temel_aralik_dk=20, z_hacim=0.0)
    assert negatif.aralik_dk == sifir.aralik_dk
