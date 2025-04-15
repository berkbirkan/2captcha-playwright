import os
import re
import sys
import uuid
import random
import string
import traceback
import time
import asyncio

from flask import Flask, request, jsonify, send_from_directory, url_for
from playwright.sync_api import sync_playwright  # Eski yapıdan kalan, gerekli olursa kullanılabilir

# Browser-use entegrasyonu için gerekli kütüphaneler
from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser, Controller
from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault("LLM_API_KEY", "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")
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

def solve_captcha(api_key):
    """
    Verilen API key ile öncelikle config.js güncellenir.
    Daha sonra browser-use paketini kullanarak, 2captcha uzantısını yükleyecek
    şekilde browser (agent) oluşturulur. Agent, belirlenen görevi (task) çalıştırır ve
    aksiyon geçmişini (model actions) sonucu olarak döndürür.
    """
    # Uzantı dizinini belirle ve config.js güncellemesi yap
    extension_path = os.path.abspath("./2captcha-solver")
    modify_config_js(api_key, extension_path)
    
    # BrowserUse için yapılandırma: burada 2captcha uzantısını yüklemek için gerekli
    # argümanlar ekleniyor. (Not: BrowserConfig yapılandırmasında args parametresi destekleniyorsa)
    config = BrowserConfig(
        headless=True,  # Operasyonunuzu headless ya da window modunda çalıştırabilirsiniz.
        disable_security=True,
        args=[
            f"--disable-extensions-except={extension_path}",
            f"--load-extension={extension_path}",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]
    )
    
    # Browser-use tarayıcı örneğini oluşturuyoruz
    browser = Browser(config=config)
    
    # AI agent için gerekli bileşenler
    controller = Controller()
    sensitive_data = {'x_email': 'XXX@XXX.com', 'x_password': 'XXX'}
    
    # llm ve planner_llm için API key’lerinizi güvenli şekilde sağlamalısınız;
    # Aşağıdaki örnekte environment değişkenlerinden ya da placeholder değer kullanılmıştır.

    llm = ChatOpenAI(model="gpt-4o-mini",api_key='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')
    planner_llm = ChatOpenAI(model='o3-mini',api_key='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')


    
    # Agent oluşturuluyor; task açıklamasını ihtiyacınıza göre güncelleyin.
    agent = Agent(
        browser=browser,
        task="X.com adresine gir ve yeni bir hesap oluştur. Email olarak x_email adresini gir ve şifre olarak x_password kullan. Eğer captcha çıkarsa Funcaptcha (Arkoselabs) ile çöz. Hesap oluşturma işlemin bittikten sonra @berkbirkan adlı kullanıcının son tweetini bul ve tweeti alıntıla.",
        llm=llm,
        planner_llm=planner_llm,
        planner_interval=1,
        controller=controller,
        sensitive_data=sensitive_data
    )
    
    # Agent asenkron çalıştığından, asyncio.run ile çağırıp tamamlanmasını bekliyoruz.
    history = asyncio.run(agent.run())
    
    # Agent’ın gerçekleştirdiği aksiyonların geçmişini string olarak döndürüyoruz.
    result = history.model_actions()
    return result

#####################################
# Flask Endpoint ve Yardımcı Fonksiyon#
#####################################

@app.route('/solve', methods=['GET'])
def solve_endpoint():
    try:
        api_key = request.args.get('api_key', None)
        if not api_key:
            return jsonify({"error": "Lütfen api_key parametresini iletin."}), 400
        
        result = solve_captcha(api_key)
        
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
# Uygulama Başlatma                   #
#####################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5031, debug=True)
