import re
import os
import sys
import uuid

from playwright.sync_api import sync_playwright


def modify_config_js(api_key, extension_path):
    config_file_path = os.path.join(extension_path, 'common', 'config.js')
    base_config = open(config_file_path).read()
    api_key_pattern = re.compile(r'(\bapiKey: )(null|".*?"),')
    updated_config = api_key_pattern.sub(rf'\1"{api_key}",', base_config)
    with open(config_file_path, 'w+') as f:
        f.write(updated_config)


def set_using_cdp(api_key, browser):
    page = browser.new_page()
    page.goto("chrome://extensions/")
    extension_id = page.query_selector_all('extensions-item')[0].get_attribute('id')
    
    print(f"ID: {extension_id}")
    
    page.evaluate(f"""() => {{
        const inspectLinks = Array.from(document.querySelectorAll('a'));
        const serviceWorkerLink = inspectLinks.find(a => a.textContent.includes('service worker'));
        if (serviceWorkerLink) serviceWorkerLink.click();
    }}""")
    page.wait_for_timeout(2000)
    
    extension_page = browser.new_page()
    extension_page.goto(f"chrome-extension://{extension_id}/options/options.html")
    
    extension_page.evaluate(f"""() => {{
        Config.set({{ apiKey: "{api_key}" }})
    }}""")


def run(pw):
    extension_path = os.path.abspath("./2captcha-solver")
    api_key = sys.argv[1]

    #Method 1
    modify_config_js(api_key, extension_path)
    
    browser = pw.chromium.launch_persistent_context(
        user_data_dir=f"/tmp/{uuid.uuid4()}",
        headless=False, # False kalmali xvfb ile kullanilmali,
        args=[
            f"--disable-extensions-except={extension_path}",
            f"--load-extension={extension_path}",
            "--headless=new",  # eklentileri headlessta kullanmak icin gerekli 
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]
    )

    #Method 2
    set_using_cdp(api_key, browser)
    
    page = browser.new_page()
    page.goto("https://www.google.com/recaptcha/api2/demo")
    page.wait_for_timeout(30000)
    page.screenshot(path="before.png")
    
    #page.locator('//div[contains(@class, "captcha-solver")]//div[contains(., "Solve with 2Captcha")]').click()

    page.wait_for_timeout(20000)
    page.screenshot(path="after.png")
    

with sync_playwright() as pw:
    run(pw)
import os
import re
import sys
import uuid
import random
import string
import traceback

from flask import Flask, request, jsonify, send_from_directory, url_for
from playwright.sync_api import sync_playwright

app = Flask(__name__, static_folder='images')

# 1) config.js dosyasını güncelleyen fonksiyon
def modify_config_js(api_key, extension_path):
    config_file_path = os.path.join(extension_path, 'common', 'config.js')
    base_config = open(config_file_path).read()
    api_key_pattern = re.compile(r'(\bapiKey: )(null|".*?"),')
    updated_config = api_key_pattern.sub(rf'\1"{api_key}",', base_config)
    with open(config_file_path, 'w+') as f:
        f.write(updated_config)

# 2) CDP aracılığıyla uzantıya API key set eden fonksiyon
def set_using_cdp(api_key, browser):
    page = browser.new_page()
    page.goto("chrome://extensions/")
    extension_elements = page.query_selector_all('extensions-item')
    if not extension_elements:
        raise Exception("Herhangi bir extension bulunamadı. Lütfen uzantının yüklendiğinden emin olun.")
    extension_id = extension_elements[0].get_attribute('id')
    
    # Debug amaçlı
    print(f"Extension ID: {extension_id}")
    
    page.evaluate(
        """() => {
            const inspectLinks = Array.from(document.querySelectorAll('a'));
            const serviceWorkerLink = inspectLinks.find(a => a.textContent.includes('service worker'));
            if (serviceWorkerLink) serviceWorkerLink.click();
        }"""
    )
    page.wait_for_timeout(2000)
    
    extension_page = browser.new_page()
    extension_page.goto(f"chrome-extension://{extension_id}/options/options.html")
    
    extension_page.evaluate(
        f"""() => {{
            Config.set({{ apiKey: "{api_key}" }});
        }}"""
    )

# 3) Asıl captcha çözme fonksiyonu
def solve_captcha(api_key):
    extension_path = os.path.abspath("./2captcha-solver")
    
    # (i) config.js güncelle
    modify_config_js(api_key, extension_path)
    
    # Playwright context başlat
    temp_user_data = f"/tmp/{uuid.uuid4()}"
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            user_data_dir=temp_user_data,
            headless=False,  # Headless çalışmazsa Xvfb vs. gerekebilir, ayarlayabilirsiniz.
            args=[
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
                "--headless=new",  # eklentileri headless modda kullanmak için
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        # (ii) API key'i uzantıya set et
        set_using_cdp(api_key, browser)
        
        page = browser.new_page()
        page.goto("https://www.google.com/recaptcha/api2/demo")
        
        # Ekran görüntüsü öncesi
        before_filename = f"before_{random_string(8)}.png"
        before_path = os.path.join("images", before_filename)
        page.wait_for_timeout(3000)  # Örnek 3 saniye bekleme
        page.screenshot(path=before_path)
        
        # Normalde tıklama vb. işlemler
        # page.locator('//div[contains(@class, "captcha-solver")]//div[contains(., "Solve with 2Captcha")]').click()
        
        page.wait_for_timeout(5000)  # 5 saniye bekleme, solver'ı tetiklemiş gibi varsayıyoruz
        
        # Ekran görüntüsü sonrası
        after_filename = f"after_{random_string(8)}.png"
        after_path = os.path.join("images", after_filename)
        page.screenshot(path=after_path)
        
        # Browser kapat
        browser.close()
    
    # before / after isimlerini döndürüyoruz
    return before_filename, after_filename

# Rastgele string oluşturma fonksiyonu
def random_string(length=8):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# images klasöründen dosya servis etmek için helper endpoint
@app.route('/images/<path:filename>', methods=['GET'])
def serve_images(filename):
    return send_from_directory('images', filename)

# Asıl solve endpoint'i
@app.route('/solve', methods=['GET'])
def solve_endpoint():
    try:
        # api_key parametresi GET query'den alınıyor -> /solve?api_key=XXXX
        api_key = request.args.get('api_key', None)
        if not api_key:
            return jsonify({"error": "Lütfen api_key parametresini iletin."}), 400
        
        before_file, after_file = solve_captcha(api_key)
        
        # Görsellerin tam URL'lerini oluşturmak için url_for kullanıyoruz
        before_url = url_for('serve_images', filename=before_file, _external=True)
        after_url = url_for('serve_images', filename=after_file, _external=True)
        
        return jsonify({
            "before_image_url": before_url,
            "after_image_url": after_url
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Flask uygulamasını 0.0.0.0:5000'da başlatalım
    app.run(host='0.0.0.0', port=5000, debug=True)
