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

  app.get('/server.ts', async (req, res) => {
    try {
      const content = await fs.readFile(path.join(process.cwd(), 'server.ts'), 'utf-8');
      res.setHeader('Content-Type', 'text/plain');
      res.send(content);
    } catch (e) { res.status(500).send('Error reading server.ts'); }
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
    const defaultRepo = 'https://github.com/kuttydevil/pwoliauto.git';
    try {
      const data = await fs.readFile(SETTINGS_FILE, 'utf-8');
      const settings = JSON.parse(data);
      if (!settings.githubRepo || settings.githubRepo.trim() === '') {
        settings.githubRepo = defaultRepo;
      }
      return settings;
    } catch {
      return { githubRepo: defaultRepo };
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
    
    // Simple, aggressive sync: Clone if missing, otherwise force pull
    const exists = await fs.access(path.join(BOT_DIR, '.git')).then(() => true).catch(() => false);
    
    let cmd;
    if (exists) {
      cmd = `cd ${BOT_DIR} && git fetch --all && git reset --hard origin/main`;
    } else {
      cmd = `rm -rf ${BOT_DIR} && git clone ${settings.githubRepo} ${BOT_DIR}`;
    }

    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        addLog(`Sync Warning: ${error.message}. Attempting fresh clone...`);
        exec(`rm -rf ${BOT_DIR} && git clone ${settings.githubRepo} ${BOT_DIR}`, () => finalizeSync());
      } else {
        addLog(`Sync Complete.`);
        finalizeSync();
      }

      function finalizeSync() {
        const reqPath = path.join(BOT_DIR, 'requirements.txt');
        fs.access(reqPath).then(() => {
          addLog("Installing Python dependencies...");
          exec(`pip3 install -r ${reqPath} --quiet`, () => addLog("Python environment ready."));
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
