"""
Uygulama yapılandırması.
Tüm hassas bilgiler (.env dosyasından) ortam değişkenleri ile yönetilir.
Bkz: .env.example
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Genel
    APP_NAME: str = "Erken İtibar Krizi Tespit ve Önleyici Karar Destek Sistemi"
    ENV: str = "development"
    # True ise transformer tabanlı modeller (BERTurk, XLM-R, mDeBERTa — bkz.
    # app/services/sentiment.py, app/services/absa.py) HİÇ yüklenmeye
    # çalışılmaz; sistem doğrudan sözlük/anahtar-kelime tabanlı motorlarla
    # çalışır. Bellek kısıtlı ortamlarda (ör. Render/Railway ücretsiz katman,
    # ~512MB RAM) torch+transformers modellerinin (~1-2GB) yüklenmeye
    # çalışılması OOM (bellek yetersizliği) ile süreci çökertebilir; bu durum
    # normal bir Python exception'ı OLMADIĞI için mevcut try/except fallback'i
    # (get_sentiment_analyzer/absa.analiz_et) devreye giremeden işlem
    # öldürülür. LITE_MODE bu riski, modeli hiç denemeyerek baştan ortadan kaldırır.
    LITE_MODE: bool = False

    # Veritabanı
    DATABASE_URL: str = "postgresql+psycopg2://itibar_user:itibar_pass@localhost:5432/itibar_db"
    # Geliştirme/test ortamında Postgres kurulu değilse SQLite'a otomatik düşer (bkz. database.py)

    REDIS_URL: str = "redis://localhost:6379/0"

    # Güvenlik / JWT
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Üretimde "*" yerine gerçek frontend domain listesi tanımlanmalı (Bölüm 17: CORS Politikası)
    CORS_ALLOWED_ORIGINS: list[str] = ["*"]
    # Anthropic API anahtarı (opsiyonel — bkz. app/services/llm_advisor.py; tanımlı değilse
    # sistem yalnızca kural-tabanlı SCCT önerisiyle çalışmaya devam eder)
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"

    # Dış veri kaynağı API anahtarları (opsiyonel - boşsa ilgili collector "devre dışı" modda çalışır)
    TWITTER_BEARER_TOKEN: str | None = None
    REDDIT_CLIENT_ID: str | None = None
    REDDIT_CLIENT_SECRET: str | None = None
    NEWSAPI_KEY: str | None = None
    GOOGLE_TRENDS_ENABLED: bool = False
    # YouTube: TAMAMEN OPSİYONEL. YouTubeCollector, YOUTUBE_API_KEY tanımlı
    # olmasa DAHİ çalışır (yt-dlp ile anahtarsız arama+yorum toplama, bkz.
    # app/collectors/connectors.py). Kullanıcı ileride Google Cloud Console'dan
    # ÜCRETSİZ bir YouTube Data API v3 anahtarı edinirse, buraya eklemek daha
    # yüksek kotalı/resmi bir veri yolunu OTOMATİK devreye sokar — kod
    # değişikliği gerekmez.
    YOUTUBE_API_KEY: str | None = None

    # Faz 7: Qdrant (vektör benzerlik, bileşen #15) / Elasticsearch (tam metin arama)
    # — Docker kurulu değilse bu servislere bağlanılamaz ve ilgili modüller
    # otomatik olarak yerleşik (in-process) fallback'lerine düşer (bkz.
    # app/services/vektor_benzerlik.py, app/services/arama.py).
    QDRANT_URL: str = "http://localhost:6333"
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # Bildirim entegrasyonları
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SLACK_WEBHOOK_URL: str | None = None
    TELEGRAM_BOT_TOKEN: str | None = None
    TEAMS_WEBHOOK_URL: str | None = None

    # Risk skorlama ağırlıkları — 16 bileşenli genişletilmiş motor
    # (2. juri eleştirisi Bölüm 5: "6 parametre yetersiz, 15-18 değişkene çıkarılmalı")
    # Ham ağırlıklar toplamı normalize edilerek 0-100 skoruna çevrilir (risk_scoring.py).
    W_NEGATIF_DUYGU: float = 16.0
    W_DUYGU_YOGUNLUGU: float = 8.0
    W_TREND_ARTISI: float = 12.0
    W_PAYLASIM_HIZI: float = 8.0
    W_PLATFORM_AGIRLIGI: float = 5.0
    W_HESAP_GUVENILIRLIGI: float = 6.0
    W_BOT_AKTIVITESI: float = 9.0
    W_ANAHTAR_KELIME: float = 6.0
    W_HABER_GUVENILIRLIGI: float = 8.0
    W_COGRAFI_YAYILIM: float = 4.0
    W_ICERIK_BENZERLIGI: float = 5.0
    W_INFLUENCER_ETKISI: float = 8.0
    W_GORSEL_ICERIK: float = 3.0
    W_SAHTE_HABER: float = 6.0
    W_GECMIS_KRIZ_BENZERLIGI: float = 4.0
    W_ICERIK_YAYILIMI: float = 8.0

    # İtibar Skoru (Reputation Score) — bkz. app/services/itibar_skoru.py
    # Fombrun & van Riel'in RepTrak/Reputation Quotient kuramı + Hovland & Weiss
    # (1951) kaynak güvenilirliği ağırlıklandırması + Ebbinghaus (1885) üstel
    # unutma eğrisi birleşimine dayanan tanh-EWMA formülü.
    # T½ (yarılanma ömrü): sosyal medyada bir içeriğin kamuoyu gündemindeki
    # etkisinin yarıya indiği süre. Literatürde 24-48 saat aralığı yaygın kabul
    # görür (viral içerik "yarı ömrü" çalışmaları); bu sistemde aralığın orta
    # noktası (36 saat) varsayılan alınmıştır, .env ile override edilebilir.
    ITIBAR_YARILANMA_OMRU_SAAT: float = 36.0
    # α (duyarlılık katsayısı): tanh(α·net_duygu) ifadesinin doygunluk hızını
    # belirler. α=2.5 seçilmiştir çünkü net_duygu∈[-1,1] için tanh(2.5·1)≈0.987
    # -> skor≈99.3/100.6 (pratik üst/alt sınırlara yaklaşır, tam 0/100'e asla
    # ulaşmaz — "hiçbir itibar mutlak sıfır/yüz değildir" ilkesini korur) ve
    # aynı zamanda orta şiddetli karışık sinyallerde (net_duygu≈±0.3) skoru
    # aşırı sıkıştırmaz (tanh(2.5·0.3)=0.635 -> hâlâ ayırt edici bir aralıkta).
    ITIBAR_ALPHA: float = 2.5

    # Tamamlayıcı istatistiksel doğrulama modeli (Document 121 s.3):
    # R_kriz_dogrulama = 100·σ(β0 + β1·Z_hacim + β2·S_olumsuz + β3·dE/dt + β4·B_anomali)
    # Bu katsayılar başlangıçta ELLE, alan bilgisiyle tutarlı biçimde seçilmiştir
    # (β0<0: tüm sinyaller sıfırken risk düşük olmalı; β1..β4 eşit ağırlıklı
    # başlangıç varsayımı). ÜRETİMDE gerçek etiketli kriz/kriz-olmayan
    # vakalarla lojistik regresyon (bkz. sklearn.linear_model.LogisticRegression)
    # ile yeniden kalibre edilmesi önerilir — bu, standart bir "uzman-öncül
    # (informative prior) ile başlayıp veriyle güncelleme" pratiğidir.
    DOGRULAMA_BETA0: float = -2.0
    DOGRULAMA_BETA1: float = 1.5   # Z_hacim (normalize edilmiş, [0,1])
    DOGRULAMA_BETA2: float = 1.5   # S_olumsuz (SCCT önlenemez küme oranı)
    DOGRULAMA_BETA3: float = 1.0   # dE/dt (yayılma ivmesi)
    DOGRULAMA_BETA4: float = 1.0   # B_anomali (Benford sapma skoru)

    # Platform ağırlıkları (Bölüm 5: "her platformun etkisi farklı olmalıdır")
    PLATFORM_AGIRLIKLARI: dict[str, float] = {
        "twitter": 1.00,
        "x": 1.00,
        "reddit": 0.75,
        "instagram": 0.85,
        "tiktok": 0.90,
        "youtube": 0.80,
        "facebook": 0.70,
        "linkedin": 0.55,
        "eksisozluk": 0.60,
        "sikayetvar": 0.65,
        "telegram": 0.50,
        "haber_sitesi": 0.95,
    }

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
