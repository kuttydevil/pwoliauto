#!/bin/bash
# NETHUNTER CORE - ULTIMATE EDITION v2.0
# PROFESSIONAL SYSTEM DEPLOYMENT SCRIPT

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${BLUE}${BOLD}====================================================${NC}"
echo -e "${BLUE}${BOLD}   _   _      _   _   _                 _           ${NC}"
echo -e "${BLUE}${BOLD}  | \ | | ___| |_| | | |_   _ _ __  | |_ ___ _ __   ${NC}"
echo -e "${BLUE}${BOLD}  |  \| |/ _ \ __| |_| | | | | '_ \ | __/ _ \ '__|  ${NC}"
echo -e "${BLUE}${BOLD}  | |\  |  __/ |_|  _  | |_| | | | || ||  __/ |     ${NC}"
echo -e "${BLUE}${BOLD}  |_| \_|\___|\__|_| |_|\__,_|_| |_| \__\___|_|     ${NC}"
echo -e "${BLUE}${BOLD}                                                    ${NC}"
echo -e "${BLUE}${BOLD}   NETHUNTER CORE - ULTIMATE DEPLOYMENT v2.0        ${NC}"
echo -e "${BLUE}${BOLD}====================================================${NC}"

# Function for professional logging
log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. System Check & Dependency Install
log_info "Performing system integrity check..."

# Enhanced Environment Detection
if [ -d "/data/data/com.termux" ]; then
    log_info "Termux environment detected. Initializing packages..."
    pkg update -y
    pkg install -y python chromium git cloudflared wget -y
    log_success "Termux dependencies installed."
elif command -v apt &> /dev/null; then
    log_info "Kali Linux detected. Synchronizing repositories..."
    sudo apt update -qq
    log_info "Deploying core runtime (Node.js, Python, Git)..."
    sudo apt install -y --no-install-recommends python3 python3-pip wget git -qq
    
    log_info "Deploying headless browser engine..."
    sudo apt install -y chromium -qq || log_warn "Chromium deployment skipped."
    
    if ! command -v cloudflared &> /dev/null; then
        log_info "Cloudflared not found. Deploying ARM64 secure bridge..."
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O cloudflared
        chmod +x cloudflared
        sudo mv cloudflared /usr/local/bin/
        log_success "Secure bridge binary deployed."
    fi
else
    log_error "Unsupported environment. System requires Kali or Termux."
    exit 1
fi

# 2. Workspace Initialization
log_info "Initializing workspace: $(pwd)"

# Detect if we are already inside the repo
if [ -f "bot.py" ]; then
    log_info "Running in 'In-Repo' mode. Skipping clone."
    IS_IN_REPO=true
else
    mkdir -p bot_repo
    IS_IN_REPO=false
fi

## 3. Write api.py (The Python Controller)
log_info "Injecting Core Engine v2.0 (Python Edition)..."
cat << 'EOF' > api.py
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
EOF

# 4. Install Python API dependencies
log_info "Installing API dependencies (Flask, Flask-CORS)..."
pip3 install flask flask-cors --quiet

# 5. Initial Repository Sync
log_info "Synchronizing core repository..."
REPO_URL="https://github.com/kuttydevil/pwoliauto.git"

if [ "$IS_IN_REPO" = true ]; then
    git pull
    log_success "Core updated (Local)."
else
    if [ ! -d "bot_repo/.git" ]; then
        rm -rf bot_repo
        git clone $REPO_URL bot_repo
        log_success "Core synchronized."
    else
        cd bot_repo && git pull && cd ..
        log_success "Core updated."
    fi
fi

# 5.1 Python Dependency Check
if [ "$IS_IN_REPO" = true ]; then
    REQ_FILE="requirements.txt"
else
    REQ_FILE="bot_repo/requirements.txt"
fi

if [ -f "$REQ_FILE" ]; then
    log_info "Installing Python dependencies from $REQ_FILE..."
    pip3 install -r "$REQ_FILE" --quiet || log_warn "Some dependencies failed to install. Check manually."
    log_success "Python environment ready."
fi

# 6. Initialize Secure Bridge
echo -e "${MAGENTA}${BOLD}[*] Establishing Secure Remote Bridge...${NC}"
rm -f .tunnel.log .remote_url
cloudflared tunnel --url http://localhost:3000 > .tunnel.log 2>&1 &

echo -n -e "${CYAN}[WAIT]${NC} Negotiating tunnel..."
for i in {1..45}; do
    sleep 2
    URL=$(grep -o 'https://[-a-z0-9.]*trycloudflare.com' .tunnel.log | head -n 1)
    if [ -n "$URL" ]; then
        echo "$URL" > .remote_url
        echo -e "\n${GREEN}${BOLD}[READY] Bridge established: $URL${NC}"
        break
    fi
    echo -n "."
done

if [ ! -f .remote_url ]; then
    log_error "Bridge negotiation failed. Check .tunnel.log"
fi

echo -e "\n${BLUE}${BOLD}====================================================${NC}"
echo -e "${GREEN}${BOLD}   DEPLOYMENT SUCCESSFUL                            ${NC}"
echo -e "${BLUE}${BOLD}====================================================${NC}"
if [ -f .remote_url ]; then
    echo -e "${CYAN} REMOTE BRIDGE URL:${NC} ${BOLD}$(cat .remote_url)${NC}"
    echo -e "${CYAN} INSTRUCTION:${NC} Use this URL in your Cloudflare Dashboard."
fi
echo -e "${BLUE}${BOLD}====================================================${NC}\n"

log_info "Launching Core Engine (Python API)..."
python3 api.py
