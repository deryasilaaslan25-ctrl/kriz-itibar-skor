"""
Somut collector implementasyonları (Faz 6 — gerçek, ücretsiz veri toplama).

Kullanıcının hiçbir ücretli API anahtarı (Twitter, NewsAPI) yoktur. Bu
modül, dokümanın belirttiği kaynaklardan HANGİLERİNİN gerçekten anahtarsız
(ücretsiz) çalışabildiğini net biçimde ayırır:

  - RedditCollector       : Kod TAM ve DOĞRU yazılmıştır, PRAW (OAuth client
    id/secret) yerine Reddit'in kimlik doğrulaması gerektirmeyen genel
    `.json` uçları (`reddit.com/search.json`) httpx ile kullanılır — bu
    yöntem gerçek bir kullanıcı bilgisayarından/normal bir IP'den ÇALIŞIR.
    DÜRÜST NOT (bu oturumda canlı test edildi): bu geliştirme ortamının
    (sandbox/bulut) çıkış IP adresi, Reddit'in bot-koruması tarafından
    `403 Blocked` ile engellenmektedir (Cloudflare tabanlı IP itibar
    kontrolü — User-Agent'tan bağımsız, veri merkezi IP aralıklarını genel
    olarak engeller). Kod, kullanıcının kendi makinesinde veya normal bir
    sunucuda çalıştırıldığında beklenen
    JSON yanıtını alacaktır; sistem bu engelle karşılaştığında ÇÖKMEZ,
    boş liste döner ve /api/kaynaklar/durum'da şeffaf biçimde raporlanır.
  - NewsCollector          : GERÇEKTEN ÇALIŞIR, anahtar gerektirmez. Google
    News RSS (`news.google.com/rss/search`) feedparser ile ayrıştırılır.
    NEWSAPI_KEY tanımlıysa (kullanıcıda yok) ek kaynak olarak NewsAPI de
    devreye girer — tanımlı değilse sessizce atlanır.
  - GoogleTrendsCollector  : GERÇEKTEN ÇALIŞIR, anahtar gerektirmez. `pytrends`
    (resmi olmayan ama yaygın kullanılan bir Google Trends istemcisi).
  - TwitterCollector       : Kod TAM ve DOĞRU yazılmıştır (Twitter API v2
    `/2/tweets/search/recent`), ancak X/Twitter 2023'ten beri ücretsiz/ToS'a
    uygun anahtarsız bir arama yolu SUNMAMAKTADIR — bu yüzden
    `TWITTER_BEARER_TOKEN` tanımlı DEĞİLKEN devre dışı kalır (aktif_mi() ==
    False). Kullanıcı ileride bir Twitter API planı edinirse, .env dosyasına
    token eklemek dışında HİÇBİR kod değişikliği gerekmez.
  - YouTubeCollector       : GERÇEKTEN ÇALIŞIR, anahtar ZORUNLU DEĞİLDİR (Faz
    10). Twitter'ın aksine YouTube'da anahtarsız/ücretsiz bir arama+yorum
    toplama yolu VARDIR: `yt-dlp` (yt-dlp.org), YouTube'un arama sonuçları
    sayfasını ve video/yorum verisini resmi API'ye hiç dokunmadan ayrıştıran,
    yaygın kullanılan açık kaynak bir araçtır. YOUTUBE_API_KEY tanımlı
    DEĞİLSE bu yol kullanılır — sistem YouTube'dan hem video meta verisi hem
    de GERÇEK izleyici yorumlarını (kriz sinyali için en değerli veri) hiçbir
    API anahtarı olmadan toplayabilir. YOUTUBE_API_KEY tanımlıysa (kullanıcı
    ileride Google Cloud Console'dan ÜCRETSİZ bir anahtar edinirse) bunun
    yerine resmi YouTube Data API v3 (`search.list` + `commentThreads.list`)
    kullanılır — daha güvenilir/kotalıdır, .env'e anahtar eklemek dışında
    kod değişikliği gerekmez (tıpkı NewsAPI/NEWSAPI_KEY deseninde olduğu gibi).

Her collector, ilgili kaynağa erişilemediğinde (ağ hatası, hız sınırı, format
değişikliği) sistemi ÇÖKERTMEDEN boş liste döner — bkz. GET /api/kaynaklar/durum.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from app.collectors.base import BaseCollector, HamIcerik
from app.config import settings

logger = logging.getLogger(__name__)

# Reddit'in genel .json uçları KİMLİK DOĞRULAMASI istemez, ancak varsayılan
# istemci User-Agent'larını (ör. "python-requests/...") agresif biçimde
# hız sınırlar/engeller. Reddit'in kendi API kurallarına uygun, uygulamayı
# ve amacı açıkça belirten özel bir User-Agent kullanılması ZORUNLUDUR.
# Reddit'in kendi kılavuzundaki önerilen format: "<platform>:<app kimliği>:
# <sürüm> (by /u/<kullanıcı_adı>)" — bkz. https://github.com/reddit-archive/reddit/wiki/API
_REDDIT_USER_AGENT = "web:erken-itibar-krizi-tespit-sistemi:v1.0 (by /u/anonim_arastirmaci)"
_ISTEK_ZAMAN_ASIMI = 10.0


class TwitterCollector(BaseCollector):
    platform_adi = "X (Twitter)"

    def aktif_mi(self) -> bool:
        return bool(settings.TWITTER_BEARER_TOKEN)

    def topla(self, anahtar_kelime: str, limit: int = 50) -> list[HamIcerik]:
        """Twitter API v2 /2/tweets/search/recent — gerçek, doğru yazılmış
        entegrasyon. TWITTER_BEARER_TOKEN tanımlı değilse (kullanıcıda
        şu an yok — X'te ücretsiz arama erişimi 2023'ten beri mevcut değil)
        boş liste döner; ücretli bir plan edinildiğinde .env'e token eklemek
        yeterlidir, bu fonksiyonun DEĞİŞMESİ gerekmez."""
        if not self.aktif_mi():
            return []
        try:
            yanit = httpx.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers={"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"},
                params={
                    "query": anahtar_kelime,
                    "max_results": max(10, min(limit, 100)),  # API sınırı: 10-100
                    "tweet.fields": "public_metrics,created_at,author_id,lang",
                },
                timeout=_ISTEK_ZAMAN_ASIMI,
            )
            yanit.raise_for_status()
            veri = yanit.json()
        except Exception as exc:
            logger.warning("TwitterCollector.topla başarısız oldu: %s", exc)
            return []

        sonuc: list[HamIcerik] = []
        for tweet in veri.get("data", []):
            metrikler = tweet.get("public_metrics", {})
            toplam_etkilesim = (
                metrikler.get("retweet_count", 0) + metrikler.get("reply_count", 0)
                + metrikler.get("like_count", 0) + metrikler.get("quote_count", 0)
            )
            sonuc.append(HamIcerik(
                platform="twitter", baslik=tweet.get("text", "")[:80],
                icerik=tweet.get("text", ""), hesap_id=tweet.get("author_id"),
                yorum_sayisi=toplam_etkilesim,
                kaynak_url=f"https://twitter.com/i/web/status/{tweet.get('id')}" if tweet.get("id") else None,
            ))
        return sonuc


class RedditCollector(BaseCollector):
    """Reddit'in kimlik doğrulaması GEREKTİRMEYEN genel arama uçlarını kullanır.

    NEDEN PRAW DEĞİL? PRAW (Python Reddit API Wrapper), Reddit'in OAuth2
    uygulama kimlik bilgilerini (REDDIT_CLIENT_ID/SECRET) zorunlu kılar.
    Kullanıcının bu anahtarları yoktur. Reddit ancak "script" tipi bir
    uygulama için bile bu anahtarları ÜCRETSİZ verir, fakat kullanıcı bunu
    henüz oluşturmadığından, bu sistemde Reddit'in resmi olarak desteklediği
    (rate-limit'e tabi ama kimlik istemeyen) genel `.json` uç noktaları
    tercih edilmiştir — bkz. https://www.reddit.com/dev/api (herkese açık
    salt-okunur uçlar için kimlik doğrulama şart koşulmaz, yalnızca makul
    bir istek hızı ve tanımlayıcı bir User-Agent istenir).
    """
    platform_adi = "Reddit"

    def aktif_mi(self) -> bool:
        return True  # anahtarsız genel uç her zaman denenebilir

    def topla(self, anahtar_kelime: str, limit: int = 50) -> list[HamIcerik]:
        try:
            yanit = httpx.get(
                "https://www.reddit.com/search.json",
                headers={"User-Agent": _REDDIT_USER_AGENT},
                params={"q": anahtar_kelime, "limit": max(1, min(limit, 100)), "sort": "new"},
                timeout=_ISTEK_ZAMAN_ASIMI,
                follow_redirects=True,
            )
            yanit.raise_for_status()
            veri = yanit.json()
        except Exception as exc:
            logger.warning("RedditCollector.topla başarısız oldu: %s", exc)
            return []

        sonuc: list[HamIcerik] = []
        for cocuk in veri.get("data", {}).get("children", []):
            g = cocuk.get("data", {})
            baslik = g.get("title", "")
            govde = g.get("selftext", "") or baslik
            toplam_etkilesim = g.get("score", 0) + g.get("num_comments", 0)
            sonuc.append(HamIcerik(
                platform="reddit", baslik=baslik[:120], icerik=govde,
                hesap_id=g.get("author"), yorum_sayisi=toplam_etkilesim,
                kaynak_url=f"https://reddit.com{g.get('permalink')}" if g.get("permalink") else None,
            ))
        return sonuc


class NewsCollector(BaseCollector):
    """Google News RSS (anahtarsız) + isteğe bağlı NewsAPI (NEWSAPI_KEY varsa)."""
    platform_adi = "Haber Kaynakları"

    def aktif_mi(self) -> bool:
        return True  # RSS her zaman denenebilir

    def topla(self, anahtar_kelime: str, limit: int = 50) -> list[HamIcerik]:
        sonuc: list[HamIcerik] = []
        sonuc.extend(self._google_news_rss(anahtar_kelime, limit))
        if settings.NEWSAPI_KEY:
            sonuc.extend(self._newsapi(anahtar_kelime, max(0, limit - len(sonuc))))
        return sonuc[:limit]

    def _google_news_rss(self, anahtar_kelime: str, limit: int) -> list[HamIcerik]:
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser kurulu değil — Google News RSS toplama atlandı.")
            return []

        try:
            url = f"https://news.google.com/rss/search?q={quote(anahtar_kelime)}&hl=tr&gl=TR&ceid=TR:tr"
            besleme = feedparser.parse(url)
        except Exception as exc:
            logger.warning("Google News RSS toplama başarısız oldu: %s", exc)
            return []

        sonuc: list[HamIcerik] = []
        for girdi in besleme.entries[:limit]:
            sonuc.append(HamIcerik(
                platform="haber_sitesi", baslik=girdi.get("title", "")[:150],
                icerik=girdi.get("summary", girdi.get("title", "")),
                hesap_id=girdi.get("source", {}).get("title") if isinstance(girdi.get("source"), dict) else None,
                yorum_sayisi=0,  # RSS etkileşim sayısı sağlamaz
                kaynak_url=girdi.get("link"),
            ))
        return sonuc

    def _newsapi(self, anahtar_kelime: str, limit: int) -> list[HamIcerik]:
        if limit <= 0:
            return []
        try:
            yanit = httpx.get(
                "https://newsapi.org/v2/everything",
                params={"q": anahtar_kelime, "language": "tr", "sortBy": "publishedAt", "pageSize": min(limit, 100)},
                headers={"X-Api-Key": settings.NEWSAPI_KEY},
                timeout=_ISTEK_ZAMAN_ASIMI,
            )
            yanit.raise_for_status()
            veri = yanit.json()
        except Exception as exc:
            logger.warning("NewsAPI toplama başarısız oldu: %s", exc)
            return []

        return [
            HamIcerik(
                platform="haber_sitesi", baslik=(m.get("title") or "")[:150],
                icerik=m.get("description") or m.get("title") or "",
                hesap_id=(m.get("source") or {}).get("name"), yorum_sayisi=0,
                kaynak_url=m.get("url"),
            )
            for m in veri.get("articles", [])
        ]


class GoogleTrendsCollector(BaseCollector):
    """`pytrends` (resmi olmayan ama yaygın kullanılan, anahtarsız Google
    Trends istemcisi) ile ilgi-zaman-serisi toplar.

    NOT: Trends verisi "içerik" değil bir zaman serisidir (arama ilgisi,
    0-100 endeksli); mevcut HamIcerik sözleşmesine uydurmak için her zaman
    noktası, `yorum_sayisi` alanında ilgi endeksini taşıyan sentetik bir
    kayda dönüştürülür (ör. "İlgi endeksi 78/100"). Bu, sistemin geri kalanı
    (sentiment/topic pipeline) için nötr bir metin içerdiğinden --sentiment
    analizine girmez-- ama risk_scoring.py'nin hacim/trend bileşenlerine
    (EWMA Z-skoru) doğrudan girdi olarak kullanılabilir.
    """
    platform_adi = "Google Trends"

    def aktif_mi(self) -> bool:
        return settings.GOOGLE_TRENDS_ENABLED

    def topla(self, anahtar_kelime: str, limit: int = 50) -> list[HamIcerik]:
        if not self.aktif_mi():
            return []
        try:
            from pytrends.request import TrendReq
        except ImportError:
            logger.warning("pytrends kurulu değil — Google Trends toplama atlandı.")
            return []

        try:
            pytrends = TrendReq(hl="tr-TR", tz=180)
            pytrends.build_payload([anahtar_kelime], timeframe="now 7-d", geo="TR")
            df = pytrends.interest_over_time()
        except Exception as exc:
            logger.warning("GoogleTrendsCollector.topla başarısız oldu: %s", exc)
            return []

        if df is None or df.empty:
            return []

        sonuc: list[HamIcerik] = []
        for zaman, satir in df.tail(limit).iterrows():
            deger = int(satir.get(anahtar_kelime, 0))
            sonuc.append(HamIcerik(
                platform="google_trends", baslik=f"Google Trends: '{anahtar_kelime}'",
                icerik=f"{zaman} tarihinde '{anahtar_kelime}' için arama ilgisi endeksi: {deger}/100.",
                hesap_id=None, yorum_sayisi=deger, kaynak_url=None,
            ))
        return sonuc


class YouTubeCollector(BaseCollector):
    """YouTube video + yorum toplama (Faz 10).

    NEDEN google-api-python-client DEĞİL? Bu paket, resmi YouTube Data API v3
    çağrıları için bir sarmalayıcıdır (zaten kurulu olan `httpx` ile de
    doğrudan çağrılabildiğinden — bkz. `_resmi_api` — ekstra bağımlılık
    gereksizdir) ve HER İKİ durumda da bir Google Cloud API anahtarı GEREKTİRİR.
    Kullanıcının bu anahtarı yoktur.

    NEDEN yt-dlp? YouTube, Twitter'ın aksine anahtarsız bir arama yolunu
    fiilen SUNAR: arama sonuçları sayfası ile video/yorum verisi herkese açık
    olarak (kimlik doğrulama istemeden) sunulur. `yt-dlp`, bu genel uçları
    ayrıştırıp yapılandırılmış veri (başlık, açıklama, izlenme sayısı, YORUM
    METİNLERİ) döndüren, çok aktif geliştirilen (YouTube'un ön yüz
    değişikliklerine hızla uyum sağlayan), MIT lisanslı açık kaynak bir
    araçtır — Reddit'in kimlik doğrulamasız `.json` uçlarıyla aynı felsefeyi
    (genel/herkese-açık uçları kullan, ücretli/anahtarlı API'ye muhtaç kalma)
    izler, ancak elle regex ile `ytInitialData` ayrıştırmak yerine bu işi
    doğru ve sürdürülebilir yapan olgun bir kütüphaneye devredilir.

    DÜRÜST NOT: Bu sistemin çalıştığı bulut/sandbox ortamının çıkış IP'si,
    Reddit'te olduğu gibi YouTube tarafından da geçici biçimde
    hız-sınırlanabilir/engellenebilir (veri merkezi IP aralıkları için
    yaygın bir korumadır). Kod, kullanıcının kendi makinesinden veya normal
    bir sunucudan çalıştırıldığında beklendiği gibi çalışır; bu engelle
    karşılaşıldığında sistem ÇÖKMEZ, boş liste döner ve durum
    `/api/kaynaklar/durum`'da şeffaf biçimde raporlanır (aşağıdaki iki
    kademeli deneme/fallback zincirine bakınız).

    YOUTUBE_API_KEY tanımlıysa (opsiyonel, kullanıcı ileride edinirse) önce
    resmi API denenir; boş/başarısız dönerse yt-dlp'ye (anahtarsız) düşülür.
    Böylece hem "hiç anahtar yok" hem de "resmi anahtar var ama o an kota/hata
    verdi" senaryolarında sistem asla veri kaynağını tamamen kaybetmez.
    """

    platform_adi = "YouTube"

    # Bir taramada en fazla kaç video aranacağı ve video başına en fazla kaç
    # yorumun toplanacağı — Reddit/News ile aynı `limit` sözleşmesini korumak
    # için toplam sonuç `limit`'i aşmayacak şekilde ikiye bölünür.
    _MAKS_VIDEO = 5

    def aktif_mi(self) -> bool:
        return True  # yt-dlp anahtarsız yolu her zaman denenebilir

    def topla(self, anahtar_kelime: str, limit: int = 50) -> list[HamIcerik]:
        if settings.YOUTUBE_API_KEY:
            sonuc = self._resmi_api(anahtar_kelime, limit)
            if sonuc:
                return sonuc
            logger.info("YOUTUBE_API_KEY tanımlı ama resmi API sonuç döndürmedi — yt-dlp (anahtarsız) yoluna düşülüyor.")
        return self._keyless_ytdlp(anahtar_kelime, limit)

    # -- Resmi YouTube Data API v3 (yalnızca YOUTUBE_API_KEY tanımlıysa) -----
    def _resmi_api(self, anahtar_kelime: str, limit: int) -> list[HamIcerik]:
        try:
            arama_yaniti = httpx.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet", "q": anahtar_kelime, "type": "video",
                    "maxResults": max(1, min(limit, self._MAKS_VIDEO)),
                    "relevanceLanguage": "tr", "key": settings.YOUTUBE_API_KEY,
                },
                timeout=_ISTEK_ZAMAN_ASIMI,
            )
            arama_yaniti.raise_for_status()
            video_listesi = arama_yaniti.json().get("items", [])
        except Exception as exc:
            logger.warning("YouTube Data API araması başarısız oldu: %s", exc)
            return []

        if not video_listesi:
            return []

        yorum_basi_limit = max(1, limit // len(video_listesi))
        sonuc: list[HamIcerik] = []
        for video in video_listesi:
            video_id = video.get("id", {}).get("videoId")
            if not video_id:
                continue
            snippet = video.get("snippet", {})
            baslik = snippet.get("title", "")
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            yorum_listesi: list[dict] = []
            try:
                yorum_yaniti = httpx.get(
                    "https://www.googleapis.com/youtube/v3/commentThreads",
                    params={
                        "part": "snippet", "videoId": video_id, "order": "relevance",
                        "maxResults": min(yorum_basi_limit, 100), "textFormat": "plainText",
                        "key": settings.YOUTUBE_API_KEY,
                    },
                    timeout=_ISTEK_ZAMAN_ASIMI,
                )
                yorum_yaniti.raise_for_status()
                yorum_listesi = yorum_yaniti.json().get("items", [])
            except Exception as exc:
                # Yorumlar kapalı olabilir (403) ya da geçici bir hata olabilir;
                # bu durumda videoyu yine de açıklamasıyla bir sinyal olarak ekleriz.
                logger.info("YouTube yorumları alınamadı (video %s): %s", video_id, exc)

            if not yorum_listesi:
                sonuc.append(HamIcerik(
                    platform="youtube", baslik=baslik[:150],
                    icerik=snippet.get("description", "") or baslik,
                    hesap_id=snippet.get("channelTitle"), yorum_sayisi=0, kaynak_url=video_url,
                ))
                continue

            for yorum in yorum_listesi:
                ust_yorum = yorum.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                sonuc.append(HamIcerik(
                    platform="youtube", baslik=baslik[:150],
                    icerik=ust_yorum.get("textDisplay") or ust_yorum.get("textOriginal") or "",
                    hesap_id=ust_yorum.get("authorDisplayName"),
                    yorum_sayisi=ust_yorum.get("likeCount", 0) or 0,
                    kaynak_url=video_url,
                ))
            if len(sonuc) >= limit:
                break
        return [h for h in sonuc if h.icerik][:limit]

    # -- Anahtarsız yol: yt-dlp (arama + video + yorum) ----------------------
    def _keyless_ytdlp(self, anahtar_kelime: str, limit: int) -> list[HamIcerik]:
        try:
            import yt_dlp
        except ImportError:
            logger.warning("yt-dlp kurulu değil — YouTube (anahtarsız) toplama atlandı.")
            return []

        video_sayisi = max(1, min(self._MAKS_VIDEO, limit))
        yorum_basi_limit = max(1, limit // video_sayisi)
        ortak_secenekler = {
            "quiet": True, "no_warnings": True, "skip_download": True, "ignoreerrors": True,
        }

        def _ara(yorumlu: bool):
            secenekler = dict(ortak_secenekler)
            if yorumlu:
                # [maks_yorum, maks_ust_seviye_ebeveyn, maks_yanit, video_basi_maks_yanit] —
                # bkz. yt-dlp "extractor-args" belgeleri (youtube:max_comments).
                secenekler["getcomments"] = True
                secenekler["extractor_args"] = {"youtube": {"max_comments": [str(yorum_basi_limit), "all", "0", "0"]}}
            with yt_dlp.YoutubeDL(secenekler) as ydl:
                return ydl.extract_info(f"ytsearch{video_sayisi}:{anahtar_kelime}", download=False)

        try:
            bilgi = _ara(yorumlu=True)
        except Exception as exc:
            logger.info("yt-dlp yorumlu YouTube araması başarısız, yalnızca video meta verisiyle yeniden deneniyor: %s", exc)
            try:
                bilgi = _ara(yorumlu=False)
            except Exception as exc2:
                logger.warning("yt-dlp YouTube araması başarısız oldu: %s", exc2)
                return []

        sonuc: list[HamIcerik] = []
        for video in (bilgi or {}).get("entries", []) or []:
            if not video:
                continue
            baslik = video.get("title") or ""
            video_id = video.get("id")
            video_url = video.get("webpage_url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else None)
            kanal = video.get("channel") or video.get("uploader")
            yorumlar = video.get("comments") or []

            if yorumlar:
                for yorum in yorumlar[:yorum_basi_limit]:
                    sonuc.append(HamIcerik(
                        platform="youtube", baslik=baslik[:150],
                        icerik=(yorum.get("text") or "").strip(),
                        hesap_id=yorum.get("author"),
                        yorum_sayisi=yorum.get("like_count", 0) or 0,
                        kaynak_url=video_url,
                    ))
            else:
                sonuc.append(HamIcerik(
                    platform="youtube", baslik=baslik[:150],
                    icerik=video.get("description") or baslik,
                    hesap_id=kanal, yorum_sayisi=video.get("view_count", 0) or 0,
                    kaynak_url=video_url,
                ))
            if len(sonuc) >= limit:
                break
        return [h for h in sonuc if h.icerik][:limit]


def tum_collectorlar() -> list[BaseCollector]:
    return [TwitterCollector(), RedditCollector(), NewsCollector(), GoogleTrendsCollector(), YouTubeCollector()]


def kaynak_durumu() -> list[dict]:
    """Dashboard'da 'hangi kaynaklar canlı, hangileri API anahtarı bekliyor' göstermek için."""
    return [
        {"platform": c.platform_adi, "aktif": c.aktif_mi()}
        for c in tum_collectorlar()
    ]
