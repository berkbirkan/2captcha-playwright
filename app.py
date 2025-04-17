import os
import re
import sys
import uuid
import random
import string
import traceback
import time
import asyncio
import threading
import queue

from flask import Flask, request, jsonify, send_from_directory, url_for
from playwright.sync_api import sync_playwright  # Eski yapıdan kalan, gerekli olursa kullanılabilir

# Browser-use entegrasyonu için gerekli kütüphaneler
from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser, Controller
from dotenv import load_dotenv
load_dotenv()

# Ortak API key değerlerini environment değişkenine ayarlıyoruz
os.environ.setdefault("LLM_API_KEY", "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")  # kısaltıldı
os.environ.setdefault("PLANNER_API_KEY", "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")
os.environ.setdefault("OPENAI_API_KEY", "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")

app = Flask(__name__, static_folder='images')

##############################################
# 2CAPTCHA UZANTISI İÇİN ORJİNAL YAPI (Method 1) #
##############################################

def modify_config_js(api_key, extension_path):
    """
    2captcha uzantısının config.js dosyasındaki apiKey ayarını günceller.
    """
    config_file_path = os.path.join(extension_path, 'common', 'config.js')
    base_config = open(config_file_path).read()
    api_key_pattern = re.compile(r'(\bapiKey: )(null|".*?"),')
    updated_config = api_key_pattern.sub(rf'\1"{api_key}",', base_config)
    with open(config_file_path, 'w+') as f:
        f.write(updated_config)

##################################################
# AI AGENT İLE 2CAPTCHA YÜKLENMİŞ BROWSER OLUŞTURMA #
##################################################

def solve_captcha(api_key, task=None):
    """
    Verilen API key ve isteğe bağlı task bilgisi ile:
      - 2captcha uzantısı yapılandırılır.
      - Browser-use paketini kullanarak 2captcha uzantılı browser (agent) oluşturulur.
      - Belirlenen görevi (task) çalıştırır, aksiyon geçmişini (model actions) döndürür.
    """
    if task is None:
        task = ("https://www.google.com/recaptcha/api2/demo adresine gir "
                "ve formu doldur. Captchanın çözülmesini bekle. "
                "Captcha çözüldükten sonra submit butonuna tıkla. ")
    
    # Uzantı dizinini belirle ve config.js güncellemesi yap
    extension_path = os.path.abspath("./2captcha-solver")
    modify_config_js(api_key, extension_path)
    
    # Browser-use yapılandırması: 2captcha uzantısını yükleyecek argümanlar
    config = BrowserConfig(
        headless=True,
        disable_security=True,
        args=[
            f"--disable-extensions-except={extension_path}",
            f"--load-extension={extension_path}",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]
    )
    
    # Tarayıcı örneğini oluştur
    browser = Browser(config=config)
    
    # AI agent için gerekli bileşenler
    controller = Controller()
    sensitive_data = {'x_email': 'neuralabz20251asdsadasd@gmail.com', 'x_password': 'kolokolokolo'}
    
    # API key’ler environment ya da doğrudan parametrelerden sağlanmalıdır
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.environ.get("LLM_API_KEY"))
    planner_llm = ChatOpenAI(model='o3-mini', api_key=os.environ.get("PLANNER_API_KEY"))

    # Agent oluşturuluyor, burada task parametresi dinamik olarak kullanılıyor.
    agent = Agent(
        browser=browser,
        task=task,
        llm=llm,
        planner_llm=planner_llm,
        planner_interval=1,
        controller=controller,
        sensitive_data=sensitive_data
    )
    
    # Agent asenkron çalıştığından, asyncio.run ile çağırıp tamamlanmasını bekliyoruz.
    history = asyncio.run(agent.run())
    
    # Örneğin, çalıştırma sırasında agent loglarını veya geçmişini kaydediyorsa (agent_history.gif gibi)
    # sonuç olarak model aksiyonlarını döndürüyoruz.
    result = history.model_actions()
    return result

#####################################
# Flask Endpoint ve Yardımcı Fonksiyon#
#####################################

@app.route('/solve', methods=['GET'])
def solve_endpoint():
    try:
        api_key = request.args.get('api_key', None)
        # Opsiyonel: URL üzerinden task parametresi de alınabilir
        task = request.args.get('task', None)
        if not api_key:
            return jsonify({"error": "Lütfen api_key parametresini iletin."}), 400
        
        result = solve_captcha(api_key, task)
        return jsonify({
            "result": result
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Gerekirse statik dosya (görsel) servisi için endpoint (örn. uzantı logları, screenshot vs.)
@app.route('/images/<path:filename>', methods=['GET'])
def serve_images(filename):
    return send_from_directory('images', filename)

#####################################
# STREAMLIT ARAYÜZÜ İÇİN YARDIMCI KODLAR #
#####################################

# Log mesajlarını yakalayabilmek için basit bir yönlendirici (logger) sınıfı
class StreamLogger:
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def write(self, message):
        if message.strip():
            self.log_queue.put(message)

    def flush(self):
        pass

#####################################
# Eğer streamlit ile çalışıyorsak, Flask’i arka planda başlatıyoruz.
#####################################
def start_flask():
    app.run(host='0.0.0.0', port=5031, debug=False)

try:
    # Eğer streamlit çalışırken bu dosya import ediliyorsa, Flask sunucusunu başlatmak için arka plan thread’i çalıştırıyoruz.
    import streamlit as st
    if not hasattr(st, "flask_started"):
        st.flask_started = True
        threading.Thread(target=start_flask, daemon=True).start()
except ImportError:
    # Streamlit yüklü değilse normal Flask çalışacaktır.
    pass

#####################################
# Streamlit Arayüzü
#####################################
# Bu bölüm, "streamlit run app.py" ile çalıştırıldığında kullanıcı arayüzünü oluşturur.
try:
    import streamlit as st

    st.title("2Captcha Çözücü")
    st.write("Lütfen 2Captcha API Key ve çalıştırmak istediğiniz görevi (task) giriniz.")
    
    api_key_input = st.text_input("2Captcha API Key")
    task_input = st.text_area("Görev (Task)", 
        ("https://www.google.com/recaptcha/api2/demo adresine gir ve formu doldur. "
         "Captchanın çözülmesini bekle. Captcha çözüldükten sonra submit butonuna tıkla."), 
         height=150)
    
    if st.button("Başlat"):
        if not api_key_input.strip():
            st.error("2Captcha API Key girilmelidir!")
        else:
            log_queue = queue.Queue()
            log_container = st.empty()
            log_text = ""
            result_container = st.empty()

            def run_agent_task(api_key, task):
                # stdout'u yönlendirerek canlı log aktarımını sağlıyoruz
                old_stdout = sys.stdout
                sys.stdout = StreamLogger(log_queue)
                try:
                    # solve_captcha çağrısı işlemi gerçekleştirir
                    res = solve_captcha(api_key, task)
                    print("\nİşlem tamamlandı.")
                    return res
                except Exception as ex:
                    print("Hata: ", ex)
                finally:
                    sys.stdout = old_stdout

            # Arka plan thread’i ile işlemi başlatıyoruz
            # Arka plan thread’i ile işlemi başlatıyoruz
            t = threading.Thread(target=run_agent_task, args=(api_key_input, task_input))
            t.start()

            # Log güncellemesi için placeholder oluşturuyoruz
            log_placeholder = st.empty()

            # Thread çalışırken log akışını belirli aralıklarla güncelliyoruz
            while t.is_alive():
                while not log_queue.empty():
                    log_text += log_queue.get()
                # Önce mevcut widget’ı temizleyip, ardından benzersiz key ile yeniden ekliyoruz.
                log_placeholder.empty()
                log_placeholder = st.empty()
                log_placeholder.text_area("Loglar", log_text, height=300, key="log_area_"+str(int(time.time()*1000)))
                time.sleep(1)

            # İşlem bittikten sonra kalan logları da güncelliyoruz
            while not log_queue.empty():
                log_text += log_queue.get()
            log_placeholder.empty()
            log_placeholder = st.empty()
            log_placeholder.text_area("Loglar", log_text, height=300, key="final_log_area")


            # İşlem sonunda agent_history.gif dosyası varsa gösteriyoruz.
            if os.path.exists("agent_history.gif"):
                st.image("agent_history.gif", caption="Agent Geçmişi (agent_history.gif)")
            else:
                st.warning("agent_history.gif dosyası bulunamadı.")
except ImportError:
    # Eğer streamlit import edilmezse bu kısım çalışmaz; normal Flask çalışır.
    pass

#####################################
# Flask Uygulamasını Standart Çalıştırma #
#####################################
if __name__ == '__main__':
    # Eğer dosya direkt python ile çalıştırılırsa, Flask sunucusunu başlatıyoruz.
    # (Streamlit ile çalıştırıldığında streamlit yukarıdaki kodları çalıştıracaktır.)
    if "streamlit" not in sys.argv[0]:
        app.run(host='0.0.0.0', port=5031, debug=True)
