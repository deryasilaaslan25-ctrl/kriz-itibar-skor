"""
Bölüm 8-9: LLM Entegrasyonu ve Hibrit SCCT (Situational Crisis Communication
Theory) Karar Motoru.

2. juri eleştirisi doğrudan şunu talep etmektedir: sistem yalnızca "Risk var"
dememeli, "Kurum ne yapmalı?" sorusuna da cevap verebilmelidir. Bu modül üç
katmanlı bir hibrit yapı sunar (Bölüm 9: "Rule Based + LLM + Makine
Öğrenmesi hibrit yapı önerilmektedir"):

  1) Rule-Based SCCT Katmanı (SCCTKuralMotoru): Coombs'un SCCT çerçevesine
     (Coombs, 2007) dayanan, kriz tipi + atfedilen sorumluluk seviyesine göre
     önerilen iletişim stratejisini (inkar, küçültme, yeniden inşa, güçlendirme)
     belirleyen deterministik, açıklanabilir ve anında çalışan bir katman.
     İnternet/API anahtarı gerektirmez, jüri demosunda her zaman çalışır.

  2) ML Katmanı (risk_scoring.py + xgboost_classifier.py çıktısı): Hangi
     bileşenlerin (bot aktivitesi, sahte haber riski, coğrafi yayılım vb.)
     baskın olduğunu belirleyerek kural motoruna "aciliyet" ve "gerçeklik
     olasılığı" sinyali sağlar.

  3) LLM Katmanı (LLMOneriMotoru): Anthropic API'si (bkz. .env ANTHROPIC_API_KEY)
     üzerinden, rule-based çıktı + risk bileşenleri prompt'a enjekte edilerek
     doğal dilde, kuruma özel, gerekçelendirilmiş bir eylem planı üretir.
     API anahtarı tanımlı değilse bu katman devre dışı kalır ve sistem yalnızca
     1. ve 2. katmanların ürettiği yapılandırılmış öneriyle çalışmaya devam
     eder (graceful degradation — sistem asla LLM'e sıkı bağımlı değildir).

Bu tasarım "LLM olmadan sistem çalışmaz" kırılganlığından kaçınır ve jüriye
hem çalışan bir demo hem de üretim yolunda net bir mühendislik planı sunar.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SorumlulukSeviyesi(str, Enum):
    DUSUK = "dusuk"      # kurban krizi (örn. doğal afet, sabotaj)
    ORTA = "orta"         # kaza krizi (örn. ürün hatası, teknik arıza)
    YUKSEK = "yuksek"     # önlenebilir kriz (örn. kurumsal ihmal, skandal)


class SCCTStratejisi(str, Enum):
    """Coombs'un (2007) SCCT çerçevesindeki 4 temel duruş (posture) — orijinal
    enum isimleri geriye dönük uyumluluk için AYNEN korunmuştur (mevcut testler
    ve routes_krizler.py bu değerlere göre çalışır) — artı Document 121'in
    eklediği 2 çağdaş/tamamlayıcı duruş. Her duruşun ALTINDA, hangi SOMUT
    taktiğin (18'den biri, bkz. SCCTAltTaktik) uygulanacağı `spesifik_strateji`
    alanında ayrıca raporlanır."""
    INKAR = "inkar"                       # A. Deny Posture
    KUCULTME = "kucultme"                 # B. Evasion & Diminish Posture
    YENIDEN_INSA = "yeniden_insa"          # C. Rebuild & Mortification Posture
    GUCLENDIRME = "guclendirme"            # E. Bolstering Posture
    CERCEVELEME = "cerceveleme"            # D. Reducing Offensiveness & Reframing (YENİ)
    PROAKTIF = "proaktif"                  # F. Çağdaş / Proaktif İletişim Stratejileri (YENİ)


class SCCTAltTaktik(str, Enum):
    """Document 121 s.6-8'deki TAM 18 akademik kriz iletişimi alt-taktiği.

    NEDEN 18? (API'de metodoloji_notu alanında da kullanıcıya sunulur):
    Coombs'un (2007) SCCT'sindeki 4 temel duruşun altına, halkla ilişkiler
    literatüründe en sık atıfta bulunulan somut alt-taktikler yerleştirilir:
    A. İnkâr (3 taktik) + B. Kaçınma/Küçültme (5 taktik, Benoit 1997 İmaj
    Onarım Teorisi'nden) + C. Yeniden İnşa (3 taktik, Hearit Apologia
    teorisiyle derinleştirilmiş) + E. Destekleme (3 taktik) = 14 klasik SCCT
    alt-taktiği. Buna, Document 121'in çağdaş literatürden eklediği D.
    Çerçeveleme (2 taktik) ve F. Proaktif İletişim (2 taktik, ör. Arpan &
    Roskos-Ewoldsen 2005 "Stealing Thunder" bulgusu) katılır: 14+2+2 = 18.
    Bu sayı keyfi değildir — 3 temel akademik kaynağın (Coombs/SCCT,
    Benoit/IRT, Hearit/Apologia) standart taktik kümelerinin birleşimidir
    (tam kaynakça: CITATIONS.md).
    """
    # A. İnkâr Duruşu Stratejileri (Deny Posture)
    DOGRUDAN_INKAR = "dogrudan_inkar"
    SUCLAYANA_SALDIRMA = "suclayana_saldirma"
    GUNAH_KECISI = "gunah_kecisi"
    # B. Sorumluluktan Kaçınma ve Azaltma Stratejileri (Evasion & Diminish)
    MAZERET = "mazeret"
    KAZA_ACIKLAMASI = "kaza_aciklamasi"
    KISKIRTMA = "kiskirtma"
    IYI_NIYET = "iyi_niyet"
    GEREKCELENDIRME = "gerekcelendirme"
    # C. Yeniden İnşa ve Onarım Stratejileri (Rebuild & Mortification)
    TAM_OZUR = "tam_ozur"
    DUZELTICI_EYLEM = "duzeltici_eylem"
    TAZMINAT = "tazminat"
    # D. Algı ve Çerçeveleme Stratejileri (Reframing)
    FARKLILASTIRMA = "farklilastirma"
    ASKINLASMA = "askinlasma"
    # E. Destekleme ve Algı Takviyesi Stratejileri (Bolstering)
    HATIRLATMA = "hatirlatma"
    OVGU_TESEKKUR = "ovgu_tesekkur"
    KURBAN_ROLU = "kurban_rolu"
    # F. Çağdaş / Proaktif İletişim Stratejileri
    YILDIRIMI_CALMA = "yildirimi_calma"
    STRATEJIK_SESSIZLIK = "stratejik_sessizlik"


@dataclass(frozen=True)
class AltTaktikBilgisi:
    ad: str
    durus: SCCTStratejisi
    akademik_kaynak: str
    aciklama: str


# Document 121 s.6-8 ile birebir: her alt-taktiğin adı, ait olduğu duruş ve
# akademik kaynağı. API yanıtında `spesifik_strateji_detay` alanı bu tablodan
# doldurulur — kullanıcı "bu kategoriler nereden geldi?" sorusunu API
# yanıtından doğrudan görebilir.
ALT_TAKTIK_BILGISI: dict[SCCTAltTaktik, AltTaktikBilgisi] = {
    SCCTAltTaktik.DOGRUDAN_INKAR: AltTaktikBilgisi(
        "Doğrudan İnkâr (Simple Denial)", SCCTStratejisi.INKAR, "Coombs (2007) SCCT",
        "Kurumun kriz konusu eylemle hiçbir bağının bulunmadığını kesin verilerle ilan etmesi."),
    SCCTAltTaktik.SUCLAYANA_SALDIRMA: AltTaktikBilgisi(
        "Suçlayana Saldırma (Attack the Accuser)", SCCTStratejisi.INKAR, "Coombs (2007) SCCT",
        "İddia sahibinin (medya, rakip, anonim hesap) manipülatif/asılsız beyanlarını kanıtla çürütmesi."),
    SCCTAltTaktik.GUNAH_KECISI: AltTaktikBilgisi(
        "Günah Keçisi İlan Etme (Scapegoating)", SCCTStratejisi.INKAR, "Coombs (2007) SCCT",
        "İhlalin üçüncü bir taraftan (tedarikçi, alt yüklenici) kaynaklandığını belgeleyerek sorumluluğu devretmesi."),
    SCCTAltTaktik.MAZERET: AltTaktikBilgisi(
        "Mazeret Gösterme (Excuse / Defeasibility)", SCCTStratejisi.KUCULTME, "Benoit (1997) İmaj Onarım Teorisi",
        "Kurumun niyetsizliğini veya olayı kontrol etme yetkisinin kısıtlı olduğunu savunması."),
    SCCTAltTaktik.KAZA_ACIKLAMASI: AltTaktikBilgisi(
        "Kaza Açıklaması (Accident)", SCCTStratejisi.KUCULTME, "Coombs (2007) SCCT",
        "Eylemin kontrol dışı çevresel/sistemsel bir kaza sonucunda meydana geldiğini açıklaması."),
    SCCTAltTaktik.KISKIRTMA: AltTaktikBilgisi(
        "Kışkırtma / Zorunlu Tepki (Provocation)", SCCTStratejisi.KUCULTME, "Benoit (1997) İmaj Onarım Teorisi",
        "Kurum eyleminin başka bir haksız dış müdahaleye zorunlu bir yanıt olduğunu belirtmesi."),
    SCCTAltTaktik.IYI_NIYET: AltTaktikBilgisi(
        "İyi Niyet Beyanı (Good Intentions)", SCCTStratejisi.KUCULTME, "Benoit (1997) İmaj Onarım Teorisi",
        "Eylemin iyi niyetli bir hedefle başlatıldığını ancak öngörülemeyen yan etkiler doğurduğunu ifade etmesi."),
    SCCTAltTaktik.GEREKCELENDIRME: AltTaktikBilgisi(
        "Gerekçelendirme ve Önemsizleştirme (Justification)", SCCTStratejisi.KUCULTME, "Coombs (2007) SCCT",
        "Olayı kabul edip, algılandığı kadar büyük bir zarar doğurmadığını verilerle açıklaması."),
    SCCTAltTaktik.TAM_OZUR: AltTaktikBilgisi(
        "Tam Özür ve Pişmanlık (Full Mortification)", SCCTStratejisi.YENIDEN_INSA, "Coombs (2007) SCCT; Hearit Apologia Teorisi",
        "Kurumun hatasını tamamen kabul ederek resmi ve samimi özür dilemesi."),
    SCCTAltTaktik.DUZELTICI_EYLEM: AltTaktikBilgisi(
        "Düzeltici Eylem (Corrective Action)", SCCTStratejisi.YENIDEN_INSA, "Coombs (2007) SCCT",
        "Sorunun kök nedenini çözmek için başlatılan sistemsel/idari reformları ilan etmesi."),
    SCCTAltTaktik.TAZMINAT: AltTaktikBilgisi(
        "Tazminat ve Telafi (Compensation)", SCCTStratejisi.YENIDEN_INSA, "Coombs (2007) SCCT",
        "Mağdur tarafların maddi/manevi zararlarını koşulsuz karşılaması."),
    SCCTAltTaktik.FARKLILASTIRMA: AltTaktikBilgisi(
        "Farklılaştırma (Differentiation)", SCCTStratejisi.CERCEVELEME, "Benoit (1997) İmaj Onarım Teorisi",
        "Kurum eylemini emsal çok daha ağır krizlerle kıyaslayarak olayın kriz niteliğini göreceli hafifletmesi."),
    SCCTAltTaktik.ASKINLASMA: AltTaktikBilgisi(
        "Aşkınlaşma / Üst Çerçeveleme (Transcendence)", SCCTStratejisi.CERCEVELEME, "Benoit (1997) İmaj Onarım Teorisi",
        "Eylemi daha yüksek/uzun vadeli kurumsal-toplumsal amaçlarla ilişkilendirmesi."),
    SCCTAltTaktik.HATIRLATMA: AltTaktikBilgisi(
        "Geçmiş Başarıları Hatırlatma (Reminding)", SCCTStratejisi.GUCLENDIRME, "Coombs (2007) SCCT",
        "Kurumun geçmiş kalite standartlarını ve başarılarını vurgulayarak krizin bir istisna olduğunu göstermesi."),
    SCCTAltTaktik.OVGU_TESEKKUR: AltTaktikBilgisi(
        "Övgü ve Teşekkür (Ingratiation)", SCCTStratejisi.GUCLENDIRME, "Coombs (2007) SCCT",
        "Kriz sürecinde yapıcı kalan paydaşlara/sadık müşterilere kamuoyu önünde teşekkür etmesi."),
    SCCTAltTaktik.KURBAN_ROLU: AltTaktikBilgisi(
        "Kurban Rolü (Victimage)", SCCTStratejisi.GUCLENDIRME, "Coombs (2007) SCCT",
        "Kurumun krizde kendisinin de doğrudan bir mağdur (siber saldırı, şantaj, sabotaj) olduğunu ortaya koyması."),
    SCCTAltTaktik.YILDIRIMI_CALMA: AltTaktikBilgisi(
        "Yıldırımı Çalma (Stealing Thunder)", SCCTStratejisi.PROAKTIF, "Arpan & Roskos-Ewoldsen (2005)",
        "Kriz medyaya sızmadan önce kurumun sorunu ilk kendisinin kamuoyuna duyurması "
        "(bu çalışmaya göre itibar kaybını >%50 azaltır) — erken uyarı sisteminin ASIL amacıyla doğrudan örtüşür."),
    SCCTAltTaktik.STRATEJIK_SESSIZLIK: AltTaktikBilgisi(
        "Stratejik Sessizlik / Bekle-Gör (Strategic Silence)", SCCTStratejisi.PROAKTIF, "Coombs (2007) SCCT",
        "Kriz şiddeti kritik eşiğin altındaysa, asılsız dedikodunun yayılma ivmesini beslememek için izleme modunda kalma."),
}


@dataclass
class SCCTOnerisi:
    strateji: SCCTStratejisi
    sorumluluk_seviyesi: SorumlulukSeviyesi
    ilk_mudahale_suresi_saat: int
    gerekce: str
    somut_adimlar: list[str] = field(default_factory=list)
    llm_destekli: bool = False
    llm_metni: str | None = None
    # Faz 5 eklentisi: 18 taktikten BİRİNCİL seçilen somut taktik + 1-2
    # alternatif (frontend'deki "Alternatif Taslak Göster (1/3)" döngüsüyle
    # birebir uyumlu — toplam 3 taslak: birincil + 2 alternatif).
    spesifik_strateji: SCCTAltTaktik | None = None
    alternatif_stratejiler: list[SCCTAltTaktik] = field(default_factory=list)
    metodoloji_notu: str = (
        "18 alt-taktik, Coombs (2007) SCCT'nin 4 temel duruşu altındaki 14 "
        "klasik taktik + Document 121'in eklediği 2 çağdaş duruştaki "
        "(Çerçeveleme, Proaktif) 4 taktiğin toplamıdır (14+2+2=18). Her "
        "taktiğin akademik kaynağı ALT_TAKTIK_BILGISI tablosunda ayrı ayrı "
        "belgelenmiştir (bkz. CITATIONS.md)."
    )


class SCCTKuralMotoru:
    """Coombs SCCT çerçevesine dayalı deterministik strateji seçimi.

    Girdi: risk_scoring.hesapla() çıktısındaki bilesenler + sorumluluk_seviyesi
    (kurum tarafından ya da bot/anahtar-kelime sinyallerinden kabaca çıkarsanır).
    """

    def strateji_belirle(
        self,
        toplam_risk_skoru: float,
        sorumluluk_seviyesi: SorumlulukSeviyesi,
        bot_aktivitesi_baskin: bool,
        sahte_haber_riski_yuksek: bool,
        kriz_siddet_ivmesi: float = 0.0,
        gecmis_itibar_trendi: float = 0.0,
    ) -> SCCTOnerisi:
        """Birincil duruş (4+2 kümeden biri) + 18 taktikten spesifik seçim.

        Yeni (opsiyonel, geriye dönük uyumlu) parametreler:
          kriz_siddet_ivmesi: dE/dt normalize [0,1] — risk_scoring.py'nin
            "yayilma_ivmesi" sinyaliyle aynı; ne kadar HIZLI büyüdüğünü belirtir.
          gecmis_itibar_trendi: itibar_skoru.py çıktısının son N ölçümdeki
            eğilimi, [-1,1] — pozitifse kurumun birikmiş itibar sermayesi var
            demektir (Fombrun'un "reputation capital" kavramı — GUCLENDIRME
            kümesinde HATIRLATMA taktiğinin ne kadar inandırıcı olacağını etkiler).
        """
        # Sahte haber / koordineli bot saldırısı => önce "inkâr" duruşu,
        # gerçek bir kurumsal hata değil bilgi kirliliği olduğu için farklı ele alınır.
        if bot_aktivitesi_baskin and sahte_haber_riski_yuksek:
            oneri = SCCTOnerisi(
                strateji=SCCTStratejisi.INKAR,
                sorumluluk_seviyesi=sorumluluk_seviyesi,
                ilk_mudahale_suresi_saat=2,
                gerekce=(
                    "Baskın sinyaller bot aktivitesi ve sahte haber riski; bu krizin "
                    "gerçek bir kurumsal hatadan değil koordineli bilgi kirliliğinden "
                    "kaynaklanma olasılığı yüksek. SCCT 'inkâr' duruşu önerilir: "
                    "gerçek dışı iddiaların kanıtla çürütülmesi."
                ),
                somut_adimlar=[
                    "Fact-check ekibi ile iddiaların doğruluğu 2 saat içinde teyit edilmeli",
                    "Kanıta dayalı düzeltme metni yayınlanmalı (kaynak, tarih, veri ile)",
                    "Platformlara koordineli/bot davranış raporu iletilmeli",
                ],
                spesifik_strateji=SCCTAltTaktik.SUCLAYANA_SALDIRMA,
                alternatif_stratejiler=[SCCTAltTaktik.DOGRUDAN_INKAR, SCCTAltTaktik.GUNAH_KECISI],
            )
            return self._proaktif_alternatif_ekle(oneri, toplam_risk_skoru)

        if sorumluluk_seviyesi == SorumlulukSeviyesi.YUKSEK or toplam_risk_skoru > 75:
            # Şiddet ivmesi yüksekse (hızla büyüyor) tam özür daha güçlü tercih edilir;
            # ivme düşükse (yavaş/duraylı) önce düzeltici eylemle başlanabilir.
            birincil = SCCTAltTaktik.TAM_OZUR if kriz_siddet_ivmesi >= 0.5 else SCCTAltTaktik.DUZELTICI_EYLEM
            alternatifler = [t for t in (SCCTAltTaktik.DUZELTICI_EYLEM, SCCTAltTaktik.TAZMINAT, SCCTAltTaktik.TAM_OZUR) if t != birincil][:2]
            oneri = SCCTOnerisi(
                strateji=SCCTStratejisi.YENIDEN_INSA,
                sorumluluk_seviyesi=sorumluluk_seviyesi,
                ilk_mudahale_suresi_saat=6,
                gerekce=(
                    "Yüksek/kritik risk skoru ve yüksek atfedilen sorumluluk seviyesi "
                    "birlikte gözlemlendi. SCCT literatürüne göre bu kombinasyonda en "
                    "uygun duruş 'yeniden inşa' (özür + telafi)dir."
                ),
                somut_adimlar=[
                    "İlk 6 saat içinde resmi açıklama yapılmalı",
                    "CEO/üst yönetim düzeyinde açıklama tavsiye edilir",
                    "Somut telafi/tazmin planı eş zamanlı duyurulmalı",
                    "Reklam/pazarlama içerikleri geçici olarak durdurulmalı",
                    "Kriz konusuyla ilgisiz hashtag kampanyaları başlatılmamalı",
                ],
                spesifik_strateji=birincil,
                alternatif_stratejiler=alternatifler,
            )
            return self._proaktif_alternatif_ekle(oneri, toplam_risk_skoru)

        if sorumluluk_seviyesi == SorumlulukSeviyesi.ORTA or toplam_risk_skoru > 50:
            oneri = SCCTOnerisi(
                strateji=SCCTStratejisi.KUCULTME,
                sorumluluk_seviyesi=sorumluluk_seviyesi,
                ilk_mudahale_suresi_saat=12,
                gerekce=(
                    "Orta düzey sorumluluk/risk. SCCT 'küçültme' duruşu: olayın "
                    "gerekçelendirilmesi ve etkisinin orantılı biçimde ele alınması."
                ),
                somut_adimlar=[
                    "12 saat içinde açıklayıcı (gerekçelendirici) bir bildirim yayınlanmalı",
                    "Teknik/operasyonel düzeltme adımları şeffaf biçimde paylaşılmalı",
                ],
                spesifik_strateji=SCCTAltTaktik.GEREKCELENDIRME,
                alternatif_stratejiler=[SCCTAltTaktik.MAZERET, SCCTAltTaktik.KAZA_ACIKLAMASI],
            )
            return self._proaktif_alternatif_ekle(oneri, toplam_risk_skoru)
        # (aşağıdaki düşük risk/sorumluluk dalı zaten <75 aralığındadır ama
        # GUCLENDIRME kümesi kendi proaktif alternatifini -- STRATEJIK_SESSIZLIK
        # -- doğrudan içerdiği için _proaktif_alternatif_ekle'ye ihtiyaç duymaz.)

        # Düşük risk/sorumluluk: kurumun geçmiş itibar sermayesi pozitifse
        # HATIRLATMA taktiği daha güçlü bir seçimdir (Fombrun'un "reputation
        # capital" kavramı — kriz anında geçmiş başarı biriktirmemiş bir
        # kurum için "hatırlatma" inandırıcı olmaz).
        birincil = SCCTAltTaktik.HATIRLATMA if gecmis_itibar_trendi >= 0 else SCCTAltTaktik.STRATEJIK_SESSIZLIK
        oneri = SCCTOnerisi(
            strateji=SCCTStratejisi.GUCLENDIRME,
            sorumluluk_seviyesi=sorumluluk_seviyesi,
            ilk_mudahale_suresi_saat=24,
            gerekce="Düşük risk/sorumluluk. Aktif müdahaleden çok izleme ve güçlendirme yeterli.",
            somut_adimlar=[
                "Kriz izlemeye devam edilmeli, aktif açıklama gerekmiyor",
                "Kurumun mevcut olumlu itibar sermayesi hatırlatılabilir",
            ],
            spesifik_strateji=birincil,
            alternatif_stratejiler=[SCCTAltTaktik.OVGU_TESEKKUR, SCCTAltTaktik.STRATEJIK_SESSIZLIK],
        )
        return oneri

    @staticmethod
    def _proaktif_alternatif_ekle(oneri: SCCTOnerisi, toplam_risk_skoru: float) -> SCCTOnerisi:
        """Arpan & Roskos-Ewoldsen (2005) 'Stealing Thunder' bulgusu: kriz henüz
        KRİTİK eşiğe (>75) ulaşmadıysa, kurumun sorunu ilk kendisinin açıklaması
        (proaktif) HER ZAMAN değerlendirilmeye değer bir alternatiftir — bu
        sistemin erken uyarı misyonuyla doğrudan örtüşür. Kritik eşik üzerinde
        (kriz zaten kamuoyuna yayılmış olma ihtimali yüksek) bu artık gerçekçi
        bir seçenek olmadığından eklenmez."""
        if toplam_risk_skoru < 75 and SCCTAltTaktik.YILDIRIMI_CALMA not in oneri.alternatif_stratejiler:
            # [-2:] (SON iki eleman) kullanılır — [:2] kullanılsaydı yeni eklenen
            # YILDIRIMI_CALMA listenin sonuna eklenip hemen ardından kırpma ile
            # kaybolurdu (bu, gerçek bir regresyon olarak test yazılırken yakalandı).
            oneri.alternatif_stratejiler = (oneri.alternatif_stratejiler + [SCCTAltTaktik.YILDIRIMI_CALMA])[-2:]
        return oneri


class LLMOneriMotoru:
    """Rule-based SCCT çıktısını doğal dile döken, opsiyonel LLM katmanı.

    ANTHROPIC_API_KEY .env içinde tanımlıysa gerçek API çağrısı yapılabilir
    (bkz. app/config.py). Tanımlı değilse yapılandırılmış rule-based öneri
    (SCCTOnerisi) tek başına, LLM metni olmadan döndürülür — sistem asla
    dışa bağımlı bir bileşen olmadan çalışmayı durdurmaz.
    """

    # Bölüm 9 güncelleme: sistem artık kendini açıkça "kıdemli bir kurumsal
    # halkla ilişkiler danışmanı" olarak konumlandırır — çıktının tonu ve
    # yapısı buna göre profesyonelleştirilmiştir (bkz. ANTHROPIC_MODEL).
    SYSTEM_PROMPT = (
        "Sen 20 yıllık deneyime sahip, kriz iletişimi alanında uzmanlaşmış "
        "kıdemli bir kurumsal halkla ilişkiler danışmanısın. Bir yönetim "
        "kuruluna veya CEO'ya doğrudan brifing verir gibi yaz: net, kararlı, "
        "somut ve savunulabilir. Sana bir risk skoru, bu skorun bileşen "
        "bazlı açıklaması ve SCCT (Coombs, 2007) tabanlı önerilen strateji "
        "verilecek. Görevin, bu yapılandırılmış veriyi kurum yöneticisinin "
        "5 dakikada okuyup uygulayabileceği, somut, profesyonel ve yayına "
        "hazır kalitede bir eylem planına çevirmek. Spekülasyon yapma, "
        "sadece verilen veriye dayan; belirsizliği açıkça belirt. Türkçe "
        "yanıt ver."
    )

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    def aktif_mi(self) -> bool:
        return bool(self.api_key)

    def oneri_uret(self, oneri: SCCTOnerisi, bilesenler: dict[str, float]) -> SCCTOnerisi:
        if not self.aktif_mi():
            # Graceful degradation: LLM yok, rule-based öneri olduğu gibi döner.
            return oneri

        import httpx

        try:
            yanit = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 700,
                    "system": self.SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": (
                        f"Strateji: {oneri.strateji.value}\n"
                        f"Sorumluluk seviyesi: {oneri.sorumluluk_seviyesi.value}\n"
                        f"Risk bileşenleri: {bilesenler}\n"
                        f"Rule-based gerekçe: {oneri.gerekce}\n"
                        f"Rule-based somut adımlar: {oneri.somut_adimlar}"
                    )}],
                },
                timeout=30.0,
            )
            yanit.raise_for_status()
            veri = yanit.json()
            oneri.llm_metni = "".join(
                blok.get("text", "") for blok in veri.get("content", []) if blok.get("type") == "text"
            ).strip() or None
            oneri.llm_destekli = oneri.llm_metni is not None
        except Exception:
            # Graceful degradation: API çağrısı başarısız olsa dahi (ağ hatası,
            # geçersiz anahtar, zaman aşımı) sistem rule-based öneriyle çalışmaya
            # devam eder — LLM'e sıkı bağımlılık yoktur.
            oneri.llm_destekli = False
            oneri.llm_metni = None
        return oneri


# ---------------------------------------------------------------------------
# Geçmiş Kriz Analizi Motoru — "Yapay Zeka Halkla İlişkiler Danışmanı" eklentisi
# ---------------------------------------------------------------------------
# Kullanıcı talebi: aktif bir kriz raporlanırken, kurumun (veya genel olarak
# ilgili sektörün) son 10 yıl içinde benzer nitelikte bir krizle karşılaşıp
# karşılaşmadığını tarayan, tarihi (kesin değilse "Eylül 2019 civarında" gibi
# yaklaşık bir dönem olarak) ve o dönemki tutumu/sonucu özetleyen, buna göre
# şimdiki krize dair somut tavsiye üreten bir katman. Üç katmanlı hibrit
# tasarım burada da korunur:
#   1) Rule-based şablon kütüphanesi (GECMIS_KRIZ_SABLONLARI): API anahtarı
#      yokken bile çalışan, sektöre/konuya göre kategorize edilmiş, ANONİM/
#      jenerik emsal olay örüntüleridir (gerçek bir marka adına atfedilmiş
#      doğrulanmamış iddia ÜRETMEMEK için bilinçli olarak marka-agnostiktir).
#   2) LLM katmanı: ANTHROPIC_API_KEY tanımlıysa, gerçek geçmiş vakaları
#      araştırması için Anthropic API'sine (mümkünse web search tool ile)
#      istek gönderir.
#   3) Sonuç her zaman "insan onayı/doğrulaması gerekir" notuyla sunulur.
from app.schemas.schemas import GecmisKrizOrnegi, GecmisKrizAnaliziCikti  # noqa: E402

GECMIS_KRIZ_SABLONLARI: dict[str, list[dict]] = {
    "Ürün Kalitesi Krizi": [
        {"ozet": "Sektörde bir üreticinin ürün parti hatası nedeniyle şikâyet dalgasıyla karşılaştığı, önce sessiz kaldığı sonra geri çağırma ile ilerlediği bir örüntü.", "kurumun_tutumu": "İlk 48 saatte sessiz kalındı, ardından kısmi özür ve iade kampanyası başlatıldı.", "sonuc": "Gecikmeli açıklama itibar kaybını uzattı; hızlı hareket eden benzer vakalarda kayıp çok daha sınırlı kalmıştır.", "basari_durumu": "olumsuz_yonetildi", "ay_araligi": (0, 11)},
        {"ozet": "Bir başka kurumun benzer kalite şikâyetinde ilk 12 saat içinde şeffaf açıklama yapıp bağımsız denetim çağrısında bulunduğu örnek.", "kurumun_tutumu": "Hızlı, şeffaf açıklama + bağımsız laboratuvar sonucu paylaşımı.", "sonuc": "İtibar skoru 2 hafta içinde kriz öncesi seviyeye yakın toparlandı.", "basari_durumu": "olumlu_yonetildi", "ay_araligi": (0, 11)},
    ],
    "Müşteri Hizmetleri Krizi": [
        {"ozet": "Yoğun şikâyet döneminde çağrı merkezi kapasitesinin yetersiz kalmasıyla oluşan güven kaybı örüntüsü.", "kurumun_tutumu": "Kapasite artışı duyurulmadan sessiz sayıda personel eklendi.", "sonuc": "Şikâyet hacmi yavaş düştü, kamuoyu algısı iyileşmesi 3-4 hafta sürdü.", "basari_durumu": "karisik", "ay_araligi": (2, 9)},
        {"ozet": "Benzer bir müşteri hizmetleri krizinde kurumun süreci kamuoyuna açık şekilde raporladığı, düzenli güncelleme paylaştığı örnek.", "kurumun_tutumu": "Haftalık şeffaf ilerleme raporu + telafi programı.", "sonuc": "Müşteri memnuniyeti krizden güçlenerek çıktı.", "basari_durumu": "olumlu_yonetildi", "ay_araligi": (2, 9)},
    ],
    "Veri İhlali / Siber Güvenlik Krizi": [
        {"ozet": "Bir kurumun veri ihlalini geç açıklaması nedeniyle düzenleyici kurum incelemesiyle karşılaştığı örüntü.", "kurumun_tutumu": "Açıklama gecikti, ilk bilgilendirme eksik/yetersizdi.", "sonuc": "KVKK/GDPR benzeri düzenleyici para cezası + uzun süreli güven kaybı.", "basari_durumu": "olumsuz_yonetildi", "ay_araligi": (1, 10)},
        {"ozet": "Aynı sektörde bir kurumun ihlali tespit eder etmez şeffaf açıklama yapıp ücretsiz kredi izleme/güvenlik desteği sunduğu örnek.", "kurumun_tutumu": "24 saat içinde açıklama + somut telafi paketi.", "sonuc": "Düzenleyici müeyyide sınırlı kaldı, marka güveni büyük ölçüde korundu.", "basari_durumu": "olumlu_yonetildi", "ay_araligi": (1, 10)},
    ],
    "Boykot Çağrısı": [
        {"ozet": "Sosyal medya kaynaklı bir boykot çağrısının doğrulanmamış iddialarla hızla yayıldığı, kurumun geç tepki verdiği örüntü.", "kurumun_tutumu": "İlk günlerde yorum yapılmadı, algı yönetimi rakiplere/organik akışa bırakıldı.", "sonuc": "Kısa vadeli satış etkisi + uzun süreli marka imajı hasarı.", "basari_durumu": "olumsuz_yonetildi", "ay_araligi": (0, 8)},
        {"ozet": "Benzer bir boykot çağrısında kurumun iddiaları kanıtla (fatura, kayıt, üçüncü taraf teyidi) hızla çürüttüğü örnek.", "kurumun_tutumu": "48 saat içinde kanıta dayalı düzeltme + ilgili STK/uzman görüşü paylaşımı.", "sonuc": "Boykot çağrısı organik olarak söndü.", "basari_durumu": "olumlu_yonetildi", "ay_araligi": (0, 8)},
    ],
    "Çalışan Hakları / İş Kazası Krizi": [
        {"ozet": "Bir iş kazası/çalışan hakları iddiasının kurumun savunmacı üslubu nedeniyle büyüdüğü örüntü.", "kurumun_tutumu": "Kurumsal savunma, sorumluluk kabul edilmedi.", "sonuc": "Basın ilgisi arttı, sendika/STK tepkisi büyüdü.", "basari_durumu": "olumsuz_yonetildi", "ay_araligi": (3, 11)},
        {"ozet": "Benzer bir olayda kurumun derhal bağımsız soruşturma başlattığı ve sonuçları kamuoyuyla paylaşacağını taahhüt ettiği örnek.", "kurumun_tutumu": "Bağımsız soruşturma + mağdur/aile ile doğrudan iletişim.", "sonuc": "Kamuoyu tepkisi belirgin şekilde yumuşadı.", "basari_durumu": "olumlu_yonetildi", "ay_araligi": (3, 11)},
    ],
    "_genel": [
        {"ozet": "Sektörde benzer nitelikte bir itibar krizinin ilk 24-48 saatlik sessizlik nedeniyle büyüdüğü, sonrasında kriz iletişimi ekibi devreye girince yatıştığı genel örüntü.", "kurumun_tutumu": "Gecikmeli, savunmacı ilk tepki; sonrasında profesyonelleşen iletişim.", "sonuc": "İtibar kaybı geri kazanılabildi ancak süreç 4-6 hafta sürdü.", "basari_durumu": "karisik", "ay_araligi": (0, 11)},
        {"ozet": "Aynı sektörde bir kurumun benzer bir krizde ilk 6 saat içinde CEO düzeyinde açıklama yaparak süreci hızla kontrol altına aldığı emsal.", "kurumun_tutumu": "Hızlı, üst düzey, empatik açıklama + somut aksiyon planı.", "sonuc": "Kriz 1 haftadan kısa sürede kamuoyu gündeminden düştü.", "basari_durumu": "olumlu_yonetildi", "ay_araligi": (0, 11)},
    ],
}


class GecmisKrizAnaliziMotoru:
    """Aktif krizle aynı/benzer türde, son 10 yıla yayılan tarihsel emsalleri
    tarayıp kurum/yöneticiye 'bu daha önce de yaşanmıştı, o zaman şöyle
    yönetilmişti, şimdi şunu öneriyoruz' formatında geri bildirim üretir.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    def aktif_mi(self) -> bool:
        return bool(self.api_key)

    def _yaklasik_donem(self, yil: int, ay_araligi: tuple[int, int]) -> str:
        aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
                 "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        a1, a2 = ay_araligi
        if a2 - a1 <= 1:
            return f"{aylar[a1 % 12]} {yil} civarında"
        return f"{yil} yılı içerisinde ({aylar[a1 % 12]}-{aylar[a2 % 12]} arası bir dönemde)"

    def analiz_uret(self, konu: str, sektor: str | None, kriz_id: int) -> GecmisKrizAnaliziCikti:
        simdiki_yil = datetime.utcnow().year
        baslangic_yil = simdiki_yil - 10

        if self.aktif_mi():
            try:
                return self._llm_ile_analiz(konu, sektor, kriz_id, baslangic_yil, simdiki_yil)
            except Exception:
                pass  # graceful degradation -> rule-based şablona düş

        sablonlar = GECMIS_KRIZ_SABLONLARI.get(konu, GECMIS_KRIZ_SABLONLARI["_genel"])
        ornekler: list[GecmisKrizOrnegi] = []
        for i, s in enumerate(sablonlar):
            # 10 yıllık pencere içinde deterministik ama farklı yıllara dağıt
            yil = baslangic_yil + ((kriz_id * 3 + i * 4) % 10)
            ornekler.append(GecmisKrizOrnegi(
                donem=self._yaklasik_donem(yil, s["ay_araligi"]),
                sektor=sektor or "İlgili sektör",
                ozet=s["ozet"],
                kurumun_tutumu=s["kurumun_tutumu"],
                sonuc=s["sonuc"],
                basari_durumu=s["basari_durumu"],
                tavsiye=self._tavsiye_uret(s["basari_durumu"]),
            ))

        return GecmisKrizAnaliziCikti(
            kriz_id=kriz_id,
            taranan_yil_araligi=f"{baslangic_yil}-{simdiki_yil}",
            ornekler=ornekler,
            genel_tavsiye=(
                "Geçmiş emsallerde ortak başarı faktörü hız ve şeffaflıktır: "
                "ilk 6-24 saat içinde açıklama yapan kurumlar itibarlarını "
                "hafta içinde toparlarken, sessiz kalanlarda süreç aylara "
                "yayılmıştır. Bu emsaller jenerik sektör örüntüleridir; "
                "yayınlamadan önce kurum içi doğrulamadan geçirin."
            ),
            llm_destekli=False,
        )

    def _tavsiye_uret(self, basari_durumu: str) -> str:
        if basari_durumu == "olumlu_yonetildi":
            return "Bu örnekteki gibi hızlı, şeffaf ve somut adım içeren bir açıklamayı şimdi sizin de yapmanızı öneriyoruz."
        if basari_durumu == "olumsuz_yonetildi":
            return "Bu örnekte yapılan gecikme/savunmacı tutum hatasını tekrarlamamanızı; ilk 24 saat içinde proaktif açıklama yapmanızı öneriyoruz."
        return "Bu örnekte olduğu gibi süreci düzenli ve şeffaf raporlarla yönetmenizi, tek seferlik açıklamayla yetinmemenizi öneriyoruz."

    def _llm_ile_analiz(self, konu, sektor, kriz_id, baslangic_yil, simdiki_yil) -> GecmisKrizAnaliziCikti:
        import httpx

        sistem = (
            "Sen kurumsal itibar yönetimi konusunda uzman, kıdemli bir halkla "
            f"ilişkiler danışmanısın. Görevin: {baslangic_yil}-{simdiki_yil} yılları "
            "arasında (son 10 yıl), verilen kriz türü ve sektörle benzer nitelikte "
            "yaşanmış, KAMUYA AÇIK ve doğrulanabilir itibar krizi örneklerini "
            "kısaca özetlemek. Tarih tam olarak bilinmiyorsa ay/yıl için yaklaşık "
            "bir ifade kullan (örn. 'Eylül 2019 civarında'). Her örnek için "
            "kurumun o dönemki tutumunu, sonucu ve şimdiki krize dair somut bir "
            "tavsiyeyi belirt. Emin olmadığın hiçbir iddiayı kesin bilgiymiş gibi "
            "sunma; belirsizse açıkça belirt. Sadece JSON döndür, başka hiçbir "
            "metin ekleme. Format: {\"ornekler\": [{\"donem\":..,\"sektor\":..,"
            "\"ozet\":..,\"kurumun_tutumu\":..,\"sonuc\":..,"
            "\"basari_durumu\":\"olumlu_yonetildi|olumsuz_yonetildi|karisik\","
            "\"tavsiye\":..}], \"genel_tavsiye\":..}"
        )
        yanit = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 1200,
                "system": sistem,
                "messages": [{"role": "user", "content": (
                    f"Kriz türü: {konu}\nSektör: {sektor or 'belirtilmedi'}\n"
                    "Bu tür ve sektöre benzer 2-3 tarihsel emsal örnek üret."
                )}],
                "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            },
            timeout=45.0,
        )
        yanit.raise_for_status()
        veri = yanit.json()
        import json as _json
        metin = "".join(b.get("text", "") for b in veri.get("content", []) if b.get("type") == "text")
        ayristirilmis = _json.loads(metin)
        ornekler = [GecmisKrizOrnegi(**o) for o in ayristirilmis["ornekler"]]
        return GecmisKrizAnaliziCikti(
            kriz_id=kriz_id,
            taranan_yil_araligi=f"{baslangic_yil}-{simdiki_yil}",
            ornekler=ornekler,
            genel_tavsiye=ayristirilmis.get("genel_tavsiye", ""),
            llm_destekli=True,
        )


def get_scct_kural_motoru() -> SCCTKuralMotoru:
    return SCCTKuralMotoru()


def get_llm_oneri_motoru() -> LLMOneriMotoru:
    return LLMOneriMotoru()


def get_gecmis_kriz_analiz_motoru() -> GecmisKrizAnaliziMotoru:
    return GecmisKrizAnaliziMotoru()
