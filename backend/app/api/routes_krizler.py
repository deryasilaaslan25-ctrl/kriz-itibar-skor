from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import Kriz, DenetimKaydi, Kullanici
from app.schemas.schemas import (
    KrizCikti, RiskSkoruDetay, TahminIstek, GecmisKrizAnaliziCikti, BildirimTercihiIstek, GeriBildirim,
    CrisisPRActionReportCikti,
)
from app.services import risk_scoring, forecasting, anomaly_detection
from app.services.llm_advisor import (
    get_scct_kural_motoru, get_llm_oneri_motoru, get_gecmis_kriz_analiz_motoru,
    SorumlulukSeviyesi, ALT_TAKTIK_BILGISI,
)
from app.core.security import gecerli_kullanici_al
from app.core.rate_limit import limiter, TARAMA_TETIKLE_LIMITI
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/krizler", tags=["krizler"])


def _kriz_to_cikti(k: Kriz) -> KrizCikti:
    risk_detay = RiskSkoruDetay(
        toplam_skor=k.siddet,
        risk_seviyesi=risk_scoring.risk_seviyesi_belirle(k.siddet),
        bilesenler={
            "negatif_duygu": k.skor_negatif_duygu,
            "duygu_yogunlugu": k.skor_duygu_yogunlugu,
            "trend_artisi": k.skor_trend_artisi,
            "paylasim_hizi": k.skor_paylasim_hizi,
            "platform_agirligi": k.skor_platform_agirligi,
            "hesap_guvenilirligi_riski": k.skor_hesap_guvenilirligi_riski,
            "bot_aktivitesi": k.skor_bot_aktivitesi,
            "anahtar_kelime_yogunlugu": k.skor_anahtar_kelime_yogunlugu,
            "haber_guvenilirligi": k.skor_haber_guvenilirligi,
            "cografi_yayilim": k.skor_cografi_yayilim,
            "icerik_benzerligi": k.skor_icerik_benzerligi,
            "influencer_etkisi": k.skor_influencer_etkisi,
            "gorsel_icerik": k.skor_gorsel_icerik,
            "sahte_haber_riski": k.skor_sahte_haber_riski,
            "gecmis_kriz_benzerligi": k.skor_gecmis_kriz_benzerligi,
            "icerik_yayilimi": k.skor_icerik_yayilimi,
        },
        aciklama=f"Toplam {k.siddet}/100 puan.",
    )
    return KrizCikti(
        id=k.id, baslik=k.baslik, aciklama=k.aciklama, siddet=k.siddet,
        platform=k.platform or [], tarih=k.tarih, konu=k.konu, durum=k.durum,
        icerik_sayisi=k.icerik_sayisi, feedback=k.feedback, risk_detay=risk_detay,
        anomali_tespit_edildi=k.anomali_tespit_edildi,
        tahmini_24s_risk=k.tahmini_24s_risk, tahmini_72s_risk=k.tahmini_72s_risk,
        tahmini_7g_risk=k.tahmini_7g_risk,
    )


@router.get("", response_model=list[KrizCikti])
def krizleri_listele(
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Veri izolasyonu: bir kurum yalnızca kendi kurum_id'sine bağlı krizleri görür."""
    krizler = (
        db.query(Kriz)
        .filter(Kriz.kurum_id == kullanici.id)
        .order_by(Kriz.tarih.desc())
        .all()
    )
    return [_kriz_to_cikti(k) for k in krizler]


def _kriz_kurumdan_al(kriz_id: int, db: Session, kullanici: Kullanici) -> Kriz:
    k = (
        db.query(Kriz)
        .filter(Kriz.id == kriz_id, Kriz.kurum_id == kullanici.id)
        .first()
    )
    if not k:
        # Kasıtlı olarak "yetkisiz" yerine "bulunamadı" döndürülür — başka bir
        # kurumun kriz id'lerinin var olup olmadığını dahi sızdırmamak için.
        raise HTTPException(404, "Kriz bulunamadı")
    return k


@router.get("/{kriz_id}", response_model=KrizCikti)
def kriz_detay(
    kriz_id: int,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    k = _kriz_kurumdan_al(kriz_id, db, kullanici)
    return _kriz_to_cikti(k)


@router.post("/{kriz_id}/risk-hesapla", response_model=RiskSkoruDetay)
@limiter.limit(TARAMA_TETIKLE_LIMITI)
def risk_hesapla(
    request: Request,
    kriz_id: int,
    girdi: risk_scoring.RiskGirdisi,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """
    Bölüm 8: Açıklanabilir risk skoru hesaplama + denetim kaydı.
    Her hesaplama DenetimKaydi tablosuna yazılır (izlenebilirlik/auditability).
    Pahalı bir ML/NLP işlemi tetiklediği için ayrı, sıkı bir hız sınırına
    tabidir (bkz. app/core/rate_limit.py: TARAMA_TETIKLE_LIMITI).
    """
    k = _kriz_kurumdan_al(kriz_id, db, kullanici)

    sonuc = risk_scoring.hesapla(girdi)

    k.siddet = sonuc.toplam_skor
    k.skor_negatif_duygu = sonuc.bilesenler["negatif_duygu"]
    k.skor_duygu_yogunlugu = sonuc.bilesenler["duygu_yogunlugu"]
    k.skor_trend_artisi = sonuc.bilesenler["trend_artisi"]
    k.skor_paylasim_hizi = sonuc.bilesenler["paylasim_hizi"]
    k.skor_platform_agirligi = sonuc.bilesenler["platform_agirligi"]
    k.skor_hesap_guvenilirligi_riski = sonuc.bilesenler["hesap_guvenilirligi_riski"]
    k.skor_bot_aktivitesi = sonuc.bilesenler["bot_aktivitesi"]
    k.skor_anahtar_kelime_yogunlugu = sonuc.bilesenler["anahtar_kelime_yogunlugu"]
    k.skor_haber_guvenilirligi = sonuc.bilesenler["haber_guvenilirligi"]
    k.skor_cografi_yayilim = sonuc.bilesenler["cografi_yayilim"]
    k.skor_icerik_benzerligi = sonuc.bilesenler["icerik_benzerligi"]
    k.skor_influencer_etkisi = sonuc.bilesenler["influencer_etkisi"]
    k.skor_gorsel_icerik = sonuc.bilesenler["gorsel_icerik"]
    k.skor_sahte_haber_riski = sonuc.bilesenler["sahte_haber_riski"]
    k.skor_gecmis_kriz_benzerligi = sonuc.bilesenler["gecmis_kriz_benzerligi"]
    k.skor_icerik_yayilimi = sonuc.bilesenler["icerik_yayilimi"]
    k.guvenilir_kaynak_teyidi = sonuc.destekleyici_sinyaller.get("guvenilir_kaynak_teyidi", 0.0)

    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="tarama",
        mesaj=sonuc.aciklama, kriz_id=k.id, kurum_id=kullanici.id,
    ))
    db.commit()

    return RiskSkoruDetay(
        toplam_skor=sonuc.toplam_skor, risk_seviyesi=sonuc.risk_seviyesi,
        bilesenler=sonuc.bilesenler, aciklama=sonuc.aciklama,
    )


def _oneri_hesapla(k: Kriz, sorumluluk_seviyesi: SorumlulukSeviyesi):
    """kriz_onerisi_getir VE rapor_indir uçlarının ortak kullandığı SCCT+LLM
    öneri hesaplama mantığı (tekrar/duplicate kod önlemek için tek yerde)."""
    bilesenler = {
        "negatif_duygu": k.skor_negatif_duygu, "bot_aktivitesi": k.skor_bot_aktivitesi,
        "sahte_haber_riski": k.skor_sahte_haber_riski,
    }
    bot_baskin = k.skor_bot_aktivitesi >= 0.5 * risk_scoring.settings.W_BOT_AKTIVITESI
    sahte_haber_yuksek = k.skor_sahte_haber_riski >= 0.5 * risk_scoring.settings.W_SAHTE_HABER

    kural_motoru = get_scct_kural_motoru()
    oneri = kural_motoru.strateji_belirle(
        toplam_risk_skoru=k.siddet, sorumluluk_seviyesi=sorumluluk_seviyesi,
        bot_aktivitesi_baskin=bot_baskin, sahte_haber_riski_yuksek=sahte_haber_yuksek,
    )

    llm_motoru = get_llm_oneri_motoru()
    if llm_motoru.aktif_mi():
        try:
            oneri = llm_motoru.oneri_uret(oneri, bilesenler)
        except NotImplementedError:
            # Graceful degradation: LLM iskeleti henüz üretime bağlanmadı,
            # rule-based öneri kullanıcıya sunulmaya devam eder.
            pass
    return oneri


@router.post("/{kriz_id}/oneri", response_model=dict)
def kriz_onerisi_getir(
    kriz_id: int,
    sorumluluk_seviyesi: SorumlulukSeviyesi = SorumlulukSeviyesi.ORTA,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """
    Bölüm 8-9: "Risk var" demekle yetinmeyip "Kurum ne yapmalı?" sorusuna
    yanıt veren hibrit SCCT + LLM karar destek uç noktası.

    sorumluluk_seviyesi kurum tarafından (veya ileride otomatik bir
    sınıflandırıcı ile, bkz. app/ml/xgboost_classifier.py) belirlenir;
    bot/sahte-haber baskınlığı ise mevcut risk bileşenlerinden otomatik
    çıkarsanır.
    """
    k = _kriz_kurumdan_al(kriz_id, db, kullanici)
    oneri = _oneri_hesapla(k, sorumluluk_seviyesi)

    def _taktik_detay(taktik):
        if taktik is None:
            return None
        bilgi = ALT_TAKTIK_BILGISI[taktik]
        return {
            "kod": taktik.value, "ad": bilgi.ad, "durus": bilgi.durus.value,
            "akademik_kaynak": bilgi.akademik_kaynak, "aciklama": bilgi.aciklama,
        }

    return {
        "strateji": oneri.strateji.value,
        "sorumluluk_seviyesi": oneri.sorumluluk_seviyesi.value,
        "ilk_mudahale_suresi_saat": oneri.ilk_mudahale_suresi_saat,
        "gerekce": oneri.gerekce,
        "somut_adimlar": oneri.somut_adimlar,
        "llm_destekli": oneri.llm_destekli,
        "llm_metni": oneri.llm_metni,
        # Faz 5: 18-taktikli SCCT/IRT/Apologia genişlemesi — birincil taktik +
        # (frontend "Alternatif Taslak Göster (1/3)" döngüsü için) alternatifler.
        "spesifik_strateji": _taktik_detay(oneri.spesifik_strateji),
        "alternatif_stratejiler": [_taktik_detay(t) for t in oneri.alternatif_stratejiler],
        "metodoloji_notu": oneri.metodoloji_notu,
        "toplam_taktik_sayisi": len(ALT_TAKTIK_BILGISI),
    }


@router.post("/{kriz_id}/tahmin", response_model=dict)
@limiter.limit(TARAMA_TETIKLE_LIMITI)
def tahmin_uret(
    request: Request,
    kriz_id: int,
    gecmis_skorlar: list[float],
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Bölüm 10: 24s/72s/7g risk tahmini."""
    k = _kriz_kurumdan_al(kriz_id, db, kullanici)

    sonuc = forecasting.tahmin_uret(gecmis_skorlar)
    k.tahmini_24s_risk = sonuc["24s"]
    k.tahmini_72s_risk = sonuc["72s"]
    k.tahmini_7g_risk = sonuc["7g"]
    db.commit()
    return sonuc


@router.post("/tara-simdi", response_model=dict)
@limiter.limit(TARAMA_TETIKLE_LIMITI)
def tara_simdi(
    request: Request,
    anahtar_kelime: str | None = None,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Faz 6/7: Uçtan uca tarama zincirini (toplama -> NLP/ABSA -> risk/itibar
    skorlama -> DB) SENKRON olarak, Celery/Redis'e ihtiyaç duymadan tetikler.

    Bu uç, frontend'deki "Şimdi Tara" butonunun bağlandığı gerçek backend
    uç noktasıdır (önceden bu tamamen istemci-taraflı bir simülasyondu,
    bkz. eski app-context.tsx taraSimdi()). Docker/Celery kuruluysa aynı
    zincir periyodik olarak app/worker.py üzerinden de otomatik çalışır;
    bu uç, o altyapı olmadığında sistemin YİNE DE tam işlevsel kalmasını sağlar.
    """
    from app.services.tarama_pipeline import tek_kurum_tara

    return tek_kurum_tara(db, kullanici, anahtar_kelime=anahtar_kelime)


@router.get("/{kriz_id}/rapor-json", response_model=CrisisPRActionReportCikti)
def rapor_json(
    kriz_id: int,
    sorumluluk_seviyesi: SorumlulukSeviyesi = SorumlulukSeviyesi.ORTA,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """rapor-indir (PDF) ile AYNI içeriği JSON olarak döner — frontend PR
    Danışmanı sayfasının rapor taslaklarını indirmeden EKRANDA gösterebilmesi
    için (bkz. app/services/pr_rapor.py)."""
    from app.services.pr_rapor import generate_academic_pr_report

    k = _kriz_kurumdan_al(kriz_id, db, kullanici)
    oneri = _oneri_hesapla(k, sorumluluk_seviyesi)
    return generate_academic_pr_report(
        oneri=oneri, kurum_adi=kullanici.kurum or "Kurum", kriz_baslik=k.baslik,
        kriz_konusu=k.konu or "Genel", risk_skoru=k.siddet,
        risk_seviyesi=risk_scoring.risk_seviyesi_belirle(k.siddet),
    )


@router.get("/{kriz_id}/rapor-indir")
@limiter.limit(TARAMA_TETIKLE_LIMITI)
def rapor_indir(
    request: Request,
    kriz_id: int,
    sorumluluk_seviyesi: SorumlulukSeviyesi = SorumlulukSeviyesi.ORTA,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Document 121 s.4/s.9: Kurumsal Kriz Müdahale Raporu'nu (Crisis PR
    Action Report) PDF olarak üretir ve indirilebilir stream olarak döner.

    Akış: SCCTOnerisi (rule+LLM) -> generate_academic_pr_report() [JSON
    strateji çıktısı] -> Jinja2 HTML şablonu -> WeasyPrint -> PDF binary.
    """
    from app.services.pr_rapor import generate_academic_pr_report, create_pdf_report

    k = _kriz_kurumdan_al(kriz_id, db, kullanici)
    oneri = _oneri_hesapla(k, sorumluluk_seviyesi)

    rapor = generate_academic_pr_report(
        oneri=oneri, kurum_adi=kullanici.kurum or "Kurum", kriz_baslik=k.baslik,
        kriz_konusu=k.konu or "Genel", risk_skoru=k.siddet,
        risk_seviyesi=risk_scoring.risk_seviyesi_belirle(k.siddet),
    )
    pdf_bytes = create_pdf_report(rapor)

    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="ayar",
        mesaj=f"Kriz PR raporu indirildi: {k.baslik}", kriz_id=k.id, kurum_id=kullanici.id,
    ))
    db.commit()

    dosya_adi = f"kriz-raporu-{kriz_id}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dosya_adi}"'},
    )


@router.post("/{kriz_id}/anomali-tara", response_model=dict)
@limiter.limit(TARAMA_TETIKLE_LIMITI)
def anomali_tara(
    request: Request,
    kriz_id: int,
    zaman_serisi: list[float],
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Bölüm 11: Ani yükseliş / anomali tespiti."""
    k = _kriz_kurumdan_al(kriz_id, db, kullanici)

    sonuc = anomaly_detection.tespit_et(zaman_serisi)
    k.anomali_tespit_edildi = sonuc["son_nokta_anomali_mi"]
    db.commit()
    return sonuc


@router.post("/{kriz_id}/gecmis-analiz", response_model=GecmisKrizAnaliziCikti)
@limiter.limit(TARAMA_TETIKLE_LIMITI)
def gecmis_kriz_analizi(
    request: Request,
    kriz_id: int,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Yapay Zeka Halkla İlişkiler Danışmanı eklentisi (Kriz Merkezi'ne ek).

    Aktif krizle aynı türde son 10 yılda yaşanmış tarihsel emsalleri tarar;
    her biri için (yaklaşık) tarih, kurumun o dönemki tutumu, sonucu ve
    şimdiki krize dair somut bir tavsiye döndürür. ANTHROPIC_API_KEY
    tanımlıysa gerçek bir araştırma çağrısı yapılır, tanımlı değilse
    sektöre/konuya göre kategorize edilmiş şablon kütüphanesiyle
    (jenerik/marka-agnostik örüntüler) çalışmaya devam eder.
    """
    k = _kriz_kurumdan_al(kriz_id, db, kullanici)
    motor = get_gecmis_kriz_analiz_motoru()
    return motor.analiz_uret(konu=k.konu or "Genel", sektor=kullanici.sektor, kriz_id=k.id)


@router.put("/{kriz_id}/geri-bildirim", response_model=KrizCikti)
def geri_bildirim_kaydet(
    kriz_id: int,
    deger: GeriBildirim,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Faz 8: İnsan geri bildirimi ("gerçek kriz" / "sıradan şikâyet").

    Bu alan (Kriz.feedback), ML modelinin (app/ml/xgboost_classifier.py)
    ileride GERÇEK etiketli veriyle eğitilebilmesi için birikir (bkz.
    app/ml/distillation.py docstring — şu an sentetik damıtma verisiyle
    çalışıyor, MIN_EGITIM_ORNEGI=200 gerçek geri bildirim biriktiğinde
    gerçek veriyle yeniden eğitilebilir).
    """
    k = _kriz_kurumdan_al(kriz_id, db, kullanici)
    k.feedback = deger
    if deger == "siradan":
        k.durum = "Kapandı"
    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="geri_bildirim",
        mesaj=f"İnsan değerlendirmesi kaydedildi: {'gerçek kriz' if deger == 'gercek' else 'sıradan şikâyet'}.",
        kriz_id=k.id, kurum_id=kullanici.id,
    ))
    db.commit()
    return _kriz_to_cikti(k)


@router.put("/bildirim-tercihi", response_model=dict)
def bildirim_tercihi_kaydet(
    istek: BildirimTercihiIstek,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(gecerli_kullanici_al),
):
    """Öğrenen bildirim sistemi: kullanıcı bir kriz türünü işaretlediğinde
    (bu tür kriz tekrar yükselirse bildirim istiyor musunuz?) tercihi kurum
    hesabına kalıcı olarak kaydeder; sonraki taramalarda bu tercihe göre
    davranılır (bkz. frontend app-context.tsx: bildirimGoster())."""
    tercihler = dict(kullanici.bildirim_tercihleri or {})
    tercihler[istek.konu] = istek.bildirim_istiyor
    kullanici.bildirim_tercihleri = tercihler
    db.add(DenetimKaydi(
        id=str(uuid.uuid4()), zaman=datetime.utcnow(), tur="ayar",
        mesaj=f"'{istek.konu}' türü krizler için bildirim tercihi: "
              f"{'açık' if istek.bildirim_istiyor else 'kapalı'}.",
        kurum_id=kullanici.id,
    ))
    db.commit()
    return {"konu": istek.konu, "bildirim_istiyor": istek.bildirim_istiyor}
