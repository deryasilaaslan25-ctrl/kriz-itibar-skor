"""
Bölüm 6: Makine Öğrenmesi Genişletmesi — Risk Sınıflandırması + SHAP Açıklanabilirliği.

Mevcut sistem (bkz. app/services/anomaly_detection.py) Isolation Forest / LOF /
One-Class SVM ile ANOMALİ tespiti yapar. 2. juri eleştirisi bunun tek başına
yeterli olmadığını, denetimli (supervised) bir RİSK SINIFLANDIRMASI ve özellik
önem analizi eklenmesini talep etmektedir (Bölüm 6): XGBoost, Random Forest, SHAP.

Bu modül üç şeyi sağlar:
  1. RiskOzellikVektoru: risk_scoring.py'deki 16 bileşenin ML girdisine
     dönüştürülmesi (aynı ad alanı — iki motor birbirini çapraz doğrular).
  2. XGBoostRiskSiniflandirici: etiketli veri ("gerçek kriz" / "sıradan dalgalanma",
     zaten ORM'de Kriz.feedback alanında toplanıyor) biriktikçe eğitilebilecek
     bir sınıflandırıcı iskeleti + eğitim fonksiyonu.
  3. shap_aciklama(): eğitilmiş modelin SHAP değerleriyle risk_scoring.py'nin
     kural-tabanlı bileşen katkılarını çapraz doğrulaması için arayüz.

NOT (bilimsel dürüstlük): Bu depoda önceden eğitilmiş model AĞIRLIKLARI
bulunmamaktadır — TÜBİTAK 1002 kapsamında toplanacak etiketli "Türkçe İtibar
Krizi Veri Seti" (bkz. VERI_SETI_VE_MLOPS.md) olmadan bir sınıflandırıcıyı
"eğitilmiş" gibi sunmak bilimsel olarak yanıltıcı olurdu. Bunun yerine, eğitim
ve açıklama fonksiyonları TAMDIR ve `Kriz.feedback` alanına yeterli etiketli
örnek biriktiğinde (>= MIN_EGITIM_ORNEGI) tek komutla (`python -m app.ml.xgboost_classifier train`)
çalıştırılabilir durumdadır.
"""
from __future__ import annotations

from dataclasses import dataclass

FEATURE_ISIMLERI = [
    "negatif_duygu", "duygu_yogunlugu", "trend_artisi", "paylasim_hizi",
    "platform_agirligi", "hesap_guvenilirligi_riski", "bot_aktivitesi",
    "anahtar_kelime_yogunlugu", "haber_guvenilirligi", "cografi_yayilim",
    "icerik_benzerligi", "influencer_etkisi", "gorsel_icerik",
    "sahte_haber_riski", "gecmis_kriz_benzerligi", "icerik_yayilimi",
]

MIN_EGITIM_ORNEGI = 200  # istatistiksel olarak anlamlı bir XGBoost eğitimi için taban örnek sayısı


@dataclass
class RiskOzellikVektoru:
    """risk_scoring.RiskSonucu.bilesenler sözlüğünü sabit sıralı bir vektöre çevirir."""

    degerler: list[float]

    @classmethod
    def bilesenlerden(cls, bilesenler: dict[str, float]) -> "RiskOzellikVektoru":
        return cls(degerler=[bilesenler.get(isim, 0.0) for isim in FEATURE_ISIMLERI])


class XGBoostRiskSiniflandirici:
    """Denetimli risk sınıflandırıcı iskeleti (gerçek/sıradan kriz ayrımı).

    Eğitim verisi: Kriz tablosundaki 16 skor bileşeni (X) + feedback alanı
    ("gercek"/"siradan", y). Kullanıcı geri bildirimi arttıkça model periyodik
    olarak yeniden eğitilir (bkz. Bölüm 25: MLOps / MLflow-DVC önerisi).
    """

    def __init__(self) -> None:
        self._model = None  # lazy: yalnızca yeterli veri olduğunda eğitilir

    def egit(self, X: list[list[float]], y: list[int]) -> dict:
        if len(X) < MIN_EGITIM_ORNEGI:
            return {
                "durum": "yetersiz_veri",
                "mevcut_ornek": len(X),
                "gereken_ornek": MIN_EGITIM_ORNEGI,
                "mesaj": (
                    f"Eğitim için en az {MIN_EGITIM_ORNEGI} etiketli örnek gerekir. "
                    f"Şu an {len(X)} örnek mevcut. Kural-tabanlı risk_scoring.py "
                    "motoru bu süreçte birincil karar mekanizması olarak kullanılmaya devam eder."
                ),
            }
        try:
            import xgboost as xgb  # opsiyonel bağımlılık, requirements.txt'de mevcut
        except ImportError:
            return {
                "durum": "bagimlilik_eksik",
                "mesaj": "xgboost paketi kurulu değil. `pip install xgboost` çalıştırın.",
            }

        dmatrix = xgb.DMatrix(X, label=y, feature_names=FEATURE_ISIMLERI)
        params = {"objective": "binary:logistic", "max_depth": 4, "eta": 0.1, "eval_metric": "logloss"}
        self._model = xgb.train(params, dmatrix, num_boost_round=200)
        return {"durum": "egitildi", "ornek_sayisi": len(X)}

    def tahmin_et(self, ozellik_vektoru: RiskOzellikVektoru) -> float | None:
        if self._model is None:
            return None
        import xgboost as xgb

        dmatrix = xgb.DMatrix([ozellik_vektoru.degerler], feature_names=FEATURE_ISIMLERI)
        return float(self._model.predict(dmatrix)[0])

    def shap_aciklama(self, ozellik_vektoru: RiskOzellikVektoru) -> dict[str, float] | None:
        """Bölüm 6: 'SHAP: Model açıklanabilirliği'. Eğitilmiş modelin her
        özelliğe verdiği SHAP katkısını risk_scoring.py'nin kural-tabanlı
        bileşen katkılarıyla karşılaştırmak için döner (çapraz doğrulama)."""
        if self._model is None:
            return None
        try:
            import shap
        except ImportError:
            return None

        explainer = shap.TreeExplainer(self._model)
        shap_degerleri = explainer.shap_values([ozellik_vektoru.degerler])[0]
        return dict(zip(FEATURE_ISIMLERI, (round(float(v), 4) for v in shap_degerleri)))


def get_siniflandirici() -> XGBoostRiskSiniflandirici:
    return XGBoostRiskSiniflandirici()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "train":
        print(
            "Eğitim komutu çağrıldı. Gerçek eğitim, veritabanındaki "
            "Kriz.feedback etiketli kayıtları çekecek bir ETL adımı "
            "gerektirir (bkz. app/ml/train_pipeline.py). Bu iskelet, "
            f"MIN_EGITIM_ORNEGI={MIN_EGITIM_ORNEGI} eşiği sağlandığında "
            "doğrudan kullanılabilir durumdadır."
        )
