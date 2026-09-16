# Erken Itibar Krizi Tespit Sistemi

TUBITAK 1002 kapsaminda hazirlanmis, kurumlara yonelik erken uyari ve kriz iletisimi karar destek prototipidir.

## Calistirma

```bash
pnpm install
pnpm dev
```

Uretim paketi icin:

```bash
pnpm run build
```

Demo hesabi: `demo@sirket.com.tr` / `Demo1234`

## Prototip siniri

Bu surum simule edilmis iceriklerle calisir. Gercek platform verisi, e-posta gonderimi ve kimlik dogrulama icin bir sunucu tarafi servis; platform izinleri; KVKK uyumu; erisim kayitlari ve insan onay akisi gerekir. Sistem tarafindan uretilen kriz siniflandirmasi ve kamuoyu metinleri nihai karar veya otomatik yayin araci degildir.

## Kalite kontrolleri

- `pnpm run typecheck`: Basarili
- `pnpm run build`: Basarili

