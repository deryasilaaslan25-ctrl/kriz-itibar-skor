"""
Bölüm 18: Bildirim Sistemi.

Tek arayüz (NotificationChannel) üzerinden birden fazla kanal desteklenir.
Her kanal .env'de ilgili anahtar/webhook tanımlıysa aktif olur; tanımlı
değilse sessizce atlanır (log'a "gönderilmedi: yapılandırılmamış" yazar).
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from app.config import settings

logger = logging.getLogger("bildirim")


class NotificationChannel(ABC):
    ad: str = "kanal"

    @abstractmethod
    def aktif_mi(self) -> bool: ...

    @abstractmethod
    async def gonder(self, baslik: str, mesaj: str) -> bool: ...


class SlackChannel(NotificationChannel):
    ad = "Slack"

    def aktif_mi(self) -> bool:
        return bool(settings.SLACK_WEBHOOK_URL)

    async def gonder(self, baslik: str, mesaj: str) -> bool:
        if not self.aktif_mi():
            return False
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.SLACK_WEBHOOK_URL, json={"text": f"*{baslik}*\n{mesaj}"})
            return resp.status_code == 200


class TeamsChannel(NotificationChannel):
    ad = "Microsoft Teams"

    def aktif_mi(self) -> bool:
        return bool(settings.TEAMS_WEBHOOK_URL)

    async def gonder(self, baslik: str, mesaj: str) -> bool:
        if not self.aktif_mi():
            return False
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.TEAMS_WEBHOOK_URL, json={"title": baslik, "text": mesaj})
            return resp.status_code == 200


class TelegramChannel(NotificationChannel):
    ad = "Telegram"

    def aktif_mi(self) -> bool:
        return bool(settings.TELEGRAM_BOT_TOKEN)

    async def gonder(self, baslik: str, mesaj: str, chat_id: str | None = None) -> bool:
        if not self.aktif_mi() or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": f"{baslik}\n{mesaj}"})
            return resp.status_code == 200


class EmailChannel(NotificationChannel):
    """SMTP tabanlı e-posta bildirimi (Bölüm 18)."""
    ad = "E-posta"

    def aktif_mi(self) -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_USER)

    async def gonder(self, baslik: str, mesaj: str, alici: str | None = None) -> bool:
        if not self.aktif_mi() or not alici:
            return False
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(mesaj)
        msg["Subject"] = baslik
        msg["From"] = settings.SMTP_USER
        msg["To"] = alici
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
                server.send_message(msg)
            return True
        except Exception as e:
            logger.warning(f"E-posta gönderilemedi: {e}")
            return False


def tum_kanallar() -> list[NotificationChannel]:
    return [SlackChannel(), TeamsChannel(), TelegramChannel(), EmailChannel()]


async def kriz_uyarisi_yayinla(baslik: str, mesaj: str) -> dict:
    """Aktif olan tüm kanallara paralel bildirim gönderir, sonuç raporu döner."""
    sonuclar = {}
    for kanal in tum_kanallar():
        if kanal.aktif_mi():
            try:
                basarili = await kanal.gonder(baslik, mesaj)
                sonuclar[kanal.ad] = "gönderildi" if basarili else "başarısız"
            except Exception as e:
                sonuclar[kanal.ad] = f"hata: {e}"
        else:
            sonuclar[kanal.ad] = "yapılandırılmamış"
    return sonuclar
