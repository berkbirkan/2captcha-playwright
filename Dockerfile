# Playwright'in resmi imajını baz alıyoruz
FROM mcr.microsoft.com/playwright/python:v1.32.3-focal

# Çalışma dizinini oluştur
WORKDIR /app

# Gerekli dosyaları kopyala
COPY requirements.txt .
COPY 2captcha-solver /app/2captcha-solver
COPY app.py .
# images klasörünü de oluşturmak istersek
RUN mkdir -p /app/images

# Python paketlerini kur
RUN pip install --no-cache-dir -r requirements.txt

# (Opsiyonel) Playwright için ek kurulumlar - genelde resmi imajda gerek kalmaz.
# RUN playwright install-deps
# RUN playwright install

# Flask uygulaması 5000 portunda çalışacak
EXPOSE 5000

# Container çalıştığında app.py'yi başlat
CMD ["python", "app.py"]
