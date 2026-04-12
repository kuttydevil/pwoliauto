import express from 'express';
import cors from 'cors';
import { spawn, ChildProcess, exec } from 'child_process';
import fs from 'fs/promises';
import path from 'path';
import { createServer as createViteServer } from 'vite';

async function startServer() {
  const app = express();
  app.use(cors());
  app.use(express.json());

  const BOT_DIR = (await fs.access(path.join(process.cwd(), 'bot.py')).then(() => true).catch(() => false)) 
    ? process.cwd() 
    : path.join(process.cwd(), 'bot_repo');

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
    
    // Use a more robust sync: stash local changes, pull, then re-apply
    const cmd = exists 
      ? `cd ${BOT_DIR} && git add . && git stash && git pull --rebase && git stash pop || true`
      : `rm -rf ${BOT_DIR} && git clone ${settings.githubRepo} ${BOT_DIR}`;

    exec(cmd, (error, stdout, stderr) => {
      if (error && !stdout.includes('Already up to date')) {
        addLog(`Sync Warning (Attempting Force): ${error.message}`);
        // If rebase/pull fails, force a reset to origin
        const forceCmd = `cd ${BOT_DIR} && git fetch --all && git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)`;
        exec(forceCmd, (fErr, fOut) => {
          if (fErr) {
            addLog(`Sync Error: ${fErr.message}`);
            return res.status(500).json({ error: fErr.message });
          }
          addLog("Force Sync Complete.");
          finalizeSync();
        });
      } else {
        addLog(`Sync Complete.`);
        finalizeSync();
      }

      function finalizeSync() {
        // Auto-install dependencies if requirements.txt exists
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
    const scriptPath = path.join(BOT_DIR, 'main.py');
    if (!(await fs.access(scriptPath).then(() => true).catch(() => false))) {
      return res.status(400).json({ error: 'main.py missing. Sync core first.' });
    }

    const startBotProcess = () => {
      addLog('Initializing main.py execution...');
      botProcess = spawn('python3', ['main.py'], { cwd: BOT_DIR });
      botProcess.stdout?.on('data', (d) => d.toString().split('\n').forEach((l: string) => addLog(l)));
      botProcess.stderr?.on('data', (d) => d.toString().split('\n').forEach((l: string) => addLog(`ERROR: ${l}`)));
      botProcess.on('close', (c) => { addLog(`Engine terminated (Code: ${c})`); botProcess = null; });
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

  // Vite middleware for development
  const distPath = path.join(process.cwd(), 'dist');
  const hasDist = await fs.access(distPath).then(() => true).catch(() => false);
  
  if (hasDist) {
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  } else {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  }

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
}

startServer();
