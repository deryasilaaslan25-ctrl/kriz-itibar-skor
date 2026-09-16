"""Dil tespiti testleri (Faz 10) — bkz. app/services/dil_tespit.py."""
from app.services import dil_tespit


def test_turkce_metin_dogru_tespit_edilir():
    sonuc = dil_tespit.tespit_et("Bu ürün gerçekten çok kötü, asla tavsiye etmiyorum ve müşteri hizmetleri hiç ilgilenmedi.")
    assert sonuc.kod == "tr"
    assert sonuc.ad == "Türkçe"


def test_ingilizce_metin_dogru_tespit_edilir():
    sonuc = dil_tespit.tespit_et("This product is absolutely terrible and I deeply regret buying it from this company.")
    assert sonuc.kod == "en"


def test_kisa_metin_varsayilan_turkceye_duser():
    sonuc = dil_tespit.tespit_et("ok")
    assert sonuc.kod == "tr"
    assert sonuc.guven == 0.0


def test_bos_metin_cokmez():
    sonuc = dil_tespit.tespit_et("")
    assert sonuc.kod == "tr"


def test_desteklenen_diller_haritasinda_turkce_ve_ingilizce_var():
    assert "tr" in dil_tespit.DESTEKLENEN_DILLER
    assert "en" in dil_tespit.DESTEKLENEN_DILLER
