"""
Faz 10: Çok Dilli Analiz Desteği — Dil Tespiti.

Neden gerekli? Sistem artık YouTube (bkz. app/collectors/connectors.py
YouTubeCollector) gibi kaynaklardan veri çekiyor; YouTube, Reddit ve haber
kaynakları TEK bir dille sınırlı değildir — küresel/çok uluslu izleyicisi
olan bir kurumun videosuna İngilizce, Almanca, Arapça, Rusça vb. dillerde
yorum gelebilir. Önceki sürümde `sentiment.py` YALNIZCA Türkçe sözlük/model
kullandığından bu yorumlar ya yanlış (nötr) sınıflandırılıyor ya da hiç
dikkate alınmıyordu — bu, kriz sinyalinin kaçırılması demektir (ör. bir
ürünün yurt dışında toplu şikayet konusu olması, yalnızca Türkçe sözlükle
görünmez kalır).

Bu modül, her içeriğin dilini TESPİT EDER; `sentiment.py` bu bilgiyi
kullanarak dile uygun duygu analiz motorunu (bkz. get_sentiment_analyzer)
seçer.

Tasarım Kararı: langdetect (anahtarsız, çevrimdışı, ücretsiz)
------------------------------------------------------------
Google Çeviri/Cloud Translation API gibi bulut servisleri hem bir API
anahtarı hem de (genellikle) ücretli bir plan gerektirir — kullanıcının
hiçbiri yoktur. `langdetect`, Google'ın eski, artık kapalı kaynak olmayan
"language-detection" kütüphanesinin (Nakatani Shuyo) Python portudur;
tamamen yerel çalışır, ağ çağrısı yapmaz, 55+ dili destekler ve MIT
lisanslıdır. Kısa/gürültülü metinlerde (tek kelimelik yorumlar, emoji
ağırlıklı metin) güvenilirliği düşebilir — bu yüzden ANLAMLI uzunluktaki
metinlerde çalıştırılır ve düşük güvenli/başarısız tespitlerde sistemin
varsayılan dili olan Türkçe'ye GÜVENLİ biçimde geri düşülür (sistem hiçbir
zaman bu modül yüzünden çökmez veya yanlış dile kilitlenip veri kaybetmez).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ISO 639-1 kod -> insan-okur ad. Yalnızca sentiment.py'nin özel motor
# tanımladığı diller ile arayüzde/raporlarda gösterilecek yaygın diller
# listelenir; langdetect bunların dışında da kod döndürebilir (bu durumda
# CokDilliLexiconSentimentAnalyzer generic/İngilizce sözlüğe düşer, bkz.
# sentiment.py get_sentiment_analyzer()).
DESTEKLENEN_DILLER: dict[str, str] = {
    "tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "fr": "Fransızca",
    "es": "İspanyolca", "ar": "Arapça", "ru": "Rusça", "it": "İtalyanca",
    "pt": "Portekizce", "nl": "Flemenkçe", "az": "Azerbaycanca",
}

# langdetect kısa metinlerde tutarsız/rastgele sonuçlar verebilir (ör. "iyi"
# tek kelimesi yanlışlıkla başka bir dile atanabilir); bu eşiğin altındaki
# metinler için tespit DENENMEZ, doğrudan varsayılan (Türkçe) kabul edilir.
_MIN_METIN_UZUNLUGU = 12
_VARSAYILAN_DIL = "tr"


@dataclass
class DilSonucu:
    kod: str            # ISO 639-1 (tr, en, de, ...)
    ad: str              # insan-okur ad (arayüzde gösterim için)
    guven: float          # 0-1, langdetect'in kendi olasılık skoru (0.0 = tespit edilemedi/varsayılan)


def _langdetect_hazirla() -> None:
    """langdetect'in dahili rastgele sayı üretecini sabitler — aksi halde
    AYNI metin, ardışık çağrılarda (nadiren) FARKLI bir dil kodu döndürebilir
    (kütüphanenin bilinen, dokümante edilmiş bir davranışıdır). Skorlamanın
    tekrarlanabilir/deterministik olması için sabitlenir."""
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0


def tespit_et(metin: str) -> DilSonucu:
    """Verilen metnin dilini tespit eder; başarısız olursa veya metin dil
    tespiti için çok kısaysa Türkçe varsayılanına GÜVENLİ biçimde düşer."""
    metin = (metin or "").strip()
    if len(metin) < _MIN_METIN_UZUNLUGU:
        return DilSonucu(_VARSAYILAN_DIL, DESTEKLENEN_DILLER[_VARSAYILAN_DIL], 0.0)

    try:
        _langdetect_hazirla()
        from langdetect import detect_langs
        from langdetect.lang_detect_exception import LangDetectException

        en_iyi = detect_langs(metin)[0]
        kod = en_iyi.lang
        guven = float(en_iyi.prob)
    except LangDetectException:
        # Yalnızca sayı/noktalama/emoji gibi "dilsiz" metinlerde oluşur.
        return DilSonucu(_VARSAYILAN_DIL, DESTEKLENEN_DILLER[_VARSAYILAN_DIL], 0.0)
    except ImportError:
        logger.warning("langdetect kurulu değil — dil tespiti atlandı, varsayılan Türkçe kabul edildi.")
        return DilSonucu(_VARSAYILAN_DIL, DESTEKLENEN_DILLER[_VARSAYILAN_DIL], 0.0)
    except Exception as exc:  # son güvenlik ağı: bu modül asla çağıranı çökertmez
        logger.warning("Dil tespiti beklenmedik biçimde başarısız oldu: %s", exc)
        return DilSonucu(_VARSAYILAN_DIL, DESTEKLENEN_DILLER[_VARSAYILAN_DIL], 0.0)

    ad = DESTEKLENEN_DILLER.get(kod, kod.upper())
    return DilSonucu(kod=kod, ad=ad, guven=round(guven, 3))
