import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  krizleriListeleApi, icerikleriListeleApi, itibarHesaplaApi, ayarlariGetirApi, ayarlariKaydetApi,
  denetimListeleApi, taraSimdiApi, geriBildirimKaydetApi, bildirimTercihiKaydetApi, benGetirApi,
} from "./api";
import { tokenOku, tokenSil } from "./api-client";
import { sifreDegistir as sifreDegistirApi, emailDegistir as emailDegistirApi } from "./auth";
import { adaptifAralikHesapla } from "./data";
import type { Ayarlar, DenetimKaydi, HaftalikVeri, Icerik, Kriz, Kullanici } from "./domain";

type AppContextType = {
  kullanici: Kullanici | null;
  setKullanici: (kullanici: Kullanici | null) => void;
  krizler: Kriz[];
  haberler: Icerik[];
  haftalikVeri: HaftalikVeri[];
  esik: number;
  setEsik: (deger: number) => void;
  taramaAraligi: number;
  setTaramaAraligi: (deger: number) => void;
  adaptifTarama: boolean;
  setAdaptifTarama: (deger: boolean) => void;
  emailBildirim: boolean;
  setEmailBildirim: (deger: boolean) => void;
  sonrakiTaramaSn: number;
  guncelAralikDk: number;
  maxSiddet: number;
  taraSimdi: () => Promise<void>;
  taraniyor: boolean;
  ayarlariKaydet: () => Promise<boolean>;
  denetimKayitlari: DenetimKaydi[];
  geriBildirimKaydet: (krizId: number, deger: "gercek" | "siradan") => Promise<void>;
  itibarSkoru: number;
  itibarAciklama: string;
  krizRiski: number;
  aktifKrizSayisi: number;
  logout: () => void;
  bildirimTercihleri: Record<string, boolean>;
  bildirimTercihiKaydet: (konu: string, bildirimIstiyor: boolean) => void;
  bildirimTercihiVarMi: (konu: string) => boolean;
  sifreDegistir: (mevcutSifre: string, yeniSifre: string, yeniSifreTekrar: string) => Promise<{ basarili: boolean; hata?: string }>;
  emailGuncelle: (yeniEmail: string, mevcutSifre: string) => Promise<{ basarili: boolean; hata?: string }>;
};

const AppContext = createContext<AppContextType | null>(null);
const VARSAYILAN_AYARLAR: Ayarlar = { esik: 6, taramaAraligi: 30, adaptifTarama: true, emailBildirim: true };
const GUN_ADLARI = ["Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"];

/** Son 7 günün gerçek içerik hacmini (backend'den gelen Icerik.tarih zaman
 * damgalarından) günlere göre gruplar. Bu bir GÖRÜNTÜLEME agregasyonudur
 * (basit sayma/gruplama) — herhangi bir skor/risk hesaplaması İÇERMEZ; tüm
 * skorlama backend'de yapılır (bkz. app/services/risk_scoring.py, itibar_skoru.py). */
function haftalikHacimHesapla(icerikler: Icerik[]): HaftalikVeri[] {
  const bugun = new Date();
  const gunler: HaftalikVeri[] = [];
  for (let i = 6; i >= 0; i--) {
    const gun = new Date(bugun);
    gun.setDate(bugun.getDate() - i);
    const anahtarTarih = gun.toDateString();
    const hacim = icerikler.filter((h) => new Date(h.tarih).toDateString() === anahtarTarih).length;
    gunler.push({ gun: GUN_ADLARI[gun.getDay()], itibar: 0, hacim });
  }
  return gunler;
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [kullaniciOverride, setKullaniciOverride] = useState<Kullanici | null | undefined>(undefined);
  const [ayarlarTaslak, setAyarlarTaslak] = useState<Ayarlar>(VARSAYILAN_AYARLAR);
  const [sonrakiTaramaSn, setSonrakiTaramaSn] = useState(VARSAYILAN_AYARLAR.taramaAraligi * 60);
  const [taraniyor, setTaraniyor] = useState(false);

  const varOlanToken = !!tokenOku();

  const { data: kullaniciSunucudan } = useQuery({
    queryKey: ["ben"],
    queryFn: benGetirApi,
    enabled: varOlanToken && kullaniciOverride === undefined,
    retry: false,
  });

  // kullaniciOverride: girisYap/hesapOlustur sonrası anında set edilir (ekstra
  // ağ çağrısı beklemeden); sayfa yenilendiğinde ise token varsa /api/auth/ben
  // ile sunucudan yeniden doğrulanır (bkz. yukarıdaki query).
  const kullanici = kullaniciOverride !== undefined ? kullaniciOverride : (kullaniciSunucudan ?? null);
  const setKullanici = useCallback((k: Kullanici | null) => setKullaniciOverride(k), []);

  const aktif = !!kullanici;

  const { data: krizler = [] } = useQuery({ queryKey: ["krizler"], queryFn: krizleriListeleApi, enabled: aktif, refetchInterval: 30_000 });
  const { data: haberler = [] } = useQuery({ queryKey: ["icerikler"], queryFn: () => icerikleriListeleApi(200), enabled: aktif, refetchInterval: 30_000 });
  const { data: itibarSonuc } = useQuery({ queryKey: ["itibar"], queryFn: itibarHesaplaApi, enabled: aktif, refetchInterval: 30_000 });
  const { data: ayarlarSunucudan } = useQuery({ queryKey: ["ayarlar"], queryFn: ayarlariGetirApi, enabled: aktif });
  const { data: denetimKayitlari = [] } = useQuery({ queryKey: ["denetim"], queryFn: denetimListeleApi, enabled: aktif, refetchInterval: 30_000 });

  useEffect(() => {
    if (ayarlarSunucudan) setAyarlarTaslak(ayarlarSunucudan);
  }, [ayarlarSunucudan]);

  const maxSiddet = useMemo(() => Math.max(0, ...krizler.filter((k) => k.durum === "Aktif").map((k) => k.siddet / 10)), [krizler]);
  const guncelAralikDk = adaptifAralikHesapla(ayarlarTaslak.taramaAraligi, maxSiddet, ayarlarTaslak.adaptifTarama);

  useEffect(() => setSonrakiTaramaSn(guncelAralikDk * 60), [guncelAralikDk]);

  const haftalikVeri = useMemo(() => haftalikHacimHesapla(haberler), [haberler]);

  const itibarSkoru = itibarSonuc?.skor ?? 50;
  const itibarAciklama = itibarSonuc?.aciklama ?? "";
  // Kriz Riski Skoru: aktif krizler arasındaki EN YÜKSEK backend risk skoru
  // (bkz. risk_scoring.py — 16 bileşen + EWMA/Benford doğrulama modeli).
  // Burada herhangi bir yeniden hesaplama YAPILMAZ, yalnızca backend'in
  // ürettiği değerlerden en yükseği seçilir (basit max() indirgeme).
  const krizRiski = useMemo(() => {
    const aktifler = krizler.filter((k) => k.durum === "Aktif");
    if (!aktifler.length) return 0;
    return Math.max(...aktifler.map((k) => k.riskDetay?.toplam_skor ?? k.siddet));
  }, [krizler]);

  const taraSimdi = useCallback(async () => {
    setTaraniyor(true);
    try {
      const sonuc = await taraSimdiApi(kullanici?.kurum);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["krizler"] }),
        queryClient.invalidateQueries({ queryKey: ["icerikler"] }),
        queryClient.invalidateQueries({ queryKey: ["itibar"] }),
        queryClient.invalidateQueries({ queryKey: ["denetim"] }),
      ]);
      if (sonuc.durum === "tamamlandi") {
        if (sonuc.kriz_olusturuldu_mu) {
          toast.warning(`Yeni/güncellenmiş kriz tespit edildi (risk: ${sonuc.risk_skoru})`, {
            description: "Kriz Merkezi'nden detayları inceleyebilirsiniz.",
          });
        } else {
          toast.success(`Tarama tamamlandı: ${sonuc.toplanan_icerik_sayisi} içerik analiz edildi.`);
        }
      } else if (sonuc.durum === "veri_bulunamadi") {
        toast.info("Tarama tamamlandı, yeni içerik bulunamadı.");
      }
    } catch (hata) {
      toast.error("Tarama başarısız oldu. Backend'e ulaşılamıyor olabilir.");
    } finally {
      setTaraniyor(false);
      setSonrakiTaramaSn(guncelAralikDk * 60);
    }
  }, [guncelAralikDk, kullanici, queryClient]);

  useEffect(() => {
    if (!kullanici) return;
    const zamanlayici = window.setInterval(() => setSonrakiTaramaSn((kalan) => {
      if (kalan <= 1) {
        taraSimdi();
        return guncelAralikDk * 60;
      }
      return kalan - 1;
    }), 1000);
    return () => window.clearInterval(zamanlayici);
  }, [guncelAralikDk, kullanici, taraSimdi]);

  const ayarlariKaydet = useCallback(async () => {
    try {
      const kaydedilen = await ayarlariKaydetApi(ayarlarTaslak);
      setAyarlarTaslak(kaydedilen);
      queryClient.setQueryData(["ayarlar"], kaydedilen);
      return true;
    } catch {
      return false;
    }
  }, [ayarlarTaslak, queryClient]);

  const setAyar = <K extends keyof Ayarlar>(alan: K, deger: Ayarlar[K]) =>
    setAyarlarTaslak((onceki) => ({ ...onceki, [alan]: deger }));

  const geriBildirimKaydet = useCallback(async (krizId: number, deger: "gercek" | "siradan") => {
    await geriBildirimKaydetApi(krizId, deger);
    await queryClient.invalidateQueries({ queryKey: ["krizler"] });
  }, [queryClient]);

  const bildirimTercihiKaydet = useCallback((konu: string, bildirimIstiyor: boolean) => {
    bildirimTercihiKaydetApi(konu, bildirimIstiyor).then(() => {
      queryClient.invalidateQueries({ queryKey: ["ben"] });
      if (kullanici) setKullaniciOverride({ ...kullanici, bildirimTercihleri: { ...kullanici.bildirimTercihleri, [konu]: bildirimIstiyor } });
    });
  }, [kullanici, queryClient]);

  const bildirimTercihiVarMi = useCallback((konu: string) => !!kullanici && konu in kullanici.bildirimTercihleri, [kullanici]);

  const logout = useCallback(() => {
    tokenSil();
    setKullaniciOverride(null);
    queryClient.clear();
    setLocation("/");
  }, [queryClient, setLocation]);

  const sifreDegistirFn = useCallback(async (mevcutSifre: string, yeniSifre: string, yeniSifreTekrar: string) => {
    if (!kullanici) return { basarili: false, hata: "Oturum bulunamadı." };
    return sifreDegistirApi(mevcutSifre, yeniSifre, yeniSifreTekrar);
  }, [kullanici]);

  const emailGuncelleFn = useCallback(async (yeniEmail: string, mevcutSifre: string) => {
    if (!kullanici) return { basarili: false, hata: "Oturum bulunamadı." };
    const sonuc = await emailDegistirApi(yeniEmail, mevcutSifre);
    if (sonuc.basarili && sonuc.yeniEmail) {
      setKullaniciOverride({ ...kullanici, email: sonuc.yeniEmail });
    }
    return sonuc;
  }, [kullanici]);

  return <AppContext.Provider value={{
    kullanici, setKullanici, krizler, haberler, haftalikVeri,
    esik: ayarlarTaslak.esik, setEsik: (deger) => setAyar("esik", deger),
    taramaAraligi: ayarlarTaslak.taramaAraligi, setTaramaAraligi: (deger) => setAyar("taramaAraligi", deger),
    adaptifTarama: ayarlarTaslak.adaptifTarama, setAdaptifTarama: (deger) => setAyar("adaptifTarama", deger),
    emailBildirim: ayarlarTaslak.emailBildirim, setEmailBildirim: (deger) => setAyar("emailBildirim", deger),
    sonrakiTaramaSn, guncelAralikDk, maxSiddet: maxSiddet * 10, taraSimdi, taraniyor, ayarlariKaydet,
    denetimKayitlari, geriBildirimKaydet,
    itibarSkoru, itibarAciklama, krizRiski, aktifKrizSayisi: krizler.filter((k) => k.durum === "Aktif").length, logout,
    bildirimTercihleri: kullanici?.bildirimTercihleri ?? {}, bildirimTercihiKaydet, bildirimTercihiVarMi,
    sifreDegistir: sifreDegistirFn, emailGuncelle: emailGuncelleFn,
  }}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useAppContext must be used within an AppProvider");
  return context;
}
