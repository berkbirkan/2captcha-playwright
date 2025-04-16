# Geçerli bir Python 3.11 imajı kullanıyoruz
FROM python:3.11

# Çalışma dizinini oluştur
WORKDIR /app

# Gerekli dosyaları kopyala
COPY requirements.txt .
COPY 2captcha-solver /app/2captcha-solver
COPY app.py .

# images klasörünü de oluştur
RUN mkdir -p /app/images

# Python paketlerini kur
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir git+https://github.com/browser-use/browser-use.git@main && \
    pip install --no-cache-dir -r requirements.txt

# Playwright bağımlılıklarını yükle
RUN playwright install-deps
RUN playwright install

# Hem Flask hem Streamlit portlarını expose ediyoruz
EXPOSE 5031 8501

# Container çalıştığında Streamlit arayüzünü çalıştırıyoruz.
CMD ["streamlit", "run", "app.py", "--server.port", "8501"]
