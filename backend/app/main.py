"""
Erken İtibar Krizi Tespit ve Önleyici Karar Destek Sistemi — Backend API Gateway.

Mimari (JURI_DEGERLENDIRME.md Bölüm 3'te önerilen katmanlı yapı):
    React + TypeScript (frontend)
        -> API Gateway (bu dosya, FastAPI)
        -> Veri Toplama Katmanı   (app/collectors)
        -> Analiz Katmanı          (app/services: sentiment, topic_modeling, fake_news, source_credibility)
        -> Makine Öğrenmesi Katmanı (app/services: anomaly_detection, bot_detection, forecasting; app/ml)
        -> Risk Hesaplama Motoru   (app/services/risk_scoring.py)
        -> Bildirim Sistemi        (app/services/notification.py)
        -> Veritabanı Katmanı      (app/database.py, app/models)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import Base, engine
from app.api import routes_icerikler, routes_krizler, routes_diger, routes_itibar
from app.core.rate_limit import limiter, GuvenlikBasliklariMiddleware


def _demo_hesaplari_tohumla() -> None:
    """Geliştirme/demo kolaylığı: frontend login sayfasındaki "Hızlı Giriş"
    butonlarının GERÇEK backend kimlik doğrulamasıyla (bcrypt+JWT) çalışabilmesi
    için 3 demo kurum hesabını, yoksa oluşturur (idempotent — zaten varsa
    dokunmaz). Yalnızca ENV=development iken çalışır; üretimde asla otomatik
    hesap oluşturulmaz."""
    if settings.ENV != "development":
        return
    from app.database import SessionLocal
    from app.models.orm import Kullanici
    from app.core.security import sifre_hashle

    DEMO_HESAPLAR = [
        ("demo@sirket.com.tr", "Demo1234", "Anadolu Gıda A.Ş.", "Gıda & İçecek"),
        ("iletisim@belediye.gov.tr", "Demo1234", "Örnek İlçe Belediyesi", "Kamu & Yerel Yönetim"),
        ("bilgi@siviltoplum.org.tr", "Demo1234", "Umut Derneği", "Sivil Toplum"),
    ]
    db = SessionLocal()
    try:
        for email, sifre, kurum, sektor in DEMO_HESAPLAR:
            if db.query(Kullanici).filter(Kullanici.email == email).first():
                continue
            db.add(Kullanici(
                email=email, hashed_password=sifre_hashle(sifre), kurum=kurum,
                sektor=sektor, rol="admin", bildirim_tercihleri={},
            ))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Geliştirme/demo kolaylığı için tabloları otomatik oluştur.
    # Üretimde bunun yerine Alembic migration'ları kullanılmalıdır.
    Base.metadata.create_all(bind=engine)
    _demo_hesaplari_tohumla()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="TÜBİTAK 1002 kapsamında geliştirilen erken itibar krizi tespit sistemi API'si.",
    version="0.2.0",
    lifespan=lifespan,
)

# Bölüm 17 (Güvenlik): Rate limiting — kaba kuvvet ve DoS önleme
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Bölüm 17 (Güvenlik): OWASP güvenlik başlıkları (XSS/clickjacking/MIME-sniffing önleme)
app.add_middleware(GuvenlikBasliklariMiddleware)

# Not: Üretimde allow_origins sınırlandırılmalı; geliştirme/demo için açık bırakıldı.
# Üretim dağıtımında CORS_ALLOWED_ORIGINS ortam değişkeni ile kurumun gerçek
# frontend domain'i (ör. https://itibar.kurumadi.com) tanımlanmalı, "*" kaldırılmalıdır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_icerikler.router)
app.include_router(routes_krizler.router)
app.include_router(routes_diger.router)
app.include_router(routes_itibar.router)


@app.get("/api/saglik")
def saglik_kontrolu():
    """Basit health-check endpoint'i (izleme/monitoring için, bkz. Bölüm 21)."""
    return {"durum": "ayakta", "servis": settings.APP_NAME}


@app.get("/metrics")
def metrikler():
    """Bölüm 16: Prometheus/Grafana izleme uç noktası.

    prometheus-client kurulu değilse (varsayılan hafif demo ortamı) sistemi
    çökertmeden basit bir JSON özet döner; kurulu ise standart Prometheus
    text formatında metrik döndürür (ops/prometheus.yml bu uç noktayı kazır).
    """
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from starlette.responses import Response as StarletteResponse

        return StarletteResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return {
            "durum": "prometheus_client_kurulu_degil",
            "not": "Üretimde `pip install prometheus-client` ile tam metrik desteği etkinleştirilmelidir.",
        }
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend aktif"}
