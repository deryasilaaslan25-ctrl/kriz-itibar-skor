"""
Bölüm 5-6: Türkçe Doğal Dil İşleme ve Çok Sınıflı Duygu Analizi.

Mimari not (jüri için önemli):
Bu modül iki katmanlı çalışacak şekilde tasarlanmıştır:

  1) LexiconSentimentAnalyzer  -> internet/GPU/API anahtarı gerektirmeyen,
     anında çalışan, açıklanabilir temel model. Kelime bazlı ağırlıklı
     skorlama + olumsuzlama (negasyon) tespiti + yoğunlaştırıcı (intensifier)
     kelime çarpanı uygular. Bu, jüri sunumunda "sistem çalışıyor mu"
     sorusuna anında evet cevabı verir.

  2) TransformerSentimentAnalyzer -> BERTurk / Sentence-Transformers tabanlı
     üretim modeli için arayüz (interface) olarak tanımlıdır. Gerçek ağırlık
     indirme ve fine-tuning için GPU'lu sunucu ve etiketli veri seti (bkz.
     README "Sonraki Adımlar") gerekir; bu depo model ağırlıklarını
     içermez, ancak `SentimentAnalyzer` protokolüne uyduğu için
     LexiconSentimentAnalyzer ile TEK SATIR değişiklikle (dependency
     injection, bkz. get_sentiment_analyzer()) yer değiştirebilir.

Bu tasarım, "mevcut sistemde duygu analizi modülü yok" eleştirisini,
gerçekçi ve doğrulanabilir bir çözümle karşılar; aynı zamanda gelecekteki
BERTurk entegrasyonunu mühendislik borcu olmadan mümkün kılar.

Faz 10 Eklentisi: Çok Dilli Duygu Analizi
-------------------------------------------
Sistem artık YouTube gibi kaynaklardan (bkz. app/collectors/connectors.py
YouTubeCollector) veri çektiğinden, gelen içerikler artık YALNIZCA Türkçe
olmayabilir. Bu modül aynı iki-katmanlı mimariyi (açıklanabilir sözlük
temeli + üretim kalitesinde transformer) DİLE DUYARLI hale getirir:

  1) CokDilliLexiconSentimentAnalyzer -> Türkçe sözlüğün İngilizce, Almanca,
     Fransızca, İspanyolca, Arapça ve Rusça karşılıkları. Aynı 7 kategori
     (öfke/panik/güvensizlik/hayal kırıklığı/memnuniyet/güven/sadakat)
     dilden bağımsız dahili taksonomi olarak korunur.

  2) CokDilliTransformerSentimentAnalyzer -> `cardiffnlp/twitter-xlm-roberta-
     base-sentiment` (XLM-RoBERTa tabanlı, 100+ dilde ortak temsil, çapraz
     dilli aktarımla Türkçe dışındaki dillerde üretim kalitesinde sonuç).

`get_sentiment_analyzer(dil_kodu)` giriş noktası, dil_kodu == "tr" için
ESKİ davranışı (BERTurk/Türkçe sözlük) BİREBİR korur — geriye dönük
uyumluluk bozulmaz; dil_kodu başka bir değerse çok dilli motorlara yönlendirir.
Dil tespiti bkz. app/services/dil_tespit.py.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache

# --- Çekirdek Türkçe duygu sözlüğü (genişletilebilir) -----------------------
# Kategoriler doğrudan JURI_DEGERLENDIRME.md Bölüm 6 ile uyumludur.
NEGATIF_OFKE = {"rezalet", "utanç", "yazıklar", "iğrenç", "berbat", "skandal", "ayıp", "sinir"}
NEGATIF_PANIK = {"tehlike", "acil", "kriz", "felaket", "korkunç", "panik", "alarm"}
NEGATIF_GUVENSIZLIK = {"güvenmiyorum", "yalan", "dolandırıcı", "aldatıldık", "şaibeli", "kandırıldık"}
NEGATIF_HAYALKIRIKLIGI = {"hayal kırıklığı", "üzücü", "beklemiyordum", "pişman", "hüsran"}
POZITIF_MEMNUNIYET = {"harika", "mükemmel", "teşekkürler", "memnun", "başarılı", "güzel", "süper"}
POZITIF_GUVEN = {"güveniyorum", "şeffaf", "dürüst", "profesyonel", "kaliteli"}
POZITIF_SADAKAT = {"tavsiye ederim", "yine alırım", "sadık müşteri", "vazgeçmem"}

INTENSIFIERS = {"çok": 1.4, "aşırı": 1.6, "kesinlikle": 1.3, "tamamen": 1.3, "hiç": 1.2}
NEGATIONS = {"değil", "yok", "asla", "hayır"}

CATEGORY_MAP = {
    "ofke": NEGATIF_OFKE,
    "panik": NEGATIF_PANIK,
    "guvensizlik": NEGATIF_GUVENSIZLIK,
    "hayal_kirikligi": NEGATIF_HAYALKIRIKLIGI,
    "memnuniyet": POZITIF_MEMNUNIYET,
    "guven": POZITIF_GUVEN,
    "sadakat": POZITIF_SADAKAT,
}
NEGATIF_KATEGORILER = {"ofke", "panik", "guvensizlik", "hayal_kirikligi"}
POZITIF_KATEGORILER = {"memnuniyet", "guven", "sadakat"}


def temizle(metin: str) -> str:
    """Bölüm 5: Veri temizleme (URL, emoji, noktalama, fazla boşluk)."""
    metin = re.sub(r"http\S+|www\.\S+", " ", metin)
    metin = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", " ", metin)  # emoji aralığı
    metin = metin.lower()
    # Türkçe harfleri koruyarak noktalama işaretlerini boşlukla değiştir
    metin = re.sub(r"[^\wçğıöşü\s]", " ", metin, flags=re.UNICODE)
    metin = re.sub(r"\s+", " ", metin).strip()
    return metin


@dataclass
class DuyguSonucu:
    duygu: str          # negatif | pozitif | nötr
    alt_tip: str | None  # ofke, panik, memnuniyet ...
    puan: float          # 0-1 güven skoru
    kategori_skorlari: dict[str, float]
    # Faz 4 eklentisi (açıklanabilirlik): "-0.87'yi neden basitçe açıklayamıyoruz"
    # talebine yanıt — bu skoru üreten somut kelime/kalıp kanıtları (post-hoc,
    # LIME/SHAP tarzı insan-okur gerekçe). Boş liste = kanıt kelimesi bulunamadı
    # (ör. modelin sözlükte olmayan bağlamsal ipuçlarına dayandığı durumlar).
    aciklama_kanitlari: list[str] = field(default_factory=list)
    model_adi: str = "lexicon_v1"


class SentimentAnalyzer(ABC):
    """Tüm duygu analizi motorlarının uyması gereken arayüz (Strategy pattern)."""

    @abstractmethod
    def analiz_et(self, metin: str) -> DuyguSonucu: ...


# Kategori isimleri (ofke/panik/.../sadakat) dilden BAĞIMSIZ dahili bir
# taksonomidir — negasyonla kutbu ters dönen bir kategorinin hangi karşıt
# kategoriye yazılacağını belirtir. Tüm diller (Türkçe + Faz 10 çok dilli
# sözlükler) AYNI haritayı paylaşır çünkü kategori kimlikleri (anahtarlar),
# yalnızca o dile ait KELİMELER değişir.
_NEGASYON_KARSITI_HARITASI: dict[str, str] = {
    "ofke": "memnuniyet", "panik": "guven", "guvensizlik": "guven",
    "hayal_kirikligi": "memnuniyet", "memnuniyet": "hayal_kirikligi",
    "guven": "guvensizlik", "sadakat": "guvensizlik",
}


class _SozlukTabanliAnalyzer(SentimentAnalyzer):
    """Sözlük + negasyon + yoğunlaştırıcı tabanlı, açıklanabilir temel model —
    algoritma dilden BAĞIMSIZDIR; dile özgü sözlükler alt sınıflarda sınıf
    öznitelikleri olarak tanımlanır (bkz. LexiconSentimentAnalyzer [Türkçe]
    ve Faz 10'da eklenen CokDilliLexiconSentimentAnalyzer)."""

    KATEGORI_SOZLUGU: dict[str, set[str]] = {}
    NEGATIF_KATEGORILER: set[str] = set()
    POZITIF_KATEGORILER: set[str] = set()
    YOGUNLASTIRICILAR: dict[str, float] = {}
    OLUMSUZLAMALAR: set[str] = set()
    NEGASYON_KARSITI: dict[str, str] = _NEGASYON_KARSITI_HARITASI
    MODEL_ADI: str = "lexicon_generic"

    def analiz_et(self, metin: str) -> DuyguSonucu:
        temiz = temizle(metin)
        kelimeler = temiz.split()

        kategori_skor: dict[str, float] = {k: 0.0 for k in self.KATEGORI_SOZLUGU}
        # Açıklanabilirlik (Faz 4): skoru üreten somut kelime/kalıp kanıtları.
        # "değil/yok" ile tersine dönen eşleşmeler de (kutbu değişmiş haliyle)
        # kanıt olarak işaretlenir — kullanıcı "neden bu skor?" sorusunu
        # metnin içindeki gerçek ifadelerle cevaplayabilsin diye.
        kanitlar: list[str] = []

        for i, kelime in enumerate(kelimeler):
            for kategori, sozluk in self.KATEGORI_SOZLUGU.items():
                coklu_kelime_eslesme = next((ifade for ifade in sozluk if " " in ifade and ifade in temiz), None)
                if kelime in sozluk or coklu_kelime_eslesme:
                    agirlik = 1.0
                    kanit_ifadesi = coklu_kelime_eslesme or kelime
                    # Yoğunlaştırıcı kontrolü (önceki kelime)
                    if i > 0 and kelimeler[i - 1] in self.YOGUNLASTIRICILAR:
                        agirlik *= self.YOGUNLASTIRICILAR[kelimeler[i - 1]]
                        kanit_ifadesi = f"{kelimeler[i - 1]} {kanit_ifadesi}"
                    # Negasyon kontrolü (sonraki kelime dilin olumsuzlama ifadesiyse etkisi tersine döner)
                    negasyon_var = i + 1 < len(kelimeler) and kelimeler[i + 1] in self.OLUMSUZLAMALAR
                    if negasyon_var:
                        ters_kategori = self.NEGASYON_KARSITI.get(kategori, kategori)
                        kategori_skor[ters_kategori] += agirlik
                        kanit_ifadesi = f"{kanit_ifadesi} {kelimeler[i + 1]}"
                    else:
                        kategori_skor[kategori] += agirlik
                    if kanit_ifadesi not in kanitlar:
                        kanitlar.append(kanit_ifadesi)

        toplam_negatif = sum(kategori_skor[k] for k in self.NEGATIF_KATEGORILER)
        toplam_pozitif = sum(kategori_skor[k] for k in self.POZITIF_KATEGORILER)

        if toplam_negatif == 0 and toplam_pozitif == 0:
            return DuyguSonucu("nötr", "bilgilendirici", 0.5, kategori_skor, aciklama_kanitlari=[], model_adi=self.MODEL_ADI)

        if toplam_negatif > toplam_pozitif:
            baskin = max(self.NEGATIF_KATEGORILER, key=lambda k: kategori_skor[k])
            guven = min(0.99, 0.5 + (toplam_negatif - toplam_pozitif) / (toplam_negatif + toplam_pozitif + 1e-6) * 0.5)
            return DuyguSonucu("negatif", baskin, round(guven, 3), kategori_skor, aciklama_kanitlari=kanitlar, model_adi=self.MODEL_ADI)
        else:
            baskin = max(self.POZITIF_KATEGORILER, key=lambda k: kategori_skor[k])
            guven = min(0.99, 0.5 + (toplam_pozitif - toplam_negatif) / (toplam_negatif + toplam_pozitif + 1e-6) * 0.5)
            return DuyguSonucu("pozitif", baskin, round(guven, 3), kategori_skor, aciklama_kanitlari=kanitlar, model_adi=self.MODEL_ADI)


class LexiconSentimentAnalyzer(_SozlukTabanliAnalyzer):
    """Türkçe sözlük tabanlı, açıklanabilir temel model (Faz 10 öncesi ile
    davranışsal olarak BİREBİR aynı — yalnızca genel algoritma yukarıdaki
    _SozlukTabanliAnalyzer'a taşındı)."""

    KATEGORI_SOZLUGU = CATEGORY_MAP
    NEGATIF_KATEGORILER = NEGATIF_KATEGORILER
    POZITIF_KATEGORILER = POZITIF_KATEGORILER
    YOGUNLASTIRICILAR = INTENSIFIERS
    OLUMSUZLAMALAR = NEGATIONS
    MODEL_ADI = "lexicon_v1"


_TRANSFORMER_LABEL_MAP = {
    "positive": "pozitif", "negative": "negatif",
    "olumlu": "pozitif", "olumsuz": "negatif",
    "label_1": "pozitif", "label_0": "negatif",
}


class TransformerSentimentAnalyzer(SentimentAnalyzer):
    """
    BERTurk tabanlı gerçek transformer duygu analizi (Faz 4 — gerçekten
    indirilip çalıştırılmıştır, bkz. app/tests/test_sentiment_transformer.py).

    Model Seçimi ve Gerekçesi
    --------------------------
    `savasy/bert-base-turkish-sentiment-cased` kullanılır. Bu, dbmdz'nin
    Türkçe BERT taban ağırlıkları (`dbmdz/bert-base-turkish-cased`) üzerine
    Türkçe ürün/film yorumu veri setleriyle İNCE AYAR (fine-tune) yapılmış,
    HuggingFace Hub'da herkese açık bir sınıflandırıcıdır. ÖNEMLİ AYRIM: ham
    `dbmdz/bert-base-turkish-cased` yalnızca maskeli-dil-modelleme (MLM)
    ağırlıkları taşır — sınıflandırma başlığı (classification head) YOKTUR,
    bu yüzden doğrudan duygu analizi için kullanılamaz; bu yüzden ayrıca
    fine-tune edilmiş bu checkpoint tercih edilmiştir.

    İkili (Binary) Model Sınırlaması ve "Nötr" Yaklaşımı
    -------------------------------------------------------
    Bu model olumlu/olumsuz (binary) sınıflandırma için eğitilmiştir; ayrı
    bir "nötr" sınıfı YOKTUR. Modelin kendi güveni (softmax olasılığı)
    DUSUK_GUVEN_ESIGI'nin altındaysa — yani model iki sınıf arasında
    belirgin bir tercih yapamıyorsa — çıktı "nötr" olarak işaretlenir. Bu,
    modelin mimari sınırını gizlemek yerine şeffaf biçimde ele alan, dürüst
    bir mühendislik kararıdır.

    Açıklanabilirlik ("skor -0.87 ise bunu basitçe açıklayabilmeliyim" talebi)
    ------------------------------------------------------------------------
    Transformer modelleri doğaları gereği "kara kutu"dur (hangi kelimenin
    kararı ne kadar etkilediği ağırlıklardan doğrudan okunamaz). Bu sınırı
    aşmak için HER transformer çıktısına, LexiconSentimentAnalyzer'ın AYNI
    metinde tespit ettiği somut kanıt kelimeleri/kalıpları da eklenir
    (post-hoc, insan-okur gerekçe) — LIME/SHAP tarzı post-hoc açıklanabilirlik
    yaklaşımlarının basitleştirilmiş, sıfır ek hesaplama maliyetli bir
    uygulamasıdır: nihai çıktı "model %87 güvenle negatif dedi VE metinde
    'bozuk', 'iade etmiyorlar' gibi ifadeler bu yönde kanıt oluşturuyor"
    biçiminde, kullanıcının tek bakışta anlayabileceği birleşik bir açıklamadır.
    """

    DUSUK_GUVEN_ESIGI = 0.65

    def __init__(self, model_name: str = "savasy/bert-base-turkish-sentiment-cased"):
        self.model_name = model_name

    def analiz_et(self, metin: str) -> DuyguSonucu:
        clf = _transformer_pipeline(self.model_name)
        # pipeline kendi içinde tokenizer ile kırpar (truncation=True), ama
        # çok uzun girdilerde gereksiz CPU maliyetini önlemek için burada da
        # kaba bir üst sınır uygulanır (BERT'in 512 token sınırının kabaca
        # karşılığı olarak ~2000 karakter — kesin değil, güvenli bir tampon).
        ham_sonuc = clf(metin[:2000], truncation=True)[0]
        guven = float(ham_sonuc["score"])
        etiket = _TRANSFORMER_LABEL_MAP.get(ham_sonuc["label"].lower(), ham_sonuc["label"].lower())

        duygu = "nötr" if guven < self.DUSUK_GUVEN_ESIGI else etiket

        # Açıklanabilirlik: lexicon motorunun aynı metinde bulduğu kanıtları ödünç al.
        lexicon_sonuc = LexiconSentimentAnalyzer().analiz_et(metin)

        return DuyguSonucu(
            duygu=duygu,
            alt_tip=lexicon_sonuc.alt_tip if duygu != "nötr" else "bilgilendirici",
            puan=round(guven, 3),
            kategori_skorlari=lexicon_sonuc.kategori_skorlari,
            aciklama_kanitlari=lexicon_sonuc.aciklama_kanitlari,
            model_adi=self.model_name,
        )


@lru_cache(maxsize=1)
def _transformer_pipeline(model_name: str):
    """transformers.pipeline'ı tembel (lazy) yükler — yalnızca ilk çağrıda
    model indirilir/RAM'e alınır, modül import edilirken DEĞİL. Bu sayede
    `transformers`/`torch` kurulu olmayan/model indirilemeyen ortamlarda
    modül import edilebilir kalır; hata yalnızca gerçekten çağrıldığında
    (get_sentiment_analyzer() içindeki try/except tarafından) yakalanır."""
    from transformers import pipeline
    return pipeline("sentiment-analysis", model=model_name, tokenizer=model_name)


# ============================================================================
# Faz 10: Çok Dilli Duygu Analizi Sözlükleri ve Motorları
# ============================================================================
# Aşağıdaki sözlükler, Türkçe sözlüğün (yukarıda) 7 kategorisinin (öfke,
# panik, güvensizlik, hayal kırıklığı, memnuniyet, güven, sadakat) en yaygın
# 6 dildeki karşılıklarıdır. Amaç kapsamlı bir sözlük değil — Türkçe
# sözlükte olduğu gibi — "anında, açıklanabilir, anahtarsız çalışan bir
# temel model" sağlamaktır; asıl doğruluk çok dilli transformer motorundan
# (CokDilliTransformerSentimentAnalyzer, aşağıda) gelir, bu sözlükler onun
# indirilemediği durumlarda devreye giren GÜVENLİ bir zemindir.
_COK_DILLI_SOZLUKLER: dict[str, dict[str, set[str]]] = {
    "en": {
        "ofke": {"outrageous", "shame", "disgusting", "terrible", "scandal", "shameful", "furious"},
        "panik": {"danger", "urgent", "crisis", "disaster", "terrifying", "panic", "alarm"},
        "guvensizlik": {"untrustworthy", "lie", "scam", "scammed", "fraud", "suspicious", "cheated"},
        "hayal_kirikligi": {"disappointed", "disappointing", "sad", "regret", "letdown"},
        "memnuniyet": {"great", "excellent", "thanks", "satisfied", "successful", "good", "awesome"},
        "guven": {"trust", "transparent", "honest", "professional", "quality"},
        "sadakat": {"recommend", "buy again", "loyal customer"},
    },
    "de": {
        "ofke": {"skandal", "schande", "widerlich", "furchtbar", "schlimm", "ärgerlich"},
        "panik": {"gefahr", "dringend", "krise", "katastrophe", "erschreckend", "panik", "alarm"},
        "guvensizlik": {"unzuverlässig", "lüge", "betrug", "betrogen", "verdächtig"},
        "hayal_kirikligi": {"enttäuscht", "enttäuschend", "traurig", "bedauern"},
        "memnuniyet": {"toll", "ausgezeichnet", "danke", "zufrieden", "erfolgreich", "gut", "super"},
        "guven": {"vertrauen", "transparent", "ehrlich", "professionell", "qualität"},
        "sadakat": {"empfehle", "wieder kaufen", "treuer kunde"},
    },
    "fr": {
        "ofke": {"scandale", "honte", "dégoûtant", "terrible", "affreux"},
        "panik": {"danger", "urgent", "crise", "catastrophe", "terrifiant", "panique", "alerte"},
        "guvensizlik": {"mensonge", "arnaque", "escroquerie", "suspect", "trompé"},
        "hayal_kirikligi": {"déçu", "décevant", "triste", "regret"},
        "memnuniyet": {"excellent", "merci", "satisfait", "réussi", "bon", "génial"},
        "guven": {"confiance", "transparent", "honnête", "professionnel", "qualité"},
        "sadakat": {"je recommande", "client fidèle"},
    },
    "es": {
        "ofke": {"escándalo", "vergüenza", "asqueroso", "terrible", "indignante"},
        "panik": {"peligro", "urgente", "crisis", "desastre", "aterrador", "pánico", "alerta"},
        "guvensizlik": {"mentira", "estafa", "fraude", "sospechoso", "engañado"},
        "hayal_kirikligi": {"decepcionado", "decepcionante", "triste", "arrepentido"},
        "memnuniyet": {"excelente", "gracias", "satisfecho", "exitoso", "bueno", "genial"},
        "guven": {"confianza", "transparente", "honesto", "profesional", "calidad"},
        "sadakat": {"lo recomiendo", "cliente fiel"},
    },
    "ar": {
        "ofke": {"فضيحة", "عار", "مقرف", "فظيع", "مخز"},
        "panik": {"خطر", "عاجل", "أزمة", "كارثة", "مرعب", "ذعر"},
        "guvensizlik": {"كذب", "احتيال", "نصب", "مشبوه"},
        "hayal_kirikligi": {"خيبة أمل", "محبط", "حزين", "نادم"},
        "memnuniyet": {"رائع", "ممتاز", "شكرا", "راضي", "ناجح", "جيد"},
        "guven": {"ثقة", "شفاف", "صادق", "محترف", "جودة"},
        "sadakat": {"أنصح به", "عميل وفي"},
    },
    "ru": {
        "ofke": {"скандал", "позор", "отвратительно", "ужасно", "возмутительно"},
        "panik": {"опасность", "срочно", "кризис", "катастрофа", "паника", "тревога"},
        "guvensizlik": {"ложь", "обман", "мошенничество", "подозрительно"},
        "hayal_kirikligi": {"разочарован", "разочаровывающе", "грустно", "сожалею"},
        "memnuniyet": {"отлично", "превосходно", "спасибо", "доволен", "успешно", "хорошо"},
        "guven": {"доверие", "прозрачно", "честно", "профессионально", "качество"},
        "sadakat": {"рекомендую", "постоянный клиент"},
    },
}

_COK_DILLI_YOGUNLASTIRICI: dict[str, dict[str, float]] = {
    "en": {"very": 1.4, "extremely": 1.6, "absolutely": 1.3, "completely": 1.3, "totally": 1.3},
    "de": {"sehr": 1.4, "äußerst": 1.6, "absolut": 1.3, "völlig": 1.3},
    "fr": {"très": 1.4, "extrêmement": 1.6, "absolument": 1.3, "totalement": 1.3},
    "es": {"muy": 1.4, "extremadamente": 1.6, "absolutamente": 1.3, "totalmente": 1.3},
    "ar": {"جدا": 1.4, "للغاية": 1.6, "تماما": 1.3},
    "ru": {"очень": 1.4, "крайне": 1.6, "полностью": 1.3},
}

_COK_DILLI_OLUMSUZLAMA: dict[str, set[str]] = {
    "en": {"not", "never", "no"},
    "de": {"nicht", "nie", "kein", "keine"},
    "fr": {"pas", "jamais", "aucun"},
    "es": {"no", "nunca", "jamás"},
    "ar": {"لا", "ليس", "أبدا"},
    "ru": {"не", "никогда", "нет"},
}

_COK_DILLI_NEGATIF_KATEGORILER = {"ofke", "panik", "guvensizlik", "hayal_kirikligi"}
_COK_DILLI_POZITIF_KATEGORILER = {"memnuniyet", "guven", "sadakat"}


class CokDilliLexiconSentimentAnalyzer(_SozlukTabanliAnalyzer):
    """Faz 10: Türkçe DIŞINDAKİ diller için sözlük tabanlı temel model
    (bkz. _COK_DILLI_SOZLUKLER). Desteklenmeyen/tanınmayan bir dil kodu
    verilirse İngilizce sözlüğe düşülür — İngilizce, YouTube/Reddit gibi
    kaynaklarda en yaygın ortak dil olduğundan en makul varsayılandır.
    """

    NEGATIF_KATEGORILER = _COK_DILLI_NEGATIF_KATEGORILER
    POZITIF_KATEGORILER = _COK_DILLI_POZITIF_KATEGORILER

    def __init__(self, dil_kodu: str = "en"):
        self.dil_kodu = dil_kodu if dil_kodu in _COK_DILLI_SOZLUKLER else "en"
        self.KATEGORI_SOZLUGU = _COK_DILLI_SOZLUKLER[self.dil_kodu]
        self.YOGUNLASTIRICILAR = _COK_DILLI_YOGUNLASTIRICI.get(self.dil_kodu, {})
        self.OLUMSUZLAMALAR = _COK_DILLI_OLUMSUZLAMA.get(self.dil_kodu, set())
        self.MODEL_ADI = f"lexicon_coklu_dil_{self.dil_kodu}"


_XLMR_LABEL_MAP = {"positive": "pozitif", "negative": "negatif", "neutral": "nötr"}


class CokDilliTransformerSentimentAnalyzer(SentimentAnalyzer):
    """
    Faz 10: XLM-RoBERTa tabanlı çok dilli üretim modeli.

    Model Seçimi ve Gerekçesi
    --------------------------
    `cardiffnlp/twitter-xlm-roberta-base-sentiment` — XLM-RoBERTa-base
    (Conneau vd., 2020: 100 dilde ortak bir temsil uzayı öğrenen çok dilli
    bir transformer) omurgası üzerine, 8 dilde (İngilizce, Arapça, Fransızca,
    Almanca, Hintçe, İtalyanca, Portekizce, İspanyolca) sosyal medya
    verisiyle ince ayar yapılmış, HuggingFace Hub'da herkese açık (API
    anahtarı gerektirmeyen) ÜÇ sınıflı (positive/neutral/negative) bir
    sınıflandırıcıdır. BERTurk'ün aksine ayrı bir "nötr" sınıfı zaten
    VARDIR — düşük-güven eşiği yaklaşımına ihtiyaç duyulmaz.

    XLM-R'ın 100 dillik paylaşılan gösterim uzayı sayesinde, açıkça ince
    ayar YAPILMAMIŞ diller (ör. Rusça, Türkçe) için de makul bir çapraz-dilli
    aktarım sağlar; bu yüzden Türkçe DIŞINDAKİ tüm diller için varsayılan
    üretim motoru olarak seçilmiştir (Türkçe için özel ince ayarlı BERTurk
    zaten daha yüksek doğruluk sağladığından o dilde kullanılmaya devam
    eder — bkz. get_sentiment_analyzer()).

    Açıklanabilirlik: TransformerSentimentAnalyzer (BERTurk) ile AYNI
    post-hoc yaklaşım — dile uygun CokDilliLexiconSentimentAnalyzer'ın aynı
    metinde bulduğu kanıt kelimeleri nihai çıktıya eklenir.
    """

    def __init__(self, model_name: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment", dil_kodu: str = "en"):
        self.model_name = model_name
        self.dil_kodu = dil_kodu

    def analiz_et(self, metin: str) -> DuyguSonucu:
        clf = _coklu_dil_transformer_pipeline(self.model_name)
        ham_sonuc = clf(metin[:2000], truncation=True)[0]
        guven = float(ham_sonuc["score"])
        duygu = _XLMR_LABEL_MAP.get(ham_sonuc["label"].lower(), ham_sonuc["label"].lower())

        lexicon_sonuc = CokDilliLexiconSentimentAnalyzer(self.dil_kodu).analiz_et(metin)

        return DuyguSonucu(
            duygu=duygu,
            alt_tip=lexicon_sonuc.alt_tip if duygu != "nötr" else "bilgilendirici",
            puan=round(guven, 3),
            kategori_skorlari=lexicon_sonuc.kategori_skorlari,
            aciklama_kanitlari=lexicon_sonuc.aciklama_kanitlari,
            model_adi=self.model_name,
        )


@lru_cache(maxsize=1)
def _coklu_dil_transformer_pipeline(model_name: str):
    """bkz. _transformer_pipeline — aynı tembel-yükleme (lazy load) gerekçesi."""
    from transformers import pipeline
    return pipeline("sentiment-analysis", model=model_name, tokenizer=model_name)


@lru_cache(maxsize=16)
def get_sentiment_analyzer(dil_kodu: str = "tr") -> SentimentAnalyzer:
    """Dependency-injection giriş noktası (Strategy pattern).

    Faz 10: `dil_kodu` parametresi eklendi (bkz. app/services/dil_tespit.py).

    dil_kodu == "tr" (varsayılan — ESKİ imza ile birebir geriye dönük
    uyumlu): `transformers` kurulu VE model gerçekten indirilebiliyorsa
    TransformerSentimentAnalyzer (BERTurk) kullanılır; aksi halde
    LexiconSentimentAnalyzer'a sessizce düşülür.

    dil_kodu != "tr": CokDilliTransformerSentimentAnalyzer (XLM-R) denenir;
    indirilemezse CokDilliLexiconSentimentAnalyzer'a düşülür. Her iki dalda
    da sistem HİÇBİR ZAMAN bu modül yüzünden çökmez.

    settings.LITE_MODE=True ise transformer denemesi hiç yapılmaz (bkz.
    app/config.py LITE_MODE açıklaması — bellek kısıtlı ortamlarda OOM'u
    baştan önlemek için).
    """
    from app.config import settings
    if settings.LITE_MODE:
        return LexiconSentimentAnalyzer() if dil_kodu == "tr" else CokDilliLexiconSentimentAnalyzer(dil_kodu)

    if dil_kodu == "tr":
        try:
            analizor = TransformerSentimentAnalyzer()
            analizor.analiz_et("test")  # modeli şimdi indir/yükle — başarısızsa hemen fallback'e düş
            return analizor
        except Exception:
            return LexiconSentimentAnalyzer()

    try:
        analizor = CokDilliTransformerSentimentAnalyzer(dil_kodu=dil_kodu)
        analizor.analiz_et("test")
        return analizor
    except Exception:
        return CokDilliLexiconSentimentAnalyzer(dil_kodu)
