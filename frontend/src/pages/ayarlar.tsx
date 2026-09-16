import React, { useEffect, useState } from "react";
import { useAppContext } from "@/lib/app-context";
import { InfoIcon } from "@/components/info-icon";
import { siddetRenk } from "@/lib/data";
import { kaynaklarDurumApi, type KaynakDurum } from "@/lib/api";
import { toast } from "sonner";
import { Save, Bell, Zap, SlidersHorizontal, Check, X, KeyRound, Mail, ShieldCheck } from "lucide-react";

export default function Ayarlar() {
  const {
    kullanici,
    esik,
    setEsik,
    taramaAraligi,
    setTaramaAraligi,
    adaptifTarama,
    setAdaptifTarama,
    emailBildirim,
    setEmailBildirim,
    ayarlariKaydet,
    sifreDegistir,
    emailGuncelle,
  } = useAppContext();

  const [mevcutSifre, setMevcutSifre] = useState("");
  const [yeniSifre, setYeniSifre] = useState("");
  const [yeniSifreTekrar, setYeniSifreTekrar] = useState("");
  const [sifreYukleniyor, setSifreYukleniyor] = useState(false);

  const [yeniEmail, setYeniEmail] = useState("");
  const [emailSifre, setEmailSifre] = useState("");
  const [emailYukleniyor, setEmailYukleniyor] = useState(false);

  const [kaynaklar, setKaynaklar] = useState<KaynakDurum[]>([]);
  useEffect(() => {
    kaynaklarDurumApi().then(setKaynaklar).catch(() => setKaynaklar([]));
  }, []);

  async function kaydet() {
    const basarili = await ayarlariKaydet();
    if (basarili) toast.success("Ayarlar backend'e kaydedildi.");
    else toast.error("Ayarlar kaydedilemedi. Backend'e ulaşılamıyor olabilir.");
  }

  async function sifreDegistirTiklandi(e: React.FormEvent) {
    e.preventDefault();
    setSifreYukleniyor(true);
    const sonuc = await sifreDegistir(mevcutSifre, yeniSifre, yeniSifreTekrar);
    setSifreYukleniyor(false);
    if (sonuc.basarili) {
      toast.success("Şifreniz başarıyla güncellendi.");
      setMevcutSifre(""); setYeniSifre(""); setYeniSifreTekrar("");
    } else {
      toast.error(sonuc.hata || "Şifre güncellenemedi.");
    }
  }

  async function emailDegistirTiklandi(e: React.FormEvent) {
    e.preventDefault();
    setEmailYukleniyor(true);
    const sonuc = await emailGuncelle(yeniEmail, emailSifre);
    setEmailYukleniyor(false);
    if (sonuc.basarili) {
      toast.success("E-posta adresiniz başarıyla güncellendi.");
      setYeniEmail(""); setEmailSifre("");
    } else {
      toast.error(sonuc.hata || "E-posta güncellenemedi.");
    }
  }

  if (!kullanici) return null;

  return (
    <div className="space-y-6 max-w-3xl mx-auto animate-in fade-in duration-500 pb-12">
      <header>
        <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-signal mb-1.5">
          <span className="pulse-dot relative inline-block w-1.5 h-1.5 rounded-full bg-signal" />
          <span className="ml-1">Yapılandırma</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground font-display">Sistem Ayarları</h1>
        <p className="text-sm text-muted-foreground mt-1">Erken uyarı parametreleri ve bildirim tercihleri yapılandırması</p>
      </header>

      <div className="surface-card overflow-hidden">
        <div className="p-4 bg-muted/50 border-b border-border">
          <h3 className="text-sm font-bold text-foreground/90 uppercase tracking-wider flex items-center">
            Kurum Profili
          </h3>
        </div>
        <div className="p-0">
          {[
            ["Kurum Adı", kullanici.kurum], 
            ["Kurumsal E-posta", kullanici.email], 
            ["Sektör", kullanici.sektor]
          ].map(([label, val], idx, arr) => (
            <div key={label} className={`flex flex-col sm:flex-row sm:items-center justify-between p-4 ${idx !== arr.length - 1 ? 'border-b border-border/70' : ''}`}>
              <span className="text-sm font-semibold text-muted-foreground mb-1 sm:mb-0">{label}</span>
              <span className="text-sm font-bold text-foreground">{val}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="surface-card overflow-hidden">
        <div className="p-4 bg-muted/50 border-b border-border">
          <h3 className="text-sm font-bold text-foreground/90 uppercase tracking-wider flex items-center">
            <ShieldCheck className="w-4 h-4 mr-2 text-muted-foreground" />
            Hesap Güvenliği
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Şifrenizi veya kurumsal e-posta adresinizi değiştirmek için mevcut şifrenizi doğrulamanız gerekir.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border/70">
          <form onSubmit={sifreDegistirTiklandi} className="p-6 space-y-3">
            <p className="text-xs font-bold text-foreground/80 uppercase tracking-wide flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5" /> Şifre Değiştir
            </p>
            <input
              type="password"
              value={mevcutSifre}
              onChange={(e) => setMevcutSifre(e.target.value)}
              placeholder="Mevcut şifreniz"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/25 focus:border-signal text-sm"
              required
            />
            <input
              type="password"
              value={yeniSifre}
              onChange={(e) => setYeniSifre(e.target.value)}
              placeholder="Yeni şifre (en az 8 karakter)"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/25 focus:border-signal text-sm"
              required
            />
            <input
              type="password"
              value={yeniSifreTekrar}
              onChange={(e) => setYeniSifreTekrar(e.target.value)}
              placeholder="Yeni şifre (tekrar)"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/25 focus:border-signal text-sm"
              required
            />
            <button
              type="submit"
              disabled={sifreYukleniyor}
              className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all shadow-sm hover:shadow-md disabled:opacity-60"
            >
              {sifreYukleniyor ? "Güncelleniyor…" : "Şifreyi Güncelle"}
            </button>
          </form>

          <form onSubmit={emailDegistirTiklandi} className="p-6 space-y-3">
            <p className="text-xs font-bold text-foreground/80 uppercase tracking-wide flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5" /> E-posta Değiştir
            </p>
            <input
              type="email"
              value={yeniEmail}
              onChange={(e) => setYeniEmail(e.target.value)}
              placeholder="Yeni kurumsal e-posta"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/25 focus:border-signal text-sm"
              required
            />
            <input
              type="password"
              value={emailSifre}
              onChange={(e) => setEmailSifre(e.target.value)}
              placeholder="Mevcut şifreniz (doğrulama için)"
              className="w-full px-3 py-2 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/25 focus:border-signal text-sm"
              required
            />
            <div className="pt-[42px]" />
            <button
              type="submit"
              disabled={emailYukleniyor}
              className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all shadow-sm hover:shadow-md disabled:opacity-60"
            >
              {emailYukleniyor ? "Güncelleniyor…" : "E-postayı Güncelle"}
            </button>
          </form>
        </div>
      </div>

      <div className="surface-card overflow-hidden">
        <div className="p-4 bg-muted/50 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-bold text-foreground/90 uppercase tracking-wider flex items-center">
            <SlidersHorizontal className="w-4 h-4 mr-2 text-muted-foreground" />
            Kriz Şiddet Eşik Değeri<InfoIcon term="krizSiddeti" />
          </h3>
        </div>
        <div className="p-6">
          <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
            Sistemin ne zaman "Kriz" alarmı vereceğini belirler. Bu değerin üzerindeki skorlarda otomatik rapor oluşturulur ve e-posta bildirimi tetiklenir.
          </p>
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <input 
                type="range" 
                min={1} 
                max={10} 
                step={0.5}
                value={esik} 
                onChange={(e) => setEsik(+e.target.value)} 
                className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-signal" 
              />
              <div className="flex justify-between text-[10px] font-bold text-muted-foreground/70 mt-2 uppercase tracking-wider">
                <span>Duyarlı (1.0)</span>
                <span>Standart (5.0)</span>
                <span>Yüksek Tolerans (10.0)</span>
              </div>
            </div>
            <div className="w-24 text-right shrink-0">
              <span className="text-3xl font-bold font-display leading-none" style={{ color: siddetRenk(esik) }}>
                {esik.toFixed(1)}
              </span>
              <span className="block text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider mt-1">Eşik Skor</span>
            </div>
          </div>
        </div>
      </div>

      <div className="surface-card overflow-hidden">
        <div className="p-4 bg-muted/50 border-b border-border">
          <h3 className="text-sm font-bold text-foreground/90 uppercase tracking-wider flex items-center">
            <Zap className="w-4 h-4 mr-2 text-muted-foreground" />
            Tarama & Bildirim Otomasyonu
          </h3>
        </div>
        <div className="p-0">
          <div className="p-6 border-b border-border/70 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center mb-1">
                <p className="text-sm font-bold text-foreground/90">Adaptif Tarama Modu</p>
                <InfoIcon term="adaptifTarama" />
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Açık olduğunda, kriz şiddeti yükseldikçe sistem tarama aralığını otomatik olarak daraltır (30dk → 15dk → 10dk → 5dk).
              </p>
            </div>
            <button 
              onClick={() => setAdaptifTarama(!adaptifTarama)} 
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-signal focus:ring-offset-2 ${adaptifTarama ? 'bg-signal' : 'bg-muted-foreground/30'}`}
              role="switch"
              aria-checked={adaptifTarama}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${adaptifTarama ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>

          <div className="p-6 border-b border-border/70">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-bold text-foreground/90">Temel Tarama Aralığı</p>
              <span className="text-sm font-bold text-foreground bg-muted px-3 py-1 rounded-md">{taramaAraligi} dk</span>
            </div>
            <input 
              type="range" 
              min={15} 
              max={120} 
              step={15} 
              value={taramaAraligi} 
              onChange={(e) => setTaramaAraligi(+e.target.value)} 
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-signal" 
            />
            <div className="flex justify-between text-[10px] font-bold text-muted-foreground/70 mt-2 uppercase tracking-wider">
              <span>Agresif (15dk)</span>
              <span>Seyrek (120dk)</span>
            </div>
          </div>

          <div className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm font-bold text-foreground/90 mb-1 flex items-center">
                <Bell className="w-3.5 h-3.5 mr-1.5" />
                E-posta Bildirimleri
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Kriz eşiği aşıldığında sistem tarafından hazırlanan otomatik karar destek raporu taslağı <strong>{kullanici.email}</strong> adresine gönderilir.
              </p>
            </div>
            <button 
              onClick={() => setEmailBildirim(!emailBildirim)} 
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-signal focus:ring-offset-2 ${emailBildirim ? 'bg-signal' : 'bg-muted-foreground/30'}`}
              role="switch"
              aria-checked={emailBildirim}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${emailBildirim ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="surface-card overflow-hidden">
        <div className="p-4 bg-muted/50 border-b border-border">
          <h3 className="text-sm font-bold text-foreground/90 uppercase tracking-wider">Veri Kaynakları (Backend'den Canlı Durum)</h3>
        </div>
        <div className="p-4 space-y-2">
          {kaynaklar.map((k) => (
            <div key={k.platform} className="flex items-center justify-between py-3 px-4 rounded-xl bg-muted/40 border border-border/70">
              <span className="text-sm font-bold text-foreground/90">{k.platform}</span>
              {k.aktif ? (
                <span className="inline-flex items-center px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-700 border border-emerald-200">
                  <Check className="w-3 h-3 mr-1" /> Aktif
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider bg-muted text-muted-foreground border border-border">
                  <X className="w-3 h-3 mr-1" /> Anahtar Bekliyor
                </span>
              )}
            </div>
          ))}
          <div className="mt-4 p-3 bg-signal/5 border border-signal/20 rounded-xl">
            <p className="text-[11px] text-foreground/70 font-medium leading-relaxed">
              <strong>Not:</strong> Reddit, Haber Kaynakları (Google News RSS) ve YouTube anahtarsız gerçek API çağrılarıyla çalışır
              (YouTube video ve yorum verisini yt-dlp ile toplar). X (Twitter) ve Google Trends, ilgili API anahtarı/ayarı backend
              `.env` dosyasına eklendiğinde otomatik aktif olur; YouTube için de isteğe bağlı olarak ücretsiz bir YOUTUBE_API_KEY
              eklenirse daha yüksek kotalı resmi API yoluna otomatik geçilir — kod hazırdır, herhangi bir değişiklik gerekmez
              (bkz. backend/app/collectors/connectors.py).
            </p>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-border">
        <button 
          onClick={kaydet} 
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-primary text-primary-foreground font-bold hover:bg-primary/90 transition-all shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-signal focus:ring-offset-2"
        >
          <Save className="w-5 h-5" /> Konfigürasyonu Kaydet
        </button>
      </div>
    </div>
  );
}
