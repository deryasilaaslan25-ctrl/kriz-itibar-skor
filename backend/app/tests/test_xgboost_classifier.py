from app.ml.xgboost_classifier import (
    RiskOzellikVektoru, XGBoostRiskSiniflandirici, FEATURE_ISIMLERI, MIN_EGITIM_ORNEGI,
)


def test_ozellik_vektoru_bilesenlerden_dogru_sirada_olusur():
    bilesenler = {isim: float(i) for i, isim in enumerate(FEATURE_ISIMLERI)}
    vektor = RiskOzellikVektoru.bilesenlerden(bilesenler)
    assert len(vektor.degerler) == len(FEATURE_ISIMLERI)
    assert vektor.degerler[0] == 0.0
    assert vektor.degerler[-1] == float(len(FEATURE_ISIMLERI) - 1)


def test_eksik_bilesen_sifir_kabul_edilir():
    vektor = RiskOzellikVektoru.bilesenlerden({})
    assert all(v == 0.0 for v in vektor.degerler)


def test_yetersiz_veri_ile_egitim_reddedilir():
    siniflandirici = XGBoostRiskSiniflandirici()
    sonuc = siniflandirici.egit(X=[[0.0] * len(FEATURE_ISIMLERI)] * 5, y=[0] * 5)
    assert sonuc["durum"] == "yetersiz_veri"
    assert sonuc["gereken_ornek"] == MIN_EGITIM_ORNEGI


def test_egitilmemis_model_tahmin_none_doner():
    siniflandirici = XGBoostRiskSiniflandirici()
    vektor = RiskOzellikVektoru.bilesenlerden({})
    assert siniflandirici.tahmin_et(vektor) is None
    assert siniflandirici.shap_aciklama(vektor) is None
