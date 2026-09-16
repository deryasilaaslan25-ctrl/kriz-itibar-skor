"""Uçtan uca tarama zinciri (Faz 6/7) entegrasyon testi.

Gerçek ağ çağrıları YAPILMAZ (collector'lar monkeypatch ile sahte, deterministik
veri döndürür) — amaç collector çıktısından risk/itibar skoruna kadar TÜM
zincirin (NLP -> ABSA -> EWMA -> Benford -> risk_scoring -> itibar_skoru ->
DB yazımı) gerçekten uçtan uca çalıştığını doğrulamaktır. Collector'ların
kendisinin gerçekten çalıştığı ayrıca test_connectors.py'de doğrulanmıştır.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.orm import Kullanici, Icerik, Kriz
from app.collectors.base import HamIcerik
import app.services.tarama_pipeline as pipeline_modul


class _SahteCollector:
    platform_adi = "Sahte Platform"

    def __init__(self, icerikler):
        self._icerikler = icerikler

    def aktif_mi(self):
        return True

    def topla(self, anahtar_kelime, limit=50):
        return self._icerikler[:limit]


def _test_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_uctan_uca_tarama_negatif_yogun_kriz_uretir(monkeypatch):
    db = _test_db_session()
    kullanici = Kullanici(email="test@kurum.com", hashed_password="x", kurum="Test Kurumu A.Ş.")
    db.add(kullanici)
    db.commit()
    db.refresh(kullanici)

    negatif_icerikler = [
        HamIcerik(
            platform="twitter", baslik=f"Test Kurumu berbat, rezalet, dolandırıcılık! #{i}",
            icerik="Ürün bozuk geldi, iade etmiyorlar, hiç güvenmiyorum bu markaya.",
            hesap_id=f"kullanici{i}", yorum_sayisi=50 + i,
        )
        for i in range(8)
    ]
    monkeypatch.setattr(
        pipeline_modul, "tum_collectorlar",
        lambda: [_SahteCollector(negatif_icerikler)],
    )

    sonuc = pipeline_modul.tek_kurum_tara(db, kullanici, anahtar_kelime="Test Kurumu")

    assert sonuc["durum"] == "tamamlandi"
    assert sonuc["toplanan_icerik_sayisi"] == 8
    assert 0 <= sonuc["risk_skoru"] <= 100
    assert 0 <= sonuc["itibar_skoru"] <= 100
    # Yoğun olumsuz/dolandırıcılık sinyali -> itibar skoru nötrün (50) altında olmalı
    assert sonuc["itibar_skoru"] < 50

    kayitli_icerikler = db.query(Icerik).filter(Icerik.kurum_id == kullanici.id).all()
    assert len(kayitli_icerikler) == 8
    assert all(i.puan is not None for i in kayitli_icerikler)


def test_bos_koleksiyon_veri_bulunamadi_doner(monkeypatch):
    db = _test_db_session()
    kullanici = Kullanici(email="bos@kurum.com", hashed_password="x", kurum="Boş Kurum")
    db.add(kullanici)
    db.commit()
    db.refresh(kullanici)

    monkeypatch.setattr(pipeline_modul, "tum_collectorlar", lambda: [_SahteCollector([])])

    sonuc = pipeline_modul.tek_kurum_tara(db, kullanici)
    assert sonuc["durum"] == "veri_bulunamadi"


def test_anahtar_kelime_yoksa_erken_cikis():
    db = _test_db_session()
    kullanici = Kullanici(email="isimsiz@kurum.com", hashed_password="x", kurum=None)
    db.add(kullanici)
    db.commit()
    db.refresh(kullanici)

    sonuc = pipeline_modul.tek_kurum_tara(db, kullanici, anahtar_kelime=None)
    assert sonuc["durum"] == "anahtar_kelime_yok"
