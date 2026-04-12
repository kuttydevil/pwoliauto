#!/bin/bash
# NH-CORE NEXUS - CLOUD EDITION v3.0
# FIREBASE-SYNCED DEPLOYMENT SCRIPT

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
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
echo -e "${BLUE}${BOLD}   NH-CORE NEXUS - CLOUD SYNC v3.0                  ${NC}"
echo -e "${BLUE}${BOLD}====================================================${NC}"

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. Environment Check
log_info "Checking environment..."
if [ -d "/data/data/com.termux" ]; then
    log_info "Termux detected."
    pkg update -y && pkg install python git wget -y
else
    log_info "Linux/Kali detected."
    sudo apt update -qq && sudo apt install python3 python3-pip git wget -qq -y
fi

# 2. Inject Firebase Configuration
log_info "Injecting Cloud Credentials..."
cat << 'EOF' > firebase-applet-config.json
{
  "projectId": "gen-lang-client-0297872488",
  "appId": "1:184880251824:web:49fdee9e8905f8ef87cc75",
  "apiKey": "AIzaSyA8nfmH6uEi-DzoBvNZvOm1aGsfYb4f2iY",
  "authDomain": "gen-lang-client-0297872488.firebaseapp.com",
  "firestoreDatabaseId": "ai-studio-c86d9d02-ec7f-4ba9-a1de-474a527264e5",
  "storageBucket": "gen-lang-client-0297872488.firebasestorage.app",
  "messagingSenderId": "184880251824",
  "measurementId": ""
}
EOF

## 3. Install Cloud Dependencies
log_info "Installing Cloud SDK (Requests)..."
pip3 install requests --quiet --break-system-packages || pip3 install requests --quiet

# 4. Inject Nexus Worker
log_info "Injecting Nexus Worker Engine..."
cat << 'EOF' > api.py
import os
import json
import subprocess
import signal
import threading
import time
import socket
import requests

# Path configuration
BASE_DIR = os.getcwd()
CONFIG_FILE = os.path.join(BASE_DIR, 'firebase-applet-config.json')

# Load Firebase Config
with open(CONFIG_FILE, 'r') as f:
    fb_config = json.load(f)

API_KEY = fb_config['apiKey']
PROJECT_ID = fb_config['projectId']
DB_ID = fb_config.get('firestoreDatabaseId', '(default)')
INSTANCE_ID = "default_instance"

# Worker Identity
WORKER_HOSTNAME = socket.gethostname()
WORKER_PID = os.getpid()

BOT_PROCESS = None
SHUTDOWN_REQUESTED = False
AUTH_TOKEN = None
TOKEN_EXPIRY = 0

def get_auth_token():
    global AUTH_TOKEN, TOKEN_EXPIRY
    if AUTH_TOKEN and time.time() < TOKEN_EXPIRY - 60:
        return AUTH_TOKEN
    
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
        resp = requests.post(url, json={"returnSecureToken": True})
        data = resp.json()
        AUTH_TOKEN = data['idToken']
        TOKEN_EXPIRY = time.time() + int(data['expiresIn'])
        return AUTH_TOKEN
    except Exception as e:
        print(f"Auth failed: {e}")
        return None

def add_log(level, msg):
    print(f"[{level}] {msg}")
    token = get_auth_token()
    if not token: return
    
    try:
        url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/{DB_ID}/documents/instances/{INSTANCE_ID}/logs"
        payload = {
            "fields": {
                "timestamp": {"timestampValue": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())},
                "level": {"stringValue": level},
                "message": {"stringValue": msg}
            }
        }
        requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    except Exception as e:
        print(f"Failed to log to Firestore: {e}")

def heartbeat():
    while not SHUTDOWN_REQUESTED:
        token = get_auth_token()
        if token:
            try:
                url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/{DB_ID}/documents/instances/{INSTANCE_ID}?updateMask.fieldPaths=lastHeartbeat&updateMask.fieldPaths=workerHostname&updateMask.fieldPaths=workerPid&updateMask.fieldPaths=status"
                status = 'running' if BOT_PROCESS and BOT_PROCESS.poll() is None else 'inactive'
                payload = {
                    "fields": {
                        "lastHeartbeat": {"timestampValue": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())},
                        "workerHostname": {"stringValue": WORKER_HOSTNAME},
                        "workerPid": {"integerValue": str(WORKER_PID)},
                        "status": {"stringValue": status}
                    }
                }
                requests.patch(url, json=payload, headers={"Authorization": f"Bearer {token}"})
            except Exception as e:
                print(f"Heartbeat failed: {e}")
        time.sleep(30)

def run_bot(bot_file, bot_dir):
    global BOT_PROCESS
    add_log("INFO", f"Initializing {bot_file} execution in {bot_dir}...")
    try:
        BOT_PROCESS = subprocess.Popen(
            ['python3', bot_file],
            cwd=bot_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in iter(BOT_PROCESS.stdout.readline, ''):
            add_log("INFO", line.strip())
        BOT_PROCESS.stdout.close()
        return_code = BOT_PROCESS.wait()
        add_log("INFO", f"Engine terminated (Code: {return_code})")
    except Exception as e:
        add_log("ERROR", f"Bot execution failed: {e}")
    finally:
        BOT_PROCESS = None

def sync_code(repo, target_dir):
    add_log("INFO", f"Synchronizing core with {repo}...")
    if os.path.exists(os.path.join(target_dir, '.git')):
        cmd = f"cd {target_dir} && git pull"
    else:
        cmd = f"git clone {repo} {target_dir}"
    
    try:
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        add_log("INFO", "Sync Complete.")
        
        req_path = os.path.join(target_dir, 'requirements.txt')
        if os.path.exists(req_path):
            add_log("INFO", "Installing Python dependencies...")
            pip_cmd = f"pip3 install -r {req_path} --quiet --break-system-packages || pip3 install -r {req_path} --quiet"
            subprocess.run(pip_cmd, shell=True)
    except Exception as e:
        add_log("ERROR", f"Sync failed: {e}")

def poll_instance():
    last_active_state = None
    while not SHUTDOWN_REQUESTED:
        token = get_auth_token()
        if token:
            try:
                url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/{DB_ID}/documents/instances/{INSTANCE_ID}"
                resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    data = resp.json().get('fields', {})
                    is_active = data.get('isActive', {}).get('booleanValue', False)
                    
                    if is_active != last_active_state:
                        last_active_state = is_active
                        if is_active and not BOT_PROCESS:
                            repo = data.get('githubRepo', {}).get('stringValue', 'https://github.com/kuttydevil/pwoliauto.git')
                            bot_file = data.get('botFile', {}).get('stringValue', 'bot.py')
                            target_dir = os.path.join(BASE_DIR, 'bot_repo')
                            sync_code(repo, target_dir)
                            
                            search_dirs = [BASE_DIR, target_dir, os.path.join(target_dir, 'bot_repo')]
                            found_dir = None
                            for d in search_dirs:
                                if os.path.exists(os.path.join(d, bot_file)):
                                    found_dir = d
                                    break
                            
                            if found_dir:
                                threading.Thread(target=run_bot, args=(bot_file, found_dir), daemon=True).start()
                            else:
                                add_log("ERROR", f"Bot script {bot_file} not found.")
                        
                        elif not is_active and BOT_PROCESS:
                            add_log("INFO", "Stopping engine...")
                            BOT_PROCESS.send_signal(signal.SIGINT)
            except Exception as e:
                print(f"Polling failed: {e}")
        time.sleep(5)

def main():
    add_log("INFO", f"Nexus Worker starting on {WORKER_HOSTNAME}...")
    threading.Thread(target=heartbeat, daemon=True).start()
    poll_instance()

if __name__ == '__main__':
    main()
EOF

echo -e "${GREEN}${BOLD}====================================================${NC}"
echo -e "${GREEN}${BOLD}   DEPLOYMENT SUCCESSFUL                            ${NC}"
echo -e "${GREEN}${BOLD}====================================================${NC}"
echo -e "${CYAN} CLOUD SYNC ACTIVE:${NC} Your device is now connected to the Nexus Cloud."
echo -e "${CYAN} INSTRUCTION:${NC} Use the AI Studio Dashboard to control this node."
echo -e "${GREEN}${BOLD}====================================================${NC}\n"

log_info "Launching Nexus Worker..."
python3 api.py
