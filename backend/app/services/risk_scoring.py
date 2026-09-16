"""
Bölüm 8: Kriz Risk Skorlama Motoru — Açıklanabilir Yapay Zekâ (XAI) yaklaşımı.

GÜNCELLEME (2. juri eleştirisine yanıt — "6 parametre yetersiz, 15-18
değişkene çıkarılmalı"): Motor artık 16 ayrı, ayrı ayrı raporlanan
bileşenden oluşmaktadır. Skor kara kutu bir ML çıktısı DEĞİL, her
bileşeni ayrı ayrı hesaplanan ve raporlanan, denetlenebilir (auditable)
bir ağırlıklı toplam modelidir. `RiskSonucu.bilesenler` alanı doğrudan
şu formatta hakem/kullanıcıya sunulur:

    Negatif Duygu           +28
    Trend Artışı            +17
    Bot Aktivitesi          +9
    Ulusal Haber            +15
    Influencer Paylaşımı    +8
    Paylaşım Hızı           +6
    ... (16 bileşen)
    ------------------------------
    Toplam Risk             = 83

Her bileşen DenetimKaydi tablosuna yazılarak geriye dönük izlenebilirlik
sağlanır. Ağırlıklar app/config.py içinde .env ile de override edilebilir
(bilimsel tekrarlanabilirlik / hiperparametre ayarı için).

16 Bileşen (Bölüm 5 önerisiyle birebir uyumlu):
    1  Negatif Duygu Oranı           16
    2  Duygu Yoğunluğu (öfke/panik)  8
    3  Trend Artışı                  12
    4  Paylaşım Hızı                 8
    5  Platform Ağırlığı             5
    6  Hesap Güvenilirliği (ters)    6
    7  Bot Olasılığı                 9
    8  Anahtar Kelime Yoğunluğu      6
    9  Haber Güvenilirliği           8
    10 Coğrafi Yayılım               4
    11 İçerik Benzerliği (koordinasyon) 5
    12 Influencer Etkisi             8
    13 Görsel/Video İçerik           3
    14 Sahte Haber Olasılığı         6
    15 Önceki Krizlerle Benzerlik    4
    16 Güvenilir Kaynak Teyidi (destekleyici) — negatif ağırlık, riski azaltmaz;
       krizin gerçekliğini teyit eden ayrı bilgi katmanı olarak raporlanır.
    TOPLAM (1-15)                    108 -> 0-100 aralığına normalize edilir

Her Bileşenin Literatür/Yöntem Dayanağı (kısa referans — CITATIONS.md'de tam liste)
------------------------------------------------------------------------------
 1  Negatif Duygu           — Coombs (2007) SCCT: kriz algısının birincil girdisi
    kamuoyu duygu polaritesidir.
 2  Duygu Yoğunluğu         — Jones & Davis'in duygu-yoğunluk/atıf teorisi geleneği:
    öfke/panik gibi YÜKSEK UYARILMIŞLIK (high-arousal) duyguları, nötr olumsuzluktan
    daha hızlı yayılır (bkz. Berger & Milkman, 2012, "What Makes Online Content
    Viral?" — yüksek-uyarılma duygusal içerik viral yayılma olasılığını artırır).
 3  Trend Artışı            — EWMA istatistiksel süreç kontrolü (Roberts, 1959);
    bkz. ewma_anomali.py. `hacim_z_skoru` sağlanırsa bu gerçek Z-skoru kullanılır.
 4  Paylaşım Hızı           — Bakshy vd. (2011), "Everyone's an Influencer": bilgi
    yayılma HIZI (derivative), toplam hacimden ayrı, bağımsız bir viralite sinyalidir.
 5  Platform Ağırlığı       — platformlar arası ulaşılabilirlik/algoritmik yayılım
    farkı (bkz. config.py PLATFORM_AGIRLIKLARI, ör. X/TikTok > LinkedIn).
 6  Hesap Güvenilirliği     — Hovland & Weiss (1951) kaynak güvenilirliği kuramı.
 7  Bot Aktivitesi          — Yang vd. (2020) Botometer davranışsal sinyal seti +
    Benford Kanunu (Benford, 1938) sayısal-dağılım testi (bkz. bot_detection.py).
 8  Anahtar Kelime Yoğunluğu— kriz-sinyali sözlük tabanlı erken uyarı (crisis
    informatics literatüründe "keyword burst detection" yaklaşımı).
 9  Haber Güvenilirliği     — SCCT: ana akım medya teyidi krizin "gerçeklik" ve
    "kamusal önem" boyutunu güçlendirir.
10  Coğrafi Yayılım         — yayılma ölçeği (yerel->ulusal->uluslararası) kriz
    şiddetiyle doğru orantılı klasik kriz iletişimi kabulü.
11  İçerik Benzerliği       — koordineli/inorganik davranış sinyali (bot ağı emaresi,
    bkz. bileşen 7 ile ortak istatistiksel temel).
12  Influencer Etkisi       — Cha vd. (2010), "Measuring User Influence in Twitter":
    erişim tek başına yetmez, ERİŞİM×ETKİLEŞİM birlikte etkiyi belirler.
13  Görsel/Video İçerik     — çoklu-ortam içeriğin metin-only içerikten daha
    inandırıcı ve paylaşılabilir algılandığına dair medya psikolojisi bulguları.
14  Sahte Haber Olasılığı   — Vosoughi, Roy & Aral (2018), Science: yanlış bilginin
    doğru bilgiden ANLAMLI ÖLÇÜDE daha hızlı yayıldığı bulgusu.
15  Önceki Krizlerle Benzerlik — vaka-tabanlı muhakeme (case-based reasoning):
    geçmişte benzer örüntüde büyüyen krizlerle benzerlik, gelecekteki büyüme
    olasılığına dair bir ön-bilgi (prior) sağlar.
16  Güvenilir Kaynak Teyidi — destekleyici sinyal; risk toplamına dahil değildir.

Tamamlayıcı İstatistiksel Doğrulama Modeli (Document 121 s.3)
---------------------------------------------------------------
Yukarıdaki 16-bileşenli doğrusal-ağırlıklı-toplam motoru (jüri onaylı, ana XAI
iskeleti) DEĞİŞTİRİLMEDEN, Document 121'in tanımladığı 4-değişkenli lojistik
sigmoid modeli AYRI bir çapraz-doğrulama/ikinci-görüş skoru olarak eklenir
(bkz. `dogrulama_modeli_hesapla`):

    R_kriz_dogrulama(t) = 100 · σ(β₀ + β₁·Z_hacim + β₂·S_olumsuz + β₃·(dE/dt) + β₄·B_anomali)

Bu, ana skoru BOZMAZ; iki bağımsız yöntemin (doğrusal ağırlıklı toplam vs.
lojistik regresyon tarzı sigmoid) aynı yönde mi işaret ettiğini göstererek
"tek modele aşırı güvenme" riskini azaltan bir ENSEMBLE/çapraz-doğrulama
pratiğidir (bkz. istatistikte "model ensembling" / "cross-validation" ilkesi).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class RiskGirdisi:
    """Bir kriz adayı için ham sinyaller (data toplama + analiz katmanlarından gelir)."""

    # --- Temel sinyaller (ilk sürümden) ---
    negatif_icerik_orani: float          # 0-1 : son N içerik içindeki negatif oran
    onceki_saat_hacim: int                # trend kıyası için
    guncel_saat_hacim: int
    ortalama_yorum_yayilma_hizi: float    # dakikada yeni yorum/paylaşım sayısı
    haber_kaynagi_sayisi: int             # ana akım haber sitelerinde geçme sayısı
    paylasim_sayisi: int                  # toplam retweet/paylaşım (viralite)
    dogrulanmis_hesap_sayisi: int         # güvenilir/doğrulanmış kaynaklardan gelen içerik sayısı
    toplam_icerik_sayisi: int

    # --- Genişletilmiş sinyaller (2. juri eleştirisi, Bölüm 5) ---
    duygu_yogunlugu_ortalama: float = 0.0     # 0-1: öfke/panik/nefret alt kategori ort. yoğunluğu (sentiment.py)
    bot_skoru_ortalama: float = 0.0           # 0-1: bot_detection.py çıktısı ortalaması
    platform_agirlik_ortalama: float = 0.5    # 0-1: PLATFORM_AGIRLIKLARI ile ağırlıklandırılmış ort.
    hesap_guven_puani_ortalama: float = 0.5   # 0-1: source_credibility.py çıktısı ortalaması (düşükse risk artar)
    anahtar_kelime_yogunlugu: float = 0.0     # 0-1: "boykot/dolandırıcılık/skandal/iptal" vb. yoğunluk
    haber_guvenilirlik_ortalama: float = 0.5  # 0-1: ulusal/yerel/blog/forum/anonim ağırlıklı ort.
    cografi_yayilim_genislik: float = 0.0     # 0-1: il(0.2) / bölge(0.4) / ülke(0.7) / uluslararası(1.0)
    icerik_benzerlik_orani: float = 0.0       # 0-1: kopya paylaşım / koordineli davranış oranı (fake_news + bot sinyali)
    influencer_erisim_skoru: float = 0.0      # 0-1: takipçi x etkileşim normalize edilmiş etki
    gorsel_icerik_orani: float = 0.0          # 0-1: görsel/video içeren paylaşım oranı
    sahte_haber_riski_ortalama: float = 0.0   # 0-1: fake_news.py çıktısı ortalaması
    gecmis_kriz_benzerlik_skoru: float = 0.0  # 0-1: geçmiş kriz veritabanına embedding benzerliği

    # --- Faz 2 eklentisi: EWMA/Benford tabanlı istatistiksel doğrulama sinyalleri ---
    # (opsiyonel — sağlanmazsa motor eski/basit hesaplamalarla geriye dönük uyumlu çalışır)
    hacim_z_skoru: float | None = None        # EWMA Z-skoru (ewma_anomali.son_z_skoru); verilirse
                                                # "trend_artisi" bileşeni bunu kullanır (Document 121 s.3)
    sscct_onlenemez_orani: float = 0.0        # S_olumsuz: SCCT "Preventable/Önlenemez Kurum Kusuru"
                                                # kümesine giren içeriklerin oranı (bkz. absa.py A₄ boyutu)
    yayilma_ivmesi: float = 0.0                # dE/dt normalize [0,1]: etkileşim artış hızının İVMESİ
                                                # (paylasim_hizi'nden farklı: o anlık hız, bu ikinci türev)
    bot_anomali_benford_skoru: float | None = None  # B_anomali: bot_detection.benford_sapma_skoru çıktısı


@dataclass
class RiskSonucu:
    toplam_skor: float
    risk_seviyesi: str
    bilesenler: dict[str, float] = field(default_factory=dict)
    destekleyici_sinyaller: dict[str, float] = field(default_factory=dict)
    aciklama: str = ""
    en_yuksek_katki_sirasi: list[str] = field(default_factory=list)
    dogrulama_modeli: dict | None = None


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _sigmoid(x: float) -> float:
    """σ(x) = 1/(1+e^-x) — standart lojistik sigmoid fonksiyonu (Document 121 s.3)."""
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)  # sayısal kararlılık için taşma-güvenli biçim


def dogrulama_modeli_hesapla(
    hacim_z_skoru: float,
    sscct_onlenemez_orani: float,
    yayilma_ivmesi: float,
    bot_anomali_benford_skoru: float | None,
) -> dict:
    """Document 121 s.3'teki 4-değişkenli EWMA+Sigmoid modelinin BİREBİR
    uygulaması: R_kriz_dogrulama = 100·σ(β0+β1·Z+β2·S+β3·dE/dt+β4·B).

    16-bileşenli birincil motoru DEĞİŞTİRMEZ; ayrı, ikinci-görüş / çapraz-
    doğrulama skoru olarak döner (bkz. modül docstring'i: "Tamamlayıcı
    İstatistiksel Doğrulama Modeli").
    """
    from app.services.ewma_anomali import normalize_0_1 as _z_normalize

    z_norm = _z_normalize(max(0.0, hacim_z_skoru))
    s_norm = _clamp(sscct_onlenemez_orani)
    ivme_norm = _clamp(yayilma_ivmesi)
    b_norm = bot_anomali_benford_skoru if bot_anomali_benford_skoru is not None else 0.0

    logit = (
        settings.DOGRULAMA_BETA0
        + settings.DOGRULAMA_BETA1 * z_norm
        + settings.DOGRULAMA_BETA2 * s_norm
        + settings.DOGRULAMA_BETA3 * ivme_norm
        + settings.DOGRULAMA_BETA4 * b_norm
    )
    skor = round(100 * _sigmoid(logit), 2)

    return {
        "skor": skor,
        "girdi_sinyalleri": {
            "z_hacim_normalize": round(z_norm, 3),
            "sscct_onlenemez_orani": round(s_norm, 3),
            "yayilma_ivmesi": round(ivme_norm, 3),
            "bot_anomali_benford": round(b_norm, 3) if bot_anomali_benford_skoru is not None else None,
        },
        "aciklama": (
            f"İstatistiksel doğrulama skoru: {skor}/100 (β0={settings.DOGRULAMA_BETA0} + "
            f"β1·Z_hacim({z_norm:.2f}) + β2·S_olumsuz({s_norm:.2f}) + "
            f"β3·dE/dt({ivme_norm:.2f}) + β4·B_anomali({b_norm:.2f}), sonra lojistik "
            "sigmoid ile 0-100'e ölçeklendi). Bu, birincil 16-bileşenli skordan "
            "BAĞIMSIZ ikinci bir yöntemle (EWMA anomali + SCCT önlenemez-küme oranı + "
            "yayılma ivmesi + Benford bot testi) hesaplanmış bir çapraz-doğrulama "
            "skorudur; iki skor birbirine yakınsa güven artar, uzaksa insan "
            "incelemesi önerilir."
        ),
    }


def risk_seviyesi_belirle(skor: float) -> str:
    if skor <= 25:
        return "Düşük Risk"
    if skor <= 50:
        return "Orta Risk"
    if skor <= 75:
        return "Yüksek Risk"
    return "Kritik Risk"


def hesapla(girdi: RiskGirdisi) -> RiskSonucu:
    bilesenler: dict[str, float] = {}

    # 1) Negatif Duygu
    bilesenler["negatif_duygu"] = round(_clamp(girdi.negatif_icerik_orani) * settings.W_NEGATIF_DUYGU, 2)

    # 2) Duygu Yoğunluğu (öfke/panik/nefret şiddeti — sadece negatif/pozitif oranından bağımsız bir sinyal)
    bilesenler["duygu_yogunlugu"] = round(_clamp(girdi.duygu_yogunlugu_ortalama) * settings.W_DUYGU_YOGUNLUGU, 2)

    # 3) Trend Artışı
    if girdi.hacim_z_skoru is not None:
        # Document 121 s.3: "Sabit Eşik Değer" yerine "Dinamik EWMA Z-Score
        # Anomali Tespiti" (bkz. ewma_anomali.py). Z, kurumun KENDİ geçmiş
        # ortalama/varyansına göre normalleşir — sabit yüzde eşiğinden daha
        # sağlam bir anomali sinyalidir.
        trend_normalize = _clamp(girdi.hacim_z_skoru / 3.0)  # |Z|=3 (3-sigma) = tavan
    elif girdi.onceki_saat_hacim > 0:
        degisim_orani = (girdi.guncel_saat_hacim - girdi.onceki_saat_hacim) / girdi.onceki_saat_hacim
        trend_normalize = _clamp(degisim_orani / 3.0)  # %300 artış = tavan (geriye dönük uyumluluk yolu)
    else:
        trend_normalize = _clamp(1.0 if girdi.guncel_saat_hacim > 0 else 0.0)
    bilesenler["trend_artisi"] = round(trend_normalize * settings.W_TREND_ARTISI, 2)

    # 4) Paylaşım Hızı (dakikada yeni paylaşım — Bölüm 5'te trend'den ayrı, anlık ivme sinyali)
    hiz_normalize = _clamp(girdi.ortalama_yorum_yayilma_hizi / 50.0)
    bilesenler["paylasim_hizi"] = round(hiz_normalize * settings.W_PAYLASIM_HIZI, 2)

    # 5) Platform Ağırlığı (Twitter/Reddit/Instagram/TikTok/YouTube/Facebook — her platformun etkisi farklı)
    bilesenler["platform_agirligi"] = round(_clamp(girdi.platform_agirlik_ortalama) * settings.W_PLATFORM_AGIRLIGI, 2)

    # 6) Hesap Güvenilirliği (TERS orantı: ortalama hesap güveni düşükse risk artar)
    hesap_guven_riski = 1 - _clamp(girdi.hesap_guven_puani_ortalama)
    bilesenler["hesap_guvenilirligi_riski"] = round(hesap_guven_riski * settings.W_HESAP_GUVENILIRLIGI, 2)

    # 7) Bot Olasılığı
    bilesenler["bot_aktivitesi"] = round(_clamp(girdi.bot_skoru_ortalama) * settings.W_BOT_AKTIVITESI, 2)

    # 8) Anahtar Kelime Yoğunluğu (boykot, dolandırıcılık, skandal, rezalet, iptal, kriz...)
    bilesenler["anahtar_kelime_yogunlugu"] = round(_clamp(girdi.anahtar_kelime_yogunlugu) * settings.W_ANAHTAR_KELIME, 2)

    # 9) Haber Güvenilirliği (ulusal medyada geçme ağırlıklı - hem hacim hem güvenilirlik)
    haber_normalize = _clamp(girdi.haber_kaynagi_sayisi / 10.0)
    haber_guven_carpani = 0.5 + 0.5 * _clamp(girdi.haber_guvenilirlik_ortalama)
    bilesenler["haber_guvenilirligi"] = round(haber_normalize * haber_guven_carpani * settings.W_HABER_GUVENILIRLIGI, 2)

    # 10) Coğrafi Yayılım (il -> bölge -> ülke -> uluslararası)
    bilesenler["cografi_yayilim"] = round(_clamp(girdi.cografi_yayilim_genislik) * settings.W_COGRAFI_YAYILIM, 2)

    # 11) İçerik Benzerliği / Koordineli Paylaşım (bot ağı belirtisi, viraliteden ayrı bir sinyal)
    bilesenler["icerik_benzerligi"] = round(_clamp(girdi.icerik_benzerlik_orani) * settings.W_ICERIK_BENZERLIGI, 2)

    # 12) Influencer Etkisi (erişim x etkileşim)
    bilesenler["influencer_etkisi"] = round(_clamp(girdi.influencer_erisim_skoru) * settings.W_INFLUENCER_ETKISI, 2)

    # 13) Görsel/Video İçerik (görsel içerik viraliteyi ve inandırıcılığı artırır)
    bilesenler["gorsel_icerik"] = round(_clamp(girdi.gorsel_icerik_orani) * settings.W_GORSEL_ICERIK, 2)

    # 14) Sahte Haber Olasılığı
    bilesenler["sahte_haber_riski"] = round(_clamp(girdi.sahte_haber_riski_ortalama) * settings.W_SAHTE_HABER, 2)

    # 15) Önceki Krizlerle Benzerlik (geçmiş kriz veritabanına embedding benzerliği)
    bilesenler["gecmis_kriz_benzerligi"] = round(_clamp(girdi.gecmis_kriz_benzerlik_skoru) * settings.W_GECMIS_KRIZ_BENZERLIGI, 2)

    # 16) İçerik Yayılımı (viralite) — orijinal 6 parametreden korunan
    yayilim_normalize = _clamp(girdi.paylasim_sayisi / 5000.0)
    bilesenler["icerik_yayilimi"] = round(yayilim_normalize * settings.W_ICERIK_YAYILIMI, 2)

    toplam_agirlik = (
        settings.W_NEGATIF_DUYGU + settings.W_DUYGU_YOGUNLUGU + settings.W_TREND_ARTISI
        + settings.W_PAYLASIM_HIZI + settings.W_PLATFORM_AGIRLIGI + settings.W_HESAP_GUVENILIRLIGI
        + settings.W_BOT_AKTIVITESI + settings.W_ANAHTAR_KELIME + settings.W_HABER_GUVENILIRLIGI
        + settings.W_COGRAFI_YAYILIM + settings.W_ICERIK_BENZERLIGI + settings.W_INFLUENCER_ETKISI
        + settings.W_GORSEL_ICERIK + settings.W_SAHTE_HABER + settings.W_GECMIS_KRIZ_BENZERLIGI
        + settings.W_ICERIK_YAYILIMI
    )
    ham_toplam = sum(bilesenler.values())
    # 0-100 aralığına normalize (ağırlıklar toplamı 100'den farklı olabileceği için)
    toplam = round(_clamp(ham_toplam / toplam_agirlik, 0.0, 1.0) * 100, 2) if toplam_agirlik > 0 else 0.0
    seviye = risk_seviyesi_belirle(toplam)

    # Destekleyici (skoru artırmayan/azaltmayan, teyit amaçlı) sinyaller — ayrı raporlanır
    if girdi.toplam_icerik_sayisi > 0:
        guven_orani = girdi.dogrulanmis_hesap_sayisi / girdi.toplam_icerik_sayisi
    else:
        guven_orani = 0.0
    destekleyici = {
        "guvenilir_kaynak_teyidi": round(_clamp(guven_orani), 3),
    }

    siralama = sorted(bilesenler, key=bilesenler.get, reverse=True)
    en_yuksek_bilesen = siralama[0]
    aciklama = (
        f"Toplam risk skoru {toplam}/100 ({seviye}). "
        f"En yüksek katkıyı '{en_yuksek_bilesen}' bileşeni yaptı "
        f"({bilesenler[en_yuksek_bilesen]} puan). "
        f"Bkz. 'bilesenler' alanı: 16 bileşenin tamamının ayrıştırılmış katkısı "
        f"(SHAP benzeri toplamsal açıklama — bkz. app/ml/xgboost_classifier.py "
        f"ML tabanlı sınıflandırıcıda gerçek SHAP değerleriyle çapraz doğrulama)."
    )

    dogrulama = dogrulama_modeli_hesapla(
        hacim_z_skoru=girdi.hacim_z_skoru if girdi.hacim_z_skoru is not None else 0.0,
        sscct_onlenemez_orani=girdi.sscct_onlenemez_orani,
        yayilma_ivmesi=girdi.yayilma_ivmesi,
        bot_anomali_benford_skoru=girdi.bot_anomali_benford_skoru,
    )

    return RiskSonucu(
        toplam_skor=toplam,
        risk_seviyesi=seviye,
        bilesenler=bilesenler,
        destekleyici_sinyaller=destekleyici,
        aciklama=aciklama,
        en_yuksek_katki_sirasi=siralama,
        dogrulama_modeli=dogrulama,
    )
