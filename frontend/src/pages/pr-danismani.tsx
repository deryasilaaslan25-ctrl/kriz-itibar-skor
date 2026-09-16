import React, { useEffect, useState } from "react";
import { useSearch } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { useAppContext } from "@/lib/app-context";
import { krizOnerisiGetirApi, raporJsonApi, gecmisKrizAnaliziApi, raporIndirApi } from "@/lib/api";
import { metniKopyala, riskSeviyesiRenk, riskSeviyesiRozetSinifi } from "@/lib/data";
import { toast } from "sonner";
import { Sparkles, Download, Copy, History, BookMarked, Users2, ListChecks, Info } from "lucide-react";

export default function PRDanismani() {
  const { krizler, kullanici } = useAppContext();
  const search = useSearch();
  const krizIdParam = new URLSearchParams(search).get("krizId");

  const secilebilirKrizler = krizler.filter((k) => k.durum !== "Kapandı");
  const [seciliKrizId, setSeciliKrizId] = useState<number | null>(
    krizIdParam ? Number(krizIdParam) : secilebilirKrizler[0]?.id ?? null,
  );

  useEffect(() => {
    if (krizIdParam) setSeciliKrizId(Number(krizIdParam));
  }, [krizIdParam]);

  const seciliKriz = krizler.find((k) => k.id === seciliKrizId) ?? null;

  const { data: oneri, isLoading: oneriYukleniyor } = useQuery({
    queryKey: ["oneri", seciliKrizId],
    queryFn: () => krizOnerisiGetirApi(seciliKrizId as number),
    enabled: !!seciliKrizId,
  });
  const { data: rapor, isLoading: raporYukleniyor } = useQuery({
    queryKey: ["rapor-json", seciliKrizId],
    queryFn: () => raporJsonApi(seciliKrizId as number),
    enabled: !!seciliKrizId,
  });
  const { data: gecmisAnaliz } = useQuery({
    queryKey: ["gecmis-analiz", seciliKrizId],
    queryFn: () => gecmisKrizAnaliziApi(seciliKrizId as number),
    enabled: !!seciliKrizId,
  });

  const [indiriliyor, setIndiriliyor] = useState(false);

  async function pdfIndir() {
    if (!seciliKrizId) return;
    setIndiriliyor(true);
    try {
      await raporIndirApi(seciliKrizId, `kriz-raporu-${seciliKrizId}.pdf`);
      toast.success("Rapor indirildi.");
    } catch {
      toast.error("Rapor indirilemedi.");
    } finally {
      setIndiriliyor(false);
    }
  }

  if (!kullanici) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-4xl mx-auto pb-16">
      <header>
        <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.18em] text-signal mb-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          <span className="ml-1">Yapay Zeka Halkla İlişkiler Danışmanı</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground font-display">PR Danışmanı</h1>
        <p className="text-sm text-muted-foreground mt-1">
          18 akademik taktikten (Coombs SCCT + Benoit İmaj Onarım Teorisi + Hearit Apologia + çağdaş proaktif stratejiler)
          backend tarafından seçilen, krize özel strateji, taslak iletişim metinleri ve geçmiş kriz analizi.
        </p>
      </header>

      {secilebilirKrizler.length === 0 ? (
        <div className="surface-card p-16 text-center border-dashed">
          <p className="text-sm text-muted-foreground">Şu anda aktif/izlenen bir kriz bulunmuyor. Strateji önerisi görüntülemek için önce Kriz Merkezi'nde bir kriz oluşmalı.</p>
        </div>
      ) : (
        <>
          <div className="surface-card p-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wide mr-1">Kriz Seç:</span>
            {secilebilirKrizler.map((k) => (
              <button
                key={k.id}
                onClick={() => setSeciliKrizId(k.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                  seciliKrizId === k.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/70"
                }`}
              >
                {k.baslik}
              </button>
            ))}
          </div>

          {seciliKriz && (
            <>
              <div className="surface-card p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-foreground font-display">{seciliKriz.baslik}</h2>
                  <p className="text-sm text-muted-foreground mt-1">{seciliKriz.aciklama}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold border ${riskSeviyesiRozetSinifi(seciliKriz.riskDetay?.risk_seviyesi)}`}>
                    {seciliKriz.riskDetay?.risk_seviyesi ?? "—"} ({seciliKriz.siddet.toFixed(0)}/100)
                  </span>
                  <button
                    onClick={pdfIndir}
                    disabled={indiriliyor}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                  >
                    <Download className="w-3.5 h-3.5" /> {indiriliyor ? "İndiriliyor…" : "PDF Raporu İndir"}
                  </button>
                </div>
              </div>

              {(oneriYukleniyor || raporYukleniyor) && (
                <div className="surface-card p-8 text-center text-sm text-muted-foreground">Strateji hesaplanıyor…</div>
              )}

              {oneri && (
                <div className="rounded-xl p-5 border border-border shadow-sm surface-card">
                  <div className="flex items-center gap-2 mb-3">
                    <ListChecks className="w-4 h-4 text-signal" />
                    <p className="text-sm font-bold text-foreground/90">Teorik Kriz Teşhisi ve Önerilen Strateji</p>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-4">{oneri.gerekce}</p>

                  {oneri.spesifik_strateji && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-3">
                      <p className="text-sm font-bold text-amber-900">{oneri.spesifik_strateji.ad}</p>
                      <p className="text-xs text-amber-800 mt-1 leading-relaxed">{oneri.spesifik_strateji.aciklama}</p>
                      <p className="text-[11px] text-amber-700/80 mt-2 italic">Akademik kaynak: {oneri.spesifik_strateji.akademik_kaynak}</p>
                    </div>
                  )}

                  {oneri.alternatif_stratejiler.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2">Alternatif Taktikler</p>
                      <div className="grid sm:grid-cols-2 gap-2">
                        {oneri.alternatif_stratejiler.map((alt) => (
                          <div key={alt.kod} className="p-3 rounded-lg bg-muted/50 border border-border/70">
                            <p className="text-xs font-bold text-foreground/90">{alt.ad}</p>
                            <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{alt.aciklama}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <ul className="text-sm text-muted-foreground space-y-1.5 list-disc list-inside">
                    {oneri.somut_adimlar.map((adim, i) => <li key={i}>{adim}</li>)}
                  </ul>

                  {oneri.llm_metni && (
                    <div className="mt-4 pt-4 border-t border-border/70">
                      <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" /> Anthropic Claude Destekli Danışman Notu
                      </p>
                      <p className="text-sm text-foreground/80 whitespace-pre-wrap leading-relaxed bg-muted/40 rounded-lg p-3">{oneri.llm_metni}</p>
                    </div>
                  )}

                  <p className="text-[11px] text-muted-foreground/70 mt-4 pt-3 border-t border-border/60 flex items-start gap-1.5">
                    <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {oneri.metodoloji_notu}
                  </p>
                </div>
              )}

              {rapor && (
                <div className="rounded-xl border border-border shadow-sm surface-card overflow-hidden">
                  <div className="p-4 bg-muted/50 border-b border-border">
                    <p className="text-sm font-bold text-foreground/90">Kanal Bazlı Taslak İletişim Metinleri</p>
                  </div>
                  <div className="divide-y divide-border/70">
                    {rapor.kanal_taslaklari.map((k) => (
                      <div key={k.kanal} className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-xs font-bold text-foreground/90">{k.kanal} <span className="text-muted-foreground font-normal">({k.ton})</span></p>
                          <button
                            onClick={async () => {
                              const ok = await metniKopyala(k.metin);
                              toast[ok ? "success" : "error"](ok ? "Kopyalandı." : "Kopyalanamadı.");
                            }}
                            className="flex items-center gap-1 text-[11px] font-bold text-signal hover:underline"
                          >
                            <Copy className="w-3 h-3" /> Kopyala
                          </button>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed bg-muted/40 rounded-lg p-3 whitespace-pre-wrap">{k.metin}</p>
                      </div>
                    ))}
                  </div>

                  <div className="p-4 bg-muted/50 border-t border-b border-border flex items-center gap-2">
                    <Users2 className="w-4 h-4 text-muted-foreground" />
                    <p className="text-sm font-bold text-foreground/90">Paydaş Etki ve İletişim Haritası</p>
                  </div>
                  <div className="p-4 grid sm:grid-cols-2 gap-2">
                    {rapor.paydas_haritasi.map((p) => (
                      <div key={p.paydas} className="p-3 rounded-lg bg-muted/40 border border-border/70">
                        <p className="text-xs font-bold text-foreground/90">{p.paydas}</p>
                        <p className="text-[11px] text-muted-foreground mt-1">{p.taktik}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {gecmisAnaliz && (
                <div className="rounded-xl p-5 border border-indigo-200 bg-indigo-50/40 shadow-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <BookMarked className="w-4 h-4 text-indigo-600" />
                    <p className="text-sm font-bold text-indigo-900">Geçmiş Kriz Analizi</p>
                  </div>
                  <p className="text-xs text-indigo-700/80 mb-4 leading-relaxed flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5 shrink-0" />
                    {gecmisAnaliz.taranan_yil_araligi} yılları arası (son 10 yıl) tarandı
                    {gecmisAnaliz.llm_destekli ? " (Anthropic Claude ile canlı araştırma)" : " (jenerik sektör örüntü kütüphanesi)"}:
                  </p>
                  <div className="space-y-3">
                    {gecmisAnaliz.ornekler.map((ornek, i) => (
                      <div key={i} className="bg-card rounded-xl border border-indigo-100 p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[11px] font-bold uppercase tracking-wide text-indigo-600">{ornek.donem}</span>
                          <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${
                            ornek.basari_durumu === "olumlu_yonetildi" ? "bg-emerald-100 text-emerald-700"
                              : ornek.basari_durumu === "olumsuz_yonetildi" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                          }`}>
                            {ornek.basari_durumu === "olumlu_yonetildi" ? "Başarıyla Yönetildi" : ornek.basari_durumu === "olumsuz_yonetildi" ? "Zayıf Yönetildi" : "Karışık Sonuç"}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed mb-2">{ornek.ozet}</p>
                        <p className="text-xs text-muted-foreground mb-1"><strong className="text-foreground/80">O dönemki tutum:</strong> {ornek.kurumun_tutumu}</p>
                        <p className="text-xs text-muted-foreground mb-2"><strong className="text-foreground/80">Sonuç:</strong> {ornek.sonuc}</p>
                        <p className="text-xs text-indigo-800 bg-indigo-50 rounded-md p-2 leading-relaxed"><strong>Danışman tavsiyesi:</strong> {ornek.tavsiye}</p>
                      </div>
                    ))}
                  </div>
                  <p className="text-[11px] text-indigo-700/70 mt-4 leading-relaxed border-t border-indigo-100 pt-3">{gecmisAnaliz.genel_tavsiye}</p>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
