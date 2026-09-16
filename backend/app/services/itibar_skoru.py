"""
İtibar Skoru (Reputation Score) — Bilimsel/Literatüre Dayalı Model.

Bu modül, Document 121 (bilimsel gereksinim belgesi) s.2'de tanımlanan formülü
BİREBİR uygular. Önceki sürümde sistemde "itibar skoru" hiç yoktu — yalnızca
kriz riski hesaplanıyordu (bkz. risk_scoring.py); frontend'deki gösterge ise
`55 + duygu_ortalaması*35 + çeşitlilik_bonusu - hacim_cezası` biçiminde tamamen
sezgisel, kaynaksız bir istemci-taraflı formüldü (bkz. app-context.tsx eski
`itibarSkoru` hesaplaması). Bu modül o sezgisel hesaplamanın YERİNİ alır.

Matematiksel Formül
--------------------
    R_itibar(t) = 50 + 50 · tanh( α · Σᵢ wᵢ·e^(−λ(t−tᵢ))·sᵢ / Σᵢ wᵢ·e^(−λ(t−tᵢ)) )

    wᵢ = w_kaynak,i · (1 + ln(1 + Etkileşimᵢ))
    λ  = ln(2) / T½

Değişkenler
-----------
- sᵢ ∈ [-1, 1]: i. içeriğin ince taneli (fine-grained) duygu skoru
  (bkz. sentiment.py: DuyguSonucu — negatif için negatif, pozitif için
  pozitif işaretli, güven ağırlıklı skora dönüştürülür, bkz. `_isaretli_skor`).
- wᵢ: içeriğin ağırlık katsayısı. w_kaynak,i kaynağın güvenilirlik/otorite
  puanı (bkz. source_credibility.py, [0,1]); ln(1+Etkileşim) beğeni+paylaşım+
  yorum toplamının LOGARİTMİK ölçeklenmesidir (10.000 paylaşımlı bir içerik,
  10 paylaşımlıdan 1000 kat değil, yaklaşık ln(10001)/ln(11) ≈ 3.8 kat ağırlıklı
  olur — sosyal medyada etkileşim dağılımları güç-yasası/log-normal olduğundan
  ham doğrusal ölçek birkaç viral içeriğin skoru tek başına domine etmesine yol
  açar; log ölçek bu "kalın kuyruk" (fat-tail) etkisini yumuşatır).
  DÜZELTME (2026-08, gerçek bir tarama sırasında tespit edildi): formül
  ÖNCEDEN yalnızca `ln(1+Etkileşim)` idi — bu, etkileşimi hiç raporlanmayan
  kaynaklar (ör. Google News RSS; bkz. connectors.py "RSS etkileşim sayısı
  sağlamaz") için wᵢ=0 üretiyor, dolayısıyla o içerik toplam ağırlıklı
  ortalamaya SIFIR katkı yapıyordu. Sadece bu tür kaynaklardan veri
  geldiğinde (ör. Reddit/Trends bir tarama esnasında engellenmişse) TÜM
  ağırlıklar sıfıra düşüyor, itibar skoru gerçek duygu dağılımından
  BAĞIMSIZ olarak "50 nötr" basıyordu — bu, formülün amacına (kaynak
  güvenilirliği + etkileşim hacminin BİRLİKTE ağırlıklandırması) aykırıydı.
  `(1 + ln(1+Etkileşim))` biçimine değiştirilerek, her içerik EN AZINDAN
  kendi kaynak-güvenilirliği kadar bir taban ağırlık taşır (Hovland & Weiss'ın
  "güvenilir kaynak" bulgusu tek başına yeterli bir sinyaldir); yüksek
  etkileşim bu taban ağırlığın ÜZERİNE logaritmik bir çarpan ekler. Bu,
  viral içeriğin ağırlıklı olarak öne çıkması gerekliliğini KORUR (bkz.
  test_yuksek_etkilesim_logaritmik_olcekle_agirliklanir) ama etkileşimsiz
  içeriği tamamen SİLMEZ.
- e^(−λ(t−tᵢ)): üstel zaman aşınımı. λ, yarılanma ömrü T½ ile hesaplanır.

Literatür Dayanağı
------------------
1. Fombrun, C. J. & van Riel, C. B. M. — RepTrak / Reputation Quotient kuramı:
   kurumsal itibarın, paydaşların kurum hakkındaki KÜMÜLATİF algısının
   ağırlıklı bir toplamı olduğunu; bu algının tek bir andaki değil, ZAMAN
   İÇİNDE biriken sinyallerin bir fonksiyonu olduğunu öne sürer. Bu, formülün
   "toplamsal ağırlıklı ortalama" iskeletinin (Σwᵢsᵢ/Σwᵢ) doğrudan kaynağıdır.
2. Hovland, C. I. & Weiss, W. (1951), "The Influence of Source Credibility on
   Communication Effectiveness", Public Opinion Quarterly — aynı mesajın
   güvenilir bir kaynaktan mı yoksa güvenilmez bir kaynaktan mı geldiğinin,
   mesajın ikna ediciliğini/etkisini anlamlı ölçüde değiştirdiğini gösterir.
   Bu, wᵢ içindeki w_kaynak,i çarpanının (kaynağı güvenilir olmayan bir
   içeriğin itibar skoruna daha az ağırlıkla katkı yapması) doğrudan
   gerekçesidir.
3. Ebbinghaus, H. (1885), Über das Gedächtnis — insan hafızasının zamanla
   ÜSTEL bir eğriyle unuttuğunu gösteren klasik "unutma eğrisi" (forgetting
   curve) bulgusu. Kamuoyu algısı da benzer şekilde eski içeriklere azalan
   ağırlık verir; bu yüzden e^(−λΔt) üstel aşınım terimi kullanılır (doğrusal
   veya basamaklı bir aşınım yerine — üstel aşınım, "yarılanma ömrü" kavramını
   matematiksel olarak tutarlı kılar: bkz. app/config.py ITIBAR_YARILANMA_OMRU_SAAT).

tanh(·) sıkıştırması: net ağırlıklı duygu (Σwᵢsᵢ/Σwᵢ) zaten [-1,1] aralığında
olduğundan aslında ek bir sıkıştırmaya gerek yoktur; tanh burada α duyarlılık
katsayısıyla birlikte DOYGUNLUK (saturation) sağlamak için kullanılır — az
sayıda ama çok güçlü sinyal, skoru anında 0/100'e kilitlemez, giderek azalan
marjinal etkiyle yaklaşır (psikofizikte Weber-Fechner yasasının log/tanh
tipi doygunluk fonksiyonlarıyla modellenmesiyle aynı ilke).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import settings

# sᵢ hesaplarken duygu kutbunun işaretini belirler (sentiment.py DuyguSonucu.duygu)
_ISARET = {"negatif": -1.0, "pozitif": 1.0, "nötr": 0.0}


@dataclass
class ItibarIcerikGirdisi:
    """Bir içeriğin itibar motoruna aktarılan ham sinyalleri."""

    duygu: str                    # "negatif" | "pozitif" | "nötr" (sentiment.py çıktısı)
    duygu_guveni: float            # 0-1: DuyguSonucu.puan (modelin kendi güveni)
    kaynak_guven_puani: float      # 0-1: source_credibility.guven_puani_hesapla() çıktısı
    etkilesim: int                 # beğeni + paylaşım + yorum toplamı (>= 0)
    icerik_zamani: datetime        # tᵢ
    kaynak_id: str | int | None = None
    ozet: str | None = None        # açıklama metninde göstermek için kısa referans


@dataclass
class ItibarKatki:
    kaynak_id: str | int | None
    ozet: str | None
    isaretli_skor: float           # sᵢ
    agirlik: float                  # wᵢ (henüz zaman aşınımı uygulanmamış)
    zaman_asinimi_carpani: float    # e^(−λΔt)
    agirlikli_katki_orani: float    # bu içeriğin toplam ağırlıklı payı (0-1)


@dataclass
class ItibarSonucu:
    skor: float                     # 0-100
    icerik_sayisi: int
    net_agirlikli_duygu: float      # tanh öncesi Σwᵢsᵢ/Σwᵢ değeri, [-1,1]
    yarilanma_omru_saat: float
    alpha: float
    katkilar: list[ItibarKatki] = field(default_factory=list)
    aciklama: str = ""


def _isaretli_skor(duygu: str, guven: float) -> float:
    """sᵢ ∈ [-1,1]: duygu kutbunun işareti × modelin kendi güven skoru.

    Örn. "negatif" + güven 0.87 -> s = -0.87 (frontend'deki "-0.87" gösterimiyle
    birebir aynı sayı ve aynı anlam: "bu içerik %87 güvenle negatif").
    """
    return _ISARET.get(duygu, 0.0) * max(0.0, min(1.0, guven))


def hesapla(
    icerikler: list[ItibarIcerikGirdisi],
    simdi: datetime | None = None,
    alpha: float | None = None,
    yarilanma_omru_saat: float | None = None,
) -> ItibarSonucu:
    """R_itibar(t) formülünü uygular; SHAP-benzeri toplamsal açıklama üretir.

    NOT (açıklanabilirlik/doğrusallık sınırı): `katkilar` listesindeki
    `agirlikli_katki_orani` değerleri tanh UYGULANMADAN ÖNCEKİ doğrusal
    ağırlıklı-ortalama uzayında hesaplanır (Σwᵢsᵢ/Σwᵢ'ye payı). tanh
    monoton artan bir fonksiyon olduğundan katkıların SIRALAMASI korunur,
    ancak tanh sonrası nihai 0-100 skoruna katkı payları TAM olarak doğrusal
    değildir (risk_scoring.py'deki 16-bileşenli motorun ham/doğrusal toplam
    üzerinden açıklama üretmesiyle aynı, kabul edilebilir ve yaygın XAI
    yaklaşımı — bkz. o modülün docstring'i).
    """
    simdi = simdi or datetime.now(timezone.utc)
    alpha = alpha if alpha is not None else settings.ITIBAR_ALPHA
    t_half = yarilanma_omru_saat if yarilanma_omru_saat is not None else settings.ITIBAR_YARILANMA_OMRU_SAAT
    lam = math.log(2) / t_half

    if not icerikler:
        return ItibarSonucu(
            skor=50.0, icerik_sayisi=0, net_agirlikli_duygu=0.0,
            yarilanma_omru_saat=t_half, alpha=alpha, katkilar=[],
            aciklama=(
                "Henüz analiz edilmiş içerik yok; skor nötr (50/100) varsayılan "
                "değerde tutuluyor. Bu, 'itibar olumlu/olumsuz değil' anlamına "
                "gelir — veri toplandıkça skor gerçek sinyale göre güncellenir."
            ),
        )

    agirlikli_toplam = 0.0
    agirlik_toplam = 0.0
    ham_katkilar: list[tuple[ItibarIcerikGirdisi, float, float, float]] = []

    for icerik in icerikler:
        s_i = _isaretli_skor(icerik.duygu, icerik.duygu_guveni)
        w_kaynak = max(0.0, min(1.0, icerik.kaynak_guven_puani))
        # "+1" tabanı: etkileşimi hiç raporlanmayan kaynaklar (ör. Google News
        # RSS) wᵢ=0 alıp toplam ağırlıklı ortalamadan tamamen SİLİNMESİN diye
        # (bkz. yukarıdaki "DÜZELTME" notu). Etkileşim arttıkça bu taban
        # ağırlığın üzerine logaritmik bir çarpan eklenir.
        w_i = w_kaynak * (1.0 + math.log1p(max(0, icerik.etkilesim)))

        delta_saat = max(0.0, (simdi - _tz_normalize(icerik.icerik_zamani, simdi)).total_seconds() / 3600.0)
        asinim = math.exp(-lam * delta_saat)

        agirlik_efektif = w_i * asinim
        agirlikli_toplam += agirlik_efektif * s_i
        agirlik_toplam += agirlik_efektif
        ham_katkilar.append((icerik, s_i, w_i, asinim))

    net = (agirlikli_toplam / agirlik_toplam) if agirlik_toplam > 0 else 0.0
    net = max(-1.0, min(1.0, net))
    skor = round(50 + 50 * math.tanh(alpha * net), 2)

    katkilar: list[ItibarKatki] = []
    for icerik, s_i, w_i, asinim in ham_katkilar:
        agirlik_efektif = w_i * asinim
        pay = (agirlik_efektif / agirlik_toplam) if agirlik_toplam > 0 else 0.0
        katkilar.append(ItibarKatki(
            kaynak_id=icerik.kaynak_id, ozet=icerik.ozet, isaretli_skor=round(s_i, 3),
            agirlik=round(w_i, 4), zaman_asinimi_carpani=round(asinim, 4),
            agirlikli_katki_orani=round(pay, 4),
        ))
    katkilar.sort(key=lambda k: abs(k.agirlikli_katki_orani), reverse=True)

    en_etkili = katkilar[0] if katkilar else None
    yorum = (
        "yüksek (olumlu algı baskın)" if skor >= 65 else
        "düşük (olumsuz algı baskın)" if skor <= 35 else
        "orta/karışık (net bir eğilim yok)"
    )
    aciklama = (
        f"İtibar skoru {skor}/100 — {yorum}. Bu skor, {len(icerikler)} içeriğin "
        f"kaynak-güvenilirliği ve etkileşim hacmiyle ağırlıklandırılmış, "
        f"{t_half:.0f} saatlik yarılanma ömrüyle zaman-aşınımına uğratılmış net "
        f"duygu ortalamasının ({net:+.3f}, [-1,1] aralığında) tanh(α={alpha}) ile "
        f"0-100 ölçeğine dönüştürülmüş halidir (50=tam nötr). "
    )
    if en_etkili is not None:
        aciklama += (
            f"En yüksek ağırlıklı katkıyı '{en_etkili.ozet or en_etkili.kaynak_id}' "
            f"içeriği yaptı (payı: %{en_etkili.agirlikli_katki_orani*100:.1f}, "
            f"işaretli duygu skoru: {en_etkili.isaretli_skor:+.2f})."
        )

    return ItibarSonucu(
        skor=skor, icerik_sayisi=len(icerikler), net_agirlikli_duygu=round(net, 4),
        yarilanma_omru_saat=t_half, alpha=alpha, katkilar=katkilar, aciklama=aciklama,
    )


def _tz_normalize(t: datetime, referans: datetime) -> datetime:
    """Naive/aware datetime karışıklığını önler (SQLite genelde naive döner)."""
    if t.tzinfo is None and referans.tzinfo is not None:
        return t.replace(tzinfo=referans.tzinfo)
    if t.tzinfo is not None and referans.tzinfo is None:
        return t.replace(tzinfo=None)
    return t
