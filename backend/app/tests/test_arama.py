"""Tam metin arama motoru testleri (bkz. app/services/arama.py).

Elasticsearch bu ortamda ÇALIŞMIYOR (Docker yok) — bu GERÇEKTEN denenir ve
otomatik Postgres/SQLite ILIKE fallback'ine düşüldüğü doğrulanır.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.orm import Kullanici, Icerik
from app.services.arama import ElasticsearchBackend, PostgresBackend, get_arama_motoru


def test_elasticsearch_bu_ortamda_erisilemez_gercekten_denendi():
    assert ElasticsearchBackend().bagli_mi() is False


def test_motor_otomatik_postgres_fallbackine_duser():
    assert isinstance(get_arama_motoru(), PostgresBackend)


def test_ilike_arama_gercekten_calisir():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    kullanici = Kullanici(email="a@b.com", hashed_password="x", kurum="Test")
    db.add(kullanici)
    db.commit()
    db.refresh(kullanici)

    db.add(Icerik(kurum_id=kullanici.id, platform="twitter", baslik="Ürün kalitesi berbat", icerik="Bozuk geldi", duygu="negatif", puan=0.8))
    db.add(Icerik(kurum_id=kullanici.id, platform="twitter", baslik="Harika hizmet", icerik="Çok memnun kaldım", duygu="pozitif", puan=0.9))
    db.commit()

    sonuc = PostgresBackend().ara(db, kullanici.id, "kalite")
    assert len(sonuc) == 1
    assert "kalite" in sonuc[0].baslik.lower()
