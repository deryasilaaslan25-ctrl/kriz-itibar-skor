import React, { useState } from "react";
import { useAppContext } from "@/lib/app-context";
import { riskSeviyesiRenk, riskSeviyesiRozetSinifi } from "@/lib/data";
import { KrizDetay } from "@/components/kriz-detay";
import { toast } from "sonner";
import { Clock, ShieldAlert } from "lucide-react";
import type { Kriz } from "@/lib/domain";

export default function KrizMerkezi() {
  const { krizler, kullanici, geriBildirimKaydet } = useAppContext();
  const [seciliKriz, setSeciliKriz] = useState<Kriz | null>(null);

  async function geriBildirim(id: number, deger: "gercek" | "siradan") {
    await geriBildirimKaydet(id, deger);
    toast.success("Geri bildirim backend'e kaydedildi.");
    setSeciliKriz(null);
  }

  if (!kullanici) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-signal mb-1.5">
            <span className="pulse-dot relative inline-block w-1.5 h-1.5 rounded-full bg-signal" />
            <span className="ml-1">Sınıflandırma & Karar Desteği</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground font-display">Kriz Merkezi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Sistem tarafından tespit edilen anormallikler, SCCT sınıflandırması ve karar destek raporları
          </p>
        </div>
        <div className="flex items-center bg-muted rounded-xl p-1 text-sm font-semibold border border-border/70">
          <div className="px-3 py-1.5 rounded-lg bg-card text-foreground shadow-sm">Tüm Krizler</div>
          <div className="px-3 py-1.5 text-muted-foreground cursor-not-allowed opacity-50">Geçmiş Arşiv</div>
        </div>
      </header>

      {krizler.length === 0 ? (
        <div className="surface-card p-16 text-center border-dashed flex flex-col items-center">
          <ShieldAlert className="w-12 h-12 text-muted-foreground/40 mb-4" />
          <h3 className="text-lg font-bold text-foreground/90">Kayıtlı Kriz Bulunmuyor</h3>
          <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
            Algoritmalar olağandışı bir içerik yığılması tespit etmedi. "Genel Bakış" sayfasından manuel tarama başlatabilirsiniz.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {krizler.map((k) => {
            const seviye = k.riskDetay?.risk_seviyesi;
            const isClosed = k.durum === "Kapandı";

            return (
              <button
                key={k.id}
                onClick={() => setSeciliKriz(k)}
                className={`group text-left rounded-2xl p-5 border transition-all duration-300 flex flex-col h-full ${
                  isClosed 
                    ? "bg-muted/40 border-border/70 opacity-75 hover:opacity-100" 
                    : "surface-card surface-card-hover"
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex flex-wrap gap-2">
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${riskSeviyesiRozetSinifi(seviye)}`}>
                      {seviye ?? "Hesaplanmadı"}
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border border-border bg-muted text-muted-foreground">
                      {k.durum}
                    </span>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground/70 whitespace-nowrap"><Clock className="w-3 h-3 inline mr-1" />{k.tarih.split(' ')[1] ?? k.tarih}</span>
                </div>

                <div className="mb-4 flex-1">
                  <h3 className="text-lg font-bold text-foreground leading-tight mb-2 font-display group-hover:text-signal transition-colors">
                    {k.baslik}
                  </h3>
                  <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
                    {k.aciklama}
                  </p>
                </div>

                <div className="pt-4 border-t border-border/70 flex items-end justify-between mt-auto">
                  <div>
                    <p className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider mb-1">Konu</p>
                    <p className="text-xs font-bold text-foreground/80">{k.konu}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider mb-1">Risk Skoru</p>
                    <p className="text-2xl font-bold font-display leading-none" style={{ color: riskSeviyesiRenk(seviye) }}>
                      {k.siddet.toFixed(0)}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {seciliKriz && (
        <KrizDetay 
          kriz={seciliKriz} 
          onKapat={() => setSeciliKriz(null)} 
          kullanici={kullanici} 
          onGeriBildirim={geriBildirim} 
        />
      )}
    </div>
  );
}
