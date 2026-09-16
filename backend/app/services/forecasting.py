"""
Bölüm 10: Kriz Tahminleme Modülü.

Faz 7 GÜNCELLEMESİ: Prophet (Taylor & Letham, 2018, "Forecasting at Scale")
bu ortamda GERÇEKTEN kurulmuş ve test edilmiştir (bkz. requirements.txt notu
— 1.3.0 sürümü Windows'ta prebuilt cmdstan wheel'iyle geldiği için 1.1.6'nın
aksine ayrı bir C++ derleyici zinciri gerekmedi). Ancak Prophet, anlamlı
mevsimsellik/trend ayrıştırması için genellikle onlarca-yüzlerce gözlem
ister; bu erken aşama sistemde henüz o hacimde geçmiş veri birikmediğinden
İKİ katmanlı bir tasarım korunur:

  - < PROPHET_MIN_GOZLEM (24) gözlem: ağırlıklı doğrusal trend ekstrapolasyonu
    (hızlı, az veriyle bile makul, hiçbir bağımlılık gerektirmez).
  - >= PROPHET_MIN_GOZLEM gözlem: Prophet devreye girer (trend + belirsizlik
    aralığı/uncertainty interval ile gerçek olasılıksal tahmin).

Prophet çalıştırılamazsa (kurulu değil VEYA çalışma zamanı hatası — ör. bu
makinede cmdstan ikili dosyası bir nedenle bulunamazsa) sistem OTOMATİK
olarak ağırlıklı-doğrusal-trend'e düşer; hiçbir zaman çökmez. API sözleşmesi
(girdi: son N risk skoru; çıktı: {ufuk: tahmin}) her iki yöntem için AYNIDIR.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

PROPHET_MIN_GOZLEM = 24  # Prophet'in anlamlı trend/belirsizlik tahmini için pratik alt sınır


def _agirlikli_egim(skorlar: list[float]) -> float:
    """Son gözlemlere daha fazla ağırlık veren basit doğrusal regresyon eğimi."""
    n = len(skorlar)
    x = np.arange(n)
    agirliklar = np.linspace(0.5, 1.5, n)  # son noktalar daha ağır
    egim, _ = np.polyfit(x, skorlar, 1, w=agirliklar)
    return float(egim)


def _dogrusal_trend_tahmini(gecmis_risk_skorlari: list[float]) -> dict:
    son_deger = gecmis_risk_skorlari[-1]
    egim = _agirlikli_egim(gecmis_risk_skorlari)

    def sinirla(v: float) -> float:
        return max(0.0, min(100.0, v))

    return {
        "24s": round(sinirla(son_deger + egim * 24), 2),
        "72s": round(sinirla(son_deger + egim * 72 * 0.6), 2),   # belirsizlik arttıkça eğim etkisi azaltılır
        "7g": round(sinirla(son_deger + egim * 168 * 0.3), 2),
        "yontem": "agirlikli_dogrusal_trend",
        "guven_notu": (
            f"Az veri ({len(gecmis_risk_skorlari)} gözlem, Prophet eşiği: "
            f"{PROPHET_MIN_GOZLEM}) nedeniyle basit ekstrapolasyon kullanıldı. "
            "Yeterli geçmiş veri biriktiğinde Prophet otomatik devreye girer."
        ),
    }


def _prophet_tahmini(gecmis_risk_skorlari: list[float]) -> dict | None:
    """Gözlemlerin SAATLİK örneklendiği varsayılır (mevcut sistem sözleşmesi);
    zaman damgaları bu varsayımla, en güncel gözlem 'şimdi' olacak şekilde
    geriye doğru sentezlenir (gerçek zaman damgaları biriktiğinde -- bkz.
    DenetimKaydi.zaman -- bu fonksiyon gerçek 'ds' değerleriyle çağrılabilir)."""
    try:
        import pandas as pd
        from prophet import Prophet
    except ImportError:
        return None

    n = len(gecmis_risk_skorlari)
    simdi = datetime.utcnow()
    zamanlar = [simdi - timedelta(hours=(n - 1 - i)) for i in range(n)]
    df = pd.DataFrame({"ds": zamanlar, "y": gecmis_risk_skorlari})

    try:
        model = Prophet(interval_width=0.8, daily_seasonality=False, weekly_seasonality=n >= 24 * 7)
        model.fit(df)
        gelecek = model.make_future_dataframe(periods=168, freq="h")  # 7 gün ileriye kadar saatlik
        tahmin = model.predict(gelecek)
    except Exception:
        return None  # cmdstan çalışma zamanı hatası vb. — graceful fallback

    def _saat_sonrasi(saat: int) -> float:
        hedef_zaman = simdi + timedelta(hours=saat)
        idx = (tahmin["ds"] - hedef_zaman).abs().idxmin()
        return float(max(0.0, min(100.0, tahmin.loc[idx, "yhat"])))

    return {
        "24s": round(_saat_sonrasi(24), 2),
        "72s": round(_saat_sonrasi(72), 2),
        "7g": round(_saat_sonrasi(168), 2),
        "yontem": "prophet",
        "guven_notu": (
            f"Prophet (Taylor & Letham, 2018) ile {n} saatlik gözlemden trend "
            "tahmini üretildi (%80 belirsizlik aralığı iç hesaplamada kullanıldı). "
        ),
    }


def tahmin_uret(gecmis_risk_skorlari: list[float]) -> dict:
    """
    gecmis_risk_skorlari: saatlik örneklenmiş, en az 4 nokta önerilir.
    Dönüş: {"24s": .., "72s": .., "7g": .., "yontem": ..., "guven_notu": ...}
    """
    if len(gecmis_risk_skorlari) < 4:
        son = gecmis_risk_skorlari[-1] if gecmis_risk_skorlari else 0.0
        return {
            "24s": round(son, 2), "72s": round(son, 2), "7g": round(son, 2),
            "yontem": "yetersiz_veri_son_deger_korunumu",
            "guven_notu": "Güvenilir tahmin için en az 4 saatlik gözlem gerekir.",
        }

    if len(gecmis_risk_skorlari) >= PROPHET_MIN_GOZLEM:
        prophet_sonuc = _prophet_tahmini(gecmis_risk_skorlari)
        if prophet_sonuc is not None:
            return prophet_sonuc

    return _dogrusal_trend_tahmini(gecmis_risk_skorlari)
