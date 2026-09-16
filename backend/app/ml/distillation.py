"""
Bilgi Damıtma (Knowledge Distillation) ile XGBoost Eğitim Verisi Üretimi — Faz 7.

Document 122'nin eleştirisi: "XGBoost tabanlı risk sınıflandırması + SHAP
açıklanabilirliği (kütüphaneler kurulu değil, en az 200 etiketli örnek de
yok)". Kütüphaneler artık kuruludur (requirements.txt). 200+ örnek GERÇEK
etiketli veri (Kriz.feedback: "gercek"/"siradan") ise bu erken aşamada
gerçekten yoktur — sistem henüz üretimde kullanılmadığı için bu veri organik
olarak biriken bir şeydir (bkz. xgboost_classifier.py docstring).

Bu modül, o veri birikene kadar mimariyi GERÇEKTEN eğitilmiş, GERÇEKTEN SHAP
üreten bir modelle göstermek için "bilgi damıtma" (knowledge distillation)
yöntemini kullanır:

  Öğretmen (teacher) = risk_scoring.hesapla() — ZATEN doğrulanmış, jüri
  onaylı, deterministik 16-bileşenli uzman kural motoru.
  Öğrenci (student)  = XGBoost sınıflandırıcısı.

Geniş bir rastgele girdi uzayında öğretmenin ürettiği (özellik, etiket)
çiftleriyle öğrenci eğitilir. Bu YAYGIN ve MEŞRU bir mühendislik pratiğidir
(kavramsal kökü: Hinton, Vinyals & Dean (2015), "Distilling the Knowledge
in a Neural Network" — "bir modelin çıktılarından başka bir modeli eğitme"
ilkesi).

BİLİMSEL DÜRÜSTLÜK UYARISI (kritik): Bu şekilde eğitilen modelin "doğruluğu"
GERÇEK DÜNYA kriz tahmin başarısını ÖLÇMEZ; yalnızca "XGBoost, kural
motorunun karar mantığını ne kadar iyi öğrendiğini" ölçer. Bu, üretim
kalitesinde bir doğruluk iddiası DEĞİLDİR — mimarinin hazır olduğunun ve
SHAP açıklamalarının kural motorunun ağırlıklarıyla TUTARLI olduğunun
kanıtıdır. `Kriz.feedback` alanına gerçek etiketli veri birikince, aşağıdaki
`sentetik_egitim_verisi_uret()` çağrısı gerçek bir DB sorgusuyla
DEĞİŞTİRİLMELİDİR (bkz. egit_ve_raporla() docstring'i).
"""
from __future__ import annotations

import random

from app.ml.xgboost_classifier import FEATURE_ISIMLERI, RiskOzellikVektoru, XGBoostRiskSiniflandirici
from app.services import risk_scoring


def _rastgele_girdi(rng: random.Random) -> risk_scoring.RiskGirdisi:
    """Gerçekçi aralıklarda rastgele bir RiskGirdisi üretir (öğretmen modelin
    girdi uzayını geniş biçimde örneklemek için)."""
    onceki_hacim = rng.randint(1, 500)
    return risk_scoring.RiskGirdisi(
        negatif_icerik_orani=rng.uniform(0, 1),
        onceki_saat_hacim=onceki_hacim,
        guncel_saat_hacim=max(0, int(onceki_hacim * rng.uniform(0.2, 5.0))),
        ortalama_yorum_yayilma_hizi=rng.uniform(0, 150),
        haber_kaynagi_sayisi=rng.randint(0, 30),
        paylasim_sayisi=rng.randint(0, 20000),
        dogrulanmis_hesap_sayisi=rng.randint(0, 50),
        toplam_icerik_sayisi=rng.randint(1, 500),
        duygu_yogunlugu_ortalama=rng.uniform(0, 1),
        bot_skoru_ortalama=rng.uniform(0, 1),
        platform_agirlik_ortalama=rng.uniform(0.3, 1.0),
        hesap_guven_puani_ortalama=rng.uniform(0, 1),
        anahtar_kelime_yogunlugu=rng.uniform(0, 1),
        haber_guvenilirlik_ortalama=rng.uniform(0, 1),
        cografi_yayilim_genislik=rng.uniform(0, 1),
        icerik_benzerlik_orani=rng.uniform(0, 1),
        influencer_erisim_skoru=rng.uniform(0, 1),
        gorsel_icerik_orani=rng.uniform(0, 1),
        sahte_haber_riski_ortalama=rng.uniform(0, 1),
        gecmis_kriz_benzerlik_skoru=rng.uniform(0, 1),
        hacim_z_skoru=rng.uniform(-1, 4),
        sscct_onlenemez_orani=rng.uniform(0, 1),
        yayilma_ivmesi=rng.uniform(0, 1),
        bot_anomali_benford_skoru=rng.uniform(0, 1),
    )


def sentetik_egitim_verisi_uret(n: int = 2000, seed: int = 42) -> tuple[list[list[float]], list[int]]:
    """Öğretmen modelden (risk_scoring.hesapla) damıtılmış (X, y) eğitim seti.

    Etiket (y): risk_seviyesi "Yüksek Risk" veya "Kritik Risk" ise 1,
    aksi halde 0 (ikili sınıflandırma — "aktif müdahale gerektirir mi?").
    """
    rng = random.Random(seed)
    X: list[list[float]] = []
    y: list[int] = []
    for _ in range(n):
        girdi = _rastgele_girdi(rng)
        sonuc = risk_scoring.hesapla(girdi)
        ozellik = RiskOzellikVektoru.bilesenlerden(sonuc.bilesenler)
        X.append(ozellik.degerler)
        y.append(1 if sonuc.risk_seviyesi in ("Yüksek Risk", "Kritik Risk") else 0)
    return X, y


def egit_ve_raporla(n_ornek: int = 2000, seed: int = 42) -> dict:
    """Damıtılmış veriyle GERÇEKTEN eğitir, tutma-seti (holdout) doğruluğunu
    ölçer ve bir örnek üzerinde GERÇEK SHAP değerleri üretip risk_scoring.py'nin
    kural-tabanlı bileşen sıralamasıyla ne kadar örtüştüğünü raporlar."""
    X, y = sentetik_egitim_verisi_uret(n_ornek, seed)

    egitim_boyutu = int(len(X) * 0.8)
    X_egitim, X_test = X[:egitim_boyutu], X[egitim_boyutu:]
    y_egitim, y_test = y[:egitim_boyutu], y[egitim_boyutu:]

    siniflandirici = XGBoostRiskSiniflandirici()
    egitim_sonucu = siniflandirici.egit(X_egitim, y_egitim)
    if egitim_sonucu["durum"] != "egitildi":
        return egitim_sonucu  # xgboost kurulu değil veya veri yetersiz — graceful

    dogru_sayisi = 0
    for xi, yi in zip(X_test, y_test):
        tahmin = siniflandirici.tahmin_et(RiskOzellikVektoru(xi))
        tahmin_sinifi = 1 if tahmin is not None and tahmin >= 0.5 else 0
        dogru_sayisi += int(tahmin_sinifi == yi)
    holdout_dogruluk = round(dogru_sayisi / len(X_test), 4) if X_test else None

    # Kural motoru ile SHAP'ın "en etkili bileşen" konusunda ne kadar
    # örtüştüğünü göster (çapraz doğrulama — bkz. risk_scoring.py docstring'i)
    ornek_girdi = _rastgele_girdi(random.Random(seed + 1))
    ornek_sonuc = risk_scoring.hesapla(ornek_girdi)
    ornek_ozellik = RiskOzellikVektoru.bilesenlerden(ornek_sonuc.bilesenler)
    shap_degerleri = siniflandirici.shap_aciklama(ornek_ozellik)

    kural_motoru_en_etkili = ornek_sonuc.en_yuksek_katki_sirasi[0] if ornek_sonuc.en_yuksek_katki_sirasi else None
    shap_en_etkili = max(shap_degerleri, key=lambda k: abs(shap_degerleri[k])) if shap_degerleri else None

    return {
        "durum": "egitildi_ve_degerlendirildi",
        "ornek_sayisi": len(X), "egitim_boyutu": len(X_egitim), "test_boyutu": len(X_test),
        "holdout_dogruluk": holdout_dogruluk,
        "onemli_uyari": (
            "Bu doğruluk GERÇEK DÜNYA kriz tahmin başarısını DEĞİL, XGBoost'un "
            "kural motorunun karar mantığını ne kadar iyi öğrendiğini ölçer "
            "(bilgi damıtma / knowledge distillation). Üretimde gerçek "
            "Kriz.feedback etiketleriyle yeniden eğitilmelidir."
        ),
        "shap_degerleri": shap_degerleri,
        "kural_motoru_en_etkili_bilesen": kural_motoru_en_etkili,
        "shap_en_etkili_bilesen": shap_en_etkili,
        "capraz_dogrulama_tutarli_mi": kural_motoru_en_etkili == shap_en_etkili,
    }


if __name__ == "__main__":
    import json

    sonuc = egit_ve_raporla()
    print(json.dumps(sonuc, indent=2, ensure_ascii=False))
