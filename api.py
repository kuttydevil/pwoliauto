import os
import json
import subprocess
import signal
import threading
import time
import socket
import firebase_admin
from firebase_admin import credentials, firestore

# Path configuration
BASE_DIR = os.getcwd()
CONFIG_FILE = os.path.join(BASE_DIR, 'firebase-applet-config.json')

# Load Firebase Config
with open(CONFIG_FILE, 'r') as f:
    fb_config = json.load(f)

# Initialize Firebase Admin
# In this environment, we use the project ID from the config
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': fb_config['projectId'],
})

db = firestore.client(database_id=fb_config.get('firestoreDatabaseId'))

# Worker Identity
WORKER_HOSTNAME = socket.gethostname()
WORKER_PID = os.getpid()
INSTANCE_ID = "default_instance" # This should ideally be passed or discovered

BOT_PROCESS = None
SHUTDOWN_REQUESTED = False

def add_log(level, msg):
    print(f"[{level}] {msg}")
    try:
        db.collection('instances').document(INSTANCE_ID).collection('logs').add({
            'timestamp': firestore.SERVER_TIMESTAMP,
            'level': level,
            'message': msg
        })
    except Exception as e:
        print(f"Failed to log to Firestore: {e}")

def get_bot_info():
    """Fetch bot info from Firestore."""
    doc = db.collection('instances').document(INSTANCE_ID).get()
    if doc.exists:
        return doc.to_dict()
    return {}

def heartbeat():
    """Send periodic heartbeat to Firestore."""
    while not SHUTDOWN_REQUESTED:
        try:
            db.collection('instances').document(INSTANCE_ID).update({
                'lastHeartbeat': firestore.SERVER_TIMESTAMP,
                'workerHostname': WORKER_HOSTNAME,
                'workerPid': WORKER_PID,
                'status': 'running' if BOT_PROCESS and BOT_PROCESS.poll() is None else 'inactive'
            })
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

def on_snapshot(doc_snapshot, changes, read_time):
    global SHUTDOWN_REQUESTED
    for doc in doc_snapshot:
        data = doc.to_dict()
        is_active = data.get('isActive', False)
        
        if is_active and not BOT_PROCESS:
            # Start Bot
            repo = data.get('githubRepo', 'https://github.com/kuttydevil/pwoliauto.git')
            bot_file = data.get('botFile', 'bot.py')
            target_dir = os.path.join(BASE_DIR, 'bot_repo')
            
            # Sync first
            sync_code(repo, target_dir)
            
            # Find bot file
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
            # Stop Bot
            add_log("INFO", "Stopping engine...")
            BOT_PROCESS.send_signal(signal.SIGINT)

def main():
    add_log("INFO", f"NH-Core Nexus Worker starting on {WORKER_HOSTNAME}...")
    
    # Watch the instance document
    doc_ref = db.collection('instances').document(INSTANCE_ID)
    doc_ref.on_snapshot(on_snapshot)
    
    # Start heartbeat thread
    threading.Thread(target=heartbeat, daemon=True).start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        global SHUTDOWN_REQUESTED
        SHUTDOWN_REQUESTED = True
        if BOT_PROCESS:
            BOT_PROCESS.terminate()
        add_log("INFO", "Worker shutting down.")

if __name__ == '__main__':
    main()
