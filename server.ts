import express from 'express';
import { createServer as createViteServer } from 'vite';
import { spawn, ChildProcess, exec } from 'child_process';
import fs from 'fs/promises';
import path from 'path';

const app = express();
app.use(express.json());

const BOT_DIR = path.join(process.cwd(), 'bot_repo');
const ACCOUNTS_FILE = path.join(BOT_DIR, 'accounts_config.json');
const SETTINGS_FILE = path.join(process.cwd(), 'settings.json');

let botProcess: ChildProcess | null = null;
let botLogs: string[] = [];
const MAX_LOGS = 1000;

function addLog(msg: string) {
  botLogs.push(`[${new Date().toLocaleTimeString()}] ${msg}`);
  if (botLogs.length > MAX_LOGS) botLogs.shift();
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
    : `git clone ${settings.githubRepo} ${BOT_DIR}`;

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

async function startServer() {
  const PORT = 3000;

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
