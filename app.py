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

#Method 1 - For Set 2CAPTCHA API Key
def modify_config_js(api_key, extension_path):
    
    config_file_path = os.path.join(extension_path, 'common', 'config.js')
    base_config = open(config_file_path).read()
    api_key_pattern = re.compile(r'(\bapiKey: )(null|".*?"),')
    updated_config = api_key_pattern.sub(rf'\1"{api_key}",', base_config)
    with open(config_file_path, 'w+') as f:
        f.write(updated_config)

#Method 2 - For Set 2CAPTCHA API Key
def set_using_cdp(api_key, browser):
    page = browser.new_page()
    page.goto("chrome://extensions/")
    extension_elements = page.query_selector_all('extensions-item')
    if not extension_elements:
        raise Exception("Herhangi bir extension bulunamadı. Lütfen uzantının yüklendiğinden emin olun.")
    extension_id = extension_elements[0].get_attribute('id')
    
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


def solve_captcha(api_key):
    extension_path = os.path.abspath("./2captcha-solver")
    #Method 1
    #modify_config_js(api_key, extension_path)
    
    temp_user_data = f"/tmp/{uuid.uuid4()}"
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            user_data_dir=temp_user_data,
            headless=False,
            args=[
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
                "--headless=new",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        #Method 2 - For Set 2CAPTCHA API Key
        set_using_cdp(api_key, browser)
        
        page = browser.new_page()
        page.goto("https://www.google.com/recaptcha/api2/demo")
        
        # Ekran görüntüsü öncesi
        before_filename = f"before_{random_string(8)}.png"
        before_path = os.path.join("images", before_filename)
        page.wait_for_timeout(5000)
        page.screenshot(path=before_path)
        
        # Örnek olarak bekleme süresi, gerçek işlemde tıklama vs. eklenebilir.
        page.wait_for_timeout(5000)
        
        # Ekran görüntüsü sonrası
        after_filename = f"after_{random_string(8)}.png"
        after_path = os.path.join("images", after_filename)
        page.screenshot(path=after_path)
        
        browser.close()
    
    return before_filename, after_filename


def random_string(length=8):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@app.route('/images/<path:filename>', methods=['GET'])
def serve_images(filename):
    return send_from_directory('images', filename)


@app.route('/solve', methods=['GET'])
def solve_endpoint():
    try:
        api_key = request.args.get('api_key', None)
        if not api_key:
            return jsonify({"error": "Lütfen api_key parametresini iletin."}), 400
        
        before_file, after_file = solve_captcha(api_key)
        
        before_url = url_for('serve_images', filename=before_file, _external=True)
        after_url = url_for('serve_images', filename=after_file, _external=True)
        
        return jsonify({
            "before_image_url": before_url,
            "after_image_url": after_url
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# Ana işlemde, artık komut satırı argümanı yerine direkt Flask sunucusunu başlatıyoruz.
if __name__ == '__main__':
    # Flask uygulamasını 0.0.0.0:5000 üzerinde başlatıyoruz.
    app.run(host='0.0.0.0', port=5031, debug=True)
