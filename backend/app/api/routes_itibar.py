"""İtibar Skoru (Reputation Score) API uç noktası.

bkz. app/services/itibar_skoru.py — Fombrun/Hovland-Weiss/Ebbinghaus tabanlı
tanh-EWMA modeli. Risk skorunun aksine (bkz. routes_krizler.py: risk-hesapla,
istemci RiskGirdisi'yi kendisi hesaplayıp gönderir) itibar skoru DOĞRUDAN bu
kurumun veritabanında zaten saklı olan Icerik kayıtlarından sunucu tarafında
hesaplanır — çünkü gerekli tüm sinyaller (duygu, kaynak güveni, etkileşim,
zaman) zaten icerikler tablosunda mevcuttur; istemciden ayrıca payload
beklemek gereksiz tekrar (duplicate logic) olurdu.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import Icerik, Kullanici
from app.schemas.schemas import ItibarSonucuCikti, ItibarKatkiCikti
from app.services import itibar_skoru
from app.core.security import gecerli_kullanici_al

router = APIRouter(prefix="/api/itibar", tags=["itibar"])


@router.get("/hesapla", response_model=ItibarSonucuCikti)
def itibar_hesapla(
    limit: int = 200,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Kurumun en güncel `limit` içeriğinden itibar skorunu hesaplar.

    Not: `limit` neden 200? İtibar formülündeki üstel zaman aşınımı (λ,
    varsayılan T½=36 saat) zaten eski içeriklerin ağırlığını otomatik olarak
    ihmal edilebilir düzeye indirir (bkz. itibar_skoru.py docstring) — bu
    yüzden "son 200 içerik" gibi sabit bir pencere, formülün kendisini
    bozmadan yalnızca hesaplama maliyetini sınırlayan bir performans
    optimizasyonudur, istatistiksel bir varsayım değildir.
    """
    icerikler = (
        db.query(Icerik)
        .filter(Icerik.kurum_id == kullanici.id)
        .order_by(Icerik.tarih.desc())
        .limit(limit)
        .all()
    )

    girdiler = [
        itibar_skoru.ItibarIcerikGirdisi(
            duygu=i.duygu,
            duygu_guveni=i.puan,
            kaynak_guven_puani=i.kaynak_guven_puani,
            etkilesim=i.yorum_sayisi,
            icerik_zamani=i.tarih,
            kaynak_id=str(i.id),
            ozet=i.baslik,
        )
        for i in icerikler
    ]

    sonuc = itibar_skoru.hesapla(girdiler)

    return ItibarSonucuCikti(
        skor=sonuc.skor,
        icerik_sayisi=sonuc.icerik_sayisi,
        net_agirlikli_duygu=sonuc.net_agirlikli_duygu,
        yarilanma_omru_saat=sonuc.yarilanma_omru_saat,
        alpha=sonuc.alpha,
        katkilar=[
            ItibarKatkiCikti(
                kaynak_id=str(k.kaynak_id) if k.kaynak_id is not None else None,
                ozet=k.ozet, isaretli_skor=k.isaretli_skor, agirlik=k.agirlik,
                zaman_asinimi_carpani=k.zaman_asinimi_carpani,
                agirlikli_katki_orani=k.agirlikli_katki_orani,
            )
            for k in sonuc.katkilar[:20]  # yalnızca en etkili 20 katkı raporlanır (UI okunabilirliği)
        ],
        aciklama=sonuc.aciklama,
    )
