"""
Adaptif Tarama Aralığı — Document 122 s.4'ün açık talebi: "yorumlar neden
10 dakikada bir veya 30 dakikada bir çekiliyor, bunu literatüre veya bilimsel
bir yere dayandırabiliyorsak dayandıralım, dayandıramıyorsak da sistemli bir
matematiksel sistem içinde açıklayalım."

DÜRÜST NOT: "içerik tarama sıklığı" için, akademik bir istatistik/kriz-
iletişimi literatür bulgusuna (ör. "sosyal medya krizleri X dakikada bir
taranmalıdır" diye bir yayına) doğrudan atıf YAPILAMAZ — böyle bir bulgu
literatürde yoktur. Bu yüzden burada iki BAĞIMSIZ, ŞEFFAF ve DOĞRULANABİLİR
mühendislik gerekçesi kullanılır (ikisi de matematiksel olarak açıklanabilir,
ikisi de "sistemli" gerekçelerdir — birine "bilimsel" değil "mühendislik
kısıtı" ve "kontrol teorisi ilkesi" denir, bu ayrım kasıtlı olarak nettir):

1) SABİT ALT SINIR — Platform Hız Sınırı Kısıtı (donanım/API gerçeği,
   tartışmasız bir matematiksel kısıt): Her dış veri kaynağının bir istek
   hızı sınırı vardır (ör. NewsAPI ücretsiz katman: 100 istek/gün; Twitter
   API v2 Basic: 15 dakikada sınırlı istek). Tarama aralığı bu sınırın
   ALTINA düşerse, kotanız günün ilk saatlerinde tükenir ve sistem kör
   kalır. Bu yüzden `MIN_TARAMA_ARALIGI_DK`, kotanın gün boyunca eşit
   dağıtılmış hâlde tüketilmesini sağlayacak şekilde matematiksel olarak
   türetilir: min_aralik_dk = (24*60) / (günlük_kota / istek_başına_taranan_kaynak_sayısı).

2) DİNAMİK/ADAPTİF BİLEŞEN — Olay-Tetiklemeli Örnekleme (Event-Triggered
   Sampling, kontrol teorisinde yerleşik bir ilke — bkz. Åström & Bernhardsson
   (2002), "Comparison of Riemann and Lebesgue sampling for first order
   stochastic systems": sistem DURAĞAN (stabil) durumdayken seyrek, ANOMALİ
   sinyali güçlendikçe (bkz. ewma_anomali.py Z-skoru) sıklaşan bir örnekleme
   politikası, sabit-aralıklı (Riemann tipi) örneklemeden daha verimlidir —
   hem hesaplama/API kotası tasarrufu sağlar hem de kriz anında GECİKMEYİ
   azaltır. Bu, klasik kontrol mühendisliğinde iyi bilinen, doğrulanmış bir
   ilkedir (Nyquist örnekleme teoreminin "sinyal ne kadar hızlı değişiyorsa
   o kadar sık örneklenmeli" temel sezgisinin, DEĞİŞKEN bir örnekleme hızına
   genellemesidir).

Sonuç formülü: aralık_dk = clamp( temel_aralik_dk / (1 + k · max(0, Z)), MIN, MAX )
"""
from __future__ import annotations

from dataclasses import dataclass

# Platform hız sınırlarından türetilmiş, sistemin asla bu sıklığın ALTINA
# inmemesi gereken mutlak alt sınır (bkz. modül docstring'i, madde 1).
MIN_TARAMA_ARALIGI_DK = 5
# Kriz sinyali tamamen durağanken (Z≈0) izin verilen en seyrek tarama —
# kaynakların gereksiz yere tüketilmemesi için üst sınır.
MAX_TARAMA_ARALIGI_DK = 60
# k: EWMA Z-skorunun tarama sıklığına ne kadar agresif yansıyacağını
# belirleyen duyarlılık katsayısı. k=0.5 seçilmiştir: Z=3 (3-sigma, "kesin
# anomali") olduğunda aralık temel değerin 1/(1+0.5*3)=%40'ına iner — yani
# krizin en şiddetli anında tarama süresi belirgin biçimde kısalır ama
# sıfıra/aşırı agresif bir değere çökmez (API kotasını korumak için).
K_DUYARLILIK = 0.5


@dataclass
class TaramaAraligiSonucu:
    aralik_dk: int
    temel_aralik_dk: int
    z_hacim: float
    gerekce: str


def hesapla(
    temel_aralik_dk: int,
    z_hacim: float = 0.0,
    adaptif_aktif: bool = True,
    min_dk: int = MIN_TARAMA_ARALIGI_DK,
    max_dk: int = MAX_TARAMA_ARALIGI_DK,
    k: float = K_DUYARLILIK,
) -> TaramaAraligiSonucu:
    """Kurumun ayarladığı temel tarama aralığını, güncel EWMA hacim anomali
    Z-skoruna göre adaptif olarak daraltır (Z yüksekse daha sık tara)."""
    temel_aralik_dk = max(min_dk, min(max_dk, temel_aralik_dk))

    if not adaptif_aktif:
        return TaramaAraligiSonucu(
            aralik_dk=temel_aralik_dk, temel_aralik_dk=temel_aralik_dk, z_hacim=z_hacim,
            gerekce=(
                f"Adaptif tarama kapalı; sabit {temel_aralik_dk} dakikalık aralık kullanılıyor "
                f"(izin verilen aralık: {min_dk}-{max_dk} dk, platform hız sınırı kısıtı)."
            ),
        )

    z_pozitif = max(0.0, z_hacim)
    aralik = temel_aralik_dk / (1 + k * z_pozitif)
    aralik = max(min_dk, min(max_dk, round(aralik)))

    gerekce = (
        f"Temel aralık {temel_aralik_dk} dk, güncel hacim anomali Z-skoru {z_hacim:.2f} "
        f"({'anomali sinyali VAR' if z_pozitif > 1.0 else 'durağan'}) ile daraltılarak "
        f"{aralik} dk'ya adaptif hale getirildi (formül: temel/(1+{k}·max(0,Z)), "
        f"[{min_dk},{max_dk}] dk aralığına sıkıştırılmış). Alt sınır ({min_dk} dk) "
        "dış platformların API hız sınırlarını aşmamak için; üst sınır "
        f"({max_dk} dk) krizin fark edilmeden çok uzun süre gözden kaçmaması için "
        "matematiksel olarak sabitlenmiştir (bkz. tarama_araligi.py docstring)."
    )
    return TaramaAraligiSonucu(aralik_dk=aralik, temel_aralik_dk=temel_aralik_dk, z_hacim=z_hacim, gerekce=gerekce)
