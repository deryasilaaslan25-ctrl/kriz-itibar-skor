"""İtibar Skoru motoru birim testleri.

bkz. app/services/itibar_skoru.py — R_itibar(t) = 50 + 50·tanh(α·net_duygu)
formülünün bilinen basit girdilerle doğrulanması.
"""
import math
from datetime import datetime, timedelta, timezone

from app.services.itibar_skoru import ItibarIcerikGirdisi, hesapla


def test_bos_liste_notr_skor_doner():
    sonuc = hesapla([])
    assert sonuc.skor == 50.0
    assert sonuc.icerik_sayisi == 0


def test_tek_maksimum_pozitif_icerik_yuksek_skor_uretir():
    simdi = datetime.now(timezone.utc)
    girdi = ItibarIcerikGirdisi(
        duygu="pozitif", duygu_guveni=1.0, kaynak_guven_puani=1.0,
        etkilesim=100, icerik_zamani=simdi,
    )
    sonuc = hesapla([girdi], simdi=simdi, alpha=2.5, yarilanma_omru_saat=36)
    # net_duygu = +1.0 (tek içerik, tam ağırlık) -> skor = 50+50*tanh(2.5) ≈ 99.31
    beklenen = 50 + 50 * math.tanh(2.5)
    assert abs(sonuc.skor - beklenen) < 0.01
    assert sonuc.skor > 95


def test_tek_maksimum_negatif_icerik_dusuk_skor_uretir():
    simdi = datetime.now(timezone.utc)
    girdi = ItibarIcerikGirdisi(
        duygu="negatif", duygu_guveni=1.0, kaynak_guven_puani=1.0,
        etkilesim=100, icerik_zamani=simdi,
    )
    sonuc = hesapla([girdi], simdi=simdi, alpha=2.5, yarilanma_omru_saat=36)
    beklenen = 50 - 50 * math.tanh(2.5)
    assert abs(sonuc.skor - beklenen) < 0.01
    assert sonuc.skor < 5


def test_notr_karisik_sinyal_50ye_yakin_kalir():
    simdi = datetime.now(timezone.utc)
    pozitif = ItibarIcerikGirdisi(
        duygu="pozitif", duygu_guveni=1.0, kaynak_guven_puani=1.0,
        etkilesim=100, icerik_zamani=simdi,
    )
    negatif = ItibarIcerikGirdisi(
        duygu="negatif", duygu_guveni=1.0, kaynak_guven_puani=1.0,
        etkilesim=100, icerik_zamani=simdi,
    )
    sonuc = hesapla([pozitif, negatif], simdi=simdi)
    assert abs(sonuc.skor - 50.0) < 0.5


def test_zaman_asinimi_yarilanma_omrunde_agirligi_yarilar():
    """T½ saat önce yayınlanmış bir içeriğin zaman-aşınım çarpanı ~0.5 olmalı
    (e^{-ln(2)/T½ · T½} = e^{-ln(2)} = 0.5 — formülün tanımı gereği)."""
    simdi = datetime.now(timezone.utc)
    t_half = 36.0
    eski_icerik_zamani = simdi - timedelta(hours=t_half)
    girdi = ItibarIcerikGirdisi(
        duygu="pozitif", duygu_guveni=1.0, kaynak_guven_puani=1.0,
        etkilesim=100, icerik_zamani=eski_icerik_zamani,
    )
    sonuc = hesapla([girdi], simdi=simdi, yarilanma_omru_saat=t_half)
    assert len(sonuc.katkilar) == 1
    assert abs(sonuc.katkilar[0].zaman_asinimi_carpani - 0.5) < 0.01


def test_daha_guvenilir_kaynak_daha_fazla_agirlik_alir():
    """Aynı duygu skoruna sahip iki içerikten kaynak güveni yüksek olanın
    ağırlıklı katkı payı, düşük olandan büyük olmalı (Hovland & Weiss, 1951)."""
    simdi = datetime.now(timezone.utc)
    guvenilir = ItibarIcerikGirdisi(
        duygu="negatif", duygu_guveni=0.8, kaynak_guven_puani=1.0,
        etkilesim=50, icerik_zamani=simdi, kaynak_id="ulusal_gazete",
    )
    guvenilmez = ItibarIcerikGirdisi(
        duygu="negatif", duygu_guveni=0.8, kaynak_guven_puani=0.2,
        etkilesim=50, icerik_zamani=simdi, kaynak_id="anonim",
    )
    sonuc = hesapla([guvenilir, guvenilmez], simdi=simdi)
    katki_map = {k.kaynak_id: k.agirlikli_katki_orani for k in sonuc.katkilar}
    assert abs(katki_map["ulusal_gazete"]) > abs(katki_map["anonim"])


def test_sifir_etkilesimli_icerik_agirliksiz_silinmez():
    """Regresyon: gerçek bir taramada keşfedildi — Google News RSS gibi
    kaynaklar etkileşim sayısı hiç raporlamaz (etkilesim=0). Formül önceden
    wᵢ=w_kaynak·ln(1+0)=0 üretiyordu; TÜM içerikler etkileşimsizse (ör.
    Reddit/Trends bir tarama sırasında engellenip yalnızca RSS verisi
    geldiğinde) toplam ağırlık sıfıra düşüyor ve skor gerçek duygudan
    BAĞIMSIZ olarak her zaman 50 (nötr) basıyordu. Artık her içerik en
    azından kaynak-güvenilirliği kadar bir taban ağırlık taşır."""
    simdi = datetime.now(timezone.utc)
    haberler = [
        ItibarIcerikGirdisi(
            duygu="pozitif", duygu_guveni=0.9, kaynak_guven_puani=0.35,
            etkilesim=0, icerik_zamani=simdi, kaynak_id=f"haber_{i}",
        )
        for i in range(5)
    ]
    sonuc = hesapla(haberler, simdi=simdi)
    # 5 içeriğin 5'i de aynı yönde (pozitif) olduğundan net_duygu sıfır
    # OLMAMALI ve skor 50'nin belirgin biçimde üzerinde olmalı.
    assert sonuc.net_agirlikli_duygu > 0.5
    assert sonuc.skor > 60
    assert all(k.agirlik > 0 for k in sonuc.katkilar)


def test_yuksek_etkilesim_logaritmik_olcekle_agirliklanir():
    """1000 etkileşimli bir içerik, 10 etkileşimliden ağır basmalı ama
    DOĞRUSAL (100x) değil, logaritmik oranda (ln(1001)/ln(11) ≈ 2.9x)."""
    simdi = datetime.now(timezone.utc)
    viral = ItibarIcerikGirdisi(
        duygu="negatif", duygu_guveni=0.5, kaynak_guven_puani=0.5,
        etkilesim=1000, icerik_zamani=simdi, kaynak_id="viral",
    )
    sakin = ItibarIcerikGirdisi(
        duygu="negatif", duygu_guveni=0.5, kaynak_guven_puani=0.5,
        etkilesim=10, icerik_zamani=simdi, kaynak_id="sakin",
    )
    sonuc = hesapla([viral, sakin], simdi=simdi)
    katki_map = {k.kaynak_id: k.agirlik for k in sonuc.katkilar}
    oran = katki_map["viral"] / katki_map["sakin"]
    assert 2.0 < oran < 4.0  # doğrusal olsaydı oran 100 olurdu
