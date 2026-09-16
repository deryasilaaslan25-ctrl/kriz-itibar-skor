import React, { useState } from "react";
import { useAppContext } from "@/lib/app-context";
import { InfoIcon } from "@/components/info-icon";
import { duyguRenk, dilEtiketi } from "@/lib/data";
import { MessageSquare, AlertTriangle, Filter, Search } from "lucide-react";
import { icerikAraApi } from "@/lib/api";
import type { Icerik } from "@/lib/domain";

/** duygu etiketinin işaretini duygu güven skoruna (0-1) uygular; yalnızca
 * GÖRÜNTÜLEME amaçlıdır (ör. "-0.87") — backend'in ürettiği ham değerleri
 * DEĞİŞTİRMEZ, yalnızca kutbu görsel olarak işaretler. */
function isaretliSkor(h: Icerik): number {
  if (h.duygu === "negatif") return -h.puan;
  if (h.duygu === "pozitif") return h.puan;
  return 0;
}

function Rozet({ children, className = "" }: { children: React.ReactNode, className?: string }) {
  return (
    <span className={`inline-flex items-center text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${className}`}>
      {children}
    </span>
  );
}

export default function Icerikler() {
  const { haberler } = useAppContext();
  const [platformFiltre, setPlatformFiltre] = useState("Tümü");
  const [duyguFiltre, setDuyguFiltre] = useState("Tümü");
  const [aramaMetni, setAramaMetni] = useState("");
  const [aramaSonuclari, setAramaSonuclari] = useState<Icerik[] | null>(null);
  const [araniyor, setAraniyor] = useState(false);

  const kaynakListe = aramaSonuclari ?? haberler;
  const platformlar = ["Tümü", ...Array.from(new Set(haberler.map((h) => h.platform)))];
  const filtreli = kaynakListe.filter((h) =>
    (platformFiltre === "Tümü" || h.platform === platformFiltre) &&
    (duyguFiltre === "Tümü" || h.duygu === duyguFiltre)
  );

  async function aramaYap(e: React.FormEvent) {
    e.preventDefault();
    if (!aramaMetni.trim()) { setAramaSonuclari(null); return; }
    setAraniyor(true);
    try {
      // Bölüm 12: Elasticsearch varsa kullanılır, yoksa PostgreSQL/SQLite
      // ILIKE fallback'ine otomatik düşülür (bkz. backend app/services/arama.py).
      const sonuclar = await icerikAraApi(aramaMetni.trim());
      setAramaSonuclari(sonuclar);
    } finally {
      setAraniyor(false);
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-4xl mx-auto">
      <header>
        <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-signal mb-1.5">
          <span className="pulse-dot relative inline-block w-1.5 h-1.5 rounded-full bg-signal" />
          <span className="ml-1">Canlı Tarama Akışı</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground font-display">İçerik Akışı</h1>
        <p className="text-sm text-muted-foreground mt-1 flex items-center">
          Toplanan girdiler, duygu kutbu<InfoIcon term="duyguKutbu" />, örtük anlam<InfoIcon term="ortukAnlam" /> ve çok dilli analiz<InfoIcon term="cokDilliAnaliz" /> ile.
        </p>
      </header>

      <form onSubmit={aramaYap} className="surface-card p-4 flex items-center gap-3">
        <Search className="w-4 h-4 text-muted-foreground shrink-0" />
        <input
          value={aramaMetni}
          onChange={(e) => setAramaMetni(e.target.value)}
          placeholder="İçeriklerde tam metin ara…"
          className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/60"
        />
        {aramaSonuclari !== null && (
          <button type="button" onClick={() => { setAramaMetni(""); setAramaSonuclari(null); }} className="text-xs font-bold text-muted-foreground hover:text-foreground">
            Temizle
          </button>
        )}
        <button type="submit" disabled={araniyor} className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-bold disabled:opacity-60">
          {araniyor ? "Aranıyor…" : "Ara"}
        </button>
      </form>

      <div className="surface-card p-4 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground mr-2">
          <Filter className="w-4 h-4" /> Filtrele:
        </div>
        
        <div className="flex flex-wrap gap-2 flex-1">
          <div className="flex flex-wrap gap-2 pr-4 border-r border-border">
            {platformlar.map((p) => (
              <button 
                key={p} 
                onClick={() => setPlatformFiltre(p)} 
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                  platformFiltre === p 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-muted text-muted-foreground hover:bg-muted/70"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
          
          <div className="flex flex-wrap gap-2 pl-2">
            {["Tümü", "negatif", "pozitif", "nötr"].map((d) => (
              <button 
                key={d} 
                onClick={() => setDuyguFiltre(d)} 
                className={`px-3 py-1.5 rounded-lg text-xs font-bold capitalize transition-colors ${
                  duyguFiltre === d 
                    ? "bg-signal text-signal-foreground" 
                    : "bg-muted text-muted-foreground hover:bg-muted/70"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground px-2 uppercase tracking-wider">
          <span>{filtreli.length} Sonuç Gösteriliyor</span>
        </div>

        {filtreli.length === 0 && (
          <div className="surface-card p-12 text-center border-dashed">
            <p className="text-sm text-muted-foreground">Bu filtrelere uyan içerik bulunamadı.</p>
            <button 
              onClick={() => { setPlatformFiltre("Tümü"); setDuyguFiltre("Tümü"); }}
              className="mt-4 text-xs font-bold text-signal hover:underline"
            >
              Filtreleri Temizle
            </button>
          </div>
        )}

        {filtreli.map((h) => (
          <div key={h.id} className="surface-card surface-card-hover p-5">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2 flex-wrap">
                <Rozet className="bg-muted text-muted-foreground border-border">{h.platform}</Rozet>
                <Rozet className="bg-indigo-50 text-indigo-700 border-indigo-100">{h.konu}</Rozet>
                {h.dil && h.dil !== "tr" && (
                  <Rozet className="bg-sky-50 text-sky-700 border-sky-100">{dilEtiketi(h.dil)}</Rozet>
                )}
                {h.ortukAnlam && (
                  <Rozet className="bg-amber-100 text-amber-800 border-amber-200 gap-1">
                    <AlertTriangle className="w-3 h-3" /> Örtük Anlam
                  </Rozet>
                )}
              </div>
              <span className="text-xs font-medium text-muted-foreground/70 font-mono whitespace-nowrap">{h.tarih}</span>
            </div>
            
            <h3 className="text-base font-bold text-foreground mb-1.5 leading-snug">{h.baslik}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed bg-muted/50 p-3 rounded-lg border border-border/70">
              {h.icerik}
            </p>
            
            <div className="flex items-center justify-between mt-4">
              <div className="flex items-center gap-3">
                <span className={`text-xs font-bold uppercase tracking-wider ${duyguRenk(h.duygu)}`}>
                  {h.duygu} <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-foreground/80 ml-1">{isaretliSkor(h).toFixed(2)}</span>
                </span>
              </div>
              <div className="flex items-center text-xs font-semibold text-muted-foreground/70">
                <MessageSquare className="w-3 h-3 mr-1.5" />
                {h.yorumSayisi ?? 0} Etkileşim
              </div>
            </div>

            {h.aciklamaKanitlari.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/60">
                <p className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider mb-1.5">
                  Bu skor neden {isaretliSkor(h).toFixed(2)}? — Tespit edilen kanıtlar
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {h.aciklamaKanitlari.map((kanit, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-md bg-muted text-[11px] font-mono text-foreground/70 border border-border/70">
                      “{kanit}”
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
