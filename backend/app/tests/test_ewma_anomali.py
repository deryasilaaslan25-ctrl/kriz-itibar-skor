"""EWMA hacim anomali motoru testleri (bkz. app/services/ewma_anomali.py,
Document 121 s.3'teki formülün birebir uygulaması)."""
import math

from app.services.ewma_anomali import (
    EwmaDurumu, guncelle, z_skoru_serisi, son_z_skoru, normalize_0_1,
)


def test_ilk_gozlemde_z_sifir():
    durum = EwmaDurumu()
    yeni_durum, z = guncelle(durum, 10.0)
    assert z == 0.0
    assert yeni_durum.mu == 10.0
    assert yeni_durum.baslatildi is True


def test_durgun_seri_dusuk_z_uretir():
    """Sabit/durağan bir seride (gürültüsüz) Z-skoru düşük kalmalı."""
    seri = [10.0] * 20
    z_son = son_z_skoru(seri)
    assert abs(z_son) < 0.5


def test_ani_sicrama_yuksek_z_uretir():
    """Durağan bir temel çizgiden sonra ani bir sıçrama yüksek |Z| üretmeli.

    NOT: gamma=0.2 (orta hafıza) ile TEK bir sıçrama adımında Z, klasik
    3-sigma eşiğini aşmayabilir (EWMA kasıtlı olarak yumuşatma yapar — bu
    onun gürültüye dayanıklılığının KAYNAĞIDIR). Burada gerçekçi beklenti
    "belirgin biçimde anomali sinyali veriyor" (>2.0), tam 3-sigma değil.
    """
    seri = [10, 11, 9, 10, 11, 10, 9, 10, 11, 10, 100]
    z_son = son_z_skoru(seri)
    assert z_son > 2.0


def test_z_skoru_serisi_uzunluk_girdiyle_esit():
    seri = [5, 6, 7, 8, 9]
    assert len(z_skoru_serisi(seri)) == len(seri)


def test_normalize_0_1_sinirlar():
    assert normalize_0_1(0.0) == 0.0
    assert normalize_0_1(3.0) == 1.0
    assert normalize_0_1(10.0) == 1.0  # üst sınırda kırpılır
    assert normalize_0_1(-5.0) == 0.0  # negatif Z (hacim düşüşü) risk açısından 0


def test_yarilanma_omru_manuel_dogrulama():
    """guncelle() formülünün elle hesaplanmış bir örnekle eşleştiğini doğrular."""
    durum = EwmaDurumu(mu=10.0, sigma2=4.0, baslatildi=True)
    yeni_durum, z = guncelle(durum, 20.0, gamma=0.2)
    beklenen_mu = 0.2 * 20.0 + 0.8 * 10.0  # = 12.0
    beklenen_sigma2 = 0.2 * (20.0 - beklenen_mu) ** 2 + 0.8 * 4.0
    assert abs(yeni_durum.mu - beklenen_mu) < 1e-9
    assert abs(yeni_durum.sigma2 - beklenen_sigma2) < 1e-9
    assert abs(z - (20.0 - beklenen_mu) / math.sqrt(beklenen_sigma2)) < 1e-9
