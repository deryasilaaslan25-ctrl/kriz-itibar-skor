"""XGBoost bilgi-damıtma eğitimi testleri — Faz 7.

xgboost/shap kurulu değilse bu testler graceful biçimde 'bagimlilik_eksik'
durumunu doğrular (çökmeden); bu ortamda ikisi de kurulu olduğundan GERÇEK
eğitim ve GERÇEK SHAP hesaplaması test edilir.
"""
from app.ml.distillation import sentetik_egitim_verisi_uret, egit_ve_raporla
from app.ml.xgboost_classifier import FEATURE_ISIMLERI, MIN_EGITIM_ORNEGI


def test_sentetik_veri_dogru_boyutta_ve_ikili_etiketli():
    X, y = sentetik_egitim_verisi_uret(n=250, seed=1)
    assert len(X) == len(y) == 250
    assert all(len(satir) == len(FEATURE_ISIMLERI) for satir in X)
    assert set(y).issubset({0, 1})


def test_egitim_gercekten_calisir_ve_holdout_dogruluk_makul():
    sonuc = egit_ve_raporla(n_ornek=max(300, MIN_EGITIM_ORNEGI + 50), seed=7)
    if sonuc["durum"] == "bagimlilik_eksik":
        import pytest
        pytest.skip("xgboost kurulu değil bu ortamda — graceful degradation zaten doğrulanmış tasarım.")
    assert sonuc["durum"] == "egitildi_ve_degerlendirildi"
    # Damıtma eğitimi kural motorunu makul doğrulukla öğrenmeli (kesin bir
    # eşik değil, ama tamamen rastgele bir modelden -0.5 çok daha iyi olmalı)
    assert sonuc["holdout_dogruluk"] > 0.7
    assert sonuc["shap_degerleri"] is not None
    assert set(sonuc["shap_degerleri"].keys()) == set(FEATURE_ISIMLERI)
    assert "GERÇEK DÜNYA" in sonuc["onemli_uyari"]  # dürüstlük uyarısı her zaman bulunmalı
