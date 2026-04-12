import os
import json
import subprocess
import signal
import threading
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_PROCESS = None
BOT_LOGS = []
MAX_LOGS = 2000

# Path configuration
BASE_DIR = os.getcwd()
BOT_DIR = os.path.join(BASE_DIR, 'bot_repo')
if os.path.exists(os.path.join(BASE_DIR, 'bot.py')):
    BOT_DIR = BASE_DIR

ACCOUNTS_FILE = os.path.join(BOT_DIR, 'accounts_config.json')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

def add_log(msg):
    global BOT_LOGS
    msg = msg.strip()
    if not msg: return
    timestamp = time.strftime('%H:%M:%S')
    BOT_LOGS.append(f"[{timestamp}] {msg}")
    if len(BOT_LOGS) > MAX_LOGS:
        BOT_LOGS.pop(0)
    print(f"[{timestamp}] {msg}")

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(request.json, f, indent=2)
        return jsonify({"success": True})
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"githubRepo": "https://github.com/kuttydevil/pwoliauto.git"})

@app.route('/api/accounts', methods=['GET', 'POST'])
def handle_accounts():
    if request.method == 'POST':
        os.makedirs(BOT_DIR, exist_ok=True)
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(request.json, f, indent=2)
        return jsonify({"success": True})
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        return jsonify({"error": "Engine already active"}), 400
    
    bot_file = 'bot.py'
    if not os.path.exists(os.path.join(BOT_DIR, bot_file)):
        bot_file = 'main.py'
    
    if not os.path.exists(os.path.join(BOT_DIR, bot_file)):
        return jsonify({"error": "Bot script missing. Sync core first."}), 400

    def run_bot():
        global BOT_PROCESS
        add_log(f"Initializing {bot_file} execution...")
        BOT_PROCESS = subprocess.Popen(
            ['python3', bot_file],
            cwd=BOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in iter(BOT_PROCESS.stdout.readline, ''):
            add_log(line)
        BOT_PROCESS.stdout.close()
        return_code = BOT_PROCESS.wait()
        add_log(f"Engine terminated (Code: {return_code})")
        BOT_PROCESS = None

    threading.Thread(target=run_bot, daemon=True).start()
    return jsonify({"success": True})

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    global BOT_PROCESS
    if not BOT_PROCESS:
        return jsonify({"error": "Engine inactive"}), 400
    add_log("Sending termination signal...")
    BOT_PROCESS.send_signal(signal.SIGINT)
    return jsonify({"success": True})

@app.route('/api/bot/status', methods=['GET'])
def get_status():
    return jsonify({"running": BOT_PROCESS is not None and BOT_PROCESS.poll() is None})

@app.route('/api/bot/logs', methods=['GET', 'DELETE'])
def handle_logs():
    global BOT_LOGS
    if request.method == 'DELETE':
        BOT_LOGS = []
        return jsonify({"success": True})
    return jsonify({"logs": BOT_LOGS})

@app.route('/api/bot/pull', methods=['POST'])
def pull_code():
    settings = handle_settings().get_json()
    repo = settings.get('githubRepo', 'https://github.com/kuttydevil/pwoliauto.git')
    add_log(f"Synchronizing core with {repo}...")
    
    if os.path.exists(os.path.join(BOT_DIR, '.git')):
        cmd = f"cd {BOT_DIR} && git pull"
    else:
        cmd = f"rm -rf {BOT_DIR} && git clone {repo} {BOT_DIR}"
    
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        add_log("Sync Complete.")
        return jsonify({"success": True, "output": output})
    except subprocess.CalledProcessError as e:
        add_log(f"Sync Error: {e.output.decode()}")
        return jsonify({"error": e.output.decode()}), 500

@app.route('/api/remote-url', methods=['GET'])
def get_remote_url():
    try:
        with open('.remote_url', 'r') as f:
            return jsonify({"url": f.read().strip()})
    except:
        return jsonify({"url": None})

@app.route('/api/bootstrap', methods=['GET'])
def get_bootstrap():
    return send_file('bootstrap.sh')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
