"""
Veritabanı katmanı.

Üretimde PostgreSQL kullanılır (bkz. docker-compose.yml).
Yerel geliştirmede Postgres kurulu değilse (bağlantı testi başarısızsa)
otomatik olarak SQLite dosyasına düşer; böylece backend Docker olmadan da
`uvicorn app.main:app` ile ayağa kalkıp demo/jüri sunumu için çalıştırılabilir.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

Base = declarative_base()


def _build_engine():
    # Postgres'e bağlanılamıyor/yanıt vermiyorsa (ör. yanlış/erişilemez
    # DATABASE_URL, ağ gecikmesi) `engine.connect()` işletim sistemi TCP
    # zaman aşımına kadar (bazı ortamlarda dakikalarca) SÜRESİZ bekleyebilir
    # — bu durumda aşağıdaki except bloğu hiç devreye giremez ve uygulama
    # başlangıcı (FastAPI lifespan) asılı kalır: süreç canlı görünür ama HTTP
    # isteklerine hiç yanıt vermez (bkz. GUNCELLEME_NOTLARI, Render deploy
    # sorunu). connect_timeout bu bekleyişi birkaç saniyeyle sınırlayıp
    # fallback'in gerçekten çalışmasını sağlar.
    connect_args = {"connect_timeout": 5} if settings.DATABASE_URL.startswith("postgresql") else {}
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
        with engine.connect():
            pass
        return engine
    except Exception:
        # Postgres erişilemiyorsa geliştirme/demo modu: yerel SQLite dosyası
        fallback_url = "sqlite:///./itibar_dev.db"
        return create_engine(fallback_url, connect_args={"check_same_thread": False})


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
