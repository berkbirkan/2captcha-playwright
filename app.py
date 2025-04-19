import os
import re
import asyncio
import threading
import traceback

from flask import Flask, request, jsonify, send_from_directory
from browser_use import Agent, BrowserConfig, Browser, Controller
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import streamlit as st

# ───────────────────────────────────────────────────────────────────────────────
# Load environment variables
load_dotenv()

# ───────────────────────────────────────────────────────────────────────────────
# Flask app for your existing `/solve` endpoint
flask_app = Flask(__name__, static_folder='images')

def modify_config_js(api_key: str, extension_path: str):
    """
    Update the 2captcha extension's common/config.js with the given API key.
    """
    config_file_path = os.path.join(extension_path, 'common', 'config.js')
    base = open(config_file_path, 'r', encoding='utf-8').read()
    pattern = re.compile(r'(\bapiKey: )(null|".*?"),')
    updated = pattern.sub(rf'\1"{api_key}",', base)
    with open(config_file_path, 'w+', encoding='utf-8') as f:
        f.write(updated)

def solve_captcha(api_key: str, task: str):
    """
    1) Patch the 2captcha extension config.
    2) Launch a headless BrowserUse browser with that extension.
    3) Spin up an Agent with your `task` string.
    4) Run, then save an agent_history.gif if supported.
    5) Return model_actions() as a list.
    """
    extension_path = os.path.abspath("./2captcha-solver")
    modify_config_js(api_key, extension_path)

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
    browser = Browser(config=config)
    controller = Controller()

    llm       = ChatOpenAI(model="gpt-4o-mini", api_key='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')
    planner   = ChatOpenAI(model="o3-mini",    api_key='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')

    agent = Agent(
        browser=browser,
        task=task,
        llm=llm,
        planner_llm=planner,
        planner_interval=1,
        controller=controller
    )

    history = asyncio.run(agent.run())

    # if the history object supports saving a GIF:
    if hasattr(history, "save_gif"):
        history.save_gif("agent_history.gif")

    return history.model_actions()

@flask_app.route('/solve', methods=['POST'])
def solve_endpoint():
    """
    Unchanged API endpoint – now expecting JSON POST with {"api_key":..., "task":...}
    """
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        task    = data.get('task')
        if not api_key or not task:
            return jsonify({"error": "Both 'api_key' and 'task' are required"}), 400

        result = solve_captcha(api_key, task)
        return jsonify({"result": result}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@flask_app.route('/images/<path:filename>', methods=['GET'])
def serve_images(filename):
    return send_from_directory('images', filename)

def run_flask():
    # Disable debugger and reloader when running in a background thread
    flask_app.run(host='0.0.0.0', port=5032, debug=False, use_reloader=False, threaded=True)

# launch Flask in a background thread
threading.Thread(target=run_flask, daemon=True).start()

# ───────────────────────────────────────────────────────────────────────────────
# Streamlit UI at “/” (root) on Streamlit’s port
st.set_page_config(page_title="2CAPTCHA Solver", layout="wide")
st.title("🧩 2CAPTCHA Solver")

st.markdown("""
Enter your **2captcha** API key and a free‑form **task** (for example:  
> “Go to https://www.google.com/recaptcha/api2/demo, fill in the form, wait for the captcha to solve, then click submit.”)
""")

api_key = st.text_input("2CAPTCHA API Key", key="api_key")
task    = st.text_area("Agent Task", key="task")

if st.button("🚀 Start Agent"):
    # a spot for live‑updating logs
    log_box = st.empty()
    gif_box = st.empty()

    try:
        log_box.text("Initializing…")
        result = solve_captcha(api_key, task)

        log_box.text("✅ Agent completed!")
        st.subheader("Agent Actions")
        st.write(result)

        if os.path.exists("agent_history.gif"):
            st.subheader("Agent History GIF")
            gif_box.image("agent_history.gif", use_column_width=True)

    except Exception as e:
        st.error(f"❌ Error running agent: {e}")
