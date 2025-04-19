import os
import re
import sys
import traceback
import asyncio
import io

from flask import Flask, request, jsonify, send_from_directory
from playwright.sync_api import sync_playwright  # Eski yapıdan kalan, gerekli olursa kullanılabilir
from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser, Controller
from dotenv import load_dotenv

import streamlit as st  # <-- Streamlit UI

# ──────────────────────────────────────────────────────────────────────────────
# Load env
load_dotenv()
os.environ.setdefault("LLM_API_KEY",     os.getenv("LLM_API_KEY", ""))
os.environ.setdefault("PLANNER_API_KEY", os.getenv("PLANNER_API_KEY", ""))
os.environ.setdefault("OPENAI_API_KEY",  os.getenv("OPENAI_API_KEY", ""))

app = Flask(__name__, static_folder='images')

# ──────────────────────────────────────────────────────────────────────────────
def modify_config_js(api_key, extension_path):
    config_file_path = os.path.join(extension_path, 'common', 'config.js')
    base = open(config_file_path, 'r', encoding='utf-8').read()
    pat = re.compile(r'(\bapiKey: )(null|".*?"),')
    updated = pat.sub(rf'\1"{api_key}",', base)
    with open(config_file_path, 'w', encoding='utf-8') as f:
        f.write(updated)

def solve_captcha(api_key: str, task: str):
    # 1) update extension config
    ext = os.path.abspath("./2captcha-solver")
    modify_config_js(api_key, ext)

    # 2) launch browser-use browser with the extension
    cfg = BrowserConfig(
        headless=True,
        disable_security=True,
        args=[
            f"--disable-extensions-except={ext}",
            f"--load-extension={ext}",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]
    )
    browser = Browser(config=cfg)
    controller = Controller()
    sensitive = {
        'x_email':    'neuralabz20251asdsadasd@gmail.com',
        'x_password': 'kolokolokolo',
    }

    llm         = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("LLM_API_KEY"))
    planner_llm = ChatOpenAI(model="o3-mini",   api_key=os.getenv("PLANNER_API_KEY"))

    agent = Agent(
        browser=browser,
        task=task,
        llm=llm,
        planner_llm=planner_llm,
        planner_interval=1,
        controller=controller,
        sensitive_data=sensitive
    )

    # run and return the action history
    history = asyncio.run(agent.run())
    return history.model_actions()

# ──────────────────────────────────────────────────────────────────────────────
@app.route('/solve', methods=['GET'])
def solve_endpoint():
    try:
        api_key = request.args.get('api_key')
        task    = request.args.get('task',
               "https://www.google.com/recaptcha/api2/demo adresine gir ve formu doldur...")
        if not api_key:
            return jsonify({"error":"Lütfen api_key parametresini iletin."}), 400

        result = solve_captcha(api_key, task)
        return jsonify({"result": result}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/images/<path:filename>', methods=['GET'])
def serve_images(filename):
    return send_from_directory('images', filename)

# ──────────────────────────────────────────────────────────────────────────────
# Streamlit UI (always runs when you invoke `streamlit run app.py`)
st.set_page_config(page_title="2Captcha Solver", layout="wide")
st.title("🧩 2Captcha Solver")

api_key = st.text_input("🔑 2Captcha API Key", "")
task    = st.text_area("📝 Task (URL or instructions)", "")

if st.button("▶️ Start"):
    log_box = st.empty()
    buf = io.StringIO()
    class TeeLogger:
        def write(self, msg):
            buf.write(msg)
            log_box.text(buf.getvalue())
        def flush(self): pass

    # hijack stdout/stderr so we see live logs
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = TeeLogger()

    try:
        result = solve_captcha(api_key, task)
    finally:
        sys.stdout, sys.stderr = old_out, old_err

    log_box.text(buf.getvalue())
    # show the gif (assuming it lands in images/)
    st.image("images/agent_history.gif", caption="Agent History GIF")
    st.write("**Result:**", result)

# ──────────────────────────────────────────────────────────────────────────────
# Only run Flask when NOT under Streamlit’s own process
if __name__ == "__main__" and "STREAMLIT_SERVER_PORT" not in os.environ:
    app.run(host='0.0.0.0', port=5031, debug=True)
