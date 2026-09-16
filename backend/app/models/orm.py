"""
SQLAlchemy ORM modelleri.
Alan adları, frontend'deki src/lib/domain.ts ile bilinçli olarak birebir
eşleştirilmiştir (Icerik, Kriz, DenetimKaydi, Ayarlar) — böylece API
şeması değişmeden mevcut React arayüzü backend'e bağlanabilir.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


class Kullanici(Base):
    """Kurum hesabı.

    Sisteme kayıt olan her kurum, tam olarak bir Kullanici kaydına karşılık
    gelir (bkz. /api/auth/kayit). Kriz ve Icerik kayıtları bu kaydın id'sine
    (kurum_id) bağlanarak kurumlar arası veri izolasyonu sağlanır — bir kurum
    başka bir kurumun kriz/itibar verisini asla göremez (bkz. routes_krizler.py,
    routes_icerikler.py: tüm sorgular `kurum_id == mevcut_kullanici.id` ile
    filtrelenir).
    """
    __tablename__ = "kullanicilar"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    kurum = Column(String, nullable=True)
    sektor = Column(String, nullable=True)
    rol = Column(String, default="analist")  # RBAC: admin, analist, izleyici
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)
    guncelleme_tarihi = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Bildirim tercihi öğrenimi (Kriz Merkezi): konu bazında "bu tür krizde
    # bildirim istiyorum/istemiyorum" tercihleri {"Ürün Kalitesi": true, ...}
    # olarak saklanır; kullanıcı işaretledikçe sistem bunu öğrenir.
    bildirim_tercihleri = Column(JSON, default=dict)


class KaynakGuvenilirlik(Base):
    """Bölüm 14: Kaynak güvenilirlik puanı."""
    __tablename__ = "kaynak_guvenilirlik"

    id = Column(Integer, primary_key=True, index=True)
    hesap_id = Column(String, index=True, nullable=False)
    platform = Column(String, nullable=False)
    hesap_tipi = Column(String, nullable=False)  # anonim, yeni, fenomen, dogrulanmis, ulusal_gazete
    guven_puani = Column(Float, nullable=False)  # 0.20 - 1.00
    hesap_yasi_gun = Column(Integer, default=0)
    guncelleme_tarihi = Column(DateTime, default=datetime.utcnow)


class Icerik(Base):
    __tablename__ = "icerikler"

    id = Column(Integer, primary_key=True, index=True)
    # Veri izolasyonu: bu içerik hangi kurum hesabına ait (bkz. Kullanici üstteki not)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=True, index=True)
    platform = Column(String, nullable=False)
    baslik = Column(String, nullable=False)
    icerik = Column(Text, nullable=False)
    duygu = Column(String, nullable=False)          # negatif | pozitif | nötr
    duygu_alt_tip = Column(String, nullable=True)    # öfke, panik, güvensizlik, memnuniyet ...
    puan = Column(Float, nullable=False)             # duygu analizinin güven skoru
    # Faz 8 (açıklanabilirlik): bu duygu skorunu üreten somut kelime/kalıp
    # kanıtları (bkz. sentiment.py DuyguSonucu.aciklama_kanitlari) — frontend'de
    # "-0.87 neden?" sorusuna doğrudan yanıt vermek için kullanılır.
    aciklama_kanitlari = Column(JSON, default=list)
    konu = Column(String, nullable=True)             # BERTopic çıktısı
    ortuk_anlam = Column(Boolean, default=False)
    tarih = Column(DateTime, default=datetime.utcnow)
    yorum_sayisi = Column(Integer, default=0)
    # Faz 10 (çok dilli analiz): app/services/dil_tespit.py tarafından tespit
    # edilen ISO 639-1 dil kodu (tr, en, de, ...). `duygu` alanını üreten
    # sentiment.get_sentiment_analyzer(dil_kodu) çağrısının hangi motoru
    # (Türkçe/BERTurk mü, çok dilli/XLM-R mi) seçtiğini şeffaf biçimde izlemek
    # ve frontend'de dile göre filtreleme yapabilmek için saklanır.
    dil = Column(String, nullable=True, default="tr")

    # Bot / sahte haber / güvenilirlik sinyalleri (Bölüm 12-14)
    hesap_id = Column(String, nullable=True, index=True)
    bot_skoru = Column(Float, default=0.0)           # 0-1, yüksek = bot olasılığı yüksek
    kaynak_guven_puani = Column(Float, default=0.5)
    sahte_haber_riski = Column(Float, default=0.0)   # 0-1

    kriz_id = Column(Integer, ForeignKey("krizler.id"), nullable=True)
    kriz = relationship("Kriz", back_populates="icerikler")


class Kriz(Base):
    __tablename__ = "krizler"

    id = Column(Integer, primary_key=True, index=True)
    # Veri izolasyonu: bu kriz hangi kurum hesabına ait (bkz. Kullanici üstteki not)
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=True, index=True)
    baslik = Column(String, nullable=False)
    aciklama = Column(Text, nullable=True)
    siddet = Column(Float, default=0.0)              # 0-100 (Bölüm 8 risk skoru)
    platform = Column(JSON, default=list)             # liste olarak saklanır
    tarih = Column(DateTime, default=datetime.utcnow)
    konu = Column(String, nullable=True)
    durum = Column(String, default="İzleniyor")        # Aktif | İzleniyor | Kapandı
    icerik_sayisi = Column(Integer, default=0)
    feedback = Column(String, nullable=True)           # gercek | siradan | null

    # Risk skorlama alt bileşenleri (16 bileşenli XAI motoru — şeffaflık için ayrı ayrı saklanır)
    # bkz. app/services/risk_scoring.py — RiskSonucu.bilesenler ile birebir eşleşir
    skor_negatif_duygu = Column(Float, default=0.0)
    skor_duygu_yogunlugu = Column(Float, default=0.0)
    skor_trend_artisi = Column(Float, default=0.0)
    skor_paylasim_hizi = Column(Float, default=0.0)
    skor_platform_agirligi = Column(Float, default=0.0)
    skor_hesap_guvenilirligi_riski = Column(Float, default=0.0)
    skor_bot_aktivitesi = Column(Float, default=0.0)
    skor_anahtar_kelime_yogunlugu = Column(Float, default=0.0)
    skor_haber_guvenilirligi = Column(Float, default=0.0)
    skor_cografi_yayilim = Column(Float, default=0.0)
    skor_icerik_benzerligi = Column(Float, default=0.0)
    skor_influencer_etkisi = Column(Float, default=0.0)
    skor_gorsel_icerik = Column(Float, default=0.0)
    skor_sahte_haber_riski = Column(Float, default=0.0)
    skor_gecmis_kriz_benzerligi = Column(Float, default=0.0)
    skor_icerik_yayilimi = Column(Float, default=0.0)
    guvenilir_kaynak_teyidi = Column(Float, default=0.0)  # destekleyici sinyal, risk skoruna dahil değil

    # Anomali tespiti / tahmin
    anomali_tespit_edildi = Column(Boolean, default=False)
    tahmini_24s_risk = Column(Float, nullable=True)
    tahmini_72s_risk = Column(Float, nullable=True)
    tahmini_7g_risk = Column(Float, nullable=True)

    icerikler = relationship("Icerik", back_populates="kriz")


class HaftalikVeri(Base):
    __tablename__ = "haftalik_veri"

    id = Column(Integer, primary_key=True, index=True)
    gun = Column(String, nullable=False)
    itibar = Column(Float, default=0.0)
    hacim = Column(Integer, default=0)
    tarih = Column(DateTime, default=datetime.utcnow)


class DenetimKaydi(Base):
    __tablename__ = "denetim_kayitlari"

    id = Column(String, primary_key=True, index=True)
    # Veri izolasyonu: bu denetim kaydı hangi kurum hesabına ait (bkz. Kullanici
    # üstteki not). Önceki sürümde bu alan yoktu; /api/denetim tüm kurumların
    # kayıtlarını herkese açık biçimde sızdırıyordu (Faz 0 güvenlik düzeltmesi).
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=True, index=True)
    zaman = Column(DateTime, default=datetime.utcnow)
    tur = Column(String, nullable=False)  # tarama | alarm | geri_bildirim | ayar
    mesaj = Column(String, nullable=False)
    kriz_id = Column(Integer, ForeignKey("krizler.id"), nullable=True)


class Ayarlar(Base):
    __tablename__ = "ayarlar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Veri izolasyonu: her kurumun kendi ayar satırı vardır (önceki sürümde tek
    # global satır tüm kurumlar arasında paylaşılıyordu — Faz 0 güvenlik düzeltmesi).
    kurum_id = Column(Integer, ForeignKey("kullanicilar.id"), unique=True, nullable=True, index=True)
    esik = Column(Float, default=50.0)
    tarama_araligi = Column(Integer, default=15)  # dakika
    adaptif_tarama = Column(Boolean, default=True)
    email_bildirim = Column(Boolean, default=True)
