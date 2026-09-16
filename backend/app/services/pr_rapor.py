"""
Kurumsal Kriz Müdahale Raporu (Crisis PR Action Report) — Document 121 s.9-10.

Kullanıcının bilgisayarına indireceği rapor basit bir duyuru metni değil;
yönetim kuruluna sunulabilecek seviyede, 4 katmanlı bir belgedir:
  1. Teorik Kriz Teşhisi ve Sorumluluk Analizi (SCCT matrisinde neden bu kümeye
     oturtulduğunun akademik açıklaması, bkz. llm_advisor.py SCCTOnerisi)
  2. 72 Saatlik Operasyonel Hİ Eylem Planı (Altın Saatler / 12. Saat / 24-72. Saat)
  3. Kanal Bazlı Taslak İletişim Metinleri (Resmi Basın / Sosyal Medya / İç
     İletişim / Müşteri Hizmetleri Scripti)
  4. Paydaş Etki ve İletişim Haritası (Tüketiciler, bayiler, medya, resmi
     düzenleyici kurumlar için ayrı taktik)

Mimari Akış (Document 121 s.4, birebir):
    Frontend "Profesyonel Raporu İndir" -> FastAPI (routes_krizler.py)
    -> generate_academic_pr_report() [bu dosya, JSON strateji çıktısı]
    -> Jinja2 HTML/CSS Template (app/templates/pr_rapor.html)
    -> WeasyPrint (HTML -> PDF)
    -> İndirilebilir PDF (Binary Download Stream)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.services.llm_advisor import SCCTOnerisi, ALT_TAKTIK_BILGISI, SCCTAltTaktik

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


@dataclass
class OperasyonelPlanAdimi:
    zaman_araligi: str
    baslik: str
    adimlar: list[str]


@dataclass
class KanalTaslagi:
    kanal: str
    ton: str
    metin: str


@dataclass
class PaydasTaktigi:
    paydas: str
    taktik: str


@dataclass
class CrisisPRActionReport:
    kurum_adi: str
    kriz_baslik: str
    kriz_konusu: str
    risk_skoru: float
    risk_seviyesi: str
    olusturma_tarihi: str
    teorik_teshis: str
    spesifik_strateji_adi: str
    spesifik_strateji_kaynak: str
    spesifik_strateji_aciklama: str
    alternatif_stratejiler: list[str]
    operasyonel_plan: list[OperasyonelPlanAdimi]
    kanal_taslaklari: list[KanalTaslagi]
    paydas_haritasi: list[PaydasTaktigi]
    metodoloji_notu: str
    llm_destekli_metin: str | None = None


# --- 72 Saatlik Operasyonel Hİ Eylem Planı şablonu (Document 121 s.9) -------
def _operasyonel_plan_uret(oneri: SCCTOnerisi) -> list[OperasyonelPlanAdimi]:
    return [
        OperasyonelPlanAdimi(
            zaman_araligi="İlk 2 Saat (Altın Saatler)",
            baslik="İç Bilgilendirme ve Durum Tespiti",
            adimlar=[
                "Kriz yönetim ekibi ve sözcü ataması yapılır",
                "Olayın kapsamı, kök nedeni ve etkilenen taraflar netleştirilir",
                "Hukuk/uyum birimiyle ön değerlendirme yapılır",
                "Çalışanlara resmi olmayan kanallardan bilgi sızmaması için iç duyuru hazırlanır",
            ],
        ),
        OperasyonelPlanAdimi(
            zaman_araligi="12. Saat",
            baslik="Medya ve Kamuoyu Açıklaması",
            adimlar=[
                f"Seçilen strateji ({oneri.strateji.value}) doğrultusunda resmi açıklama yayınlanır",
                "Sosyal medya hesaplarından tutarlı, tek-ses ilkesiyle paylaşım yapılır",
                "Müşteri hizmetleri/çağrı merkezi standart yanıt scripti ile donatılır",
            ],
        ),
        OperasyonelPlanAdimi(
            zaman_araligi="24-72. Saat",
            baslik="Düzeltici Eylemlerin İlanı ve İzleme",
            adimlar=[
                "Somut düzeltici eylem planı (varsa tazminat/telafi) kamuoyuna duyurulur",
                "Etkilenen paydaşlarla birebir görüşmeler başlatılır",
                "İtibar/kriz skorları saatlik izlenir; eğilim tersine dönene kadar iletişim sürdürülür",
                "72 saat sonunda süreç bir 'kriz sonrası değerlendirme (post-mortem)' ile kapatılır",
            ],
        ),
    ]


# --- Kanal Bazlı Taslak İletişim Metinleri (Document 121 s.9) --------------
def _kanal_taslaklari_uret(oneri: SCCTOnerisi, kurum_adi: str, kriz_konusu: str) -> list[KanalTaslagi]:
    taktik_adi = ALT_TAKTIK_BILGISI[oneri.spesifik_strateji].ad if oneri.spesifik_strateji else oneri.strateji.value

    return [
        KanalTaslagi(
            kanal="Resmi Basın Açıklaması", ton="Kurumsal, ölçülü, kanıta dayalı",
            metin=(
                f"{kurum_adi}, kamuoyunda gündeme gelen '{kriz_konusu}' başlıklı konudan haberdardır. "
                f"Seçilen iletişim stratejimiz doğrultusunda ({taktik_adi}) konuyu titizlikle "
                f"inceliyoruz. {oneri.gerekce} Gelişmeler şeffaflıkla paylaşılmaya devam edecektir."
            ),
        ),
        KanalTaslagi(
            kanal="Sosyal Medya Duyurusu (X / Instagram)", ton="Şeffaf, hızlı, net",
            metin=(
                f"'{kriz_konusu}' konusundaki geri bildirimlerinizden haberdarız. Konuyu ciddiyetle "
                f"ele alıyoruz, gelişmeleri bu hesaptan paylaşacağız. Sorularınız için buradayız."
            ),
        ),
        KanalTaslagi(
            kanal="İç İletişim / Çalışan Bilgilendirme Metni", ton="Bilgilendirici, birleştirici",
            metin=(
                f"Değerli çalışma arkadaşlarım, '{kriz_konusu}' ile ilgili kamuoyunda çıkan haberler "
                f"hakkında sizi bilgilendirmek isteriz. Konu {oneri.ilk_mudahale_suresi_saat} saat "
                f"içinde ele alınacak şekilde yönetiliyor. Müşteri/basın sorularını lütfen ilgili "
                f"birime yönlendirin, sosyal medyada kişisel yorum yapmaktan kaçının."
            ),
        ),
        KanalTaslagi(
            kanal="Müşteri Hizmetleri Call-Center / Chatbot Scripti", ton="Empatik, çözüm odaklı",
            metin=(
                f"Bizi aradığınız/yazdığınız için teşekkür ederiz. '{kriz_konusu}' konusundan "
                f"haberdarız ve durumu ciddiyetle takip ediyoruz. Size özel mağduriyetiniz varsa "
                f"kaydınızı alalım, ilgili ekibimiz en kısa sürede sizinle iletişime geçecektir."
            ),
        ),
    ]


# --- Paydaş Etki ve İletişim Haritası (Document 121 s.9) --------------------
def _paydas_haritasi_uret() -> list[PaydasTaktigi]:
    return [
        PaydasTaktigi("Tüketiciler", "Şeffaf, düzenli güncellemeler; şikayet kanallarının görünürlüğü artırılır."),
        PaydasTaktigi("Bayiler / İş Ortakları", "Doğrudan bilgilendirme mektubu; saha ekiplerine standart yanıt seti."),
        PaydasTaktigi("Medya", "Sözcü ataması, basın bülteni, gerekirse basın toplantısı."),
        PaydasTaktigi("Resmi Düzenleyici Kurumlar (Bakanlıklar/İlgili Kurul)", "Proaktif bilgilendirme, mevzuata uyum belgelerinin hazır tutulması."),
        PaydasTaktigi("Çalışanlar", "İç iletişim metni + soru-cevap oturumu."),
    ]


def generate_academic_pr_report(
    oneri: SCCTOnerisi,
    kurum_adi: str,
    kriz_baslik: str,
    kriz_konusu: str,
    risk_skoru: float,
    risk_seviyesi: str,
) -> CrisisPRActionReport:
    """Document 121 s.9'daki 4 katmanlı raporu SCCTOnerisi'nden üretir."""
    spesifik = ALT_TAKTIK_BILGISI.get(oneri.spesifik_strateji) if oneri.spesifik_strateji else None
    alternatif_adlar = [ALT_TAKTIK_BILGISI[t].ad for t in oneri.alternatif_stratejiler]

    teorik_teshis = (
        f"Bu kriz, SCCT (Coombs, 2007) matrisinde '{oneri.strateji.value}' duruşuna "
        f"({oneri.sorumluluk_seviyesi.value} atfedilen sorumluluk seviyesiyle) yerleştirilmiştir. "
        f"{oneri.gerekce}"
    )

    return CrisisPRActionReport(
        kurum_adi=kurum_adi, kriz_baslik=kriz_baslik, kriz_konusu=kriz_konusu,
        risk_skoru=risk_skoru, risk_seviyesi=risk_seviyesi,
        olusturma_tarihi=datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC"),
        teorik_teshis=teorik_teshis,
        spesifik_strateji_adi=spesifik.ad if spesifik else oneri.strateji.value,
        spesifik_strateji_kaynak=spesifik.akademik_kaynak if spesifik else "Coombs (2007) SCCT",
        spesifik_strateji_aciklama=spesifik.aciklama if spesifik else "",
        alternatif_stratejiler=alternatif_adlar,
        operasyonel_plan=_operasyonel_plan_uret(oneri),
        kanal_taslaklari=_kanal_taslaklari_uret(oneri, kurum_adi, kriz_konusu),
        paydas_haritasi=_paydas_haritasi_uret(),
        metodoloji_notu=oneri.metodoloji_notu,
        llm_destekli_metin=oneri.llm_metni,
    )


def create_pdf_report(report: CrisisPRActionReport) -> bytes:
    """Jinja2 (app/templates/pr_rapor.html) + WeasyPrint ile PDF üretir.

    weasyprint yoksa (kurulu değil/sistem kütüphaneleri eksikse — Windows'ta
    Pango/GDK-Pixbuf gerektirir) düz-metin bir fallback rapor üretilir; bu
    modül HİÇBİR ZAMAN çağıranı bir ImportError ile çökertmez.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=select_autoescape(["html"]))
    template = env.get_template("pr_rapor.html")
    html_icerik = template.render(rapor=report)

    try:
        from weasyprint import HTML
        return HTML(string=html_icerik).write_pdf()
    except Exception as exc:  # pragma: no cover - ortam bağımlı (Windows sistem kütüphaneleri)
        # Graceful degradation: WeasyPrint'in Windows'ta çalışması için Pango/
        # GDK-Pixbuf (GTK3 runtime) sistem kütüphaneleri gerekir; bunlar kurulu
        # değilse (pip paketi kurulu olsa bile) HTML->PDF dönüşümü başarısız
        # olabilir. Bu durumda kullanıcı yine de raporun İÇERİĞİNİ (düz metin/
        # HTML olarak) kaybetmemelidir.
        uyari = (
            f"[PDF oluşturulamadı: {exc}. WeasyPrint için Windows'ta GTK3 "
            "runtime (Pango/GDK-Pixbuf) gerekir — bkz. KURULUM_REHBERI.md. "
            "Aşağıda raporun HTML içeriği düz metin olarak sunulmuştur.]\n\n"
        )
        return (uyari + html_icerik).encode("utf-8")
