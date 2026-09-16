import React from "react";
import { Link } from "wouter";
import { useAppContext } from "@/lib/app-context";
import { riskSeviyesiRenk, riskSeviyesiRozetSinifi } from "@/lib/data";
import { InfoIcon } from "./info-icon";
import { toast } from "sonner";
import { X, CheckCircle, AlertCircle, Sparkles, Bell, BellOff, ArrowRight } from "lucide-react";
import type { Kriz, Kullanici } from "@/lib/domain";

/**
 * Faz 8 GÜNCELLEMESİ: Bu modal önceden taslak kamuoyu açıklamasını VE tam
 * raporu istemci tarafında (data.ts: taslakMetniUret/raporMetniOlustur) yerel
 * şablonlardan üretiyordu. Artık yalnızca krizin backend'den gelen ÖZET
 * bilgilerini (16-bileşenli risk skoru, SCCT duruşu) gösterir; TAM strateji,
 * taslak iletişim metinleri, geçmiş kriz analizi ve PDF indirme — hepsi
 * gerçek backend uç noktalarını kullanan "PR Danışmanı" sayfasına taşınmıştır
 * (üst navigasyon menüsünden her zaman erişilebilir, yalnızca bu modalden
 * değil — kullanıcı isteği).
 */
export function KrizDetay({
  kriz,
  onKapat,
  kullanici,
  onGeriBildirim,
}: {
  kriz: Kriz;
  onKapat: () => void;
  kullanici: Kullanici;
  onGeriBildirim: (id: number, deger: "gercek" | "siradan") => void;
}) {
  const { bildirimTercihiKaydet, bildirimTercihiVarMi } = useAppContext();
  const bildirimSorulduMu = bildirimTercihiVarMi(kriz.konu);
  const bilesenler = kriz.riskDetay?.bilesenler ?? {};
  const enYuksekBilesenler = Object.entries(bilesenler).sort((a, b) => b[1] - a[1]).slice(0, 5);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/65 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-card rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-border flex flex-col animate-in zoom-in-95 slide-in-from-bottom-2 duration-200">

        <div className="flex items-start justify-between p-6 border-b border-border bg-muted/40 sticky top-0 z-10 backdrop-blur-sm">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h3 className="text-xl font-bold text-foreground font-display">{kriz.baslik}</h3>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-red-100 text-red-700 border border-red-200">
                {kriz.durum}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{kriz.aciklama}</p>
          </div>
          <button onClick={onKapat} className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors shrink-0 ml-3">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl p-4 bg-muted/50 border border-border/70">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center">
                Kriz Risk Skoru<InfoIcon term="krizSiddeti" />
              </p>
              <p className="text-3xl font-bold font-display" style={{ color: riskSeviyesiRenk(kriz.riskDetay?.risk_seviyesi) }}>
                {kriz.siddet.toFixed(0)} <span className="text-sm text-muted-foreground font-sans font-medium">/ 100</span>
              </p>
              <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${riskSeviyesiRozetSinifi(kriz.riskDetay?.risk_seviyesi)}`}>
                {kriz.riskDetay?.risk_seviyesi ?? "Hesaplanmadı"}
              </span>
            </div>
            <div className="rounded-xl p-4 bg-muted/50 border border-border/70">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center">
                Platformlar
              </p>
              <p className="text-sm font-bold text-foreground/90">{kriz.platform.join(", ") || "—"}</p>
              <p className="text-xs text-muted-foreground mt-1 font-medium">İçerik sayısı: {kriz.icerikSayisi}</p>
            </div>
          </div>

          {enYuksekBilesenler.length > 0 && (
            <div className="rounded-xl p-5 border border-border">
              <p className="text-sm font-bold text-foreground/90 mb-3">En Yüksek Katkılı Risk Bileşenleri</p>
              <div className="space-y-2">
                {enYuksekBilesenler.map(([ad, deger]) => (
                  <div key={ad} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-40 shrink-0 capitalize">{ad.replace(/_/g, " ")}</span>
                    <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                      <div className="h-full bg-signal" style={{ width: `${Math.min(100, deger * 8)}%` }} />
                    </div>
                    <span className="text-xs font-mono text-foreground/80 w-10 text-right">{deger.toFixed(1)}</span>
                  </div>
                ))}
              </div>
              {kriz.riskDetay?.aciklama && (
                <p className="text-xs text-muted-foreground mt-3 pt-3 border-t border-border/60 leading-relaxed">{kriz.riskDetay.aciklama}</p>
              )}
            </div>
          )}

          <Link
            href={`/pr-danismani?krizId=${kriz.id}`}
            onClick={onKapat}
            className="flex items-center justify-between p-4 rounded-xl border border-signal/30 bg-signal/5 hover:bg-signal/10 transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-signal/15 text-signal flex items-center justify-center shrink-0">
                <Sparkles className="w-4.5 h-4.5" />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">PR Danışmanı'nda Görüntüle</p>
                <p className="text-xs text-muted-foreground">18 taktikli strateji, taslak iletişim metinleri, geçmiş kriz analizi ve PDF rapor</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-signal shrink-0 transition-transform group-hover:translate-x-1" />
          </Link>

          {!bildirimSorulduMu && (
            <div className="rounded-xl p-4 border border-border bg-muted/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-xs font-medium text-muted-foreground leading-relaxed">
                <strong className="text-foreground/90">"{kriz.konu}"</strong> türü krizler tekrar yükseldiğinde bildirim almak ister misiniz?
              </p>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => { bildirimTercihiKaydet(kriz.konu, true); toast.success(`"${kriz.konu}" için bildirimler açık olarak kaydedildi.`); }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors"
                >
                  <Bell className="w-3.5 h-3.5" /> Evet, bildir
                </button>
                <button
                  onClick={() => { bildirimTercihiKaydet(kriz.konu, false); toast.success(`"${kriz.konu}" için bildirimler kapalı olarak kaydedildi.`); }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-muted text-muted-foreground border border-border hover:bg-muted/70 transition-colors"
                >
                  <BellOff className="w-3.5 h-3.5" /> Hayır, bildirme
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="p-6 border-t border-border bg-muted/40 flex items-center justify-between mt-auto">
          <span className="text-sm font-medium text-muted-foreground">Geri bildirim (AI modelini eğitmek için):</span>
          <div className="flex gap-2">
            <button
              onClick={() => onGeriBildirim(kriz.id, "siradan")}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                kriz.feedback === "siradan" ? "bg-emerald-600 text-white" : "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
              }`}
            >
              <CheckCircle className="w-4 h-4" /> Sıradan Şikâyet
            </button>
            <button
              onClick={() => onGeriBildirim(kriz.id, "gercek")}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                kriz.feedback === "gercek" ? "bg-red-600 text-white" : "bg-red-50 text-red-700 border border-red-200 hover:bg-red-100"
              }`}
            >
              <AlertCircle className="w-4 h-4" /> Gerçek Kriz
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
