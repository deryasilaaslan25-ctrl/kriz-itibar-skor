export type Duygu = "negatif" | "pozitif" | "nötr";
export type KrizDurumu = "Aktif" | "İzleniyor" | "Kapandı";
export type GeriBildirim = "gercek" | "siradan" | null;

export type Kullanici = {
  email: string;
  kurum: string;
  sektor: string;
  rol?: string;
  bildirimTercihleri: Record<string, boolean>;
};

export type Icerik = {
  id: number;
  platform: string;
  baslik: string;
  icerik: string;
  duygu: Duygu;
  puan: number;
  konu: string;
  ortukAnlam: boolean;
  tarih: string;
  yorumSayisi: number;
  /** Faz 4/8: bu duygu skorunu üreten somut kelime/kalıp kanıtları (backend sentiment.py). */
  aciklamaKanitlari: string[];
  /** Faz 10: tespit edilen ISO 639-1 dil kodu (tr, en, de, ...) — bkz. backend app/services/dil_tespit.py. */
  dil: string;
};

export type RiskDetay = {
  toplam_skor: number;
  risk_seviyesi: string;
  bilesenler: Record<string, number>;
  aciklama: string;
};

export type Kriz = {
  id: number;
  baslik: string;
  aciklama: string;
  siddet: number;
  platform: string[];
  tarih: string;
  konu: string;
  durum: KrizDurumu;
  icerikSayisi: number;
  feedback: GeriBildirim;
  /** Faz 8: backend'in 16-bileşenli açıklanabilir risk motoru çıktısı (bkz. risk_scoring.py). */
  riskDetay: RiskDetay | null;
  anomaliTespitEdildi: boolean;
  tahmini24s: number | null;
  tahmini72s: number | null;
  tahmini7g: number | null;
};

export type HaftalikVeri = { gun: string; itibar: number; hacim: number };

export type DenetimKaydi = {
  id: string;
  zaman: string;
  tur: "tarama" | "alarm" | "geri_bildirim" | "ayar";
  mesaj: string;
  krizId?: number;
};

export type Ayarlar = {
  esik: number;
  taramaAraligi: number;
  adaptifTarama: boolean;
  emailBildirim: boolean;
};

/** Faz 1: backend itibar_skoru.py çıktısı. */
export type ItibarKatki = {
  kaynak_id: string | null;
  ozet: string | null;
  isaretli_skor: number;
  agirlik: number;
  zaman_asinimi_carpani: number;
  agirlikli_katki_orani: number;
};

export type ItibarSonucu = {
  skor: number;
  icerik_sayisi: number;
  net_agirlikli_duygu: number;
  yarilanma_omru_saat: number;
  alpha: number;
  katkilar: ItibarKatki[];
  aciklama: string;
};

/** Faz 5: backend llm_advisor.py 18-taktikli SCCT/IRT/Apologia motoru çıktısı. */
export type SpesifikTaktikDetay = {
  kod: string;
  ad: string;
  durus: string;
  akademik_kaynak: string;
  aciklama: string;
};

export type KrizOnerisi = {
  strateji: string;
  sorumluluk_seviyesi: string;
  ilk_mudahale_suresi_saat: number;
  gerekce: string;
  somut_adimlar: string[];
  llm_destekli: boolean;
  llm_metni: string | null;
  spesifik_strateji: SpesifikTaktikDetay | null;
  alternatif_stratejiler: SpesifikTaktikDetay[];
  metodoloji_notu: string;
  toplam_taktik_sayisi: number;
};

export type GecmisKrizOrnegi = {
  donem: string;
  sektor: string;
  ozet: string;
  kurumun_tutumu: string;
  sonuc: string;
  basari_durumu: "olumlu_yonetildi" | "olumsuz_yonetildi" | "karisik";
  tavsiye: string;
};

export type GecmisKrizAnaliziCikti = {
  kriz_id: number;
  taranan_yil_araligi: string;
  ornekler: GecmisKrizOrnegi[];
  genel_tavsiye: string;
  llm_destekli: boolean;
};

/** Faz 5: backend pr_rapor.py — Kurumsal Kriz Müdahale Raporu (PDF ile aynı içerik, JSON). */
export type CrisisPRActionReport = {
  kurum_adi: string;
  kriz_baslik: string;
  kriz_konusu: string;
  risk_skoru: number;
  risk_seviyesi: string;
  olusturma_tarihi: string;
  teorik_teshis: string;
  spesifik_strateji_adi: string;
  spesifik_strateji_kaynak: string;
  spesifik_strateji_aciklama: string;
  alternatif_stratejiler: string[];
  operasyonel_plan: { zaman_araligi: string; baslik: string; adimlar: string[] }[];
  kanal_taslaklari: { kanal: string; ton: string; metin: string }[];
  paydas_haritasi: { paydas: string; taktik: string }[];
  metodoloji_notu: string;
  llm_destekli_metin: string | null;
};

/** Faz 6/7: backend tarama_pipeline.py uçtan uca tarama sonucu. */
export type TaramaSonucu = {
  durum: string;
  toplanan_icerik_sayisi?: number;
  kaynaklar?: { platform: string; aktif: boolean; toplanan: number }[];
  risk_skoru?: number;
  risk_seviyesi?: string;
  itibar_skoru?: number;
  kriz_id?: number | null;
  kriz_olusturuldu_mu?: boolean;
};
