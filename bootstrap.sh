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
    pkg install -y nodejs python chromium git cloudflared wget -y
    log_success "Termux dependencies installed."
elif command -v apt &> /dev/null; then
    log_info "Kali Linux detected. Synchronizing repositories..."
    sudo apt update -qq
    log_info "Deploying core runtime (Node.js, Python, Git)..."
    sudo apt install -y --no-install-recommends nodejs python3 python3-pip wget git -qq
    
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

# 3. Write package.json
cat << 'EOF' > package.json
{
  "name": "nethunter-core-engine",
  "version": "2.0.0",
  "type": "module",
  "scripts": {
    "dev": "tsx server.ts"
  },
  "dependencies": {
    "express": "^4.21.2",
    "cors": "^2.8.5",
    "tsx": "^4.19.2"
  }
}
EOF

# 4. Write server.ts (The Professional Controller)
log_info "Injecting Core Engine v2.0..."
cat << 'EOF' > server.ts
import express from 'express';
import cors from 'cors';
import { spawn, ChildProcess, exec } from 'child_process';
import fs from 'fs/promises';
import path from 'path';

const app = express();
app.use(cors());
app.use(express.json());

// CRITICAL: This route must be defined BEFORE any other middleware or Vite
app.get('/api/bootstrap', async (req, res) => {
  try {
    const bootstrapPath = path.join(process.cwd(), 'bootstrap.sh');
    const content = await fs.readFile(bootstrapPath, 'utf-8');
    res.setHeader('Content-Type', 'text/plain');
    res.send(content);
  } catch (e) {
    res.status(500).send('Bootstrap read error: ' + (e instanceof Error ? e.message : String(e)));
  }
});

const getBotDir = async () => {
  const repoPath = path.join(process.cwd(), 'bot_repo');
  const hasRepo = await fs.access(repoPath).then(() => true).catch(() => false);
  if (hasRepo) return repoPath;
  
  const hasMain = await fs.access(path.join(process.cwd(), 'main.py')).then(() => true).catch(() => false);
  const hasBot = await fs.access(path.join(process.cwd(), 'bot.py')).then(() => true).catch(() => false);
  if (hasMain || hasBot) return process.cwd();
  
  return repoPath; // Default fallback
};

const BOT_DIR = await getBotDir();
const ACCOUNTS_FILE = path.join(BOT_DIR, 'accounts_config.json');
const SETTINGS_FILE = path.join(process.cwd(), 'settings.json');

let botProcess: ChildProcess | null = null;
let botLogs: string[] = [];
const MAX_LOGS = 2000;

const COLORS = {
  reset: "\x1b[0m",
  bright: "\x1b[1m",
  dim: "\x1b[2m",
  blue: "\x1b[34m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  red: "\x1b[31m",
  cyan: "\x1b[36m",
  magenta: "\x1b[35m"
};

function printPro(type: 'INFO' | 'SUCCESS' | 'ERROR' | 'WARN' | 'SYSTEM', message: string) {
  const timestamp = new Date().toLocaleTimeString();
  const color = type === 'SUCCESS' ? COLORS.green : 
                type === 'ERROR' ? COLORS.red : 
                type === 'WARN' ? COLORS.yellow : 
                type === 'SYSTEM' ? COLORS.magenta : COLORS.blue;
  
  console.log(`${COLORS.dim}[${timestamp}]${COLORS.reset} ${COLORS.bright}${color}${type.padEnd(7)}${COLORS.reset} ${message}`);
}

function addLog(msg: string) {
  const cleanMsg = msg.trim();
  if (!cleanMsg) return;

  botLogs.push(`[${new Date().toLocaleTimeString()}] ${cleanMsg}`);
  if (botLogs.length > MAX_LOGS) botLogs.shift();

  if (cleanMsg.toLowerCase().includes('error') || cleanMsg.toLowerCase().includes('failed')) {
    printPro('ERROR', cleanMsg);
  } else if (cleanMsg.toLowerCase().includes('success') || cleanMsg.toLowerCase().includes('completed')) {
    printPro('SUCCESS', cleanMsg);
  } else if (cleanMsg.toLowerCase().includes('warning')) {
    printPro('WARN', cleanMsg);
  } else {
    printPro('INFO', cleanMsg);
  }
}

async function getSettings() {
  try {
    const data = await fs.readFile(SETTINGS_FILE, 'utf-8');
    return JSON.parse(data);
  } catch {
    return { githubRepo: 'https://github.com/kuttydevil/pwoliauto.git' };
  }
}

async function saveSettings(settings: any) {
  await fs.writeFile(SETTINGS_FILE, JSON.stringify(settings, null, 2));
}

app.get('/api/settings', async (req, res) => res.json(await getSettings()));
app.post('/api/settings', async (req, res) => {
  await saveSettings(req.body);
  res.json({ success: true });
});

app.post('/api/bot/pull', async (req, res) => {
  const settings = await getSettings();
  addLog(`Synchronizing core with ${settings.githubRepo}...`);
  
  const exists = await fs.access(path.join(BOT_DIR, '.git')).then(() => true).catch(() => false);
  const mainExists = await fs.access(path.join(BOT_DIR, 'main.py')).then(() => true).catch(() => false);
  const botExists = await fs.access(path.join(BOT_DIR, 'bot.py')).then(() => true).catch(() => false);

  let cmd;
  if (exists && (mainExists || botExists)) {
    // If repo exists and we have an entry point, try to update safely
    cmd = `cd ${BOT_DIR} && git fetch --all && git reset --hard origin/main`;
  } else {
    // If repo is broken or entry point is missing, do a fresh clone
    addLog("Entry point missing or repo corrupted. Performing fresh clone...");
    cmd = `rm -rf ${BOT_DIR} && git clone ${settings.githubRepo} ${BOT_DIR}`;
  }

  exec(cmd, (error, stdout, stderr) => {
    if (error) {
      addLog(`Sync Error: ${error.message}`);
      // Last ditch effort
      const lastDitch = `rm -rf ${BOT_DIR} && git clone ${settings.githubRepo} ${BOT_DIR}`;
      exec(lastDitch, () => finalizeSync());
    } else {
      addLog(`Sync Complete.`);
      finalizeSync();
    }

    function finalizeSync() {
      const reqPath = path.join(BOT_DIR, 'requirements.txt');
      fs.access(reqPath).then(() => {
        addLog("Installing Python dependencies...");
        exec(`pip3 install -r ${reqPath} --quiet`, (pErr) => {
          if (pErr) addLog(`Dependency Warning: ${pErr.message}`);
          else addLog("Python environment synchronized.");
        });
      }).catch(() => {});
      
      if (!res.headersSent) res.json({ success: true, stdout, stderr });
    }
  });
});

app.get('/api/accounts', async (req, res) => {
  try {
    const data = await fs.readFile(ACCOUNTS_FILE, 'utf-8');
    res.json(JSON.parse(data));
  } catch { res.json([]); }
});

app.post('/api/accounts', async (req, res) => {
  try {
    await fs.mkdir(BOT_DIR, { recursive: true });
    await fs.writeFile(ACCOUNTS_FILE, JSON.stringify(req.body, null, 2));
    res.json({ success: true });
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

app.post('/api/bot/start', async (req, res) => {
  if (botProcess) return res.status(400).json({ error: 'Engine already active' });
  
  const mainPath = path.join(BOT_DIR, 'main.py');
  const botPath = path.join(BOT_DIR, 'bot.py');
  
  let scriptToRun = '';
  if (await fs.access(mainPath).then(() => true).catch(() => false)) {
    scriptToRun = 'main.py';
  } else if (await fs.access(botPath).then(() => true).catch(() => false)) {
    scriptToRun = 'bot.py';
  }

  if (!scriptToRun) {
    return res.status(400).json({ error: 'No entry point found (main.py or bot.py). Sync core first.' });
  }

  const startBotProcess = () => {
    addLog(`Initializing ${scriptToRun} execution...`);
    botProcess = spawn('python3', [scriptToRun], { cwd: BOT_DIR });
    botProcess.stdout?.on('data', (d) => d.toString().split('\n').forEach((l: string) => addLog(l)));
    botProcess.stderr?.on('data', (d) => d.toString().split('\n').forEach((l: string) => addLog(`ERROR: ${l}`)));
    botProcess.on('close', (c) => { 
      addLog(`Engine terminated (Code: ${c})`); 
      botProcess = null; 
    });
  };

  addLog('Verifying Python dependencies...');
  const reqPath = path.join(BOT_DIR, 'requirements.txt');
  const hasReqs = await fs.access(reqPath).then(() => true).catch(() => false);
  
  if (hasReqs) {
    exec(`pip3 install -r ${reqPath} --quiet`, (err) => {
      if (err) addLog(`Dependency warning: ${err.message}`);
      startBotProcess();
    });
  } else {
    exec(`pip3 install requests --quiet`, () => startBotProcess());
  }

  res.json({ success: true });
});

app.post('/api/bot/stop', async (req, res) => {
  if (!botProcess) return res.status(400).json({ error: 'Engine inactive' });
  addLog('Sending termination signal...');
  botProcess.kill('SIGINT');
  res.json({ success: true });
});

app.get('/api/bot/status', (req, res) => res.json({ running: !!botProcess }));
app.get('/api/bot/logs', (req, res) => res.json({ logs: botLogs }));
app.delete('/api/bot/logs', (req, res) => { botLogs = []; res.json({ success: true }); });

app.get('/api/remote-url', async (req, res) => {
  try {
    const url = await fs.readFile(path.join(process.cwd(), '.remote_url'), 'utf-8');
    res.json({ url: url.trim() });
  } catch { res.json({ url: null }); }
});

app.get('/api/bootstrap', async (req, res) => {
  try {
    const content = await fs.readFile(path.join(process.cwd(), 'bootstrap.sh'), 'utf-8');
    res.setHeader('Content-Type', 'text/x-sh');
    res.send(content);
  } catch { res.status(500).send('Bootstrap read error'); }
});

const PORT = 3000;
app.listen(PORT, '0.0.0.0', () => {
  console.clear();
  console.log(`\n${COLORS.blue}${COLORS.bright}====================================================${COLORS.reset}`);
  console.log(`${COLORS.blue}${COLORS.bright}   NETHUNTER CORE - ULTIMATE ENGINE v2.0            ${COLORS.reset}`);
  console.log(`${COLORS.blue}${COLORS.bright}====================================================${COLORS.reset}`);
  printPro('SYSTEM', `Engine listening on port ${PORT}`);
  printPro('SYSTEM', `Secure Bridge: Active`);
  
  fs.readFile('.remote_url', 'utf-8').then(url => {
    printPro('SYSTEM', `Public URL: ${COLORS.bright}${COLORS.cyan}${url.trim()}${COLORS.reset}`);
  }).catch(() => {});
  console.log(`${COLORS.dim}----------------------------------------------------${COLORS.reset}\n`);
});
EOF

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

log_info "Launching Core Engine..."
npm install --silent
npm run dev
