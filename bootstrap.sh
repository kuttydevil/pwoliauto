#!/bin/bash
# NETHUNTER CORE - MASTER BOOTSTRAP (PROFESSIONAL GRADE)

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
echo -e "${BLUE}${BOLD}   NETHUNTER CORE - PROFESSIONAL SYSTEM DEPLOY      ${NC}"
echo -e "${BLUE}${BOLD}====================================================${NC}"

# Function for professional logging
log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. Environment Detection & Dependency Install
if command -v apt &> /dev/null; then
    log_info "Kali NetHunter detected. Initializing APT..."
    sudo apt update -qq
    log_info "Installing core dependencies (Node.js, Python, Git)..."
    sudo apt install -y --no-install-recommends nodejs python3 python3-pip wget git -qq
    
    log_info "Installing Chromium engine..."
    sudo apt install -y chromium -qq || log_warn "Chromium install skipped."
    
    if ! command -v cloudflared &> /dev/null; then
        log_info "Cloudflared not found. Deploying ARM64 binary..."
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O cloudflared
        chmod +x cloudflared
        sudo mv cloudflared /usr/local/bin/
        log_success "Cloudflared deployed successfully."
    fi
elif command -v pkg &> /dev/null; then
    log_info "Termux environment detected. Initializing PKG..."
    pkg install -y nodejs python chromium git cloudflared wget -y
else
    log_error "Unknown environment. Manual setup required."
    exit 1
fi

# 2. Create Project Structure
log_info "Configuring workspace structure..."
mkdir -p bot_repo

# 3. Write package.json
cat << 'EOF' > package.json
{
  "name": "nethunter-engine",
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
log_info "Deploying Professional Controller..."
cat << 'EOF' > server.ts
import express from 'express';
import cors from 'cors';
import { createServer as createViteServer } from 'vite';
import { spawn, ChildProcess, exec } from 'child_process';
import fs from 'fs/promises';
import path from 'path';

const app = express();
app.use(cors());
app.use(express.json());

const BOT_DIR = path.join(process.cwd(), 'bot_repo');
const ACCOUNTS_FILE = path.join(BOT_DIR, 'accounts_config.json');
const SETTINGS_FILE = path.join(process.cwd(), 'settings.json');

let botProcess: ChildProcess | null = null;
let botLogs: string[] = [];
const MAX_LOGS = 1000;

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

  // Professional Terminal Output
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

// Ensure settings exist
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

// API Routes
app.get('/api/settings', async (req, res) => {
  res.json(await getSettings());
});

app.post('/api/settings', async (req, res) => {
  await saveSettings(req.body);
  res.json({ success: true });
});

app.post('/api/bot/pull', async (req, res) => {
  const settings = await getSettings();
  if (!settings.githubRepo) {
    return res.status(400).json({ error: 'GitHub repo not configured' });
  }

  addLog(`Pulling from ${settings.githubRepo}...`);
  
  const exists = await fs.access(path.join(BOT_DIR, '.git')).then(() => true).catch(() => false);
  
  const cmd = exists 
    ? `cd ${BOT_DIR} && git pull`
    : `rm -rf ${BOT_DIR} && git clone ${settings.githubRepo} ${BOT_DIR}`;

  exec(cmd, (error, stdout, stderr) => {
    if (error) {
      addLog(`Git Error: ${error.message}`);
      return res.status(500).json({ error: error.message });
    }
    if (stdout) addLog(`Git: ${stdout}`);
    if (stderr) addLog(`Git: ${stderr}`);
    res.json({ success: true, stdout, stderr });
  });
});

app.get('/api/accounts', async (req, res) => {
  try {
    const data = await fs.readFile(ACCOUNTS_FILE, 'utf-8');
    res.json(JSON.parse(data));
  } catch {
    res.json([]);
  }
});

app.post('/api/accounts', async (req, res) => {
  try {
    await fs.mkdir(BOT_DIR, { recursive: true });
    await fs.writeFile(ACCOUNTS_FILE, JSON.stringify(req.body, null, 2));
    res.json({ success: true });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/bot/start', async (req, res) => {
  if (botProcess) {
    return res.status(400).json({ error: 'Bot is already running' });
  }

  const scriptPath = path.join(BOT_DIR, 'bot.py');
  const exists = await fs.access(scriptPath).then(() => true).catch(() => false);
  
  if (!exists) {
    return res.status(400).json({ error: 'bot.py not found. Please pull from GitHub first.' });
  }

  addLog('Starting bot.py...');
  botProcess = spawn('python3', ['bot.py'], { cwd: BOT_DIR });

  botProcess.stdout?.on('data', (data) => {
    const lines = data.toString().split('\n').filter(Boolean);
    lines.forEach((l: string) => addLog(`${l}`));
  });

  botProcess.stderr?.on('data', (data) => {
    const lines = data.toString().split('\n').filter(Boolean);
    lines.forEach((l: string) => addLog(`ERROR: ${l}`));
  });

  botProcess.on('close', (code) => {
    addLog(`Bot process exited with code ${code}`);
    botProcess = null;
  });

  res.json({ success: true });
});

app.post('/api/bot/stop', async (req, res) => {
  if (!botProcess) {
    return res.status(400).json({ error: 'Bot is not running' });
  }
  
  addLog('Stopping bot...');
  botProcess.kill('SIGINT');
  botProcess = null;
  res.json({ success: true });
});

app.get('/api/bot/status', (req, res) => {
  res.json({ running: !!botProcess });
});

app.get('/api/bot/logs', (req, res) => {
  res.json({ logs: botLogs });
});

app.get('/api/remote-url', async (req, res) => {
  try {
    const url = await fs.readFile(path.join(process.cwd(), '.remote_url'), 'utf-8');
    res.json({ url: url.trim() });
  } catch {
    res.json({ url: null });
  }
});

app.delete('/api/bot/logs', (req, res) => {
  botLogs = [];
  res.json({ success: true });
});

app.get('/api/bootstrap', async (req, res) => {
  try {
    const content = await fs.readFile(path.join(process.cwd(), 'bootstrap.sh'), 'utf-8');
    res.setHeader('Content-Type', 'text/x-sh');
    res.send(content);
  } catch (e) {
    res.status(500).send('Error reading bootstrap.sh');
  }
});

async function startServer() {
  const PORT = 3000;

  app.listen(PORT, '0.0.0.0', () => {
    console.clear();
    console.log(`\n${COLORS.blue}${COLORS.bright}====================================================${COLORS.reset}`);
    console.log(`${COLORS.blue}${COLORS.bright}   NETHUNTER CORE - PROFESSIONAL ENGINE v2.0        ${COLORS.reset}`);
    console.log(`${COLORS.blue}${COLORS.bright}====================================================${COLORS.reset}`);
    printPro('SYSTEM', `Engine initialized on port ${PORT}`);
    printPro('SYSTEM', `CORS enabled for remote dashboard access`);
    
    fs.readFile('.remote_url', 'utf-8').then(url => {
      printPro('SYSTEM', `Remote URL: ${COLORS.bright}${COLORS.cyan}${url.trim()}${COLORS.reset}`);
    }).catch(() => {
      printPro('WARN', `Remote URL not found. Run bootstrap.sh to start tunnel.`);
    });
    console.log(`${COLORS.dim}----------------------------------------------------${COLORS.reset}\n`);
  });
}

startServer();
EOF

# 5. Initial Repository Sync
log_info "Syncing automation repository..."
REPO_URL="https://github.com/kuttydevil/pwoliauto.git"
if [ ! -d "bot_repo/.git" ]; then
    rm -rf bot_repo
    git clone $REPO_URL bot_repo
    log_success "Repository cloned successfully."
else
    cd bot_repo && git pull && cd ..
    log_success "Repository updated successfully."
fi

# 6. Initialize Remote Tunnel
echo -e "${MAGENTA}${BOLD}[*] Initializing Secure Remote Bridge...${NC}"
rm -f .tunnel.log .remote_url
cloudflared tunnel --url http://localhost:3000 > .tunnel.log 2>&1 &

echo -n -e "${CYAN}[WAIT]${NC} Generating secure URL..."
for i in {1..20}; do
    sleep 1
    URL=$(grep -o 'https://[-a-z0-9.]*trycloudflare.com' .tunnel.log | head -n 1)
    if [ -n "$URL" ]; then
        echo "$URL" > .remote_url
        echo -e "\n${GREEN}${BOLD}[READY] Tunnel established: $URL${NC}"
        break
    fi
    echo -n "."
done

if [ ! -f .remote_url ]; then
    log_error "Tunnel timeout. Please check .tunnel.log"
fi

echo -e "\n${BLUE}${BOLD}====================================================${NC}"
echo -e "${GREEN}${BOLD}   SYSTEM DEPLOYMENT COMPLETE                       ${NC}"
echo -e "${BLUE}${BOLD}====================================================${NC}"
if [ -f .remote_url ]; then
    echo -e "${CYAN} REMOTE ACCESS URL:${NC} ${BOLD}$(cat .remote_url)${NC}"
    echo -e "${CYAN} ACTION:${NC} Paste this URL into your Cloudflare Settings."
fi
echo -e "${BLUE}${BOLD}====================================================${NC}\n"

log_info "Starting Engine..."
npm install --silent
npm run dev
