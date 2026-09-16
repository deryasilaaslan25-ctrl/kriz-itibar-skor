"""
Bölüm 9: Makine Öğrenmesi Altyapısı — Eğitim İskeleti.

BU DOSYA ÇALIŞTIRILABİLİR BİR EĞİTİM BETİĞİDİR, ANCAK etiketli veri seti
(geçmiş krizler + "gerçek kriz miydi / sıradan mıydı" etiketleri, bkz.
frontend'deki GeriBildirim alanı) henüz yeterli hacimde birikmediğinden
üretim modeli olarak devreye alınmamıştır.

Sistemdeki `feedback` alanı (gercek/siradan), kullanıcıların jüri
raporunda istenen tam da bu etiketli veriyi zaman içinde organik olarak
biriktirmesini sağlayacak şekilde tasarlanmıştır — yani ürün, kendi
eğitim verisini kullanım sırasında üretir (bkz. README "Veri Birikim
Stratejisi").

Yeterli veri (>= birkaç yüz etiketli örnek) toplandığında bu betik:
    1. DenetimKaydi + Kriz + Icerik tablolarından özellik çıkarımı yapar
       (negatif oranı, trend, etkileşim hızı, haber sayısı vb. — risk_scoring.py
       ile AYNI özellik seti, böylece açıklanabilir skor ile öğrenilen model
       karşılaştırılabilir olur).
    2. LightGBM / XGBoost ile ikili sınıflandırma eğitir (gercek vs siradan).
    3. Doğrulama metriklerini (Accuracy, Precision, Recall, F1, ROC-AUC)
       raporlar (Bölüm 23).
"""
from __future__ import annotations

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score


FEATURE_COLUMNS = [
    "skor_negatif_duygu", "skor_trend_artisi", "skor_etkilesim_hizi",
    "skor_haber_sayisi", "skor_icerik_yayilimi", "skor_guvenilir_kaynak",
]


def egit_ve_degerlendir(X: np.ndarray, y: np.ndarray) -> dict:
    """
    X: (n_ornek, 6) risk bileşenleri matrisi (risk_scoring.py çıktılarından)
    y: (n_ornek,) 1=gerçek kriz, 0=sıradan/yanlış alarm (frontend feedback alanından)

    NOT: Üretimde RandomForest yerine LightGBM/XGBoost (Bölüm 9'da belirtilen)
    kullanılması önerilir; bu iskelet, harici ağır bağımlılık eklemeden
    (LightGBM derleme bağımlılıkları gerektirir) ilk doğrulamayı scikit-learn
    ile yapabilmek için RandomForest ile yazılmıştır. API'si (fit/predict)
    birebir aynı olduğundan geçiş tek satırdır.
    """
    if len(X) < 30:
        return {
            "durum": "yetersiz_veri",
            "mesaj": f"Güvenilir eğitim için en az 30 etiketli örnek gerekir, mevcut: {len(X)}.",
        }

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42, class_weight="balanced")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrikler = {
        "accuracy": round(accuracy_score(y_test, y_pred), 3),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
        "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 3),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 3) if len(set(y_test)) > 1 else None,
        "ozellik_onemleri": dict(zip(FEATURE_COLUMNS, [round(v, 3) for v in model.feature_importances_])),
    }
    return {"durum": "basarili", "metrikler": metrikler, "model": model}


if __name__ == "__main__":
    # Örnek/demo: sentetik veriyle iskeletin çalıştığını doğrulamak için.
    # GERÇEK KULLANIMDA bu blok, veritabanından gerçek etiketli veriyi
    # çeken bir sorguyla değiştirilmelidir.
    rng = np.random.default_rng(42)
    X_demo = rng.uniform(0, 25, size=(50, 6))
    y_demo = (X_demo.sum(axis=1) > 75).astype(int)
    sonuc = egit_ve_degerlendir(X_demo, y_demo)
    print(sonuc.get("metrikler", sonuc))
