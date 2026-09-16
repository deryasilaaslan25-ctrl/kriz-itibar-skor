"""
Bölüm 7: Konu Modelleme.

BERTopic, embedding modeli (BERTurk/Sentence-Transformers) ve HDBSCAN
kümeleme gerektirir; bu iki bağımlılık da GPU'suz/internetsiz ortamda
ağır ve tutarsız kurulum riski taşır. Bu modül, aynı ÇIKTI sözleşmesini
(bir metne konu etiketi atamak) sağlayan, anahtar kelime eşleştirmeli bir
temel sınıflandırıcı sunar. `TopicModel` arayüzü BERTopic'e geçişte API
tüketicilerini (frontend, risk skorlama motoru) etkilemeyecek şekilde
tasarlanmıştır.

Faz 3 güncellemesi (Document 121 s.4-5, Document 122: "5-6 etiketle
kalmasın ama literatüre dayalı olsun" talebi): Aşağıdaki ~20 kriz-türü
kategorisi SİLİNMEDİ — bunlar kullanıcının istediği geniş, isimlendirilmiş
taksonomiyi sağlar. Ancak artık her biri, app/services/absa.py'de tanımlanan
5 AKADEMİK ÜST-BOYUTTAN (Fombrun RepTrak × Parasuraman/Zeithaml/Berry
SERVQUAL) birine eşlenir (bkz. KONU_TO_ABSA_BOYUT) — böylece sistem hem
"5-6 etiketle sınırlı kalmıyor" hem de "tamamen literatüre dayalı" olma
gereksinimlerini AYNI ANDA karşılar: geniş taksonomi akademik üst-boyutların
ALT-TÜRLERİ olarak konumlanır.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

# Genişletilmiş kriz nedeni kategori kütüphanesi (Bölüm 7).
# Not: BERTopic/embedding tabanlı açık kümelemeye geçişte bu sözlük yalnızca
# "soğuk başlangıç" (cold-start) ve açıklanabilirlik referansı olarak kalmaya
# devam eder; get_topic_model() üretimde bu kütüphaneyi bir zero-shot/embedding
# sınıflandırıcıyla (ör. sentence-transformers tabanlı) değiştirebilecek şekilde
# soyutlanmıştır (bkz. TopicModel ABC). Kategori sayısı jüri eleştirisi üzerine
# 6'dan ~20'ye çıkarılmıştır; yeni bir kriz türü eklemek için tek yapılması
# gereken bu sözlüğe bir anahtar eklemektir — kod tabanının başka hiçbir
# yerinde değişiklik gerekmez.
KONU_ANAHTAR_KELIMELER = {
    "Fiyat Krizi": {"fiyat", "zam", "pahalı", "ücret", "fiyatlandırma", "zamlandı"},
    "Ürün Kalitesi Krizi": {"kalite", "bozuk", "arızalı", "hatalı", "kusurlu", "çürük", "son kullanma"},
    "CEO / Üst Yönetim Kaynaklı Kriz": {"ceo", "genel müdür", "yönetici", "patron", "yönetim kurulu"},
    "Boykot Çağrısı": {"boykot", "boykot ediyorum", "almayın", "destek olmayın", "boykota"},
    "Reklam / Kampanya Krizi": {"reklam", "kampanya", "afiş", "reklam filmi", "billboard"},
    "Veri İhlali / Siber Güvenlik Krizi": {"veri", "sızıntı", "hack", "şifre", "kvkk", "veri ihlali", "siber saldırı"},
    "Müşteri Hizmetleri Krizi": {"müşteri hizmetleri", "çağrı merkezi", "yanıt vermiyor", "iade", "cevap yok"},
    "Yeni Ürün / Lansman Tepkisi": {"yeni ürün", "lansman", "çıktı", "piyasaya sürüldü"},
    "Kurumsal Davranış / Etik Skandal": {"skandal", "yolsuzluk", "usulsüzlük", "etik", "rüşvet"},
    "Çalışan Hakları / İş Kazası Krizi": {"işçi", "grev", "iş kazası", "mobbing", "maaş ödenmedi", "sendika"},
    "Ürün Geri Çağırma Krizi": {"geri çağırma", "toplatıldı", "toplatma", "recall"},
    "Sahte Ürün / Taklit Krizi": {"taklit", "sahte ürün", "orijinal değil", "kopya"},
    "Lojistik / Teslimat Krizi": {"kargo", "teslimat", "gecikme", "sipariş gelmedi", "elime ulaşmadı"},
    "Çevre / Sürdürülebilirlik Krizi": {"çevre kirliliği", "karbon", "atık", "sürdürülebilirlik", "ekolojik"},
    "Ayrımcılık / Nefret Söylemi İddiası": {"ayrımcılık", "ırkçı", "cinsiyetçi", "nefret söylemi", "dışlayıcı"},
    "Siyasi / Toplumsal Tartışma Krizi": {"siyasi", "toplumsal", "protesto", "tartışma yarattı"},
    "Influencer / Marka Elçisi Krizi": {"influencer", "marka elçisi", "sponsorlu içerik", "reklamı yapan"},
    "Rakip Kaynaklı / Kıyaslama Krizi": {"rakip", "kıyaslandı", "karşılaştırma", "diss"},
    "Yasal Süreç / Denetim Krizi": {"dava", "mahkeme", "soruşturma", "ceza kesildi", "denetim"},
    "Doğal Afet / Mücbir Sebep": {"deprem", "sel", "yangın", "doğal afet", "mücbir sebep"},
    "Genel": set(),  # eşleşme bulunamazsa varsayılan; insan incelemesi önerilir
}

# Her alt-tür kategorinin hangi akademik üst-boyuta (absa.py ABSA_BOYUTLARI
# anahtarlarından biri) ait olduğunu belirtir. Eşleme gerekçesi (Document 121
# s.4-5'teki taksonomik eşlemeyle birebir):
#   - urun_hizmet_degeri  <- ürünün kendisiyle/fiziksel teslimiyle ilgili krizler
#   - yanit_verebilirlik  <- kurumun tepki/iletişim SÜRECİYLE ilgili krizler
#   - inovasyon           <- yeni ürün/lansman algısı
#   - yonetisim_etik      <- şeffaflık, hukuk, etik, güvenlik/mahremiyet, siyaset
#   - sosyal_sorumluluk   <- çevre, toplum, ayrımcılık, doğal afet/mücbir sebep
KONU_TO_ABSA_BOYUT: dict[str, str] = {
    "Fiyat Krizi": "yonetisim_etik",
    "Ürün Kalitesi Krizi": "urun_hizmet_degeri",
    "CEO / Üst Yönetim Kaynaklı Kriz": "yonetisim_etik",
    "Boykot Çağrısı": "yonetisim_etik",
    "Reklam / Kampanya Krizi": "inovasyon",
    "Veri İhlali / Siber Güvenlik Krizi": "yonetisim_etik",
    "Müşteri Hizmetleri Krizi": "yanit_verebilirlik",
    "Yeni Ürün / Lansman Tepkisi": "inovasyon",
    "Kurumsal Davranış / Etik Skandal": "yonetisim_etik",
    "Çalışan Hakları / İş Kazası Krizi": "sosyal_sorumluluk",
    "Ürün Geri Çağırma Krizi": "urun_hizmet_degeri",
    "Sahte Ürün / Taklit Krizi": "urun_hizmet_degeri",
    "Lojistik / Teslimat Krizi": "yanit_verebilirlik",
    "Çevre / Sürdürülebilirlik Krizi": "sosyal_sorumluluk",
    "Ayrımcılık / Nefret Söylemi İddiası": "sosyal_sorumluluk",
    "Siyasi / Toplumsal Tartışma Krizi": "sosyal_sorumluluk",
    "Influencer / Marka Elçisi Krizi": "inovasyon",
    "Rakip Kaynaklı / Kıyaslama Krizi": "yonetisim_etik",
    "Yasal Süreç / Denetim Krizi": "yonetisim_etik",
    "Doğal Afet / Mücbir Sebep": "sosyal_sorumluluk",
    "Genel": "yonetisim_etik",  # sınıflandırılamayan sinyaller varsayılan olarak "insan incelemesi" gerektiren yönetişim boyutuna düşer
}


class TopicModel(ABC):
    @abstractmethod
    def konu_belirle(self, metin: str) -> str: ...


class KeywordTopicModel(TopicModel):
    def konu_belirle(self, metin: str) -> str:
        metin_lower = metin.lower()
        en_iyi_konu, en_iyi_skor = "Genel", 0
        for konu, kelimeler in KONU_ANAHTAR_KELIMELER.items():
            skor = sum(1 for k in kelimeler if k in metin_lower)
            if skor > en_iyi_skor:
                en_iyi_konu, en_iyi_skor = konu, skor
        return en_iyi_konu


def boyut_belirle(konu: str) -> str:
    """Bir alt-tür kriz kategorisini 5 akademik ABSA üst-boyutundan birine eşler."""
    return KONU_TO_ABSA_BOYUT.get(konu, "yonetisim_etik")


def get_topic_model() -> TopicModel:
    return KeywordTopicModel()
