from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import Icerik, Kullanici
from app.schemas.schemas import IcerikAnalizIstek, IcerikCikti
from app.services.sentiment import get_sentiment_analyzer
from app.services.topic_modeling import get_topic_model
from app.services import dil_tespit
from app.services.bot_detection import get_bot_classifier, BotSinyalleri
from app.services.source_credibility import guven_puani_hesapla
from app.core.security import gecerli_kullanici_al

router = APIRouter(prefix="/api/icerikler", tags=["içerikler"])


@router.post("/analiz-et", response_model=IcerikCikti)
def icerik_analiz_et(
    istek: IcerikAnalizIstek,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """
    Uçtan uca NLP pipeline giriş noktası:
    ham metin -> temizleme -> duygu analizi -> konu modelleme -> kaynak güven puanı
    -> bot skoru (varsayılan sinyallerle) -> veritabanına kayıt.

    Bu endpoint, Bölüm 4-6-7-12-14'te tarif edilen tüm analiz zincirini
    tek bir çağrıda birleştirir.
    """
    # Faz 10 (çok dilli analiz): metnin dili tespit edilip dile uygun motor seçilir.
    dil_sonucu = dil_tespit.tespit_et(istek.icerik)
    analyzer = get_sentiment_analyzer(dil_sonucu.kod)
    duygu_sonucu = analyzer.analiz_et(istek.icerik)

    topic_model = get_topic_model()
    konu = topic_model.konu_belirle(istek.icerik)

    guven_puani = guven_puani_hesapla("yeni")  # collector'dan hesap tipi gelmiyorsa varsayılan

    yeni_icerik = Icerik(
        kurum_id=kullanici.id,
        platform=istek.platform,
        baslik=istek.baslik,
        icerik=istek.icerik,
        duygu=duygu_sonucu.duygu,
        duygu_alt_tip=duygu_sonucu.alt_tip,
        puan=duygu_sonucu.puan,
        konu=konu,
        yorum_sayisi=istek.yorum_sayisi,
        hesap_id=istek.hesap_id,
        kaynak_guven_puani=guven_puani,
        aciklama_kanitlari=duygu_sonucu.aciklama_kanitlari,
        dil=dil_sonucu.kod,
    )
    db.add(yeni_icerik)
    db.commit()
    db.refresh(yeni_icerik)
    return yeni_icerik


@router.get("", response_model=list[IcerikCikti])
def icerikleri_listele(
    limit: int = 100,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Veri izolasyonu: bir kurum yalnızca kendi kurum_id'sine bağlı içerikleri görür."""
    return (
        db.query(Icerik)
        .filter(Icerik.kurum_id == kullanici.id)
        .order_by(Icerik.tarih.desc())
        .limit(limit)
        .all()
    )


@router.get("/ara", response_model=list[IcerikCikti])
def icerik_ara(
    q: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Bölüm 12: Tam metin arama (Elasticsearch varsa kullanılır, yoksa
    PostgreSQL/SQLite ILIKE fallback'ine otomatik düşülür — bkz. app/services/arama.py)."""
    from app.services.arama import get_arama_motoru

    motor = get_arama_motoru()
    return motor.ara(db, kullanici.id, q, limit=limit)
