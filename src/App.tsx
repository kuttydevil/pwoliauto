import { useState, useEffect, useRef } from 'react';
import { Play, Square, Settings, Plus, Trash2, Save, Terminal, Users, Activity, Github, Server, CheckCircle2, XCircle, ChevronRight, Loader2, RefreshCw, Globe, Copy, ExternalLink } from 'lucide-react';
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
  const [remoteUrl, setRemoteUrl] = useState<string | null>(null);
  const [isPulling, setIsPulling] = useState(false);
  const [apiUrl, setApiUrl] = useState(localStorage.getItem('nethunter_api_url') || '');
  const logsEndRef = useRef<HTMLDivElement>(null);

  const apiFetch = (path: string, options?: RequestInit) => fetch(`${apiUrl}${path}`, options);

  const fetchStatus = async () => {
    try {
      const res = await apiFetch('/api/bot/status');
      const data = await res.json();
      setBotStatus(data);
    } catch (e) {}
  };

  const fetchRemoteUrl = async () => {
    try {
      const res = await apiFetch('/api/remote-url');
      const data = await res.json();
      setRemoteUrl(data.url);
    } catch (e) {}
  };

  const fetchLogs = async () => {
    try {
      const res = await apiFetch('/api/bot/logs');
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) {}
  };

  const fetchAccounts = async () => {
    try {
      const res = await apiFetch('/api/accounts');
      const data = await res.json();
      setAccounts(data);
    } catch (e) {}
  };

  const fetchSettings = async () => {
    try {
      const res = await apiFetch('/api/settings');
      const data = await res.json();
      setSettings(data);
    } catch (e) {}
  };

  useEffect(() => {
    fetchStatus();
    fetchAccounts();
    fetchSettings();
    fetchRemoteUrl();
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
    await apiFetch(endpoint, { method: 'POST' });
    fetchStatus();
  };

  const pullCode = async () => {
    setIsPulling(true);
    await apiFetch('/api/bot/pull', { method: 'POST' });
    await fetchLogs();
    setIsPulling(false);
  };

  const saveAccounts = async (newAccounts: any[]) => {
    await apiFetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newAccounts),
    });
    setAccounts(newAccounts);
  };

  const saveSettings = async (newSettings: any) => {
    await apiFetch('/api/settings', {
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
    <div className="min-h-screen bg-surface-900 text-gray-100 font-mono flex overflow-hidden relative">
      <div className="scanline pointer-events-none" />
      
      {/* Sidebar - Technical Rail */}
      <div className="w-64 bg-surface-800 border-r border-brand-primary/20 flex flex-col z-10 relative">
        <div className="p-6 border-b border-brand-primary/20">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded bg-brand-primary/10 border border-brand-primary/30 flex items-center justify-center neon-glow">
              <Server size={18} className="text-brand-primary" />
            </div>
            <h1 className="text-sm font-bold tracking-widest text-brand-primary uppercase">NH-CORE v2.0</h1>
          </div>
          <p className="text-[10px] text-brand-primary/50 font-medium uppercase tracking-[0.2em]">Automated Engine</p>
        </div>
        
        <nav className="flex-1 px-3 py-6 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 rounded text-[11px] font-bold uppercase tracking-widest transition-all duration-300 border",
                  isActive 
                    ? "bg-brand-primary/10 border-brand-primary/40 text-brand-primary neon-glow" 
                    : "border-transparent text-gray-500 hover:text-gray-300 hover:bg-white/5"
                )}
              >
                <Icon size={14} className={cn(isActive ? "text-brand-primary" : "text-gray-600")} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-brand-primary/20 bg-black/20">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className={cn("w-1.5 h-1.5 rounded-full", botStatus.running ? "bg-brand-primary animate-pulse shadow-[0_0_8px_#00ff41]" : "bg-gray-600")} />
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                {botStatus.running ? 'System Online' : 'System Offline'}
              </span>
            </div>
          </div>
          <button
            onClick={toggleBot}
            className={cn(
              "w-full flex items-center justify-center gap-2 px-4 py-3 rounded text-[11px] font-bold uppercase tracking-widest transition-all duration-300",
              botStatus.running 
                ? "bg-red-500/10 border border-red-500/40 text-red-500 hover:bg-red-500/20" 
                : "bg-brand-primary/10 border border-brand-primary/40 text-brand-primary hover:bg-brand-primary/20 neon-glow"
            )}
          >
            {botStatus.running ? <><Square size={14} /> Terminate</> : <><Play size={14} /> Initialize</>}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden relative">
        {/* Header Rail */}
        <header className="h-14 bg-surface-800/80 backdrop-blur-xl border-b border-brand-primary/20 px-8 flex items-center justify-between z-20">
          <div className="flex items-center gap-4 text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em]">
            <span className="text-brand-primary/60">Root</span>
            <ChevronRight size={12} />
            <span className="text-gray-200">{activeTab}</span>
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={pullCode}
              disabled={isPulling}
              className="flex items-center gap-2 px-4 py-1.5 rounded border border-brand-primary/30 text-[10px] font-bold uppercase tracking-widest text-brand-primary hover:bg-brand-primary/10 transition-all disabled:opacity-50"
            >
              {isPulling ? <Loader2 size={12} className="animate-spin" /> : <Github size={12} />}
              Sync Core
            </button>
          </div>
        </header>

        {/* Content Viewport */}
        <main className="flex-1 overflow-auto p-8 bg-[radial-gradient(circle_at_center,rgba(0,255,65,0.03)_0%,transparent_70%)]">
          <div className="max-w-6xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                {/* DASHBOARD VIEW */}
                {activeTab === 'dashboard' && (
                  <div className="space-y-8">
                    <div className="flex items-end justify-between border-b border-brand-primary/10 pb-6">
                      <div>
                        <h2 className="text-2xl font-bold tracking-[0.1em] text-white uppercase">Command Center</h2>
                        <p className="text-brand-primary/40 text-[10px] mt-1 font-bold uppercase tracking-widest">Real-time engine telemetry and node status</p>
                      </div>
                      <div className="flex items-center gap-3 bg-brand-primary/5 border border-brand-primary/20 px-4 py-2 rounded">
                        <div className="w-1.5 h-1.5 rounded-full bg-brand-primary animate-pulse" />
                        <span className="text-[9px] font-bold text-brand-primary uppercase tracking-[0.3em]">Telemetry Active</span>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      {[
                        { label: 'Total Nodes', value: accounts.length, icon: Users, color: 'text-blue-400' },
                        { label: 'Active Threads', value: botStatus.running ? activeWorkers.length : 0, icon: Activity, color: 'text-brand-primary' },
                        { label: 'Engine Load', value: botStatus.running ? '12.4%' : '0.0%', icon: Server, color: 'text-purple-400' },
                        { label: 'Log Stream', value: logs.length > 0 ? 'Active' : 'Idle', icon: Terminal, color: 'text-orange-400' },
                      ].map((stat, i) => (
                        <div key={i} className="bg-surface-800 border border-brand-primary/10 p-5 rounded relative overflow-hidden group hover:border-brand-primary/30 transition-all">
                          <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                            <stat.icon size={48} />
                          </div>
                          <h3 className="text-gray-500 text-[9px] font-bold uppercase tracking-[0.2em] mb-2">{stat.label}</h3>
                          <p className={cn("text-2xl font-bold tracking-tighter", stat.color)}>{stat.value}</p>
                        </div>
                      ))}
                    </div>

                    {/* Remote Access - High Tech Bridge */}
                    {remoteUrl && (
                      <div className="bg-surface-800 border border-brand-primary/20 rounded p-8 relative overflow-hidden neon-glow">
                        <div className="absolute top-0 left-0 w-1 h-full bg-brand-primary" />
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 relative z-10">
                          <div className="flex items-center gap-6">
                            <div className="w-14 h-14 rounded bg-brand-primary/10 border border-brand-primary/30 flex items-center justify-center">
                              <Globe size={28} className="text-brand-primary" />
                            </div>
                            <div>
                              <h3 className="text-lg font-bold text-white uppercase tracking-widest">Secure Remote Bridge</h3>
                              <p className="text-brand-primary/50 text-[10px] font-bold uppercase tracking-widest mt-1">Global encrypted tunnel established</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="bg-black/40 border border-brand-primary/20 px-6 py-3 rounded font-mono text-xs text-brand-primary select-all tracking-wider">
                              {remoteUrl}
                            </div>
                            <button 
                              onClick={() => {
                                navigator.clipboard.writeText(remoteUrl);
                                alert('ENCRYPTED URL COPIED');
                              }}
                              className="p-3 rounded bg-brand-primary/10 border border-brand-primary/30 text-brand-primary hover:bg-brand-primary/20 transition-all active:scale-95"
                            >
                              <Copy size={18} />
                            </button>
                            <a 
                              href={remoteUrl} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="p-3 rounded bg-brand-primary/10 border border-brand-primary/30 text-brand-primary hover:bg-brand-primary/20 transition-all active:scale-95"
                            >
                              <ExternalLink size={18} />
                            </a>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      <div className="lg:col-span-2">
                        <div className="bg-surface-800 border border-brand-primary/20 rounded overflow-hidden">
                          <div className="px-6 py-4 border-b border-brand-primary/10 flex items-center justify-between bg-black/20">
                            <h3 className="text-[11px] font-bold text-gray-300 uppercase tracking-widest">Node Fleet Registry</h3>
                            <span className="text-[9px] font-bold text-brand-primary animate-pulse">SYNCING...</span>
                          </div>
                          <div className="p-4 space-y-2">
                            {accounts.map((acc, i) => {
                              const isActive = activeWorkers.includes(acc.username);
                              return (
                                <div key={i} className="flex items-center justify-between p-3 rounded bg-black/20 border border-brand-primary/5 hover:border-brand-primary/20 transition-all group">
                                  <div className="flex items-center gap-4">
                                    <div className={cn(
                                      "w-8 h-8 rounded border flex items-center justify-center font-bold text-xs",
                                      isActive ? "bg-brand-primary/10 border-brand-primary/40 text-brand-primary" : "bg-gray-800 border-gray-700 text-gray-500"
                                    )}>
                                      {acc.username ? acc.username.charAt(0).toUpperCase() : '?'}
                                    </div>
                                    <div>
                                      <p className="text-xs font-bold text-gray-200 uppercase tracking-widest">@{acc.username || 'unknown'}</p>
                                      <p className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">Target: {acc.target_username}</p>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-6">
                                    <div className="text-right">
                                      <p className={cn("text-[10px] font-bold uppercase tracking-widest", isActive ? "text-brand-primary" : "text-gray-600")}>
                                        {isActive ? 'Executing' : 'Standby'}
                                      </p>
                                    </div>
                                    <div className={cn("w-1.5 h-1.5 rounded-full", isActive ? "bg-brand-primary shadow-[0_0_8px_#00ff41]" : "bg-gray-700")} />
                                  </div>
                                </div>
                              );
                            })}
                            {accounts.length === 0 && <p className="text-center py-12 text-gray-600 text-[10px] font-bold uppercase tracking-[0.3em]">No nodes registered</p>}
                          </div>
                        </div>
                      </div>

                      <div className="space-y-6">
                        <div className="bg-surface-800 border border-brand-primary/20 rounded p-6 relative overflow-hidden">
                          <h3 className="text-[11px] font-bold text-gray-300 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <Github size={14} className="text-brand-primary" />
                            Core Repository
                          </h3>
                          <div className="bg-black/40 p-3 rounded border border-brand-primary/10 mb-6">
                            <p className="text-[10px] text-gray-400 font-mono break-all">
                              {settings.githubRepo || 'Not Configured'}
                            </p>
                          </div>
                          <button 
                            onClick={pullCode}
                            disabled={isPulling}
                            className="w-full py-3 rounded bg-brand-primary/10 border border-brand-primary/40 text-brand-primary text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-brand-primary/20 transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
                          >
                            {isPulling ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                            Force Core Update
                          </button>
                        </div>

                        <div className="bg-surface-800 border border-brand-primary/20 rounded p-6">
                          <h3 className="text-[11px] font-bold text-gray-300 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <Activity size={14} className="text-brand-primary" />
                            System Resources
                          </h3>
                          <div className="space-y-5">
                            {[
                              { label: 'CPU Load', value: botStatus.running ? '12%' : '1%', color: 'bg-brand-primary' },
                              { label: 'Memory', value: botStatus.running ? '248MB' : '42MB', color: 'bg-purple-500' },
                            ].map((res, i) => (
                              <div key={i}>
                                <div className="flex justify-between text-[9px] font-bold uppercase text-gray-500 mb-2 tracking-widest">
                                  <span>{res.label}</span>
                                  <span>{res.value}</span>
                                </div>
                                <div className="h-1 bg-black/40 rounded-full overflow-hidden">
                                  <div className={cn("h-full transition-all duration-1000", res.color, botStatus.running ? "w-[40%]" : "w-[5%]")} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* WORKERS VIEW */}
                {activeTab === 'accounts' && (
                  <div className="space-y-6">
                    <div className="flex justify-between items-center border-b border-brand-primary/10 pb-6">
                      <div>
                        <h2 className="text-2xl font-bold tracking-[0.1em] text-white uppercase">Node Configuration</h2>
                        <p className="text-brand-primary/40 text-[10px] mt-1 font-bold uppercase tracking-widest">Manage worker credentials and automation logic</p>
                      </div>
                      <button
                        onClick={() => {
                          const newAcc = { username: '', password: '', target_username: '', max_reels: 100, repost_interval: 2000, custom_prompt: '' };
                          saveAccounts([...accounts, newAcc]);
                        }}
                        className="flex items-center gap-2 bg-brand-primary/10 border border-brand-primary/40 text-brand-primary px-6 py-2.5 rounded text-[11px] font-bold uppercase tracking-widest hover:bg-brand-primary/20 transition-all neon-glow"
                      >
                        <Plus size={14} /> Add Node
                      </button>
                    </div>

                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                      {accounts.map((acc, index) => (
                        <div key={index} className="bg-surface-800 border border-brand-primary/10 rounded overflow-hidden hover:border-brand-primary/30 transition-all">
                          <div className="px-6 py-3 border-b border-brand-primary/10 bg-black/20 flex justify-between items-center">
                            <div className="flex items-center gap-3">
                              <div className="w-6 h-6 rounded bg-brand-primary/10 border border-brand-primary/30 flex items-center justify-center text-brand-primary font-bold text-[10px]">
                                {acc.username ? acc.username.charAt(0).toUpperCase() : '?'}
                              </div>
                              <span className="text-[11px] font-bold text-gray-200 uppercase tracking-widest">{acc.username || 'Unidentified Node'}</span>
                            </div>
                            <button
                              onClick={() => {
                                const newAccs = [...accounts];
                                newAccs.splice(index, 1);
                                saveAccounts(newAccs);
                              }}
                              className="text-gray-600 hover:text-red-500 transition-colors p-2"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                          
                          <div className="p-6 space-y-6">
                            <div className="grid grid-cols-2 gap-6">
                              {[
                                { label: 'Username', value: acc.username, key: 'username' },
                                { label: 'Password', value: acc.password, key: 'password', type: 'password' },
                                { label: 'Target Profile', value: acc.target_username, key: 'target_username' },
                                { label: 'Interval (ms)', value: acc.repost_interval, key: 'repost_interval', type: 'number' },
                              ].map((field) => (
                                <div key={field.key} className="space-y-2">
                                  <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">{field.label}</label>
                                  <input
                                    type={field.type || 'text'}
                                    value={field.value}
                                    onChange={(e) => {
                                      const newAccs = [...accounts];
                                      (newAccs[index] as any)[field.key] = field.type === 'number' ? parseInt(e.target.value) : e.target.value;
                                      setAccounts(newAccs);
                                    }}
                                    className="w-full bg-black/40 border border-brand-primary/10 rounded px-4 py-2.5 text-xs text-brand-primary focus:outline-none focus:border-brand-primary/40 transition-all font-mono"
                                  />
                                </div>
                              ))}
                            </div>
                            
                            <div className="space-y-2">
                              <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">Logic Strategy (AI Prompt)</label>
                              <textarea
                                value={acc.custom_prompt}
                                onChange={(e) => {
                                  const newAccs = [...accounts];
                                  newAccs[index].custom_prompt = e.target.value;
                                  setAccounts(newAccs);
                                }}
                                rows={4}
                                className="w-full bg-black/40 border border-brand-primary/10 rounded px-4 py-3 text-xs text-brand-primary focus:outline-none focus:border-brand-primary/40 transition-all resize-none font-mono"
                              />
                            </div>

                            <button
                              onClick={() => saveAccounts(accounts)}
                              className="w-full flex items-center justify-center gap-2 bg-brand-primary/5 border border-brand-primary/30 text-brand-primary py-3 rounded text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-brand-primary/10 transition-all"
                            >
                              <Save size={14} /> Commit Configuration
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* LISTENER VIEW */}
                {activeTab === 'listener' && (
                  <div className="h-full flex flex-col space-y-4">
                    <div className="flex justify-between items-center border-b border-brand-primary/10 pb-6">
                      <div>
                        <h2 className="text-2xl font-bold tracking-[0.1em] text-white uppercase">Live Stream</h2>
                        <p className="text-brand-primary/40 text-[10px] mt-1 font-bold uppercase tracking-widest">Encrypted real-time node telemetry</p>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-3 bg-black/40 border border-brand-primary/20 px-4 py-2 rounded">
                          <span className="relative flex h-2 w-2">
                            {botStatus.running && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-primary opacity-75"></span>}
                            <span className={cn("relative inline-flex rounded-full h-2 w-2", botStatus.running ? "bg-brand-primary" : "bg-gray-600")}></span>
                          </span>
                          <span className="text-[10px] font-bold text-brand-primary uppercase tracking-widest">
                            {activeWorkers.length} Active Nodes
                          </span>
                        </div>
                        <button 
                          onClick={() => apiFetch('/api/bot/logs', { method: 'DELETE' }).then(fetchLogs)} 
                          className="text-[9px] font-bold text-gray-500 hover:text-brand-primary uppercase tracking-widest transition-colors"
                        >
                          Wipe Buffer
                        </button>
                      </div>
                    </div>

                    <div className="flex-1 bg-black/60 rounded border border-brand-primary/20 flex flex-col overflow-hidden neon-glow relative">
                      <div className="h-8 bg-surface-800 border-b border-brand-primary/10 flex items-center px-4 gap-2">
                        <div className="flex gap-1.5">
                          <div className="w-2 h-2 rounded-full bg-red-500/50"></div>
                          <div className="w-2 h-2 rounded-full bg-yellow-500/50"></div>
                          <div className="w-2 h-2 rounded-full bg-brand-primary/50"></div>
                        </div>
                        <span className="ml-4 text-[9px] font-bold text-gray-600 uppercase tracking-widest">Stream: /dev/nethunter/core</span>
                      </div>
                      <div className="flex-1 p-6 overflow-auto font-mono text-[12px] leading-relaxed scrollbar-hide">
                        {logs.length === 0 ? (
                          <div className="text-brand-primary/20 animate-pulse">Waiting for handshake...</div>
                        ) : (
                          logs.map((log, i) => {
                            let colorClass = "text-gray-400";
                            if (log.includes('ERROR') || log.includes('FAILED')) colorClass = "text-red-500";
                            else if (log.includes('SUCCESS') || log.includes('OK')) colorClass = "text-brand-primary";
                            else if (log.includes('WARN')) colorClass = "text-yellow-500";
                            else if (log.includes('SYSTEM')) colorClass = "text-magenta-400";

                            const formattedLog = log.replace(/\[@(.*?)\]/g, '<span class="text-brand-primary font-bold">[@$1]</span>');

                            return (
                              <div 
                                key={i} 
                                className={cn("whitespace-pre-wrap break-words py-1 border-l-2 border-transparent hover:border-brand-primary/30 hover:bg-brand-primary/5 pl-3 transition-all", colorClass)}
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

                {/* SETTINGS VIEW */}
                {activeTab === 'settings' && (
                  <div className="space-y-6 max-w-3xl">
                    <div className="border-b border-brand-primary/10 pb-6">
                      <h2 className="text-2xl font-bold tracking-[0.1em] text-white uppercase">System Matrix</h2>
                      <p className="text-brand-primary/40 text-[10px] mt-1 font-bold uppercase tracking-widest">Core engine parameters and network bridge</p>
                    </div>
                    
                    <div className="bg-surface-800 border border-brand-primary/20 rounded p-8 space-y-8">
                      <div className="space-y-6">
                        <div className="space-y-3">
                          <label className="text-[11px] font-bold text-gray-300 uppercase tracking-widest">Core Repository</label>
                          <p className="text-[10px] text-gray-500 uppercase tracking-widest">Source for automation logic and engine updates</p>
                          <input
                            type="text"
                            value={settings.githubRepo}
                            onChange={(e) => setSettings({ ...settings, githubRepo: e.target.value })}
                            placeholder="https://github.com/username/repo.git"
                            className="w-full bg-black/40 border border-brand-primary/10 rounded px-4 py-3 text-xs text-brand-primary focus:outline-none focus:border-brand-primary/40 transition-all font-mono"
                          />
                        </div>
                        
                        <div className="space-y-3 pt-8 border-t border-brand-primary/10">
                          <label className="text-[11px] font-bold text-gray-300 uppercase tracking-widest">Network Bridge URL</label>
                          <p className="text-[10px] text-gray-500 uppercase tracking-widest">Handshake URL for remote dashboard synchronization</p>
                          <input
                            type="text"
                            value={apiUrl}
                            onChange={(e) => {
                              setApiUrl(e.target.value);
                              localStorage.setItem('nethunter_api_url', e.target.value);
                            }}
                            placeholder="https://your-tunnel.trycloudflare.com"
                            className="w-full bg-black/40 border border-brand-primary/10 rounded px-4 py-3 text-xs text-brand-primary focus:outline-none focus:border-brand-primary/40 transition-all font-mono"
                          />
                        </div>

                        <div className="pt-6">
                          <button
                            onClick={() => saveSettings(settings)}
                            className="flex items-center justify-center gap-3 bg-brand-primary/10 border border-brand-primary/40 text-brand-primary px-8 py-3 rounded text-[11px] font-bold uppercase tracking-[0.2em] hover:bg-brand-primary/20 transition-all neon-glow"
                          >
                            <Save size={16} /> Commit System Changes
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
