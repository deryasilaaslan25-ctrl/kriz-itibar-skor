"""
EWMA (Exponentially Weighted Moving Average) Tabanlı Hacim Anomali Tespiti.

Document 121 s.3'te tanımlanan formülü birebir uygular:

    μₜ = γVₜ + (1−γ)μₜ₋₁
    σₜ² = γ(Vₜ−μₜ)² + (1−γ)σₜ₋₁²
    Z_hacim(t) = (Vₜ − μₜ) / σₜ

Literatür
---------
- Roberts, S. W. (1959), "Control Chart Tests Based on Geometric Moving
  Averages", Technometrics, 1(3), 239–250 — EWMA kontrol şemasının orijinal
  tanımı; istatistiksel süreç kontrolünde (SPC) durağan olmayan (non-stationary)
  zaman serilerinde ani sapmaları, sabit bir eşikten çok daha güvenilir
  biçimde yakalamak için geliştirilmiştir.
- Montgomery, D. C., Introduction to Statistical Quality Control (ders kitabı,
  EWMA kontrol şemaları standart referansı) — γ (düzeltme/"smoothing"
  katsayısı) için 0.05-0.25 aralığının pratikte en sık kullanılan aralık
  olduğunu belirtir; bu modülde γ=0.2 varsayılan alınmıştır (orta hafıza).

Neden EWMA (Document 122'nin eleştirdiği "sabit eşik değer, örn. >100 tweet"
yerine)?
Sabit bir eşik her kurum/sektör için farklı temel hacme (baseline) sahip
olduğundan yanlış pozitif/negatif üretir: küçük bir STK için 50 gönderi/saat
anomaliyken büyük bir ulusal marka için gürültüdür. EWMA, HER kurumun kendi
geçmişine göre normalleşen adaptif bir temel çizgi (baseline: μₜ, σₜ) tutar;
böylece "10 kişilik bir esnaf hesabı" ile "10 milyon takipçili bir marka"
AYNI algoritmayla, kendi ölçeğine göre tutarlı biçimde değerlendirilir. Bu,
risk_scoring.py'deki "trend_artisi" bileşeninin önceki sürümdeki basit
yüzde-değişim hesaplamasının (`(guncel-onceki)/onceki`) yerini alır — o
hesap tek bir önceki döneme bakar ve gürültüye karşı savunmasızdır; EWMA
Z-skoru TÜM geçmişin ağırlıklı hafızasını kullanır.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Literatürde SPC EWMA şemalarında yaygın kullanılan düzeltme katsayısı aralığı
# (Montgomery): 0.05 (uzun hafıza / yavaş tepki) - 0.25 (kısa hafıza / hızlı
# tepki). 0.2, kriz erken uyarı bağlamında "gürültüye aşırı duyarlı olmadan
# makul hızda tepki verme" dengesini sağladığı için seçilmiştir.
VARSAYILAN_GAMMA = 0.2

# İstatistikte |Z| > 3 klasik olarak "aşırı uç değer" eşiği kabul edilir
# (3-sigma kuralı: normal dağılımda gözlemlerin >%99.7'si bu aralıkta kalır).
# Bu yüzden risk bileşenine dönüştürülürken Z=3 -> normalize edilmiş 1.0
# (tam doygunluk) alınır.
DOYGUNLUK_Z = 3.0


@dataclass
class EwmaDurumu:
    """Bir kurumun hacim EWMA hesaplama durumu (zaman serisinde taşınır)."""

    mu: float = 0.0
    sigma2: float = 0.0
    baslatildi: bool = False


def guncelle(durum: EwmaDurumu, v_t: float, gamma: float = VARSAYILAN_GAMMA) -> tuple[EwmaDurumu, float]:
    """Tek bir yeni gözlemle EWMA durumunu günceller, o anki Z-skorunu döner.

    İlk gözlemde (baslatildi=False) μ₀=V₀, σ₀²=0 alınır (ısınma noktası);
    Z=0.0 döner çünkü henüz bir varyans tahmini yoktur.
    """
    if not durum.baslatildi:
        return EwmaDurumu(mu=v_t, sigma2=0.0, baslatildi=True), 0.0

    mu_t = gamma * v_t + (1 - gamma) * durum.mu
    sigma2_t = gamma * (v_t - mu_t) ** 2 + (1 - gamma) * durum.sigma2
    sigma_t = math.sqrt(sigma2_t)
    z = (v_t - mu_t) / sigma_t if sigma_t > 1e-9 else 0.0
    return EwmaDurumu(mu=mu_t, sigma2=sigma2_t, baslatildi=True), z


def z_skoru_serisi(zaman_serisi: list[float], gamma: float = VARSAYILAN_GAMMA) -> list[float]:
    """Bir hacim zaman serisinin TAMAMI için EWMA Z-skorlarını hesaplar
    (ısınma dönemi dahil). Son eleman, "şu anki" hacim anomalisi sinyalidir."""
    durum = EwmaDurumu()
    sonuclar: list[float] = []
    for v in zaman_serisi:
        durum, z = guncelle(durum, v, gamma)
        sonuclar.append(round(z, 4))
    return sonuclar


def son_z_skoru(zaman_serisi: list[float], gamma: float = VARSAYILAN_GAMMA) -> float:
    """Bir zaman serisindeki EN GÜNCEL hacim anomali Z-skoru (risk_scoring.py
    'trend_artisi'/'paylasim_hizi' bileşenlerinin girdisi)."""
    if not zaman_serisi:
        return 0.0
    return z_skoru_serisi(zaman_serisi, gamma)[-1]


def normalize_0_1(z: float, doygunluk_z: float = DOYGUNLUK_Z) -> float:
    """EWMA Z-skorunu [0,1] aralığına sıkıştırır (risk bileşeni girdisi için).

    Yalnızca POZİTİF sapmalar (hacim artışı = kriz sinyali) dikkate alınır;
    negatif Z (hacim düşüşü) risk açısından nötr kabul edilip 0'a kırpılır.
    """
    return max(0.0, min(1.0, z / doygunluk_z))
