/**
 * Backend API çağrı fonksiyonları (Faz 8) — @tanstack/react-query hook'ları
 * (bkz. app-context.tsx) bu fonksiyonları sarmalar. Tipler backend Pydantic
 * şemalarıyla (app/schemas/schemas.py) birebir eşleşecek şekilde tanımlanmıştır.
 */
import { api, API_BASE_URL, tokenOku } from "./api-client";
import type {
  Ayarlar, DenetimKaydi, Icerik, ItibarSonucu, Kriz, Kullanici,
  KrizOnerisi, GecmisKrizAnaliziCikti, TaramaSonucu, CrisisPRActionReport,
} from "./domain";

// ---- Kimlik Doğrulama ----------------------------------------------------
export async function girisYapApi(email: string, sifre: string): Promise<string> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", sifre);
  const { data } = await api.post("/api/auth/giris", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data.access_token as string;
}

export async function kayitOlApi(email: string, sifre: string, sifreTekrar: string, kurum: string, sektor: string): Promise<string> {
  const { data } = await api.post("/api/auth/kayit", {
    email, sifre, sifre_tekrar: sifreTekrar, kurum, sektor: sektor || undefined,
  });
  return data.access_token as string;
}

export async function benGetirApi(): Promise<Kullanici> {
  const { data } = await api.get("/api/auth/ben");
  return {
    email: data.email, kurum: data.kurum ?? "", sektor: data.sektor ?? "",
    rol: data.rol, bildirimTercihleri: data.bildirim_tercihleri ?? {},
  };
}

export async function sifreDegistirApi(mevcutSifre: string, yeniSifre: string, yeniSifreTekrar: string): Promise<void> {
  await api.put("/api/auth/sifre-degistir", {
    mevcut_sifre: mevcutSifre, yeni_sifre: yeniSifre, yeni_sifre_tekrar: yeniSifreTekrar,
  });
}

export async function emailDegistirApi(yeniEmail: string, mevcutSifre: string): Promise<string> {
  const { data } = await api.put("/api/auth/email-degistir", { yeni_email: yeniEmail, mevcut_sifre: mevcutSifre });
  return data.access_token as string;
}

// ---- Krizler --------------------------------------------------------------
function krizDonustur(k: any): Kriz {
  return {
    id: k.id, baslik: k.baslik, aciklama: k.aciklama ?? "", siddet: k.siddet,
    platform: k.platform ?? [], tarih: k.tarih, konu: k.konu ?? "Genel", durum: k.durum,
    icerikSayisi: k.icerik_sayisi, feedback: k.feedback, riskDetay: k.risk_detay ?? null,
    anomaliTespitEdildi: k.anomali_tespit_edildi,
    tahmini24s: k.tahmini_24s_risk, tahmini72s: k.tahmini_72s_risk, tahmini7g: k.tahmini_7g_risk,
  };
}

export async function krizleriListeleApi(): Promise<Kriz[]> {
  const { data } = await api.get("/api/krizler");
  return data.map(krizDonustur);
}

export async function krizOnerisiGetirApi(krizId: number, sorumlulukSeviyesi = "orta"): Promise<KrizOnerisi> {
  const { data } = await api.post(`/api/krizler/${krizId}/oneri`, null, { params: { sorumluluk_seviyesi: sorumlulukSeviyesi } });
  return data;
}

export async function gecmisKrizAnaliziApi(krizId: number): Promise<GecmisKrizAnaliziCikti> {
  const { data } = await api.post(`/api/krizler/${krizId}/gecmis-analiz`);
  return data;
}

export async function raporJsonApi(krizId: number, sorumlulukSeviyesi = "orta"): Promise<CrisisPRActionReport> {
  const { data } = await api.get(`/api/krizler/${krizId}/rapor-json`, { params: { sorumluluk_seviyesi: sorumlulukSeviyesi } });
  return data;
}

export async function taraSimdiApi(anahtarKelime?: string): Promise<TaramaSonucu> {
  const { data } = await api.post("/api/krizler/tara-simdi", null, { params: anahtarKelime ? { anahtar_kelime: anahtarKelime } : {} });
  return data;
}

export async function geriBildirimKaydetApi(krizId: number, deger: "gercek" | "siradan"): Promise<Kriz> {
  const { data } = await api.put(`/api/krizler/${krizId}/geri-bildirim`, null, { params: { deger } });
  return krizDonustur(data);
}

export async function bildirimTercihiKaydetApi(konu: string, bildirimIstiyor: boolean): Promise<void> {
  await api.put("/api/krizler/bildirim-tercihi", { konu, bildirim_istiyor: bildirimIstiyor });
}

/** Rapor PDF'ini indirir (backend'den binary stream) ve tarayıcıda indirme diyaloğunu tetikler. */
export async function raporIndirApi(krizId: number, dosyaAdi: string): Promise<void> {
  const token = tokenOku();
  const yanit = await fetch(`${API_BASE_URL}/api/krizler/${krizId}/rapor-indir`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!yanit.ok) throw new Error(`Rapor indirilemedi (HTTP ${yanit.status})`);
  const blob = await yanit.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = dosyaAdi;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---- İtibar -----------------------------------------------------------------
export async function itibarHesaplaApi(): Promise<ItibarSonucu> {
  const { data } = await api.get("/api/itibar/hesapla");
  return data;
}

// ---- İçerikler --------------------------------------------------------------
function icerikDonustur(i: any): Icerik {
  return {
    id: i.id, platform: i.platform, baslik: i.baslik, icerik: i.icerik, duygu: i.duygu,
    puan: i.puan, konu: i.konu ?? "Genel", ortukAnlam: i.ortuk_anlam, tarih: i.tarih,
    yorumSayisi: i.yorum_sayisi, aciklamaKanitlari: i.aciklama_kanitlari ?? [],
    dil: i.dil ?? "tr",
  };
}

export async function icerikleriListeleApi(limit = 100): Promise<Icerik[]> {
  const { data } = await api.get("/api/icerikler", { params: { limit } });
  return data.map(icerikDonustur);
}

export async function icerikAraApi(sorgu: string): Promise<Icerik[]> {
  const { data } = await api.get("/api/icerikler/ara", { params: { q: sorgu } });
  return data.map(icerikDonustur);
}

// ---- Ayarlar / Denetim -------------------------------------------------------
function ayarlarDonustur(a: any): Ayarlar {
  return { esik: a.esik, taramaAraligi: a.tarama_araligi, adaptifTarama: a.adaptif_tarama, emailBildirim: a.email_bildirim };
}

export async function ayarlariGetirApi(): Promise<Ayarlar> {
  const { data } = await api.get("/api/ayarlar");
  return ayarlarDonustur(data);
}

export async function ayarlariKaydetApi(ayarlar: Ayarlar): Promise<Ayarlar> {
  const { data } = await api.put("/api/ayarlar", null, {
    params: {
      esik: ayarlar.esik, tarama_araligi: ayarlar.taramaAraligi,
      adaptif_tarama: ayarlar.adaptifTarama, email_bildirim: ayarlar.emailBildirim,
    },
  });
  return ayarlarDonustur(data);
}

export async function denetimListeleApi(): Promise<DenetimKaydi[]> {
  const { data } = await api.get("/api/denetim");
  return data.map((d: any) => ({ id: d.id, zaman: d.zaman, tur: d.tur, mesaj: d.mesaj, krizId: d.kriz_id ?? undefined }));
}

// ---- Veri Kaynağı Durumu ------------------------------------------------
export type KaynakDurum = { platform: string; aktif: boolean };

export async function kaynaklarDurumApi(): Promise<KaynakDurum[]> {
  const { data } = await api.get("/api/kaynaklar/durum");
  return data;
}
