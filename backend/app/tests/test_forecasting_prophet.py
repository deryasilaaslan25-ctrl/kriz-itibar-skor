"""Prophet tabanlı zaman serisi tahmini testleri — Faz 7.

Bu ortamda Prophet GERÇEKTEN kurulu ve çalışır durumdadır (bkz. requirements.txt
notu); bu testler gerçek Prophet.fit()/predict() çağrısını tetikler.
"""
import random

from app.services.forecasting import tahmin_uret, PROPHET_MIN_GOZLEM


def test_az_veriyle_dogrusal_trend_kullanilir():
    sonuc = tahmin_uret([40, 42, 45, 48, 50])
    assert sonuc["yontem"] == "agirlikli_dogrusal_trend"


def test_yeterli_veriyle_prophet_gercekten_calisir():
    random.seed(0)
    seri = [50 + i * 0.5 + random.uniform(-2, 2) for i in range(PROPHET_MIN_GOZLEM + 5)]
    sonuc = tahmin_uret(seri)
    assert sonuc["yontem"] == "prophet"
    assert 0 <= sonuc["24s"] <= 100
    assert 0 <= sonuc["72s"] <= 100
    assert 0 <= sonuc["7g"] <= 100


def test_prophet_yukselen_trendi_yakalamali():
    """Belirgin biçimde artan bir seride Prophet'in 24s tahmini, son
    gözlenen değerin çok altında olmamalı (trend yönünü doğru okumalı)."""
    seri = [30 + i * 1.2 for i in range(PROPHET_MIN_GOZLEM + 10)]
    sonuc = tahmin_uret(seri)
    assert sonuc["yontem"] == "prophet"
    assert sonuc["24s"] >= seri[-1] - 5
