FROM python:3.11

WORKDIR /app

COPY requirements.txt .
COPY 2captcha-solver /app/2captcha-solver
COPY app.py .

RUN mkdir -p /app/images

# install Python deps
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Playwright needs these
RUN playwright install-deps
RUN playwright install

# expose both Flask & Streamlit ports
EXPOSE 5031 8501

# start both servers:
#  - Streamlit on 8501 
#  - Flask on 5031
CMD ["sh","-c", \
  "streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.enableCORS=false & " \
  "python app.py"]
