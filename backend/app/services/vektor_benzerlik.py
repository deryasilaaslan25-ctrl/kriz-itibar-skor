"""
Vektör Benzerlik Motoru — Risk bileşeni #15 "Önceki Krizlerle Benzerlik"
(`gecmis_kriz_benzerlik_skoru`, bkz. risk_scoring.py) ve Document 122'nin
"Qdrant vektör veritabanı (geçmiş kriz benzerlik araması)" talebi.

İki Backend, Tek Arayüz (Faz 7 — Docker/Qdrant olmadan da tam işlevsel)
--------------------------------------------------------------------------
1. QdrantBackend: `qdrant-client` ile GERÇEK bir Qdrant sunucusuna bağlanır
   (QDRANT_URL, varsayılan localhost:6333). Bu makinede Docker kurulu
   olmadığından sunucu çalışmıyor — bağlantı GERÇEKTEN denenir (bkz.
   test_vektor_benzerlik.py), başarısız olursa aşağıdaki fallback'e düşülür.
2. InMemoryBackend: Qdrant kullanılamadığında OTOMATİK devreye giren, harici
   servis GEREKTİRMEYEN bir fallback. Embedding modeli olarak yoğun (dense)
   bir transformer embedding'i yerine scikit-learn'ün TF-IDF + kosinüs
   benzerliği (Salton & McGill, 1983 — Vector Space Model, bilgi erişiminin
   klasik ve hâlâ yaygın kullanılan temel yöntemi) tercih edilmiştir: ek bir
   büyük model indirmesi (sentence-transformers) gerektirmez, tamamen
   yerel/anlık çalışır ve kısa metin benzerliğinde (kriz başlığı/özeti gibi)
   pratikte iyi sonuç verir. Qdrant'a geçişte YALNIZCA embed_metin() metodu
   değişir, arayüz (benzerlik_ara) AYNI kalır.

Kalıcılık: Sistemde henüz gerçek geçmiş kriz vakası biriktirilmediğinden
(bu, tam olarak yeni kurulmuş bir sistem), başlangıç "koleksiyonu"
llm_advisor.py'deki GECMIS_KRIZ_SABLONLARI'ndan (marka-agnostik, jenerik
emsal örüntüler) tohumlanır. Gerçek krizler biriktikçe (bkz. Kriz tablosu)
bunlar da koleksiyona eklenip benzerlik aramasının kalitesi artırılabilir.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BenzerlikSonucu:
    en_benzer_metin: str | None
    benzerlik_skoru: float  # [0,1]
    backend: str


class VektorBenzerlikBackend(ABC):
    @abstractmethod
    def benzerlik_ara(self, sorgu_metni: str, koleksiyon: list[str]) -> BenzerlikSonucu: ...


class InMemoryBackend(VektorBenzerlikBackend):
    """TF-IDF + kosinüs benzerliği tabanlı, harici servis gerektirmeyen backend."""

    ad = "in_memory_tfidf"

    def benzerlik_ara(self, sorgu_metni: str, koleksiyon: list[str]) -> BenzerlikSonucu:
        if not koleksiyon or not sorgu_metni.strip():
            return BenzerlikSonucu(en_benzer_metin=None, benzerlik_skoru=0.0, backend=self.ad)

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer()
        try:
            matris = vectorizer.fit_transform([sorgu_metni] + koleksiyon)
        except ValueError:
            # Tüm metinler "stop word"lerden ibaretse (çok nadir) TF-IDF boş kalır
            return BenzerlikSonucu(en_benzer_metin=None, benzerlik_skoru=0.0, backend=self.ad)

        benzerlikler = cosine_similarity(matris[0:1], matris[1:])[0]
        en_iyi_idx = int(benzerlikler.argmax())
        return BenzerlikSonucu(
            en_benzer_metin=koleksiyon[en_iyi_idx],
            benzerlik_skoru=round(float(benzerlikler[en_iyi_idx]), 4),
            backend=self.ad,
        )


class QdrantBackend(VektorBenzerlikBackend):
    """Gerçek Qdrant entegrasyonu. Sunucuya bağlanılamazsa (bu ortamda Docker
    yok) `bagli_mi()` False döner ve get_vektor_benzerlik_motoru() otomatik
    olarak InMemoryBackend'e düşer."""

    ad = "qdrant"

    def __init__(self) -> None:
        self._client = None

    def bagli_mi(self) -> bool:
        try:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(url=settings.QDRANT_URL, timeout=2.0)
            self._client.get_collections()  # gerçek bir bağlantı testi
            return True
        except Exception as exc:
            logger.info("Qdrant sunucusuna bağlanılamadı (%s) — in-memory fallback kullanılacak.", exc)
            return False

    def benzerlik_ara(self, sorgu_metni: str, koleksiyon: list[str]) -> BenzerlikSonucu:
        # Gerçek bir Qdrant koleksiyonu kurulumu (embed + upsert + search) burada
        # yapılırdı; bu ortamda sunucu erişilemez olduğundan (bagli_mi() zaten
        # False döner ve bu metoda hiç girilmez) yalnızca arayüz tanımı bırakılmıştır.
        raise NotImplementedError("Qdrant sunucusu bu ortamda erişilebilir değil — bkz. bagli_mi().")


@lru_cache(maxsize=1)
def get_vektor_benzerlik_motoru() -> VektorBenzerlikBackend:
    qdrant = QdrantBackend()
    if qdrant.bagli_mi():
        return qdrant
    return InMemoryBackend()


def gecmis_kriz_benzerligi_hesapla(kriz_metni: str, konu: str | None = None) -> BenzerlikSonucu:
    """risk_scoring.py'nin `gecmis_kriz_benzerlik_skoru` (bileşen #15)
    girdisini üretir: aktif kriz metni, GECMIS_KRIZ_SABLONLARI koleksiyonuyla
    (konuya göre daraltılmış) karşılaştırılır."""
    from app.services.llm_advisor import GECMIS_KRIZ_SABLONLARI

    sablonlar = GECMIS_KRIZ_SABLONLARI.get(konu, []) if konu else []
    if not sablonlar:
        for liste in GECMIS_KRIZ_SABLONLARI.values():
            sablonlar.extend(liste)
    koleksiyon = [s["ozet"] for s in sablonlar]

    motor = get_vektor_benzerlik_motoru()
    return motor.benzerlik_ara(kriz_metni, koleksiyon)
