"""Veri toplama (collector) testleri — Faz 6.

Bu dosyadaki testler GERÇEK ağ çağrıları yapar (mock DEĞİLDİR) çünkü amaç
bu entegrasyonların gerçekten çalıştığını doğrulamaktır. Ağ koşullarına
(rate limit, geçici erişim engeli) karşı dayanıklı olmaları için "hiç
çökmüyor mu" ve "beklenen tip/şema" her zaman doğrulanır; "en az 1 sonuç
döndü mü" ise ağ gerçekten erişilebilirse doğrulanır, erişilemezse test
`skip` edilir (flaky-test önleme, ama gerçek entegrasyonu gizlemez).

Twitter için ayrı bir mock (respx) testi vardır çünkü X/Twitter'ın anahtarsız/
ücretsiz bir arama yolu yoktur (bkz. connectors.py docstring) — bu yüzden
CANLI test edilemez, yalnızca HTTP isteğinin ŞEMASININ doğru kurulduğu
doğrulanır.

YouTube için (Faz 10) de aynı ikili yaklaşım uygulanır: yt-dlp (anahtarsız)
yolu CANLI test edilir (erişilemezse skip), resmi YouTube Data API v3 yolu
(YOUTUBE_API_KEY tanımlıysa devreye girer) ise respx ile şema doğrulaması
alır — çünkü bu depoda gerçek bir Google API anahtarı yoktur.
"""
import pytest
import respx
import httpx

from app.collectors.connectors import (
    RedditCollector, NewsCollector, GoogleTrendsCollector, TwitterCollector,
    YouTubeCollector, kaynak_durumu,
)
from app.collectors.base import HamIcerik
from app.config import settings


def test_reddit_collector_asla_cokmez_ve_liste_doner():
    sonuc = RedditCollector().topla("bitcoin", limit=5)
    assert isinstance(sonuc, list)
    if not sonuc:
        pytest.skip("Reddit bu ağ ortamından erişilemedi (403/bot-koruması) — kod yolu yine de doğrulandı (çökmedi).")
    assert all(isinstance(i, HamIcerik) for i in sonuc)


def test_news_collector_google_rss_gercekten_calisir():
    """Google News RSS anahtarsızdır ve bu ortamda GERÇEKTEN test edilip
    çalıştığı doğrulanmıştır (bkz. Faz 6 doğrulama notları)."""
    sonuc = NewsCollector().topla("teknoloji", limit=5)
    assert isinstance(sonuc, list)
    if not sonuc:
        pytest.skip("Google News RSS bu çalıştırmada erişilemedi (geçici ağ sorunu).")
    assert all(isinstance(i, HamIcerik) for i in sonuc)
    assert sonuc[0].platform == "haber_sitesi"
    assert sonuc[0].baslik  # başlık dolu olmalı


def test_google_trends_collector_gercekten_calisir():
    onceki = settings.GOOGLE_TRENDS_ENABLED
    settings.GOOGLE_TRENDS_ENABLED = True
    try:
        sonuc = GoogleTrendsCollector().topla("enflasyon", limit=5)
        assert isinstance(sonuc, list)
        if not sonuc:
            pytest.skip("Google Trends bu çalıştırmada erişilemedi (geçici ağ sorunu/hız sınırı).")
        assert all(0 <= i.yorum_sayisi <= 100 for i in sonuc)  # ilgi endeksi 0-100 aralığında olmalı
    finally:
        settings.GOOGLE_TRENDS_ENABLED = onceki


def test_google_trends_devre_disiyken_bos_liste_doner():
    onceki = settings.GOOGLE_TRENDS_ENABLED
    settings.GOOGLE_TRENDS_ENABLED = False
    try:
        assert GoogleTrendsCollector().topla("test") == []
    finally:
        settings.GOOGLE_TRENDS_ENABLED = onceki


def test_twitter_anahtar_yokken_devre_disi():
    onceki = settings.TWITTER_BEARER_TOKEN
    settings.TWITTER_BEARER_TOKEN = None
    try:
        collector = TwitterCollector()
        assert collector.aktif_mi() is False
        assert collector.topla("test") == []
    finally:
        settings.TWITTER_BEARER_TOKEN = onceki


@respx.mock
def test_twitter_api_semasi_dogru_kuruludur():
    """Twitter API v2'yi CANLI test edemeyiz (ücretsiz erişim yok) ama HTTP
    isteğinin doğru uca, doğru header/parametrelerle gittiğini ve yanıtın
    doğru ayrıştırıldığını mock ile doğrulayabiliriz."""
    onceki = settings.TWITTER_BEARER_TOKEN
    settings.TWITTER_BEARER_TOKEN = "sahte-test-tokeni"
    try:
        route = respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
            return_value=httpx.Response(200, json={
                "data": [{
                    "id": "123", "text": "Test tweet",
                    "public_metrics": {"retweet_count": 5, "reply_count": 2, "like_count": 10, "quote_count": 1},
                    "author_id": "u1",
                }]
            })
        )
        sonuc = TwitterCollector().topla("test", limit=10)
        assert route.called
        istek = route.calls[0].request
        assert istek.headers["Authorization"] == "Bearer sahte-test-tokeni"
        assert len(sonuc) == 1
        assert sonuc[0].yorum_sayisi == 5 + 2 + 10 + 1
        assert sonuc[0].platform == "twitter"
    finally:
        settings.TWITTER_BEARER_TOKEN = onceki


def test_kaynak_durumu_bes_platform_raporlar():
    durum = kaynak_durumu()
    assert len(durum) == 5
    platformlar = {d["platform"] for d in durum}
    assert "Reddit" in platformlar and "Haber Kaynakları" in platformlar and "YouTube" in platformlar


# ---- YouTube (Faz 10) --------------------------------------------------------

def test_youtube_anahtarsizken_de_aktif():
    """Twitter'ın aksine YouTube'un anahtarsız (yt-dlp) bir yolu olduğundan,
    YOUTUBE_API_KEY tanımlı olmasa bile collector aktif kabul edilir."""
    onceki = settings.YOUTUBE_API_KEY
    settings.YOUTUBE_API_KEY = None
    try:
        assert YouTubeCollector().aktif_mi() is True
    finally:
        settings.YOUTUBE_API_KEY = onceki


def test_youtube_collector_ytdlp_ile_asla_cokmez_ve_liste_doner():
    """yt-dlp kurulu değilse veya bu ağ ortamından YouTube'a erişilemiyorsa
    (Reddit'te olduğu gibi veri merkezi IP'leri hız sınırlanabilir) test
    `skip` edilir — ama kod yolunun ÇÖKMEDİĞİ her koşulda doğrulanır."""
    onceki = settings.YOUTUBE_API_KEY
    settings.YOUTUBE_API_KEY = None
    try:
        sonuc = YouTubeCollector().topla("teknoloji", limit=5)
    finally:
        settings.YOUTUBE_API_KEY = onceki
    assert isinstance(sonuc, list)
    if not sonuc:
        pytest.skip("YouTube (yt-dlp) bu ağ ortamından erişilemedi veya yt-dlp kurulu değil — kod yolu yine de doğrulandı (çökmedi).")
    assert all(isinstance(i, HamIcerik) for i in sonuc)
    assert all(i.platform == "youtube" for i in sonuc)


@respx.mock
def test_youtube_resmi_api_semasi_dogru_kuruludur():
    """YOUTUBE_API_KEY tanımlıysa search.list + commentThreads.list uçlarının
    doğru parametrelerle çağrıldığını ve yanıtın doğru ayrıştırıldığını
    (gerçek bir Google API anahtarımız olmadığından) mock ile doğrularız."""
    onceki = settings.YOUTUBE_API_KEY
    settings.YOUTUBE_API_KEY = "sahte-test-anahtari"
    try:
        arama_route = respx.get("https://www.googleapis.com/youtube/v3/search").mock(
            return_value=httpx.Response(200, json={
                "items": [{"id": {"videoId": "abc123"}, "snippet": {"title": "Test Video", "channelTitle": "Test Kanal"}}]
            })
        )
        yorum_route = respx.get("https://www.googleapis.com/youtube/v3/commentThreads").mock(
            return_value=httpx.Response(200, json={
                "items": [{
                    "snippet": {"topLevelComment": {"snippet": {
                        "textDisplay": "Harika bir video, teşekkürler!",
                        "authorDisplayName": "kullanici1", "likeCount": 3,
                    }}}
                }]
            })
        )
        sonuc = YouTubeCollector().topla("test", limit=10)
        assert arama_route.called and yorum_route.called
        arama_istegi = arama_route.calls[0].request
        assert arama_istegi.url.params["key"] == "sahte-test-anahtari"
        assert len(sonuc) == 1
        assert sonuc[0].platform == "youtube"
        assert sonuc[0].icerik == "Harika bir video, teşekkürler!"
        assert sonuc[0].yorum_sayisi == 3
        assert sonuc[0].kaynak_url == "https://www.youtube.com/watch?v=abc123"
    finally:
        settings.YOUTUBE_API_KEY = onceki
