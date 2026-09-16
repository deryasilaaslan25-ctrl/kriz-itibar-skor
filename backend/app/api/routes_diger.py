import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import DenetimKaydi, Ayarlar, Kullanici
from app.schemas.schemas import BotTespitIstek, KayitIstek, SifreDegistirIstek, EmailDegistirIstek
from app.services.bot_detection import get_bot_classifier, BotSinyalleri
from app.collectors.connectors import kaynak_durumu
from app.core.security import sifre_dogrula, sifre_hashle, token_olustur, gecerli_kullanici_al
from app.core.rate_limit import limiter, GIRIS_LIMITI
from fastapi import Request

router = APIRouter(tags=["diğer"])


# ---- Bot Tespiti (Bölüm 12) -------------------------------------------------
@router.post("/api/bot-tespit/skorla")
def bot_skorla(istek: BotTespitIstek):
    classifier = get_bot_classifier()
    sinyaller = BotSinyalleri(
        hesap_yasi_gun=istek.hesap_yasi_gun,
        son_24s_paylasim_sayisi=istek.son_24s_paylasim_sayisi,
        tekrarlayan_icerik_orani=istek.tekrarlayan_icerik_orani,
        hashtag_yogunlugu=istek.hashtag_yogunlugu,
    )
    skor = classifier.skorla(sinyaller)
    return {
        "hesap_id": istek.hesap_id,
        "bot_skoru": skor,
        "degerlendirme": "yüksek bot olasılığı" if skor > 0.6 else ("şüpheli" if skor > 0.35 else "muhtemelen insan"),
    }


# ---- Veri Kaynağı Durumu (Bölüm 4) -----------------------------------------
@router.get("/api/kaynaklar/durum")
def kaynaklarin_durumu():
    """Hangi dış veri kaynakları (Twitter, Reddit, News, Trends) API anahtarıyla
    aktif, hangileri henüz yapılandırılmadı — şeffaflık için."""
    return kaynak_durumu()


# ---- Denetim Kaydı (Audit Log) ---------------------------------------------
# Faz 0 güvenlik düzeltmesi: bu uç önceden auth'suzdu ve kurum_id filtresi
# uygulamıyordu — herhangi bir kimliksiz istemci TÜM kurumların denetim
# kayıtlarını okuyabiliyordu. Artık Icerik/Kriz ile aynı tenant-izolasyon
# deseni uygulanır (bkz. routes_krizler.py: kurum_id == mevcut_kullanici.id).
@router.get("/api/denetim")
def denetim_listele(
    limit: int = 100,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    kayitlar = (
        db.query(DenetimKaydi)
        .filter(DenetimKaydi.kurum_id == kullanici.id)
        .order_by(DenetimKaydi.zaman.desc())
        .limit(limit)
        .all()
    )
    return kayitlar


# ---- Ayarlar ----------------------------------------------------------------
# Faz 0 güvenlik düzeltmesi: önceden tek global Ayarlar satırı tüm kurumlar
# arasında paylaşılıyordu (bir kurumun eşik/e-posta ayarı değiştirilirse
# HERKESİNKİ değişiyordu) ve uç auth'suzdu. Artık her kurumun kendi satırı var.
@router.get("/api/ayarlar")
def ayarlari_getir(db: Session = Depends(get_db), kullanici: Kullanici = Depends(gecerli_kullanici_al)):
    ayar = db.query(Ayarlar).filter(Ayarlar.kurum_id == kullanici.id).first()
    if not ayar:
        ayar = Ayarlar(kurum_id=kullanici.id)
        db.add(ayar)
        db.commit()
        db.refresh(ayar)
    return ayar


@router.put("/api/ayarlar")
def ayarlari_guncelle(
    esik: float,
    tarama_araligi: int,
    adaptif_tarama: bool,
    email_bildirim: bool,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    ayar = db.query(Ayarlar).filter(Ayarlar.kurum_id == kullanici.id).first()
    if not ayar:
        ayar = Ayarlar(kurum_id=kullanici.id)
        db.add(ayar)
    ayar.esik = esik
    ayar.tarama_araligi = tarama_araligi
    ayar.adaptif_tarama = adaptif_tarama
    ayar.email_bildirim = email_bildirim
    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="ayar",
        mesaj="Ayarlar güncellendi", kurum_id=kullanici.id,
    ))
    db.commit()
    return ayar


# ---- Kimlik Doğrulama (Bölüm 20: JWT + OAuth2) -----------------------------
# Kayıt akışı: kurum önce e-posta, ardından şifre + şifre tekrarı ve kurum adı
# girerek bir profil oluşturur. Şifre asla düz metin olarak saklanmaz — bcrypt
# (passlib CryptContext, bkz. core/security.py) ile hash'lenir. Oluşturulan
# hesabın verileri (kriz, içerik) yalnızca kendi kurum_id'sine bağlanır; başka
# hiçbir hesap bu veriyi göremez (bkz. routes_krizler.py / routes_icerikler.py).
@router.post("/api/auth/kayit", status_code=201)
@limiter.limit(GIRIS_LIMITI)
def kayit_ol(request: Request, istek: KayitIstek, db: Session = Depends(get_db)):
    if istek.sifre != istek.sifre_tekrar:
        raise HTTPException(status_code=400, detail="Şifreler birbiriyle eşleşmiyor")
    if len(istek.sifre) < 8:
        raise HTTPException(status_code=400, detail="Şifre en az 8 karakter olmalıdır")
    if not istek.kurum.strip():
        raise HTTPException(status_code=400, detail="Kurum adı boş olamaz")

    mevcut = db.query(Kullanici).filter(Kullanici.email == istek.email.lower().strip()).first()
    if mevcut:
        raise HTTPException(status_code=409, detail="Bu e-posta adresiyle zaten bir hesap mevcut")

    kullanici = Kullanici(
        email=istek.email.lower().strip(),
        hashed_password=sifre_hashle(istek.sifre),
        kurum=istek.kurum.strip(),
        sektor=istek.sektor,
        rol="admin",  # kaydı oluşturan kurum kendi hesabının admin'idir
        bildirim_tercihleri={},
    )
    db.add(kullanici)
    db.commit()
    db.refresh(kullanici)
    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="ayar",
        mesaj=f"Yeni kurum hesabı oluşturuldu: {kullanici.kurum}", kurum_id=kullanici.id,
    ))
    db.commit()

    token = token_olustur({"sub": kullanici.email, "rol": kullanici.rol}, timedelta(minutes=60))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/api/auth/giris")
@limiter.limit(GIRIS_LIMITI)
def giris_yap(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    kullanici = db.query(Kullanici).filter(Kullanici.email == form_data.username.lower().strip()).first()
    if not kullanici or not sifre_dogrula(form_data.password, kullanici.hashed_password):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    token = token_olustur({"sub": kullanici.email, "rol": kullanici.rol}, timedelta(minutes=60))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/api/auth/ben")
def ben(kullanici: Kullanici = Depends(gecerli_kullanici_al)):
    return {
        "email": kullanici.email, "kurum": kullanici.kurum, "sektor": kullanici.sektor,
        "rol": kullanici.rol, "bildirim_tercihleri": kullanici.bildirim_tercihleri or {},
    }


# ---- Sistem Ayarları > Hesap Güvenliği: şifre / e-posta değiştirme ---------
# Kullanıcı isteği: hesap sahibi kurum, sistem ayarları kısmından isterse
# şifresini isterse e-posta adresini değiştirebilmelidir; her iki işlem de
# mevcut şifrenin doğrulanmasını zorunlu kılar.
@router.put("/api/auth/sifre-degistir")
def sifre_degistir(istek: SifreDegistirIstek, db: Session = Depends(get_db), kullanici: Kullanici = Depends(gecerli_kullanici_al)):
    if not sifre_dogrula(istek.mevcut_sifre, kullanici.hashed_password):
        raise HTTPException(status_code=401, detail="Mevcut şifre hatalı")
    if istek.yeni_sifre != istek.yeni_sifre_tekrar:
        raise HTTPException(status_code=400, detail="Yeni şifreler birbiriyle eşleşmiyor")
    if len(istek.yeni_sifre) < 8:
        raise HTTPException(status_code=400, detail="Yeni şifre en az 8 karakter olmalıdır")

    kullanici.hashed_password = sifre_hashle(istek.yeni_sifre)
    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="ayar",
        mesaj="Hesap şifresi değiştirildi.", kurum_id=kullanici.id,
    ))
    db.commit()
    return {"durum": "şifre güncellendi"}


@router.put("/api/auth/email-degistir")
def email_degistir(istek: EmailDegistirIstek, db: Session = Depends(get_db), kullanici: Kullanici = Depends(gecerli_kullanici_al)):
    if not sifre_dogrula(istek.mevcut_sifre, kullanici.hashed_password):
        raise HTTPException(status_code=401, detail="Mevcut şifre hatalı")
    yeni_email = istek.yeni_email.lower().strip()
    if db.query(Kullanici).filter(Kullanici.email == yeni_email, Kullanici.id != kullanici.id).first():
        raise HTTPException(status_code=409, detail="Bu e-posta adresi başka bir hesap tarafından kullanılıyor")

    eski_email = kullanici.email
    kullanici.email = yeni_email
    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="ayar",
        mesaj=f"Hesap e-postası değiştirildi: {eski_email} -> {yeni_email}", kurum_id=kullanici.id,
    ))
    db.commit()

    token = token_olustur({"sub": kullanici.email, "rol": kullanici.rol}, timedelta(minutes=60))
    return {"durum": "e-posta güncellendi", "access_token": token, "token_type": "bearer"}
