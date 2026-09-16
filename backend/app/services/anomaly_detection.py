"""
Bölüm 11: Anomali Tespiti.

Krizler çoğu zaman ani hacim/duygu yükselişleriyle başlar. Bu modül,
scikit-learn'ün IsolationForest algoritmasını zaman serisi üzerinde
kullanarak "normal" davranış paterninden sapan noktaları tespit eder.

Neden Isolation Forest?
- Etiketli veri gerektirmez (unsupervised) -> soğuk başlangıç (cold start)
  probleminde bile çalışır, bu erken aşamadaki bir sistem için kritiktir.
- Az veri ile de (>= 10-15 gözlem) makul sonuç verir.
- Hesaplama maliyeti düşüktür, gerçek zamanlı tarama döngüsüne uygundur.

Local Outlier Factor (LOF) ve One-Class SVM alternatifleri de
`AnomalyMethod` enum'u ile desteklenir; jüri sunumunda karşılaştırmalı
sonuç göstermek için üçü de aynı arayüzden çağrılabilir.
"""
from __future__ import annotations

from enum import Enum

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM


class AnomalyMethod(str, Enum):
    ISOLATION_FOREST = "isolation_forest"
    LOCAL_OUTLIER_FACTOR = "lof"
    ONE_CLASS_SVM = "one_class_svm"


def tespit_et(
    zaman_serisi: list[float],
    yontem: AnomalyMethod = AnomalyMethod.ISOLATION_FOREST,
    contamination: float = 0.1,
) -> dict:
    """
    zaman_serisi: örn. son N saatteki hacim veya negatif-duygu-oranı değerleri.
    Dönüş: {"anomali_indeksleri": [...], "skorlar": [...], "son_nokta_anomali_mi": bool}
    """
    if len(zaman_serisi) < 8:
        return {
            "anomali_indeksleri": [],
            "skorlar": [],
            "son_nokta_anomali_mi": False,
            "not": "Güvenilir anomali tespiti için en az 8 gözlem gerekir.",
        }

    X = np.array(zaman_serisi).reshape(-1, 1)

    if yontem == AnomalyMethod.ISOLATION_FOREST:
        model = IsolationForest(contamination=contamination, random_state=42)
        etiketler = model.fit_predict(X)          # -1 = anomali, 1 = normal
        skorlar = model.decision_function(X)
    elif yontem == AnomalyMethod.LOCAL_OUTLIER_FACTOR:
        model = LocalOutlierFactor(n_neighbors=min(5, len(X) - 1), contamination=contamination)
        etiketler = model.fit_predict(X)
        skorlar = model.negative_outlier_factor_
    else:  # ONE_CLASS_SVM
        model = OneClassSVM(nu=contamination, kernel="rbf", gamma="auto")
        etiketler = model.fit_predict(X)
        skorlar = model.decision_function(X)

    anomali_idx = [i for i, e in enumerate(etiketler) if e == -1]

    return {
        "anomali_indeksleri": anomali_idx,
        "skorlar": [round(float(s), 4) for s in skorlar],
        "son_nokta_anomali_mi": bool(len(etiketler) and etiketler[-1] == -1),
        "yontem": yontem.value,
    }
