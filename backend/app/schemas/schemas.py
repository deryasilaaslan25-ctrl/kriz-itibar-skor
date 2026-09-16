"""API giriş/çıkış şemaları (Pydantic v2)."""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict

Duygu = Literal["negatif", "pozitif", "nötr"]
KrizDurumu = Literal["Aktif", "İzleniyor", "Kapandı"]
GeriBildirim = Optional[Literal["gercek", "siradan"]]


class IcerikAnalizIstek(BaseModel):
    """Ham metin gönderip analiz sonucu almak için (NLP pipeline giriş noktası)."""
    platform: str
    baslik: str
    icerik: str
    hesap_id: Optional[str] = None
    yorum_sayisi: int = 0


class IcerikCikti(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    baslik: str
    icerik: str
    duygu: Duygu
    duygu_alt_tip: Optional[str] = None
    puan: float
    konu: Optional[str] = None
    ortuk_anlam: bool
    tarih: datetime
    yorum_sayisi: int
    bot_skoru: float
    kaynak_guven_puani: float
    sahte_haber_riski: float
    aciklama_kanitlari: list[str] = []
    # Faz 10 (çok dilli analiz): tespit edilen ISO 639-1 dil kodu (bkz. app/services/dil_tespit.py)
    dil: Optional[str] = "tr"


class RiskSkoruDetay(BaseModel):
    """Bölüm 8: Açıklanabilir risk skoru — jürinin en çok sorgulayacağı çıktı."""
    toplam_skor: float
    risk_seviyesi: Literal["Düşük Risk", "Orta Risk", "Yüksek Risk", "Kritik Risk"]
    bilesenler: dict[str, float]
    aciklama: str


class KrizCikti(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    baslik: str
    aciklama: Optional[str] = None
    siddet: float
    platform: list[str]
    tarih: datetime
    konu: Optional[str] = None
    durum: KrizDurumu
    icerik_sayisi: int
    feedback: GeriBildirim
    risk_detay: Optional[RiskSkoruDetay] = None
    anomali_tespit_edildi: bool
    tahmini_24s_risk: Optional[float] = None
    tahmini_72s_risk: Optional[float] = None
    tahmini_7g_risk: Optional[float] = None


class TahminIstek(BaseModel):
    kriz_id: int
    ufuk: Literal["24s", "72s", "7g"] = "24s"


class KayitIstek(BaseModel):
    """Kurum hesabı oluşturma (Bölüm 20: kayıt ol -> e-posta + şifre + şifre tekrar + kurum adı)."""
    email: str
    sifre: str
    sifre_tekrar: str
    kurum: str
    sektor: Optional[str] = None


class SifreDegistirIstek(BaseModel):
    mevcut_sifre: str
    yeni_sifre: str
    yeni_sifre_tekrar: str


class EmailDegistirIstek(BaseModel):
    yeni_email: str
    mevcut_sifre: str


class BildirimTercihiIstek(BaseModel):
    """Bir konu/kriz türü için bildirim tercihini kaydeder (öğrenen bildirim sistemi)."""
    konu: str
    bildirim_istiyor: bool


class GecmisKrizOrnegi(BaseModel):
    """Geçmiş Kriz Analizi motorunun (LLMOneriMotoru altındaki yapay zeka itibar
    danışmanı) ürettiği tek bir tarihsel emsal olay kaydı."""
    donem: str  # "2019" veya "Eylül 2019 civarında" gibi yaklaşık/kesin tarih
    sektor: str
    ozet: str
    kurumun_tutumu: str
    sonuc: str
    basari_durumu: Literal["olumlu_yonetildi", "olumsuz_yonetildi", "karisik"]
    tavsiye: str


class GecmisKrizAnaliziCikti(BaseModel):
    kriz_id: int
    taranan_yil_araligi: str
    ornekler: list[GecmisKrizOrnegi]
    genel_tavsiye: str
    llm_destekli: bool


class ItibarKatkiCikti(BaseModel):
    """Bir içeriğin itibar skoruna yaptığı ağırlıklı katkı (SHAP-benzeri açıklama)."""
    kaynak_id: Optional[str] = None
    ozet: Optional[str] = None
    isaretli_skor: float          # sᵢ ∈ [-1, 1]
    agirlik: float                  # wᵢ (zaman aşınımı UYGULANMADAN önce)
    zaman_asinimi_carpani: float    # e^(−λΔt) ∈ (0, 1]
    agirlikli_katki_orani: float    # bu içeriğin toplam ağırlıklı paya oranı


class ItibarSonucuCikti(BaseModel):
    """Bkz. app/services/itibar_skoru.py — Fombrun/Hovland-Weiss/Ebbinghaus
    tabanlı tanh-EWMA itibar skoru modelinin API çıktısı."""
    skor: float
    icerik_sayisi: int
    net_agirlikli_duygu: float
    yarilanma_omru_saat: float
    alpha: float
    katkilar: list[ItibarKatkiCikti]
    aciklama: str


class OperasyonelPlanAdimiCikti(BaseModel):
    zaman_araligi: str
    baslik: str
    adimlar: list[str]


class KanalTaslagiCikti(BaseModel):
    kanal: str
    ton: str
    metin: str


class PaydasTaktigiCikti(BaseModel):
    paydas: str
    taktik: str


class CrisisPRActionReportCikti(BaseModel):
    """Bkz. app/services/pr_rapor.py — PDF ile AYNI içeriğin JSON hâli
    (frontend PR Danışmanı sayfasında ekranda göstermek için)."""
    kurum_adi: str
    kriz_baslik: str
    kriz_konusu: str
    risk_skoru: float
    risk_seviyesi: str
    olusturma_tarihi: str
    teorik_teshis: str
    spesifik_strateji_adi: str
    spesifik_strateji_kaynak: str
    spesifik_strateji_aciklama: str
    alternatif_stratejiler: list[str]
    operasyonel_plan: list[OperasyonelPlanAdimiCikti]
    kanal_taslaklari: list[KanalTaslagiCikti]
    paydas_haritasi: list[PaydasTaktigiCikti]
    metodoloji_notu: str
    llm_destekli_metin: Optional[str] = None


class BotTespitIstek(BaseModel):
    hesap_id: str
    hesap_yasi_gun: int
    son_24s_paylasim_sayisi: int
    tekrarlayan_icerik_orani: float  # 0-1
    hashtag_yogunlugu: float          # ortalama hashtag/gönderi
