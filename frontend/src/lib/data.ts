/**
 * Faz 8 GÜNCELLEMESİ: Bu dosya önceden istemci-taraflı SİMÜLASYON verisi VE
 * mantığı içeriyordu (ICERIK_HAVUZU, DEMO_KRIZLER, krizRiskiHesapla,
 * siniflandir/SCCT_KUMELER, taslakMetniUret/raporMetniOlustur — tümü backend'in
 * gerçek karşılıklarını (risk_scoring.py, itibar_skoru.py, llm_advisor.py,
 * pr_rapor.py) yerel olarak taklit ediyordu). Bunların TÜMÜ kaldırıldı;
 * ilgili veriler artık YALNIZCA backend'den gelir (bkz. lib/api.ts).
 *
 * Bu dosyada geriye yalnızca SAF GÖRÜNTÜLEME yardımcıları (renk/etiket
 * eşlemeleri, terimler sözlüğü, pano formatlama) kalmıştır — hiçbiri skor
 * HESAPLAMAZ, yalnızca backend'den gelen sayısal bir değeri bir renge/etikete
 * çevirir.
 */

export const TERIMLER = {
  itibarSkoru: {
    baslik: "İtibar Skoru",
    aciklama:
      "0-100 arası; Fombrun'un RepTrak/Reputation Quotient kuramı, Hovland & Weiss kaynak güvenilirliği ve Ebbinghaus üstel zaman aşınımına dayanan ağırlıklı-ortalama formülüyle backend'de hesaplanır (bkz. app/services/itibar_skoru.py). Yüksek = iyi.",
  },
  krizRiski: {
    baslik: "Kriz Riski Skoru",
    aciklama:
      "0-100 arası; 16 bileşenli açıklanabilir risk motorunun (Coombs SCCT, EWMA anomali tespiti, Benford Kanunu bot testi) ürettiği skordur (bkz. app/services/risk_scoring.py). Aktif krizler arasındaki en yüksek backend risk skorudur. Yüksek = tehlikeli.",
  },
  duyguKutbu: {
    baslik: "Duygu Kutbu",
    aciklama: "İçeriğin pozitif / negatif / nötr olarak sınıflandırılması (NLP literatüründe 'sentiment polarity'); backend'de BERTurk tabanlı transformer modeli veya sözlük-tabanlı model ile hesaplanır (bkz. app/services/sentiment.py).",
  },
  ortukAnlam: {
    baslik: "Örtük Anlam (İroni / Dolaylı Eleştiri)",
    aciklama: "Yüzeysel ifade olumlu görünse de asıl niyetin alaycı/eleştirel olduğu durumlar (NLP'de 'irony/sarcasm detection').",
  },
  krizSiddeti: {
    baslik: "Kriz Risk Skoru",
    aciklama: "0-100 arası; backend'in 16-bileşenli açıklanabilir risk motorunun ürettiği toplam skor (bkz. Kriz Detayı'ndaki bileşen dökümü).",
  },
  krizKumesi: {
    baslik: "Kriz Duruşu (SCCT)",
    aciklama: "Coombs'un (2007) Durumsal Kriz İletişimi Teorisi'ne (SCCT) göre krizin kurumun sorumluluk derecesine göre hangi duruşa (İnkâr, Küçültme, Yeniden İnşa, Destekleme, Çerçeveleme, Proaktif) oturtulduğu — backend'in 18 taktikli motoru tarafından belirlenir (bkz. app/services/llm_advisor.py).",
  },
  krizStratejisi: {
    baslik: "Kriz Karşılama Stratejisi",
    aciklama: "18 akademik taktikten (Coombs SCCT + Benoit İmaj Onarım Teorisi + Hearit Apologia + çağdaş proaktif stratejiler) backend tarafından seçilen, krize özel spesifik iletişim taktiği.",
  },
  adaptifTarama: {
    baslik: "Adaptif Tarama",
    aciklama: "Kriz şiddeti yükseldikçe verinin taranma sıklığının otomatik olarak artması. Backend'de EWMA hacim-anomali Z-skoruna ters orantılı matematiksel bir politika olarak gerekçelendirilmiştir (bkz. app/services/tarama_araligi.py).",
  },
  cokDilliAnaliz: {
    baslik: "Çok Dilli Analiz",
    aciklama: "İçeriğin dili önce otomatik tespit edilir (bkz. app/services/dil_tespit.py); Türkçe içerik BERTurk/Türkçe sözlük, diğer diller ise XLM-RoBERTa tabanlı çok dilli bir model (veya dile özgü sözlük) ile analiz edilir (bkz. app/services/sentiment.py). Böylece YouTube/Reddit gibi kaynaklardan gelen yabancı dildeki yorumlar da kriz sinyaline dahil edilir.",
  },
};

/** Faz 10: ISO 639-1 dil kodundan bayrak emojisi + kısa etiket (yalnızca
 * GÖRÜNTÜLEME amaçlı, backend'in ürettiği `dil` alanını değiştirmez). */
export const DIL_ETIKETLERI: Record<string, string> = {
  tr: "🇹🇷 Türkçe", en: "🇬🇧 İngilizce", de: "🇩🇪 Almanca", fr: "🇫🇷 Fransızca",
  es: "🇪🇸 İspanyolca", ar: "🇸🇦 Arapça", ru: "🇷🇺 Rusça", it: "🇮🇹 İtalyanca",
  pt: "🇵🇹 Portekizce", nl: "🇳🇱 Flemenkçe", az: "🇦🇿 Azerbaycanca",
};

export function dilEtiketi(kod: string): string {
  return DIL_ETIKETLERI[kod] ?? kod.toUpperCase();
}

/** Backend'in risk_seviyesi metnini (Düşük/Orta/Yüksek/Kritik Risk) renge çevirir. */
export function riskSeviyesiRenk(seviye: string | undefined) {
  if (seviye === "Kritik Risk") return "#dc2626";
  if (seviye === "Yüksek Risk") return "#ea580c";
  if (seviye === "Orta Risk") return "#d97706";
  return "#059669";
}

export function riskSeviyesiRozetSinifi(seviye: string | undefined) {
  if (seviye === "Kritik Risk") return "bg-red-100 text-red-700 border-red-200";
  if (seviye === "Yüksek Risk") return "bg-orange-100 text-orange-700 border-orange-200";
  if (seviye === "Orta Risk") return "bg-amber-100 text-amber-700 border-amber-200";
  return "bg-emerald-100 text-emerald-700 border-emerald-200";
}

export function duyguRenk(duygu: string) {
  if (duygu === "negatif") return "text-red-600";
  if (duygu === "pozitif") return "text-emerald-600";
  return "text-slate-500";
}

/** siddet: backend'in 0-100 ölçekli risk skoru (Kriz.siddet). */
export function siddetRenk(siddet: number) {
  if (siddet >= 75) return "#dc2626";
  if (siddet >= 50) return "#d97706";
  return "#059669";
}

export function itibarRenk(skor: number) {
  if (skor >= 70) return "#10b981";
  if (skor >= 50) return "#f59e0b";
  return "#ef4444";
}

export function riskRenk(skor: number) {
  if (skor >= 70) return "#dc2626";
  if (skor >= 40) return "#d97706";
  return "#10b981";
}

export function riskEtiket(skor: number) {
  if (skor >= 70) return "Yüksek";
  if (skor >= 40) return "Orta";
  return "Düşük";
}

export function fmtDakika(saniye: number) {
  const dk = Math.floor(saniye / 60);
  const sn = Math.floor(saniye % 60);
  return `${String(dk).padStart(2, "0")}:${String(sn).padStart(2, "0")}`;
}

/**
 * UI GÖRÜNTÜLEME yardımcısı: "sıradaki tarama" geri sayımının ekranda
 * gösterdiği süre. Bu, backend'deki GERÇEK, literatüre dayalı adaptif tarama
 * motorunun (EWMA Z-skoruna ters orantılı, bkz. app/services/tarama_araligi.py)
 * basitleştirilmiş bir istemci-taraflı YANSIMASIDIR — kesin zamanlama Celery
 * Beat/worker tarafında (Docker ile) veya bu ekrandaki "Şimdi Tara" butonuyla
 * yapılır; buradaki değer yalnızca kullanıcıya bir sonraki otomatik taramanın
 * YAKLAŞIK ne zaman tetikleneceğini göstermek içindir, herhangi bir risk/itibar
 * skoru ÜRETMEZ.
 */
export function adaptifAralikHesapla(baseDakika: number, maxSiddet: number, adaptifAcik: boolean) {
  if (!adaptifAcik) return baseDakika;
  if (maxSiddet >= 8) return 5;
  if (maxSiddet >= 6) return 10;
  if (maxSiddet >= 4) return 15;
  return baseDakika;
}

export async function metniKopyala(text: string) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    throw new Error("clipboard API yok");
  } catch (e) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e2) {
      return false;
    }
  }
}

/** Login sayfasındaki "Hızlı Giriş" butonları için — parolalar burada TUTULMAZ
 * (backend/app/main.py::_demo_hesaplari_tohumla ile geliştirme ortamında
 * gerçek bcrypt-hash'li hesaplar olarak oluşturulur); burada yalnızca
 * görüntüleme amaçlı kurum adı/e-posta listesi bulunur. Gerçek kimlik
 * doğrulama her zaman backend /api/auth/giris üzerinden yapılır. */
export const DEMO_HESAPLAR_GORUNUM = [
  { email: "demo@sirket.com.tr", sifre: "Demo1234", kurum: "Anadolu Gıda A.Ş.", sektor: "Gıda & İçecek" },
  { email: "iletisim@belediye.gov.tr", sifre: "Demo1234", kurum: "Örnek İlçe Belediyesi", sektor: "Kamu & Yerel Yönetim" },
  { email: "bilgi@siviltoplum.org.tr", sifre: "Demo1234", kurum: "Umut Derneği", sektor: "Sivil Toplum" },
];
