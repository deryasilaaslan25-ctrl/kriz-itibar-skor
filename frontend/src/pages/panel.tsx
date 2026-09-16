import React from "react";
import { Link } from "wouter";
import { useAppContext } from "@/lib/app-context";
import { Daire } from "@/components/gauge";
import { InfoIcon } from "@/components/info-icon";
import { itibarRenk, riskRenk, riskEtiket, fmtDakika, siddetRenk } from "@/lib/data";
import { BarChart, Bar, ResponsiveContainer, XAxis, Tooltip, Cell } from "recharts";
import { Activity, Clock, ArrowRight, Shield, Radar, Rss } from "lucide-react";

export default function Dashboard() {
  const {
    kullanici,
    krizler,
    haberler,
    itibarSkoru,
    krizRiski,
    haftalikVeri,
    sonrakiTaramaSn,
    guncelAralikDk,
    adaptifTarama,
    taraSimdi,
    taraniyor,
  } = useAppContext();

  if (!kullanici) return null;

  const aktifKrizler = krizler.filter((k) => k.durum === "Aktif");
  const negatifSayi = haberler.filter((h) => h.duygu === "negatif").length;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-signal mb-1.5">
            <span className="pulse-dot relative inline-block w-1.5 h-1.5 rounded-full bg-signal" />
            <span className="ml-1">Komuta Merkezi</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground font-display">Genel Bakış</h1>
          <p className="text-sm text-muted-foreground mt-1">{kullanici.kurum}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* İtibar Skoru */}
        <div className="surface-card surface-card-hover p-6 flex items-center gap-6">
          <Daire skor={itibarSkoru} renk={itibarRenk(itibarSkoru)} />
          <div>
            <h2 className="text-sm font-bold text-foreground/90 uppercase tracking-wide flex items-center">
              İtibar Skoru<InfoIcon term="itibarSkoru" />
            </h2>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              Güncel algı durumunu gösterir. Son içeriklerin analiziyle hesaplanmıştır.
            </p>
          </div>
        </div>
        
        {/* Kriz Riski */}
        <div className="surface-card surface-card-hover p-6 flex items-center gap-6">
          <Daire skor={krizRiski} renk={riskRenk(krizRiski)} />
          <div>
            <h2 className="text-sm font-bold text-foreground/90 uppercase tracking-wide flex items-center">
              Kriz Riski Skoru<InfoIcon term="krizRiski" />
            </h2>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              Geleceğe dönük tahmin. Risk düzeyi: <strong className="font-bold ml-1" style={{ color: riskRenk(krizRiski) }}>{riskEtiket(krizRiski)}</strong>
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Aktif Kriz Sayısı */}
        <div className="surface-card surface-card-hover p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Aktif Krizler</h3>
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${aktifKrizler.length > 0 ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-600"}`}>
                <Shield className="w-3.5 h-3.5" />
              </div>
            </div>
            <p className="text-4xl font-bold font-display" style={{ color: aktifKrizler.length > 0 ? "#dc2626" : "#059669" }}>
              {aktifKrizler.length}
            </p>
            <p className="text-[11px] text-muted-foreground/80 mt-2 leading-tight">
              Müdahale bekleyen veya izlenen aktif olay sayısı.
            </p>
          </div>
          <Link href="/krizler" className="inline-flex items-center text-xs font-bold text-signal mt-4 hover:underline group">
            Kriz Merkezi'ne git <ArrowRight className="w-3 h-3 ml-1 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>

        {/* İçerik Hacmi */}
        <div className="surface-card surface-card-hover p-6">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wide">24 Saatlik İçerik</h3>
            <div className="w-7 h-7 rounded-lg bg-signal/10 text-signal flex items-center justify-center">
              <Rss className="w-3.5 h-3.5" />
            </div>
          </div>
          <p className="text-4xl font-bold font-display text-foreground">
            {haberler.length}
          </p>
          <div className="mt-3 flex items-center gap-2">
            <span className="px-2 py-1 rounded-md bg-red-50 text-red-700 text-[10px] font-bold border border-red-100">
              {negatifSayi} Olumsuz
            </span>
            <span className="text-[10px] text-muted-foreground/80 font-medium">Tespit edildi</span>
          </div>
        </div>

        {/* Tarama Durumu */}
        <div className="surface-card surface-card-hover p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wide flex items-center">
                Tarama Modu<InfoIcon term="adaptifTarama" />
              </h3>
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${adaptifTarama ? 'bg-amber-50 text-amber-500' : 'bg-muted text-muted-foreground'}`}>
                <Activity className={`w-3.5 h-3.5 ${adaptifTarama ? 'animate-pulse' : ''}`} />
              </div>
            </div>
            <p className="text-sm font-semibold text-foreground/90">
              {adaptifTarama ? "Adaptif (Aktif)" : "Sabit Aralık"}
            </p>
            <p className="text-xs text-muted-foreground mt-1 flex items-center">
              <Clock className="w-3 h-3 mr-1" /> {guncelAralikDk} dakikada bir tarıyor
            </p>
          </div>
          
          <div className="mt-4 flex items-center justify-between pt-4 border-t border-border/70">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider mb-0.5">Sıradaki</span>
              <span className="text-lg font-bold text-foreground font-mono tracking-tight">{fmtDakika(sonrakiTaramaSn)}</span>
            </div>
            <button
              onClick={() => { taraSimdi(); }}
              disabled={taraniyor}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-bold rounded-lg transition-all shadow-sm hover:shadow-md flex items-center gap-1.5 disabled:opacity-60"
            >
              <Radar className={`w-3.5 h-3.5 ${taraniyor ? "animate-spin" : ""}`} /> {taraniyor ? "Taranıyor…" : "Şimdi Tara"}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Haftalık Trend Chart */}
        <div className="surface-card p-6 flex flex-col">
          <div className="mb-6">
            <h3 className="text-sm font-bold text-foreground/90 uppercase tracking-wide">Haftalık İçerik Hacmi</h3>
            <p className="text-xs text-muted-foreground/80 mt-1">Platformlarda tespit edilen günlük toplam girdi sayısı.</p>
          </div>
          <div className="h-48 w-full mt-auto">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={haftalikVeri} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--signal))" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.85} />
                  </linearGradient>
                </defs>
                <Tooltip 
                  cursor={{ fill: 'hsl(var(--signal) / 0.06)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-sidebar text-white text-xs p-2.5 rounded-lg shadow-xl border border-sidebar-border">
                          <p className="font-bold mb-1">{payload[0].payload.gun}</p>
                          <p className="text-slate-300">Hacim: <span className="font-mono text-signal">{payload[0].value}</span></p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="hacim" radius={[6, 6, 0, 0]} fill="url(#barGrad)" />
                <XAxis dataKey="gun" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} dy={10} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Latest Crises */}
        <div className="surface-card p-6">
          <div className="mb-5 flex items-center justify-between">
            <h3 className="text-sm font-bold text-foreground/90 uppercase tracking-wide">Son Aktif Krizler</h3>
            {aktifKrizler.length > 3 && <span className="text-[10px] text-muted-foreground/80 font-bold uppercase">+ {aktifKrizler.length - 3} DAHA</span>}
          </div>
          
          {aktifKrizler.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-center">
              <div className="w-12 h-12 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mb-3">
                <Shield className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-foreground/80">Her şey yolunda</p>
              <p className="text-xs text-muted-foreground mt-1">Şu anda aktif kriz bulunmuyor.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {aktifKrizler.slice(0, 3).map((k) => (
                <Link key={k.id} href="/krizler" className="block group">
                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-border/70 bg-muted/40 group-hover:bg-muted group-hover:border-signal/25 transition-all">
                    <div className="overflow-hidden mr-4">
                      <p className="text-sm font-bold text-foreground truncate">{k.baslik}</p>
                      <p className="text-[11px] text-muted-foreground truncate mt-0.5">{k.aciklama}</p>
                    </div>
                    <div className="flex flex-col items-end shrink-0">
                      <span className="text-lg font-bold font-display leading-none" style={{ color: siddetRenk(k.siddet) }}>
                        {k.siddet.toFixed(1)}
                      </span>
                      <span className="text-[9px] font-bold text-muted-foreground/70 uppercase tracking-wider mt-1">Skor</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
