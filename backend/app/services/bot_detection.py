"""
Bölüm 12: Bot Tespiti — Manipülasyon Ayrıştırma.

Etiketli bot veri seti olmadan (henüz) denetimli bir sınıflandırıcı
eğitmek yanıltıcı olacağından, bu modül literatürde kabul görmüş
(Botometer, Yang vd. 2020) dört ağırlıklı davranışsal sinyali birleştiren
şeffaf bir skorlama fonksiyonu kullanır. Yeterli etiketli veri
toplandığında `app/ml/train_pipeline.py` üzerinden bir
LightGBM/XGBoost sınıflandırıcısına geçiş için hazır arayüz sağlanır
(bkz. BotClassifier ABC).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BotSinyalleri:
    hesap_yasi_gun: int
    son_24s_paylasim_sayisi: int
    tekrarlayan_icerik_orani: float   # 0-1
    hashtag_yogunlugu: float           # ortalama hashtag / gönderi


class BotClassifier(ABC):
    @abstractmethod
    def skorla(self, sinyaller: BotSinyalleri) -> float: ...


class HeuristicBotClassifier(BotClassifier):
    """0 (kesin insan) - 1 (kesin bot) arası ağırlıklı skor."""

    W_HESAP_YASI = 0.30
    W_PAYLASIM_SIKLIGI = 0.25
    W_TEKRAR_ICERIK = 0.30
    W_HASHTAG = 0.15

    def skorla(self, s: BotSinyalleri) -> float:
        # Hesap yaşı: 30 günden yeni hesaplar şüpheli, 365+ gün güvenli kabul edilir
        yas_riski = max(0.0, 1 - s.hesap_yasi_gun / 365)

        # Paylaşım sıklığı: günde 50+ paylaşım insan davranışının çok üzerinde
        siklik_riski = min(1.0, s.son_24s_paylasim_sayisi / 100)

        # Tekrarlayan içerik oranı doğrudan risk sinyali
        tekrar_riski = min(1.0, s.tekrarlayan_icerik_orani)

        # Hashtag yoğunluğu: gönderi başına 8+ hashtag spam/bot paternidir
        hashtag_riski = min(1.0, s.hashtag_yogunlugu / 8)

        skor = (
            self.W_HESAP_YASI * yas_riski
            + self.W_PAYLASIM_SIKLIGI * siklik_riski
            + self.W_TEKRAR_ICERIK * tekrar_riski
            + self.W_HASHTAG * hashtag_riski
        )
        return round(min(1.0, skor), 3)


def get_bot_classifier() -> BotClassifier:
    return HeuristicBotClassifier()


# ---------------------------------------------------------------------------
# Benford Kanunu Tabanlı Manipülasyon/Koordinasyon Testi
# ---------------------------------------------------------------------------
# Document 121 s.3: 16-bileşenli risk motorunun "Bot Aktivitesi" bileşenini
# tek bir heuristic sinyale (yukarıdaki HeuristicBotClassifier) bağımlı
# bırakmak yerine, davranışsal sinyallerden BAĞIMSIZ, sayısal bir istatistiksel
# test ile çapraz doğrulamak için eklenmiştir.
#
# Benford Kanunu (Newcomb 1881; Benford, F. (1938), "The Law of Anomalous
# Numbers", Proceedings of the American Philosophical Society, 78(4)):
# doğal/organik biçimde oluşan (insan davranışından türeyen, manipüle
# edilmemiş) sayı kümelerinde ilk basamağın d olma olasılığı
#     P(d) = log10(1 + 1/d),  d ∈ {1,...,9}
# dağılımını izler (1 rakamı ~%30.1, 9 rakamı ~%4.6 ile başlar). Bu kanun
# muhasebe denetiminde sahte kayıt tespiti (Nigrini, M. J. (1999), "I've Got
# Your Number", Journal of Accountancy) ve sosyal medyada koordineli/bot
# davranış tespitinde (paylaşım sayıları, yorum sayıları, hesap oluşturma
# zaman damgaları gibi ORGANİK OLMASI BEKLENEN sayısal serilerin doğal
# dağılımdan sapması -> yapay/koordineli üretim şüphesi) kullanılır.
#
# Bu modülde, bir kriz kümesindeki içeriklerin ETKİLEŞİM SAYILARI (beğeni,
# paylaşım, yorum) test edilir: organik bir kriz tepkisinde bu sayılar geniş
# bir aralığa yayılır ve Benford dağılımını yaklaşık izler; koordineli bir
# bot ağı (ör. hepsi "50 retweet" civarında sabitlenmiş sahte hesaplar)
# belirgin biçimde sapar.
import math
from collections import Counter

_BENFORD_BEKLENEN = {d: math.log10(1 + 1 / d) for d in range(1, 10)}

# Benford testi az sayıda gözlemle güvenilir değildir (istatistiksel güç
# düşük kalır); denetim literatüründe (Nigrini) yaygın pratik en az 50-100
# gözlem önerir. Bu eşiğin altında sonuç ÜRETİLMEZ (None) — "veri yok" ile
# "manipülasyon yok" birbirine karıştırılmamalıdır.
BENFORD_MIN_GOZLEM = 50


def _ilk_basamak(sayi: int) -> int | None:
    sayi = abs(int(sayi))
    if sayi == 0:
        return None
    while sayi >= 10:
        sayi //= 10
    return sayi if sayi >= 1 else None


def benford_sapma_skoru(sayisal_seri: list[int]) -> tuple[float | None, str]:
    """Bir sayısal serinin (ör. içerik etkileşim sayıları) ilk-basamak
    dağılımının Benford Kanunu'ndan sapmasını ki-kare testiyle ölçer.

    Dönüş: (skor, açıklama)
      skor ∈ [0,1]: 1 - p_değeri olarak hesaplanır (p_değeri ne kadar
      düşükse, yani gözlenen dağılım Benford'dan ne kadar anlamlı biçimde
      sapıyorsa, skor o kadar yüksek/şüpheli olur). Klasik %5 anlamlılık
      eşiği: skor > 0.95 -> istatistiksel olarak anlamlı sapma.
      Yetersiz veri varsa (< BENFORD_MIN_GOZLEM) skor=None döner.
    """
    basamaklar = [b for b in (_ilk_basamak(s) for s in sayisal_seri) if b is not None]
    n = len(basamaklar)
    if n < BENFORD_MIN_GOZLEM:
        return None, (
            f"Benford testi için yetersiz veri ({n}/{BENFORD_MIN_GOZLEM} gözlem) — "
            "bu sinyal risk skoruna dahil edilmedi."
        )

    sayac = Counter(basamaklar)
    gozlenen = [sayac.get(d, 0) for d in range(1, 10)]
    beklenen = [_BENFORD_BEKLENEN[d] * n for d in range(1, 10)]

    try:
        from scipy.stats import chisquare
        istatistik, p_degeri = chisquare(f_obs=gozlenen, f_exp=beklenen)
    except ImportError:
        # scipy yoksa (scikit-learn'ün örtük bağımlılığı olduğundan normalde
        # kurulu olur) manuel ki-kare hesapla + serbestlik derecesi 8 için
        # kaba bir p-değeri yaklaşıklaması yerine doğrudan istatistiği [0,1]'e
        # sıkıştırılmış bir "sapma skoruna" çevir (daha az kesin ama asla çökmez).
        istatistik = sum((o - e) ** 2 / e for o, e in zip(gozlenen, beklenen) if e > 0)
        skor = max(0.0, min(1.0, 1 - math.exp(-istatistik / 30.0)))
        return round(skor, 3), (
            f"scipy kurulu değil; ki-kare istatistiği ({istatistik:.2f}) doğrudan "
            "[0,1] aralığına sıkıştırılarak yaklaşık skor üretildi (p-değeri değil)."
        )

    skor = round(max(0.0, min(1.0, 1 - p_degeri)), 3)
    yorum = "istatistiksel olarak anlamlı sapma (p<0.05) — koordineli/bot davranış şüphesi" if p_degeri < 0.05 else "Benford dağılımına yakın — organik davranışla tutarlı"
    return skor, f"χ²={istatistik:.2f}, p={p_degeri:.4f} ({n} gözlem) — {yorum}"


def kombine_bot_skoru(
    heuristic_skor: float,
    etkilesim_serisi: list[int] | None = None,
) -> tuple[float, dict]:
    """HeuristicBotClassifier çıktısını (davranışsal sinyaller) Benford testi
    sonucuyla (sayısal dağılım sinyali) birleştirir — iki BAĞIMSIZ kanıt
    kaynağının ortalaması, tek bir sinyale güvenmekten daha sağlam bir
    tahmin üretir (ensemble/çoklu-kanıt prensibi).

    Benford testi çalıştırılamazsa (yetersiz veri) yalnızca heuristic skor
    kullanılır — sistem asla bu ek sinyale sıkı bağımlı değildir.
    """
    detay = {"heuristic_skor": heuristic_skor, "benford_skor": None, "benford_not": None}
    if not etkilesim_serisi:
        return heuristic_skor, detay

    benford_skor, benford_not = benford_sapma_skoru(etkilesim_serisi)
    detay["benford_skor"] = benford_skor
    detay["benford_not"] = benford_not
    if benford_skor is None:
        return heuristic_skor, detay

    kombine = round(0.65 * heuristic_skor + 0.35 * benford_skor, 3)
    return kombine, detay
