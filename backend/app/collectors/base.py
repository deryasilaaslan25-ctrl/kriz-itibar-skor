"""
Bölüm 4: Veri Toplama Altyapısı.

Her dış kaynak (X/Twitter, Reddit, Google News, Google Trends, forumlar)
için ayrı bir "Collector" sınıfı tanımlanır. Bu tasarımın amacı:

  - Yeni bir kaynak eklemek mevcut kodu bozmadan mümkün olsun
    (Open/Closed Principle).
  - API anahtarı henüz temin edilmemiş kaynaklar sistemi ÇÖKERTMESİN;
    `.env` dosyasında ilgili anahtar boşsa collector "devre dışı" durumda
    kalır ve boş liste döner, sistemin geri kalanı (skorlama, anomali
    tespiti, dashboard) mock/demo veri ile çalışmaya devam eder.

Gerçek API entegrasyonu için yapılması gereken (README'de detaylandırıldı):
  - Twitter/X API v2 : app/collectors/twitter.py -> TWITTER_BEARER_TOKEN
  - Reddit API        : app/collectors/reddit.py  -> PRAW + REDDIT_CLIENT_ID/SECRET
  - Google News/RSS   : app/collectors/news.py    -> feedparser (API anahtarı gerekmez)
  - NewsAPI            : app/collectors/news.py    -> NEWSAPI_KEY
  - Google Trends      : app/collectors/trends.py  -> pytrends (API anahtarı gerekmez)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class HamIcerik:
    platform: str
    baslik: str
    icerik: str
    hesap_id: str | None
    yorum_sayisi: int
    kaynak_url: str | None = None


class BaseCollector(ABC):
    platform_adi: str = "bilinmeyen"

    @abstractmethod
    def aktif_mi(self) -> bool:
        """API anahtarı/kimlik bilgisi mevcut mu?"""
        ...

    @abstractmethod
    def topla(self, anahtar_kelime: str, limit: int = 50) -> list[HamIcerik]:
        ...
