FROM python:3.11

WORKDIR /app

# Copy your code + extension
COPY requirements.txt .
COPY 2captcha-solver /app/2captcha-solver
COPY app.py .

# Folder for screenshots / gifs
RUN mkdir -p /app/images

# Install Python deps
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir git+https://github.com/browser-use/browser-use.git@main && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright & browsers
RUN playwright install-deps && \
    playwright install

# Expose Streamlit UI port + Flask API port
EXPOSE 8502
EXPOSE 5033

# Launch the Streamlit UI (which in turn spawns Flask on 5032)
ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8502", \
            "--server.address=0.0.0.0"]
