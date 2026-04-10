import { useState, useEffect, useRef } from 'react';
import { Play, Square, Settings, Plus, Trash2, Save, Terminal, Users, Activity, Github, Server, CheckCircle2, XCircle, ChevronRight, Loader2 } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { motion, AnimatePresence } from 'motion/react';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'accounts' | 'listener' | 'settings'>('dashboard');
  const [botStatus, setBotStatus] = useState({ running: false });
  const [logs, setLogs] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [settings, setSettings] = useState({ githubRepo: '' });
  const [isPulling, setIsPulling] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/bot/status');
      const data = await res.json();
      setBotStatus(data);
    } catch (e) {}
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/bot/logs');
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) {}
  };

  const fetchAccounts = async () => {
    try {
      const res = await fetch('/api/accounts');
      const data = await res.json();
      setAccounts(data);
    } catch (e) {}
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/settings');
      const data = await res.json();
      setSettings(data);
    } catch (e) {}
  };

  useEffect(() => {
    fetchStatus();
    fetchAccounts();
    fetchSettings();
    const interval = setInterval(() => {
      fetchStatus();
      fetchLogs();
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeTab === 'listener') {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, activeTab]);

  const toggleBot = async () => {
    const endpoint = botStatus.running ? '/api/bot/stop' : '/api/bot/start';
    await fetch(endpoint, { method: 'POST' });
    fetchStatus();
  };

  const pullCode = async () => {
    setIsPulling(true);
    await fetch('/api/bot/pull', { method: 'POST' });
    await fetchLogs();
    setIsPulling(false);
  };

  const saveAccounts = async (newAccounts: any[]) => {
    await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newAccounts),
    });
    setAccounts(newAccounts);
  };

  const saveSettings = async (newSettings: any) => {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newSettings),
    });
    setSettings(newSettings);
  };

  // Parse logs to find active workers
  const activeWorkers = Array.from(new Set(
    logs
      .filter(l => l.includes('[@'))
      .map(l => {
        const match = l.match(/\[@(.*?)\]/);
        return match ? match[1] : null;
      })
      .filter(Boolean)
  ));

  const navItems = [
    { id: 'dashboard', label: 'Overview', icon: Activity },
    { id: 'accounts', label: 'Workers & Accounts', icon: Users },
    { id: 'listener', label: 'Live Listener', icon: Terminal },
    { id: 'settings', label: 'System Settings', icon: Settings },
  ] as const;

  return (
    <div className="min-h-screen bg-[#F5F5F7] text-[#1D1D1F] font-sans flex selection:bg-blue-200">
      {/* Sidebar - Apple/Google Style */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col shadow-sm z-10">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
            <Server size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-gray-900">NetHunter Core</h1>
            <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">Production Env</p>
          </div>
        </div>
        
        <nav className="flex-1 px-4 py-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200",
                  isActive 
                    ? "bg-blue-50 text-blue-700" 
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                )}
              >
                <Icon size={18} className={cn(isActive ? "text-blue-600" : "text-gray-400")} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="p-4 m-4 bg-gray-50 rounded-2xl border border-gray-100">
          <div className="flex items-center gap-2 mb-3">
            <div className={cn("w-2 h-2 rounded-full", botStatus.running ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" : "bg-gray-400")} />
            <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
              {botStatus.running ? 'System Online' : 'System Offline'}
            </span>
          </div>
          <button
            onClick={toggleBot}
            className={cn(
              "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 shadow-sm",
              botStatus.running 
                ? "bg-white border border-gray-200 text-red-600 hover:bg-red-50 hover:border-red-200" 
                : "bg-gray-900 text-white hover:bg-gray-800 hover:shadow-md"
            )}
          >
            {botStatus.running ? <><Square size={16} /> Terminate</> : <><Play size={16} /> Initialize</>}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[#F5F5F7]">
        {/* Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-gray-200 px-8 flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-500">
            <span>NetHunter Core</span>
            <ChevronRight size={14} />
            <span className="text-gray-900 capitalize">{activeTab.replace('-', ' ')}</span>
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={pullCode}
              disabled={isPulling}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium text-gray-700 bg-white border border-gray-200 hover:bg-gray-50 hover:shadow-sm transition-all disabled:opacity-50"
            >
              {isPulling ? <Loader2 size={16} className="animate-spin" /> : <Github size={16} />}
              Sync Repository
            </button>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-6xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                {/* DASHBOARD */}
                {activeTab === 'dashboard' && (
                  <div className="space-y-6">
                    <h2 className="text-2xl font-semibold tracking-tight text-gray-900">System Overview</h2>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 flex flex-col">
                        <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center mb-4">
                          <Users size={20} className="text-blue-600" />
                        </div>
                        <h3 className="text-gray-500 text-sm font-medium mb-1">Configured Workers</h3>
                        <p className="text-3xl font-semibold text-gray-900">{accounts.length}</p>
                      </div>
                      
                      <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 flex flex-col">
                        <div className="w-10 h-10 rounded-full bg-green-50 flex items-center justify-center mb-4">
                          <Activity size={20} className="text-green-600" />
                        </div>
                        <h3 className="text-gray-500 text-sm font-medium mb-1">Active Threads</h3>
                        <p className="text-3xl font-semibold text-gray-900">{botStatus.running ? activeWorkers.length : 0}</p>
                      </div>

                      <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 flex flex-col">
                        <div className="w-10 h-10 rounded-full bg-purple-50 flex items-center justify-center mb-4">
                          <Server size={20} className="text-purple-600" />
                        </div>
                        <h3 className="text-gray-500 text-sm font-medium mb-1">Engine Status</h3>
                        <div className="flex items-center gap-2 mt-1">
                          {botStatus.running ? (
                            <><CheckCircle2 size={24} className="text-green-500" /><span className="text-xl font-semibold text-gray-900">Operational</span></>
                          ) : (
                            <><XCircle size={24} className="text-gray-400" /><span className="text-xl font-semibold text-gray-900">Standby</span></>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                        <h3 className="text-sm font-semibold text-gray-900">Recent System Activity</h3>
                      </div>
                      <div className="p-6">
                        <div className="space-y-3">
                          {logs.slice(-5).map((log, i) => (
                            <div key={i} className="text-sm text-gray-600 font-mono bg-gray-50 px-4 py-2 rounded-lg border border-gray-100">
                              {log}
                            </div>
                          ))}
                          {logs.length === 0 && <p className="text-sm text-gray-400 italic">No recent activity.</p>}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* ACCOUNTS / WORKERS */}
                {activeTab === 'accounts' && (
                  <div className="space-y-6">
                    <div className="flex justify-between items-center">
                      <h2 className="text-2xl font-semibold tracking-tight text-gray-900">Worker Configurations</h2>
                      <button
                        onClick={() => {
                          const newAcc = { username: '', password: '', target_username: '', max_reels: 100, repost_interval: 2000, custom_prompt: '' };
                          saveAccounts([...accounts, newAcc]);
                        }}
                        className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
                      >
                        <Plus size={16} /> Add Worker
                      </button>
                    </div>

                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                      {accounts.map((acc, index) => (
                        <div key={index} className="bg-white rounded-3xl shadow-sm border border-gray-200 overflow-hidden transition-all hover:shadow-md">
                          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-sm">
                                {acc.username ? acc.username.charAt(0).toUpperCase() : '?'}
                              </div>
                              <span className="font-semibold text-gray-900">{acc.username || 'New Worker'}</span>
                            </div>
                            <button
                              onClick={() => {
                                const newAccs = [...accounts];
                                newAccs.splice(index, 1);
                                saveAccounts(newAccs);
                              }}
                              className="text-gray-400 hover:text-red-500 transition-colors p-2 rounded-full hover:bg-red-50"
                            >
                              <Trash2 size={18} />
                            </button>
                          </div>
                          
                          <div className="p-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                              <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Username</label>
                                <input
                                  type="text"
                                  value={acc.username}
                                  onChange={(e) => {
                                    const newAccs = [...accounts];
                                    newAccs[index].username = e.target.value;
                                    setAccounts(newAccs);
                                  }}
                                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                />
                              </div>
                              <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Password</label>
                                <input
                                  type="password"
                                  value={acc.password}
                                  onChange={(e) => {
                                    const newAccs = [...accounts];
                                    newAccs[index].password = e.target.value;
                                    setAccounts(newAccs);
                                  }}
                                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                />
                              </div>
                              <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Target Profile</label>
                                <input
                                  type="text"
                                  value={acc.target_username}
                                  onChange={(e) => {
                                    const newAccs = [...accounts];
                                    newAccs[index].target_username = e.target.value;
                                    setAccounts(newAccs);
                                  }}
                                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                />
                              </div>
                              <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Interval (ms)</label>
                                <input
                                  type="number"
                                  value={acc.repost_interval}
                                  onChange={(e) => {
                                    const newAccs = [...accounts];
                                    newAccs[index].repost_interval = parseInt(e.target.value);
                                    setAccounts(newAccs);
                                  }}
                                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                />
                              </div>
                            </div>
                            
                            <div className="space-y-1.5">
                              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">AI Prompt Strategy</label>
                              <textarea
                                value={acc.custom_prompt}
                                onChange={(e) => {
                                  const newAccs = [...accounts];
                                  newAccs[index].custom_prompt = e.target.value;
                                  setAccounts(newAccs);
                                }}
                                rows={4}
                                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none font-mono text-[13px]"
                              />
                            </div>

                            <div className="pt-2">
                              <button
                                onClick={() => saveAccounts(accounts)}
                                className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-gray-800 transition-colors shadow-sm"
                              >
                                <Save size={16} /> Save Configuration
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                      {accounts.length === 0 && (
                        <div className="col-span-full bg-white rounded-3xl border border-dashed border-gray-300 p-12 text-center">
                          <Users size={48} className="mx-auto text-gray-300 mb-4" />
                          <h3 className="text-lg font-medium text-gray-900 mb-1">No Workers Configured</h3>
                          <p className="text-gray-500 text-sm">Add a worker to start automating accounts.</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* LISTENER / TERMINAL */}
                {activeTab === 'listener' && (
                  <div className="h-full flex flex-col space-y-4">
                    <div className="flex justify-between items-center">
                      <h2 className="text-2xl font-semibold tracking-tight text-gray-900">Live Listener</h2>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full border border-gray-200 shadow-sm">
                          <span className="relative flex h-2.5 w-2.5">
                            {botStatus.running && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                            <span className={cn("relative inline-flex rounded-full h-2.5 w-2.5", botStatus.running ? "bg-green-500" : "bg-gray-400")}></span>
                          </span>
                          <span className="text-xs font-medium text-gray-600">
                            {activeWorkers.length} Active Threads
                          </span>
                        </div>
                        <button 
                          onClick={() => fetch('/api/bot/logs', { method: 'DELETE' }).then(fetchLogs)} 
                          className="text-xs font-medium text-gray-500 hover:text-gray-900 bg-white border border-gray-200 px-3 py-1.5 rounded-full hover:bg-gray-50 transition-colors shadow-sm"
                        >
                          Clear Output
                        </button>
                      </div>
                    </div>

                    <div className="flex-1 bg-[#1E1E1E] rounded-2xl shadow-lg border border-gray-800 flex flex-col overflow-hidden">
                      <div className="h-10 bg-[#2D2D2D] border-b border-gray-800 flex items-center px-4 gap-2">
                        <div className="flex gap-1.5">
                          <div className="w-3 h-3 rounded-full bg-[#FF5F56]"></div>
                          <div className="w-3 h-3 rounded-full bg-[#FFBD2E]"></div>
                          <div className="w-3 h-3 rounded-full bg-[#27C93F]"></div>
                        </div>
                        <span className="ml-4 text-xs font-medium text-gray-400 font-mono">nethunter@core:~</span>
                      </div>
                      <div className="flex-1 p-4 overflow-auto font-mono text-[13px] leading-relaxed">
                        {logs.length === 0 ? (
                          <div className="text-gray-500 italic">Waiting for incoming streams...</div>
                        ) : (
                          logs.map((log, i) => {
                            // Simple syntax highlighting for logs
                            let colorClass = "text-gray-300";
                            if (log.includes('ERROR') || log.includes('FAILED')) colorClass = "text-red-400";
                            else if (log.includes('SUCCESS') || log.includes('OK')) colorClass = "text-green-400";
                            else if (log.includes('WARN')) colorClass = "text-yellow-400";
                            else if (log.includes('INFO')) colorClass = "text-blue-300";

                            // Highlight account tags [@username]
                            const formattedLog = log.replace(/\[@(.*?)\]/g, '<span class="text-purple-400 font-semibold">[@$1]</span>');

                            return (
                              <div 
                                key={i} 
                                className={cn("whitespace-pre-wrap break-words py-0.5 hover:bg-white/5", colorClass)}
                                dangerouslySetInnerHTML={{ __html: formattedLog }}
                              />
                            );
                          })
                        )}
                        <div ref={logsEndRef} />
                      </div>
                    </div>
                  </div>
                )}

                {/* SETTINGS */}
                {activeTab === 'settings' && (
                  <div className="space-y-6 max-w-2xl">
                    <h2 className="text-2xl font-semibold tracking-tight text-gray-900">System Settings</h2>
                    
                    <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-8">
                      <h3 className="text-lg font-medium text-gray-900 mb-6">Repository Configuration</h3>
                      
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-gray-700">GitHub Repository URL</label>
                          <p className="text-sm text-gray-500 mb-2">The core engine will pull updates from this repository.</p>
                          <input
                            type="text"
                            value={settings.githubRepo}
                            onChange={(e) => setSettings({ ...settings, githubRepo: e.target.value })}
                            placeholder="https://github.com/username/repo.git"
                            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                          />
                        </div>
                        
                        <div className="pt-4">
                          <button
                            onClick={() => saveSettings(settings)}
                            className="flex items-center justify-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
                          >
                            <Save size={18} /> Save Configuration
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
