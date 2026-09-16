/**
 * Kurum hesabı kayıt / giriş / güvenlik yardımcı modülü — Faz 8.
 *
 * ÖNCEKİ SÜRÜM: şifreler tarayıcıda Web Crypto PBKDF2 ile hash'lenip
 * localStorage'a yazılıyordu (gerçek bir kimlik doğrulama sunucusu yoktu).
 * BU SÜRÜM: gerçek backend'e bağlanır — backend/app/core/security.py
 * (bcrypt hash + JWT, RFC 6238 uyumlu altyapıya hazır) ile üretim
 * kalitesinde kimlik doğrulama yapılır. Parola bu dosyadan HİÇBİR ZAMAN
 * düz metin olarak saklanmaz; yalnızca HTTPS/backend'e iletilir, backend
 * bcrypt ile hash'ler (bkz. core/security.py sifre_hashle).
 */
import { girisYapApi, kayitOlApi, benGetirApi, sifreDegistirApi, emailDegistirApi } from "./api";
import { tokenYaz, tokenSil, apiHataMesaji } from "./api-client";
import type { Kullanici } from "./domain";

export type KayitSonucu = { basarili: true; kullanici: Kullanici } | { basarili: false; hata: string };
export type GirisSonucu = { basarili: true; kullanici: Kullanici } | { basarili: false; hata: string };

export async function hesapOlustur(
  email: string,
  sifre: string,
  sifreTekrar: string,
  kurum: string,
  sektor: string,
): Promise<KayitSonucu> {
  try {
    const token = await kayitOlApi(email, sifre, sifreTekrar, kurum, sektor);
    tokenYaz(token);
    const kullanici = await benGetirApi();
    return { basarili: true, kullanici };
  } catch (hata) {
    return { basarili: false, hata: apiHataMesaji(hata, "Kurum hesabı oluşturulamadı.") };
  }
}

export async function girisYap(email: string, sifre: string): Promise<GirisSonucu> {
  try {
    const token = await girisYapApi(email, sifre);
    tokenYaz(token);
    const kullanici = await benGetirApi();
    return { basarili: true, kullanici };
  } catch (hata) {
    return { basarili: false, hata: apiHataMesaji(hata, "E-posta veya şifre hatalı.") };
  }
}

export function oturumuKapat() {
  tokenSil();
}

export async function sifreDegistir(
  mevcutSifre: string,
  yeniSifre: string,
  yeniSifreTekrar: string,
): Promise<{ basarili: boolean; hata?: string }> {
  try {
    await sifreDegistirApi(mevcutSifre, yeniSifre, yeniSifreTekrar);
    return { basarili: true };
  } catch (hata) {
    return { basarili: false, hata: apiHataMesaji(hata, "Şifre güncellenemedi.") };
  }
}

export async function emailDegistir(
  yeniEmail: string,
  mevcutSifre: string,
): Promise<{ basarili: boolean; hata?: string; yeniEmail?: string }> {
  try {
    const token = await emailDegistirApi(yeniEmail, mevcutSifre);
    tokenYaz(token);
    return { basarili: true, yeniEmail };
  } catch (hata) {
    return { basarili: false, hata: apiHataMesaji(hata, "E-posta güncellenemedi.") };
  }
}
