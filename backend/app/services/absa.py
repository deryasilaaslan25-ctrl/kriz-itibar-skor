"""
Varlık Tabanlı Duygu Analizi (Aspect-Based Sentiment Analysis - ABSA)
5 Akademik Boyut: RepTrak (Fombrun) × SERVQUAL (Parasuraman, Zeithaml & Berry, 1988)

Document 121 s.4-5, s.11-12'de tanımlanan mimarinin BİREBİR uygulaması.

Neden ABSA (tek-etiketli konu sınıflandırma yerine)?
Kullanıcı yorumları genellikle BİRDEN FAZLA boyut içerir (Document 121 örneği:
"Ürün çok kaliteli ama müşteri hizmetleri hiç ilgilenmedi" — bu cümle hem
olumlu bir Ürün&Hizmet Değeri sinyali HEM DE olumsuz bir Yanıt Verebilirlik
sinyali taşır). Metne TEK bir etiket basan topic_modeling.KeywordTopicModel
bu durumda bilgi kaybeder. ABSA, metni cümlelere ayırıp HER cümleyi TÜM
akademik boyutlara karşı test ederek çoklu-boyut çıkarımı yapar.

5 Akademik Boyut ve Kaynakları (Document 121 s.4-5)
----------------------------------------------------
1. urun_hizmet_degeri   — RepTrak: Products & Services / SERVQUAL: Tangibles
                           & Reliability. Ürünün kalitesi, lezzeti, ambalajı,
                           vaat edilen işlevi yerine getirme güvenilirliği.
2. yanit_verebilirlik   — SERVQUAL: Responsiveness & Empathy. Şikayetlere
                           dönüş hızı, müşteri temsilcisi tutumu, çözüm odaklılık.
3. inovasyon            — RepTrak: Innovation. Yeni ürün, lansman, Ar-Ge algısı.
4. yonetisim_etik       — RepTrak: Governance & Ethics / SCCT kriz-sorumluluğu
                           boyutuyla örtüşür. Şeffaflık, adil fiyatlandırma,
                           tüketici hakları, yanıltıcı bilgilendirme, güvenlik.
5. sosyal_sorumluluk    — RepTrak: Citizenship. Sürdürülebilirlik, çevre,
                           toplumsal katkı, ayrımcılık/etik değerler.

Teknik Uygulama (Document 121 s.5, s.11-12)
--------------------------------------------
1) Cümle bölme: Türkçe noktalama tabanlı basit bölücü (spaCy/nltk indirmeden
   — TokenizerModel arayüzü ileride spaCy ile değiştirilebilir biçimde
   soyutlanmıştır).
2) Sıfır-Örnekli Sınıflandırma (Zero-Shot Classification - NLI): Her cümle,
   5 akademik boyutun hipotez cümlesine karşı çok-dilli bir Doğal Dil Çıkarım
   (NLI) modeliyle test edilir. Kullanılan model:
   `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` — Türkçe dahil
   100+ dilde XNLI + ek NLI veri setleriyle eğitilmiş, HuggingFace'te herkese
   açık (API anahtarı gerektirmeyen), zero-shot-classification pipeline'ına
   doğrudan uyumlu bir mDeBERTa-v3 sağlamlaştırması (MoritzLaurer, 2023).
   `multi_label=True` ile HER boyut BAĞIMSIZ olarak test edilir (softmax
   yerine sigmoid) — bu, tek bir cümlenin BİRDEN FAZLA boyuta atanabilmesini
   sağlayan teknik mekanizmadır.
3) Duygu Çıkarımı: Bir boyuta atanan her cümleye sentiment.py'deki mevcut
   duygu analizörü (BERTurk varsa transformer, yoksa lexicon — bkz.
   get_sentiment_analyzer()) ayrı ayrı uygulanır; böylece HER boyut kendi
   BAĞIMSIZ duygu skorunu alır (tüm metnin ortalaması değil).

Soft-dependency / Graceful Degradation
---------------------------------------
`transformers` kurulu değilse veya model indirilemezse (ağ hatası vb.),
`KeywordAbsaAnalyzer` fallback'i devreye girer: topic_modeling.py'nin
mevcut ~20 kategorilik anahtar-kelime sözlüğü, her kategorinin bağlı
olduğu akademik boyuta (KONU_TO_ABSA_BOYUT) göre yeniden gruplanarak
kullanılır. Sistem HİÇBİR ZAMAN bu modül yüzünden çökmez.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache

from app.services.topic_modeling import KONU_ANAHTAR_KELIMELER, KONU_TO_ABSA_BOYUT

ABSA_BOYUTLARI: dict[str, dict[str, str]] = {
    "urun_hizmet_degeri": {
        "ad": "Ürün ve Hizmet Değeri",
        "akademik_kaynak": "RepTrak: Products & Services / SERVQUAL: Tangibles & Reliability",
        "etiket_ifadesi": "ürün kalitesi, lezzeti, ambalajı veya vaat edilen işlevi yerine getirme güvenilirliği",
    },
    "yanit_verebilirlik": {
        "ad": "Yanıt Verebilirlik ve Müşteri Destek Süreçleri",
        "akademik_kaynak": "SERVQUAL: Responsiveness & Empathy",
        "etiket_ifadesi": "müşteri hizmetleri, şikayetlere dönüş hızı veya destek süreci",
    },
    "inovasyon": {
        "ad": "İnovasyon ve Ürün Geliştirme",
        "akademik_kaynak": "RepTrak: Innovation",
        "etiket_ifadesi": "yeni ürün, lansman veya inovasyon",
    },
    "yonetisim_etik": {
        "ad": "Yönetişim, Etik ve Fiyatlandırma",
        "akademik_kaynak": "RepTrak: Governance & Ethics / SCCT kriz-sorumluluğu boyutu",
        "etiket_ifadesi": "şeffaflık, adil fiyatlandırma, tüketici hakları veya yönetişim",
    },
    "sosyal_sorumluluk": {
        "ad": "Sosyal Sorumluluk ve Kurumsal Vatandaşlık",
        "akademik_kaynak": "RepTrak: Citizenship",
        "etiket_ifadesi": "sürdürülebilirlik, çevre veya toplumsal katkı",
    },
}

ZERO_SHOT_MODEL_ADI = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
HIPOTEZ_SABLONU = "Bu cümle {} ile ilgilidir."
# multi_label=True modunda her etiket BAĞIMSIZ bir sigmoid olasılığı alır
# (softmax gibi etiketler arasında rekabet YOKTUR); 0.5 "entailment,
# contradiction'dan daha olası" anlamına gelen doğal karar sınırıdır.
ZERO_SHOT_ESIK = 0.5

_CUMLE_AYIRICI = re.compile(r"(?<=[.!?…])\s+")

_ISARET = {"negatif": -1.0, "pozitif": 1.0, "nötr": 0.0}


def cumlelere_ayir(metin: str) -> list[str]:
    """Basit noktalama-tabanlı Türkçe cümle bölücü.

    NOT: spaCy/nltk gibi ağır bağımlılıklar YOKTUR — bu, "Dr.", "vb." gibi
    kısaltmalarda hatalı bölünmeye yol açabilir (bilinen sınırlama). ABSA
    sonucunun kalitesini bozacak ölçüde nadir olduğu ve modülün asıl gücünün
    zero-shot sınıflandırmadan geldiği değerlendirilmiştir; TokenizerModel
    arayüzü (aşağıda) ileride spaCy ile TEK SATIR değişiklikle yer değiştirebilir.
    """
    metin = metin.strip()
    if not metin:
        return []
    parcalar = [p.strip() for p in _CUMLE_AYIRICI.split(metin) if p.strip()]
    return parcalar or [metin]


@dataclass
class AbsaBoyutEslesme:
    boyut: str
    boyut_adi: str
    cumle: str
    zero_shot_skor: float | None   # None ise fallback (anahtar kelime) kullanıldı
    duygu_skoru: float               # [-1, 1]


@dataclass
class AbsaSonucu:
    metin: str
    boyut_skorlari: dict[str, float] = field(default_factory=dict)   # boyut -> ortalama duygu [-1,1]
    boyut_guven: dict[str, float] = field(default_factory=dict)       # boyut -> ortalama zero-shot güveni (varsa)
    eslesmeler: list[AbsaBoyutEslesme] = field(default_factory=list)
    yontem: str = ""


class AbsaAnalyzer(ABC):
    @abstractmethod
    def analiz_et(self, metin: str) -> AbsaSonucu: ...


def _cumle_duygu_skoru(cumle: str) -> float:
    from app.services.sentiment import get_sentiment_analyzer
    sonuc = get_sentiment_analyzer().analiz_et(cumle)
    return _ISARET.get(sonuc.duygu, 0.0) * sonuc.puan


@lru_cache(maxsize=1)
def _zero_shot_pipeline():
    """transformers.pipeline'ı tembel (lazy) yükler — yalnızca ilk çağrıda
    model indirilir/RAM'e alınır, modül import edilirken DEĞİL."""
    from transformers import pipeline
    return pipeline("zero-shot-classification", model=ZERO_SHOT_MODEL_ADI)


class ZeroShotAbsaAnalyzer(AbsaAnalyzer):
    """mDeBERTa-v3 tabanlı çok-dilli NLI ile gerçek zero-shot ABSA."""

    def analiz_et(self, metin: str) -> AbsaSonucu:
        clf = _zero_shot_pipeline()  # ImportError/OSError -> çağıran yere yükselir (fallback tetiklenir)
        cumleler = cumlelere_ayir(metin)
        etiket_ifadeleri = [v["etiket_ifadesi"] for v in ABSA_BOYUTLARI.values()]
        ifade_to_boyut = {v["etiket_ifadesi"]: k for k, v in ABSA_BOYUTLARI.items()}

        eslesmeler: list[AbsaBoyutEslesme] = []
        boyut_toplam: dict[str, list[float]] = {k: [] for k in ABSA_BOYUTLARI}
        boyut_guven_toplam: dict[str, list[float]] = {k: [] for k in ABSA_BOYUTLARI}

        for cumle in cumleler:
            sonuc = clf(cumle, candidate_labels=etiket_ifadeleri, hypothesis_template=HIPOTEZ_SABLONU, multi_label=True)
            for etiket, skor in zip(sonuc["labels"], sonuc["scores"]):
                if skor < ZERO_SHOT_ESIK:
                    continue
                boyut = ifade_to_boyut[etiket]
                duygu = _cumle_duygu_skoru(cumle)
                eslesmeler.append(AbsaBoyutEslesme(
                    boyut=boyut, boyut_adi=ABSA_BOYUTLARI[boyut]["ad"], cumle=cumle,
                    zero_shot_skor=round(float(skor), 4), duygu_skoru=round(duygu, 4),
                ))
                boyut_toplam[boyut].append(duygu)
                boyut_guven_toplam[boyut].append(float(skor))

        boyut_skorlari = {k: round(sum(v) / len(v), 4) for k, v in boyut_toplam.items() if v}
        boyut_guven = {k: round(sum(v) / len(v), 4) for k, v in boyut_guven_toplam.items() if v}

        return AbsaSonucu(
            metin=metin, boyut_skorlari=boyut_skorlari, boyut_guven=boyut_guven,
            eslesmeler=eslesmeler, yontem="zero_shot_nli_mdeberta",
        )


# Fallback: anahtar-kelime tabanlı boyut sözlüğü — topic_modeling.py'nin
# mevcut kategori sözlüğünü akademik boyutlara göre yeniden gruplar.
_ABSA_BOYUT_ANAHTAR_KELIMELER: dict[str, set[str]] = {boyut: set() for boyut in ABSA_BOYUTLARI}
for _konu, _kelimeler in KONU_ANAHTAR_KELIMELER.items():
    _boyut = KONU_TO_ABSA_BOYUT.get(_konu)
    if _boyut:
        _ABSA_BOYUT_ANAHTAR_KELIMELER[_boyut] |= _kelimeler


class KeywordAbsaAnalyzer(AbsaAnalyzer):
    """transformers kurulu değilse/model inemezse devreye giren, anahtar
    kelime eşleştirmeli, HER ZAMAN çalışan geri dönüş (fallback) motoru."""

    def analiz_et(self, metin: str) -> AbsaSonucu:
        cumleler = cumlelere_ayir(metin)
        eslesmeler: list[AbsaBoyutEslesme] = []
        boyut_toplam: dict[str, list[float]] = {k: [] for k in ABSA_BOYUTLARI}

        for cumle in cumleler:
            cumle_lower = cumle.lower()
            for boyut, kelimeler in _ABSA_BOYUT_ANAHTAR_KELIMELER.items():
                if any(k in cumle_lower for k in kelimeler):
                    duygu = _cumle_duygu_skoru(cumle)
                    eslesmeler.append(AbsaBoyutEslesme(
                        boyut=boyut, boyut_adi=ABSA_BOYUTLARI[boyut]["ad"], cumle=cumle,
                        zero_shot_skor=None, duygu_skoru=round(duygu, 4),
                    ))
                    boyut_toplam[boyut].append(duygu)

        boyut_skorlari = {k: round(sum(v) / len(v), 4) for k, v in boyut_toplam.items() if v}
        return AbsaSonucu(
            metin=metin, boyut_skorlari=boyut_skorlari, boyut_guven={},
            eslesmeler=eslesmeler, yontem="anahtar_kelime_fallback",
        )


def analiz_et(metin: str) -> AbsaSonucu:
    """Dependency-injection giriş noktası: önce gerçek zero-shot NLI dener,
    herhangi bir nedenle (kurulu değil, model inemedi, ağ hatası) başarısız
    olursa anahtar-kelime fallback'ine sessizce düşer — sistem asla çökmez.

    settings.LITE_MODE=True ise mDeBERTa hiç denenmez (bkz. app/config.py —
    bellek kısıtlı ortamlarda OOM'u baştan önlemek için)."""
    from app.config import settings
    if settings.LITE_MODE:
        return KeywordAbsaAnalyzer().analiz_et(metin)
    try:
        return ZeroShotAbsaAnalyzer().analiz_et(metin)
    except Exception:
        return KeywordAbsaAnalyzer().analiz_et(metin)
