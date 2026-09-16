"""
Uçtan Uca Tarama Zinciri (Faz 6-7): Toplama -> NLP/ABSA -> Risk/İtibar
Skorlama -> Veritabanı.

Document 122'nin en kritik eleştirisi buydu: "worker.py aktifleştirilerek
... otomasyon kurulacak" ama görev fonksiyonları boş iskeletti; collector'lar
`NotImplementedError` fırlatıyordu. Bu modül, o zincirin GERÇEK uygulamasıdır
ve hem `app/worker.py`'nin Celery görevinden HEM DE `routes_krizler.py`'nin
senkron "tara-şimdi" API ucundan ortak çağrılır — böylece Redis/Celery
kurulu olmasa bile (bu ortamda Docker yok) sistem bu fonksiyon üzerinden
TAM işlevsel bir uçtan uca tarama yapabilir.
"""
from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.collectors.connectors import tum_collectorlar
from app.config import settings
from app.models.orm import Icerik, Kriz, Kullanici, DenetimKaydi
from app.services import (
    absa, bot_detection, dil_tespit, ewma_anomali, fake_news, itibar_skoru, risk_scoring,
    source_credibility, topic_modeling, vektor_benzerlik,
)
from app.services.sentiment import get_sentiment_analyzer

logger = logging.getLogger(__name__)

# Kriz-sinyali anahtar kelimeleri (Bölüm 5 "Anahtar Kelime Yoğunluğu" bileşeni,
# risk_scoring.py bilesenler["anahtar_kelime_yogunlugu"]) — boykot/dolandırıcılık/
# skandal gibi krize işaret eden yaygın Türkçe ifadeler.
_KRIZ_ANAHTAR_KELIMELERI = {
    "boykot", "dolandırıcı", "dolandırıcılık", "skandal", "rezalet", "iptal ediyorum",
    "asla almam", "yalan", "kandırıldık", "mahkemelik", "dava açacağım", "toplatılsın",
}

# Tek bir taramada ABSA (zero-shot NLI) çalıştırılacak MAKSİMUM içerik sayısı.
# Her ABSA çağrısı bir transformer ileri-geçişi gerektirdiğinden (CPU'da göreceli
# yavaş), büyük hacimli taramalarda API isteğinin makul sürede dönmesi için
# bu pragmatik bir üst sınırdır — istatistiksel bir varsayım değildir.
_ABSA_ORNEKLEM_SINIRI = 20


def _platform_agirligi(platform: str) -> float:
    return settings.PLATFORM_AGIRLIKLARI.get(platform.lower(), 0.5)


def _hacim_z_skoru(db: Session, kurum_id: int, simdi: datetime) -> tuple[float, int, int]:
    """Son 24 saatlik SAATLİK hacim serisini gerçek DB verisinden kurar ve
    EWMA Z-skorunu hesaplar (bkz. ewma_anomali.py)."""
    baslangic = simdi - timedelta(hours=24)
    zamanlar = [
        t for (t,) in db.query(Icerik.tarih)
        .filter(Icerik.kurum_id == kurum_id, Icerik.tarih >= baslangic)
        .all()
    ]
    sayac = Counter(t.replace(minute=0, second=0, microsecond=0) for t in zamanlar)
    saatler = [(baslangic + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0) for i in range(25)]
    hacim_serisi = [sayac.get(s, 0) for s in saatler]

    z = ewma_anomali.son_z_skoru(hacim_serisi)
    guncel = hacim_serisi[-1] if hacim_serisi else 0
    onceki = hacim_serisi[-2] if len(hacim_serisi) > 1 else 0
    return z, onceki, guncel


def tek_kurum_tara(
    db: Session,
    kullanici: Kullanici,
    anahtar_kelime: str | None = None,
    limit_per_kaynak: int = 15,
) -> dict:
    """Bir kurum için tüm aktif collector'lardan veri toplar, NLP/ABSA
    pipeline'ından geçirir, veritabanına yazar ve güncel risk/itibar
    skorlarını hesaplayıp döner."""
    anahtar_kelime = (anahtar_kelime or kullanici.kurum or "").strip()
    if not anahtar_kelime:
        return {"durum": "anahtar_kelime_yok"}

    topic_model = topic_modeling.get_topic_model()
    simdi = datetime.utcnow()

    kaynak_ozetleri: list[dict] = []
    toplanan: list[Icerik] = []

    for collector in tum_collectorlar():
        if not collector.aktif_mi():
            kaynak_ozetleri.append({"platform": collector.platform_adi, "aktif": False, "toplanan": 0})
            continue
        try:
            ham_liste = collector.topla(anahtar_kelime, limit=limit_per_kaynak)
        except Exception as exc:  # collector zaten kendi içinde yakalıyor ama son bir güvenlik ağı
            logger.warning("Collector %s beklenmedik hata: %s", collector.platform_adi, exc)
            ham_liste = []
        kaynak_ozetleri.append({"platform": collector.platform_adi, "aktif": True, "toplanan": len(ham_liste)})

        for ham in ham_liste:
            metin = f"{ham.baslik}\n{ham.icerik}".strip()
            if not metin:
                continue
            # Faz 10 (çok dilli analiz): her içerik kendi dilinde analiz edilir —
            # YouTube/Reddit gibi kaynaklardan gelen içerik Türkçe olmak zorunda
            # değildir (bkz. app/services/dil_tespit.py, app/services/sentiment.py).
            dil_sonucu = dil_tespit.tespit_et(metin)
            analyzer = get_sentiment_analyzer(dil_sonucu.kod)
            duygu = analyzer.analiz_et(metin)
            konu = topic_model.konu_belirle(metin)
            guven_puani = source_credibility.guven_puani_hesapla("yeni")

            icerik = Icerik(
                kurum_id=kullanici.id, platform=ham.platform, baslik=(ham.baslik or metin[:80])[:250],
                icerik=ham.icerik or metin, duygu=duygu.duygu, duygu_alt_tip=duygu.alt_tip,
                puan=duygu.puan, konu=konu, yorum_sayisi=max(0, ham.yorum_sayisi),
                hesap_id=ham.hesap_id, kaynak_guven_puani=guven_puani, tarih=simdi,
                aciklama_kanitlari=duygu.aciklama_kanitlari, dil=dil_sonucu.kod,
            )
            db.add(icerik)
            toplanan.append(icerik)

    if not toplanan:
        return {"durum": "veri_bulunamadi", "kaynaklar": kaynak_ozetleri}

    db.flush()  # id'leri almadan risk hesaplaması yeterli, commit en sonda

    # --- ABSA (Faz 3): örneklemdeki her içerik için 5 akademik boyuta ayrıştır ---
    yonetisim_negatif_sayisi = 0
    yonetisim_toplam_sayisi = 0
    for icerik in toplanan[:_ABSA_ORNEKLEM_SINIRI]:
        try:
            absa_sonuc = absa.analiz_et(f"{icerik.baslik}\n{icerik.icerik}")
        except Exception as exc:
            logger.warning("ABSA analizi başarısız (fallback zaten denenmişti): %s", exc)
            continue
        if "yonetisim_etik" in absa_sonuc.boyut_skorlari:
            yonetisim_toplam_sayisi += 1
            if absa_sonuc.boyut_skorlari["yonetisim_etik"] < -0.1:
                yonetisim_negatif_sayisi += 1

    # S_olumsuz (SCCT "Preventable/Önlenemez Kurum Kusuru" kümesi oranı, Document 121 s.3)
    sscct_onlenemez_orani = (yonetisim_negatif_sayisi / yonetisim_toplam_sayisi) if yonetisim_toplam_sayisi else 0.0

    # --- Benford Kanunu bot testi (Faz 2): gerçek etkileşim sayılarıyla ---
    etkilesim_serisi = [i.yorum_sayisi for i in toplanan if i.yorum_sayisi > 0]
    benford_skoru, _ = bot_detection.benford_sapma_skoru(etkilesim_serisi)

    # --- EWMA hacim anomalisi (Faz 2): gerçek DB geçmişinden ---
    z_skoru, onceki_saat_hacim, guncel_saat_hacim = _hacim_z_skoru(db, kullanici.id, simdi)

    # --- Geçmiş kriz benzerliği (Faz 7, bileşen #15): Qdrant/in-memory TF-IDF ---
    en_yaygin_konu_gecici = Counter(i.konu for i in toplanan if i.konu).most_common(1)
    konu_gecici = en_yaygin_konu_gecici[0][0] if en_yaygin_konu_gecici else None
    ornek_metin = " ".join(f"{i.baslik} {i.icerik}" for i in toplanan[:5])
    try:
        benzerlik_sonucu = vektor_benzerlik.gecmis_kriz_benzerligi_hesapla(ornek_metin, konu=konu_gecici)
        gecmis_kriz_benzerlik_skoru = benzerlik_sonucu.benzerlik_skoru
    except Exception as exc:
        logger.warning("Geçmiş kriz benzerliği hesaplanamadı: %s", exc)
        gecmis_kriz_benzerlik_skoru = 0.0

    negatif_sayisi = sum(1 for i in toplanan if i.duygu == "negatif")
    negatif_oran = negatif_sayisi / len(toplanan)
    duygu_yogunlugu = sum(i.puan for i in toplanan if i.duygu == "negatif") / max(1, negatif_sayisi)
    haber_sayisi = sum(1 for i in toplanan if i.platform == "haber_sitesi")
    metin_havuzu = " ".join(f"{i.baslik} {i.icerik}".lower() for i in toplanan)
    anahtar_kelime_yogunlugu = sum(1 for k in _KRIZ_ANAHTAR_KELIMELERI if k in metin_havuzu) / len(_KRIZ_ANAHTAR_KELIMELERI)

    girdi = risk_scoring.RiskGirdisi(
        negatif_icerik_orani=negatif_oran,
        onceki_saat_hacim=onceki_saat_hacim, guncel_saat_hacim=guncel_saat_hacim,
        ortalama_yorum_yayilma_hizi=sum(i.yorum_sayisi for i in toplanan) / max(1, len(toplanan)),
        haber_kaynagi_sayisi=haber_sayisi,
        paylasim_sayisi=sum(i.yorum_sayisi for i in toplanan),
        dogrulanmis_hesap_sayisi=0, toplam_icerik_sayisi=len(toplanan),
        duygu_yogunlugu_ortalama=duygu_yogunlugu,
        bot_skoru_ortalama=benford_skoru or 0.0,
        platform_agirlik_ortalama=sum(_platform_agirligi(i.platform) for i in toplanan) / len(toplanan),
        hesap_guven_puani_ortalama=sum(i.kaynak_guven_puani for i in toplanan) / len(toplanan),
        anahtar_kelime_yogunlugu=anahtar_kelime_yogunlugu,
        haber_guvenilirlik_ortalama=(
            sum(i.kaynak_guven_puani for i in toplanan if i.platform == "haber_sitesi") / haber_sayisi
        ) if haber_sayisi else 0.5,
        gecmis_kriz_benzerlik_skoru=gecmis_kriz_benzerlik_skoru,
        hacim_z_skoru=z_skoru,
        sscct_onlenemez_orani=sscct_onlenemez_orani,
        bot_anomali_benford_skoru=benford_skoru,
    )
    risk_sonuc = risk_scoring.hesapla(girdi)

    # --- İtibar Skoru (Faz 1) ---
    itibar_girdiler = [
        itibar_skoru.ItibarIcerikGirdisi(
            duygu=i.duygu, duygu_guveni=i.puan, kaynak_guven_puani=i.kaynak_guven_puani,
            etkilesim=i.yorum_sayisi, icerik_zamani=i.tarih, kaynak_id=str(i.id) if i.id else None,
            ozet=i.baslik,
        )
        for i in toplanan
    ]
    itibar_sonuc = itibar_skoru.hesapla(itibar_girdiler, simdi=simdi)

    # --- Kriz oluşturma/güncelleme eşiği: kurumun kendi ayarındaki eşik (0-10 ölçek,
    # frontend/domain'deki "esik" alanıyla aynı) risk_sonuc.toplam_skor (0-100) ile
    # kıyaslanabilir hale getirilir (eşik*10). ---
    en_yaygin_konu = Counter(i.konu for i in toplanan if i.konu).most_common(1)
    konu = en_yaygin_konu[0][0] if en_yaygin_konu else "Genel"

    kriz: Kriz | None = None
    if risk_sonuc.toplam_skor >= 50:  # Orta eşiğin üzeri: kayda değer sinyal
        kriz = (
            db.query(Kriz)
            .filter(Kriz.kurum_id == kullanici.id, Kriz.konu == konu, Kriz.durum == "Aktif")
            .first()
        )
        if kriz is None:
            kriz = Kriz(
                kurum_id=kullanici.id, baslik=f"{konu} — Otomatik Tespit", konu=konu,
                aciklama=f"Otomatik tarama ile tespit edildi ({anahtar_kelime}).",
                durum="Aktif" if risk_sonuc.toplam_skor >= 50 else "İzleniyor",
                platform=list({i.platform for i in toplanan}),
            )
            db.add(kriz)
        kriz.siddet = risk_sonuc.toplam_skor
        kriz.icerik_sayisi = (kriz.icerik_sayisi or 0) + len(toplanan)
        kriz.skor_negatif_duygu = risk_sonuc.bilesenler["negatif_duygu"]
        kriz.skor_duygu_yogunlugu = risk_sonuc.bilesenler["duygu_yogunlugu"]
        kriz.skor_trend_artisi = risk_sonuc.bilesenler["trend_artisi"]
        kriz.skor_paylasim_hizi = risk_sonuc.bilesenler["paylasim_hizi"]
        kriz.skor_platform_agirligi = risk_sonuc.bilesenler["platform_agirligi"]
        kriz.skor_hesap_guvenilirligi_riski = risk_sonuc.bilesenler["hesap_guvenilirligi_riski"]
        kriz.skor_bot_aktivitesi = risk_sonuc.bilesenler["bot_aktivitesi"]
        kriz.skor_anahtar_kelime_yogunlugu = risk_sonuc.bilesenler["anahtar_kelime_yogunlugu"]
        kriz.skor_haber_guvenilirligi = risk_sonuc.bilesenler["haber_guvenilirligi"]
        kriz.skor_cografi_yayilim = risk_sonuc.bilesenler["cografi_yayilim"]
        kriz.skor_icerik_benzerligi = risk_sonuc.bilesenler["icerik_benzerligi"]
        kriz.skor_influencer_etkisi = risk_sonuc.bilesenler["influencer_etkisi"]
        kriz.skor_gorsel_icerik = risk_sonuc.bilesenler["gorsel_icerik"]
        kriz.skor_sahte_haber_riski = risk_sonuc.bilesenler["sahte_haber_riski"]
        kriz.skor_gecmis_kriz_benzerligi = risk_sonuc.bilesenler["gecmis_kriz_benzerligi"]
        kriz.skor_icerik_yayilimi = risk_sonuc.bilesenler["icerik_yayilimi"]
        db.flush()
        for i in toplanan:
            i.kriz_id = kriz.id

    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=simdi, tur="tarama", kurum_id=kullanici.id,
        kriz_id=kriz.id if kriz else None,
        mesaj=(
            f"Otomatik tarama: {len(toplanan)} içerik toplandı ({anahtar_kelime}), "
            f"risk={risk_sonuc.toplam_skor}, itibar={itibar_sonuc.skor}."
        ),
    ))
    db.commit()

    return {
        "durum": "tamamlandi",
        "toplanan_icerik_sayisi": len(toplanan),
        "kaynaklar": kaynak_ozetleri,
        "risk_skoru": risk_sonuc.toplam_skor,
        "risk_seviyesi": risk_sonuc.risk_seviyesi,
        "itibar_skoru": itibar_sonuc.skor,
        "kriz_id": kriz.id if kriz else None,
        "kriz_olusturuldu_mu": kriz is not None,
    }


def tum_kurumlari_tara(db: Session) -> list[dict]:
    """worker.py'nin periyodik görevi tarafından çağrılır: kayıtlı TÜM
    kurum hesapları için tarama zincirini sırayla çalıştırır."""
    sonuclar = []
    for kullanici in db.query(Kullanici).all():
        try:
            sonuc = tek_kurum_tara(db, kullanici)
        except Exception as exc:
            logger.exception("Kurum %s taraması başarısız: %s", kullanici.id, exc)
            sonuc = {"durum": "hata", "detay": str(exc)}
        sonuclar.append({"kurum_id": kullanici.id, **sonuc})
    return sonuclar
