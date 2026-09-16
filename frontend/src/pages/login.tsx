import React, { useState } from "react";
import { useLocation } from "wouter";
import { useAppContext } from "@/lib/app-context";
import { DEMO_HESAPLAR_GORUNUM } from "@/lib/data";
import { hesapOlustur, girisYap } from "@/lib/auth";
import { Shield, Lock, ShieldCheck, Radar, Activity, TrendingUp, Building2, ArrowRight } from "lucide-react";

export default function Login() {
  const [, setLocation] = useLocation();
  const { setKullanici } = useAppContext();
  const [sekme, setSekme] = useState<"giris" | "kayit">("giris");

  // Giriş formu
  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");
  const [hata, setHata] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);

  // Kayıt formu
  const [kEmail, setKEmail] = useState("");
  const [kSifre, setKSifre] = useState("");
  const [kSifreTekrar, setKSifreTekrar] = useState("");
  const [kKurum, setKKurum] = useState("");
  const [kSektor, setKSektor] = useState("");

  async function girisYapTiklandi(e: React.FormEvent) {
    e.preventDefault();
    setYukleniyor(true);
    setHata("");
    const sonuc = await girisYap(email, sifre);
    setYukleniyor(false);
    if (!sonuc.basarili) {
      setHata(sonuc.hata);
      return;
    }
    setKullanici(sonuc.kullanici);
    setLocation("/panel");
  }

  async function kayitOlTiklandi(e: React.FormEvent) {
    e.preventDefault();
    setYukleniyor(true);
    setHata("");
    const sonuc = await hesapOlustur(kEmail, kSifre, kSifreTekrar, kKurum, kSektor);
    setYukleniyor(false);
    if (!sonuc.basarili) {
      setHata(sonuc.hata);
      return;
    }
    setKullanici(sonuc.kullanici);
    setLocation("/panel");
  }

  async function hizliGiris(u: typeof DEMO_HESAPLAR_GORUNUM[0]) {
    setHata("");
    setYukleniyor(true);
    // Gerçek backend kimlik doğrulaması (bkz. backend/app/main.py
    // _demo_hesaplari_tohumla — bu hesaplar geliştirme ortamında gerçek
    // bcrypt-hash'li kayıtlar olarak DB'ye önceden eklenir).
    const sonuc = await girisYap(u.email, u.sifre);
    setYukleniyor(false);
    if (!sonuc.basarili) {
      setHata(sonuc.hata);
      return;
    }
    setKullanici(sonuc.kullanici);
    setLocation("/panel");
  }

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] bg-background">
      {/* SOL PANEL — Komuta Merkezi Vitrini */}
      <div className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-sidebar text-sidebar-foreground px-12 py-12 noise-grid">
        {/* arka plan halkaları */}
        <div className="pointer-events-none absolute -top-24 -left-24 w-[420px] h-[420px] rounded-full border border-signal/20" />
        <div className="pointer-events-none absolute -top-24 -left-24 w-[300px] h-[300px] rounded-full border border-signal/15" />
        <div className="pointer-events-none absolute -top-24 -left-24 w-[180px] h-[180px] rounded-full border border-signal/10" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-sidebar" />

        <div className="relative z-10 flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-signal/15 border border-signal/30 flex items-center justify-center">
            <Shield className="w-4.5 h-4.5 text-signal" />
          </div>
          <span className="font-display font-semibold tracking-wide text-sm text-slate-200">İtibar Komuta Merkezi</span>
        </div>

        <div className="relative z-10 max-w-md">
          <div className="inline-flex items-center gap-2 pulse-dot text-signal mb-6">
            <span className="relative inline-block w-2 h-2 rounded-full bg-signal" />
            <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-signal/90 ml-1">Canlı İzleme Aktif</span>
          </div>
          <h1 className="font-display text-4xl font-semibold leading-[1.15] tracking-tight text-white">
            Kriz büyümeden önce<br /><span className="text-signal">sinyali yakalayın.</span>
          </h1>
          <p className="text-sm text-slate-400 mt-5 leading-relaxed">
            KOBİ'ler, yerel yönetimler ve STK'lar için gerçek zamanlı itibar radarı: içerik akışını tarar, anormallikleri sınıflandırır, karar destek raporunu sizin için hazırlar.
          </p>

          <div className="mt-9 space-y-4">
            {[
              { ikon: <Radar className="w-4 h-4" />, baslik: "Adaptif tarama", aciklama: "Risk yükseldikçe tarama sıklığı otomatik daralır." },
              { ikon: <Activity className="w-4 h-4" />, baslik: "SCCT sınıflandırması", aciklama: "Kriz kümesi ve sorumluluk seviyesi otomatik belirlenir." },
              { ikon: <TrendingUp className="w-4 h-4" />, baslik: "Karar destek raporu", aciklama: "Kamuoyu açıklaması taslağı saniyeler içinde hazır." },
            ].map((f) => (
              <div key={f.baslik} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3.5">
                <div className="w-8 h-8 rounded-lg bg-signal/10 border border-signal/20 flex items-center justify-center text-signal shrink-0">
                  {f.ikon}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-100">{f.baslik}</p>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{f.aciklama}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-[11px] text-slate-500 font-medium tracking-wide">
          Akademik prototip · Tüm veriler simülasyondur
        </p>
      </div>

      {/* SAĞ PANEL — Kimlik Doğrulama */}
      <div className="flex items-center justify-center p-4 sm:p-8 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8 lg:hidden">
            <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center bg-primary text-primary-foreground shadow-lg">
              <Shield className="w-7 h-7 text-signal" />
            </div>
          </div>
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-foreground font-display tracking-tight">Erken İtibar Krizi Tespit Sistemi</h1>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">KOBİ, yerel yönetim ve STK'lar için erken uyarı ve karar destek paneli</p>
          </div>

          <div className="flex bg-muted rounded-xl p-1 mb-5 border border-border/60">
            <button
              type="button"
              onClick={() => { setSekme("giris"); setHata(""); }}
              className={`flex-1 py-2.5 rounded-lg text-sm font-bold transition-all ${sekme === "giris" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            >
              Giriş Yap
            </button>
            <button
              type="button"
              onClick={() => { setSekme("kayit"); setHata(""); }}
              className={`flex-1 py-2.5 rounded-lg text-sm font-bold transition-all ${sekme === "kayit" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            >
              Kurum Hesabı Oluştur
            </button>
          </div>

          {hata && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl p-3 mb-4 animate-in fade-in slide-in-from-top-1 duration-200">
              {hata}
            </div>
          )}

          {sekme === "giris" ? (
            <form onSubmit={girisYapTiklandi} className="surface-card p-6 space-y-5">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Kurumsal E-posta</label>
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  type="email"
                  placeholder="demo@sirket.com.tr"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/30 focus:border-signal text-sm transition-all"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Şifre</label>
                <input
                  value={sifre}
                  onChange={(e) => setSifre(e.target.value)}
                  type="password"
                  placeholder="Demo1234"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/30 focus:border-signal text-sm transition-all"
                />
              </div>

              <button
                type="submit"
                disabled={yukleniyor}
                className="w-full py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-all shadow-sm hover:shadow-md disabled:opacity-60 flex items-center justify-center gap-2 group"
              >
                {yukleniyor ? "Giriş yapılıyor…" : (<>Giriş Yap <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" /></>)}
              </button>
            </form>
          ) : (
            <form onSubmit={kayitOlTiklandi} className="surface-card p-6 space-y-4">
              <div className="flex items-start gap-2 bg-emerald-50 border border-emerald-100 rounded-lg p-3 mb-1">
                <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
                <p className="text-[11px] text-emerald-800 leading-relaxed">
                  Şifreniz asla düz metin olarak saklanmaz; tarayıcınızda tuzlanarak (salt) hash'lenir. Oluşturduğunuz kurum hesabına ait kriz ve itibar verilerini yalnızca siz görebilirsiniz.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Kurumsal E-posta</label>
                <input value={kEmail} onChange={(e) => setKEmail(e.target.value)} type="email" placeholder="iletisim@kurumunuz.com" className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/30 focus:border-signal text-sm transition-all" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Şifre</label>
                  <input value={kSifre} onChange={(e) => setKSifre(e.target.value)} type="password" placeholder="En az 8 karakter" className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/30 focus:border-signal text-sm transition-all" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Şifre (Tekrar)</label>
                  <input value={kSifreTekrar} onChange={(e) => setKSifreTekrar(e.target.value)} type="password" placeholder="Şifrenizi tekrar girin" className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/30 focus:border-signal text-sm transition-all" />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Kurum Adı</label>
                <input value={kKurum} onChange={(e) => setKKurum(e.target.value)} type="text" placeholder="Örn. Anadolu Gıda A.Ş." className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/30 focus:border-signal text-sm transition-all" />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Sektör (opsiyonel)</label>
                <input value={kSektor} onChange={(e) => setKSektor(e.target.value)} type="text" placeholder="Örn. Gıda & İçecek" className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background/60 focus:outline-none focus:ring-2 focus:ring-signal/30 focus:border-signal text-sm transition-all" />
              </div>

              <button
                type="submit"
                disabled={yukleniyor}
                className="w-full py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-all shadow-sm hover:shadow-md disabled:opacity-60 flex items-center justify-center gap-2"
              >
                <Lock className="w-4 h-4" /> {yukleniyor ? "Hesap oluşturuluyor…" : "Kurum Hesabı Oluştur"}
              </button>
            </form>
          )}

          <div className="mt-7">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground font-semibold tracking-wide">Veya demo hesap seçin</span>
              </div>
            </div>

            <div className="mt-6 space-y-2.5">
              {DEMO_HESAPLAR_GORUNUM.map((u) => (
                <button
                  key={u.email}
                  type="button"
                  onClick={() => hizliGiris(u)}
                  className="w-full flex items-center gap-3.5 p-4 rounded-xl bg-card border border-border hover:border-signal/40 hover:shadow-sm transition-all group text-left"
                >
                  <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center text-muted-foreground group-hover:bg-signal/10 group-hover:text-signal transition-colors shrink-0">
                    <Building2 className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="block font-bold text-foreground text-sm group-hover:text-signal transition-colors truncate">{u.kurum}</span>
                    <span className="block text-[11px] font-medium text-muted-foreground mt-0.5">{u.sektor}</span>
                  </div>
                  <span className="text-xs text-muted-foreground/70 group-hover:text-muted-foreground transition-colors shrink-0">{u.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
