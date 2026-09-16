# NOT (Faz 8/9 düzeltmesi): docker-compose.yml bu dosyaya referans veriyordu
# ancak dosya hiç mevcut değildi — "docker compose up --build" frontend
# servisinde başarısız olurdu. Bu, sistemi gerçekten uçtan uca çalıştırırken
# bulunan ve düzeltilen gerçek bir eksiklikti (bkz. GUNCELLEME_NOTLARI_v4.md).
#
# Geliştirme/demo amaçlı basit bir Vite dev-server konteyneri (üretimde
# statik build + nginx/Vercel/Netlify önerilir, bkz. README.md "Yayınlama").
FROM node:22-slim

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 5173

CMD ["pnpm", "run", "dev"]
