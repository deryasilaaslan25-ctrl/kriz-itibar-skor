"""Bölüm 14: Kaynak Güvenilirlik Puanı. Rapor Bölüm 14 tablosuyla birebir uyumlu taban değerler."""
from __future__ import annotations

HESAP_TIPI_TABAN_PUAN = {
    "anonim": 0.20,
    "yeni": 0.35,
    "fenomen": 0.75,
    "dogrulanmis": 0.90,
    "ulusal_gazete": 1.00,
}


def guven_puani_hesapla(hesap_tipi: str, hesap_yasi_gun: int = 0, takipci_sayisi: int = 0) -> float:
    """Taban puana hesap yaşı ve takipçi sayısına dayalı küçük düzeltmeler uygular."""
    taban = HESAP_TIPI_TABAN_PUAN.get(hesap_tipi, 0.20)

    # Hesap yaşı düzeltmesi: 1 yıldan eski hesaplar için +0.05 tavan bonus
    yas_bonus = 0.05 if hesap_yasi_gun >= 365 else 0.0

    # Takipçi sayısı düzeltmesi (yalnızca anonim/yeni kategoriler için anlamlı)
    takipci_bonus = 0.05 if takipci_sayisi >= 10000 and taban < 0.75 else 0.0

    return round(min(1.0, taban + yas_bonus + takipci_bonus), 3)
