# Geçerli bir Playwright imajı kullanıyoruz
FROM mcr.microsoft.com/playwright/python:v1.51.0-jammy

# Çalışma dizinini oluştur
WORKDIR /app

# Gerekli dosyaları kopyala
COPY requirements.txt .
COPY 2captcha-solver /app/2captcha-solver
COPY app.py .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir git+https://github.com/browser-use/browser-use.git@main && \
    pip install --no-cache-dir -r requirements.txt
# images klasörünü de oluştur
RUN mkdir -p /app/images

# Python paketlerini kur
RUN pip install --no-cache-dir -r requirements.txt

# (Opsiyonel) Playwright için ek kurulumlar - genelde resmi imajda gerek kalmaz.
# RUN playwright install-deps
# RUN playwright install

# Flask uygulaması 5000 portunda çalışacak
EXPOSE 5031

# Container çalıştığında app.py'yi başlat
CMD ["python", "app.py"]
