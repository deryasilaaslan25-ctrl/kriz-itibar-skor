/**
 * Gerçek backend API istemcisi (Faz 8).
 *
 * Önceki sürümde bu dosya yoktu — frontend tamamen istemci-taraflı
 * simülasyondu (bkz. eski app-context.tsx/data.ts). Artık tüm veri
 * backend/app/main.py (FastAPI) üzerinden gelir.
 *
 * Token saklama kararı: sessionStorage (localStorage DEĞİL). Ödünleşim:
 * sessionStorage sekme kapanınca silinir (kullanıcı her sekme açılışında
 * yeniden giriş yapar) ama localStorage'a göre XSS ile kalıcı token
 * hırsızlığına karşı biraz daha az kalıcıdır. Üretimde en güvenli seçenek
 * backend'in httpOnly+Secure cookie ile token vermesidir (bu, JWT'yi
 * JavaScript'in hiç göremeyeceği şekilde saklar); bu değişiklik backend
 * CORS/cookie yapılandırmasında ek iş gerektirdiğinden bu sürümde
 * sessionStorage ile sınırlı tutulmuştur — bkz. GUNCELLEME_NOTLARI_v3.md.
 */
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://kriz-itibar-skor.onrender.com";

const TOKEN_ANAHTARI = "erken-uyari:token";

export function tokenOku(): string | null {
  return sessionStorage.getItem(TOKEN_ANAHTARI);
}

export function tokenYaz(token: string) {
  sessionStorage.setItem(TOKEN_ANAHTARI, token);
}

export function tokenSil() {
  sessionStorage.removeItem(TOKEN_ANAHTARI);
}

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = tokenOku();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 401 (token geçersiz/süresi dolmuş) alındığında oturumu temizle; bileşenler
// `kullanici === null` durumunu görüp login'e yönlendirir (bkz. App.tsx ProtectedRoute).
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      tokenSil();
    }
    return Promise.reject(error);
  },
);

/** Backend hata yanıtlarından (FastAPI HTTPException {detail: "..."}) okunabilir mesaj çıkarır. */
export function apiHataMesaji(hata: unknown, varsayilan = "Bir hata oluştu, lütfen tekrar deneyin."): string {
  if (axios.isAxiosError(hata)) {
    const detail = hata.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (hata.code === "ERR_NETWORK") return "Sunucuya bağlanılamadı. Backend'in çalıştığından emin olun.";
  }
  return varsayilan;
}
