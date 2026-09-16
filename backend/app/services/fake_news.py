"""
Bölüm 13: Sahte Haber Tespiti.

Tam bir "fact-checking" modeli (iddia-kanıt eşleştirme) etiketli veri ve
harici bilgi tabanı (knowledge base) gerektirdiğinden bu aşamada kapsam
dışıdır ve README'de gelecek çalışma olarak belirtilmiştir. Bunun yerine,
doğrulanabilir ve hemen çalışan üç sinyalden oluşan bir "sahte haber
riski" skoru üretilir: kaynak çeşitliliği, kaynak güvenilirliği ve
yayılma hızının haber doğrulama hızını aşıp aşmadığı.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SahteHaberGirdisi:
    farkli_kaynak_sayisi: int          # aynı iddiayı bildiren bağımsız kaynak sayısı
    ortalama_kaynak_guveni: float       # 0-1, source_credibility.py çıktısı ortalaması
    yayilma_hizi_dk: float              # dakikada yeni paylaşım
    ana_akim_teyidi_var: bool           # ulusal_gazete kategorisinde en az 1 kaynak var mı


def risk_hesapla(g: SahteHaberGirdisi) -> float:
    # Az kaynak + düşük güven + yüksek hız + ana akım teyidi yok => yüksek risk
    kaynak_cesitliligi_riski = max(0.0, 1 - g.farkli_kaynak_sayisi / 5)
    guven_riski = 1 - g.ortalama_kaynak_guveni
    hiz_riski = min(1.0, g.yayilma_hizi_dk / 100)
    teyit_riski = 0.0 if g.ana_akim_teyidi_var else 1.0

    skor = (
        0.35 * kaynak_cesitliligi_riski
        + 0.30 * guven_riski
        + 0.20 * hiz_riski
        + 0.15 * teyit_riski
    )
    return round(min(1.0, skor), 3)
