FROM python:3.12-slim

WORKDIR /app

# libpango/libgdk-pixbuf/libcairo: WeasyPrint'in PDF üretebilmesi için gereklidir
# (Windows'ta bu depoda GTK3 Runtime kurulumuyla eşdeğeri sorun burada çözülür —
# bkz. GUNCELLEME_NOTLARI_v4.md "Bu Ortamda Karşılaşılan Sorunlar" bölümü).
# g++/make: prophet paketi kurulumu sırasında CmdStan (C++ tabanlı Bayes
# örnekleyici) derlemesini tetikleyebilir; bu araçlar olmadan `pip install`
# adımı derleme (build) aşamasında hata verip Docker imajının tamamının
# oluşturulmasını engelleyebilir (bkz. Render deploy hatası: "Exited with
# status 1 while building your code").
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make libpq-dev \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
