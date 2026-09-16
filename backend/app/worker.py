"""
Bölüm 13: Redis'in Queue / Task Scheduler / Background Worker olarak
kullanılması (2. juri eleştirisi: "Redis yalnızca önbellek olarak
kullanılmamalı").

Celery uygulaması burada tanımlanır. Ağır/uzun süren işler (toplu NLP
analizi, ML model eğitimi, harici API çağrıları) API isteğini bloklamadan
bu worker üzerinden asenkron çalıştırılır.

Çalıştırma: celery -A app.worker worker --loglevel=info
Periyodik tarama (Bölüm 3: gerçek zamanlı analiz) için Celery Beat:
celery -A app.worker beat --loglevel=info
"""
from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "itibar_krizi",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
    enable_utc=True,
    beat_schedule={
        "periyodik-kriz-taramasi": {
            "task": "app.worker.periyodik_tarama_gorevi",
            "schedule": 15 * 60.0,  # varsayılan 15 dk (Ayarlar.tarama_araligi ile override edilebilir)
        },
    },
)


@celery_app.task(name="app.worker.periyodik_tarama_gorevi")
def periyodik_tarama_gorevi() -> dict:
    """Bölüm 3: Gerçek zamanlı analiz — toplama + NLP/ABSA + risk/itibar
    skorlama zincirini tetikleyen arka plan görevi.

    Faz 6/7 GÜNCELLEMESİ: Bu görev artık boş bir iskelet DEĞİLDİR — gerçek
    zinciri (app/services/tarama_pipeline.py) çağırır: tüm kayıtlı kurum
    hesapları için collector'lardan veri toplar, NLP/ABSA/risk/itibar
    motorlarından geçirir ve veritabanına yazar. Bu fonksiyon HEM Celery
    Beat üzerinden (15 dk'da bir, aşağıdaki beat_schedule) HEM DE Celery/
    Redis kurulu olmayan ortamlarda `routes_krizler.py`'nin senkron
    "tara-şimdi" ucu üzerinden (doğrudan tarama_pipeline çağrısıyla)
    tetiklenebilir — sistem Celery olmadan da tam işlevseldir.
    """
    from app.database import SessionLocal
    from app.services.tarama_pipeline import tum_kurumlari_tara

    db = SessionLocal()
    try:
        sonuclar = tum_kurumlari_tara(db)
    finally:
        db.close()
    return {"durum": "tarama_tamamlandi", "kurum_sonuclari": sonuclar}


@celery_app.task(name="app.worker.bildirim_gonder_gorevi")
def bildirim_gonder_gorevi(kriz_id: int) -> dict:
    """E-posta/Slack/Telegram bildirimlerini API isteğini bloklamadan,
    arka planda gönderir (bkz. app/services/notification.py).

    Faz 6/7 GÜNCELLEMESİ: notification.kriz_uyarisi_yayinla() artık
    GERÇEKTEN çağrılır (önceden bu görev yalnızca bir durum sözlüğü
    döndürüyordu, hiçbir kanala bildirim göndermiyordu)."""
    import asyncio

    from app.database import SessionLocal
    from app.models.orm import Kriz
    from app.services.notification import kriz_uyarisi_yayinla

    db = SessionLocal()
    try:
        kriz = db.query(Kriz).filter(Kriz.id == kriz_id).first()
        if kriz is None:
            return {"durum": "kriz_bulunamadi", "kriz_id": kriz_id}
        baslik = f"Kriz Uyarısı: {kriz.baslik}"
        mesaj = f"Şiddet: {kriz.siddet}/100. Konu: {kriz.konu}. Durum: {kriz.durum}."
        kanal_sonuclari = asyncio.run(kriz_uyarisi_yayinla(baslik, mesaj))
    finally:
        db.close()
    return {"durum": "bildirim_gonderildi", "kriz_id": kriz_id, "kanal_sonuclari": kanal_sonuclari}
