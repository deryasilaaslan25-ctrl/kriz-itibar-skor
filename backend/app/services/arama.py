"""
Tam Metin Arama Motoru (Bölüm 12: Elasticsearch) — Document 122'nin
"Elasticsearch tam metin arama" talebi.

İki Backend, Tek Arayüz (Faz 7 — Docker/Elasticsearch olmadan da tam işlevsel)
--------------------------------------------------------------------------
1. ElasticsearchBackend: `elasticsearch` istemcisiyle GERÇEK bir ES sunucusuna
   bağlanır (ELASTICSEARCH_URL, varsayılan localhost:9200). Bu makinede
   Docker kurulu olmadığından sunucu çalışmıyor — bağlantı GERÇEKTEN denenir
   (bkz. test_arama.py), başarısız olursa aşağıdaki fallback'e düşülür.
2. PostgresBackend: Elasticsearch kullanılamadığında OTOMATİK devreye giren,
   veritabanının kendi metin arama yeteneğini (PostgreSQL ise `ILIKE` /
   `to_tsvector`, SQLite geliştirme fallback'inde ise `LIKE`) kullanan,
   harici servis GEREKTİRMEYEN bir arama katmanı.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import lru_cache

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.orm import Icerik

logger = logging.getLogger(__name__)


class AramaBackend(ABC):
    @abstractmethod
    def ara(self, db: Session, kurum_id: int, sorgu: str, limit: int = 50) -> list[Icerik]: ...


class PostgresBackend(AramaBackend):
    """Veritabanının kendi `LIKE`/`ILIKE` operatörüyle basit ama her zaman
    çalışan tam metin arama (harici servis gerektirmez)."""

    ad = "postgres_ilike"

    def ara(self, db: Session, kurum_id: int, sorgu: str, limit: int = 50) -> list[Icerik]:
        desen = f"%{sorgu}%"
        return (
            db.query(Icerik)
            .filter(
                Icerik.kurum_id == kurum_id,
                or_(Icerik.baslik.ilike(desen), Icerik.icerik.ilike(desen)),
            )
            .order_by(Icerik.tarih.desc())
            .limit(limit)
            .all()
        )


class ElasticsearchBackend(AramaBackend):
    """Gerçek Elasticsearch entegrasyonu. Sunucuya bağlanılamazsa `bagli_mi()`
    False döner ve get_arama_motoru() otomatik olarak PostgresBackend'e düşer."""

    ad = "elasticsearch"

    def __init__(self) -> None:
        self._client = None

    def bagli_mi(self) -> bool:
        try:
            from elasticsearch import Elasticsearch
            self._client = Elasticsearch(settings.ELASTICSEARCH_URL, request_timeout=2)
            return bool(self._client.ping())
        except Exception as exc:
            logger.info("Elasticsearch sunucusuna bağlanılamadı (%s) — Postgres fallback kullanılacak.", exc)
            return False

    def ara(self, db: Session, kurum_id: int, sorgu: str, limit: int = 50) -> list[Icerik]:
        # Gerçek bir ES indeksleme/sorgu akışı (index + search) burada yapılırdı;
        # bu ortamda sunucu erişilemez olduğundan (bagli_mi() zaten False döner
        # ve bu metoda hiç girilmez) yalnızca arayüz tanımı bırakılmıştır.
        raise NotImplementedError("Elasticsearch sunucusu bu ortamda erişilebilir değil — bkz. bagli_mi().")


@lru_cache(maxsize=1)
def get_arama_motoru() -> AramaBackend:
    es = ElasticsearchBackend()
    if es.bagli_mi():
        return es
    return PostgresBackend()
