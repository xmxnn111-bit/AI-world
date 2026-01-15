import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Plus,
  Send,
  Settings,
  Square,
  History,
  Menu,
  ChevronRight,
  Sparkles,
  Mic,
  Image as ImageIcon,
  Compass,
  X,
  Globe,
  Trash2,
  MessageSquare,
  Copy,
  RotateCw
} from 'lucide-react';
import { MODELS, WS_URL } from './constants';
import { Model, Message, ViewState } from './types';
import MarkdownRenderer from './components/MarkdownRenderer';

// --- API 配置 ---
const API_BASE = 'http://127.0.0.1:8000/api';

interface ChatSessionSummary {
  id: string;
  title: string;
  model: string;
  updated_at: number;
}

const TRANSLATIONS = {
  zh: {
    landingTitle: 'AI World',
    landingDesc: '下一代智能聚合平台。连接最强大的 AI 模型，实时交互，探索无限可能。',
    startChat: '开始对话',
    newChat: '新对话',
    recent: '最近',
    settings: '设置',
    returnHome: '返回首页',
    currentModel: '当前模型',
    hello: '你好，',
    chatSubtitle: '今天要聊点什么？',
    inputPlaceholder: '输入问题、指令或代码...',
    aiWarning: 'AI World 可能会生成不准确的信息，请务必核实。',
    settingsTitle: '设置',
    language: '语言 / Language',
    close: '关闭',
    connected: '已连接',
    disconnected: '未连接',
    deleteChat: '删除',
    historyItems: []
  },
  en: {
    landingTitle: 'AI World',
    landingDesc: 'Next-generation AI aggregation platform. Connect with the most powerful models, interact in real-time.',
    startChat: 'Start Chat',
    newChat: 'New Chat',
    recent: 'Recent',
    settings: 'Settings',
    returnHome: 'Back to Home',
    currentModel: 'Current Model',
    hello: 'Hello,',
    chatSubtitle: 'How can I help you today?',
    inputPlaceholder: 'Enter a prompt here...',
    aiWarning: 'AI Nexus may display inaccurate info, so double-check its responses.',
    settingsTitle: 'Settings',
    language: 'Language',
    close: 'Close',
    connected: 'Connected',
    disconnected: 'Disconnected',
    deleteChat: 'Delete',
    historyItems: []
  }
};

type LangType = 'zh' | 'en';

const App: React.FC = () => {
  // --- 状态管理 ---
  const [view, setView] = useState<ViewState>(() => {
    const savedView = localStorage.getItem('app_view');
    return (savedView as ViewState) || ViewState.LANDING;
  });

  const [selectedModel, setSelectedModel] = useState<Model>(MODELS[0]);

  // Key: Model ID, Value: Message[]
  const [conversations, setConversations] = useState<Record<string, Message[]>>({});
  const [typingStatus, setTypingStatus] = useState<Record<string, boolean>>({});

  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // 历史记录 API 相关
  const [historyList, setHistoryList] = useState<ChatSessionSummary[]>([]);

  const [currentChatId, setCurrentChatId] = useState<string | null>(() => {
    return localStorage.getItem('current_chat_id');
  });

  const [lang, setLang] = useState<LangType>('zh');
  const [showSettings, setShowSettings] = useState(false);

  const t = (key: keyof typeof TRANSLATIONS['zh']) => TRANSLATIONS[lang][key];

  const socketRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const currentChatIdRef = useRef(currentChatId);

  // === 1. 新增：智能滚动开关 ===
  const shouldAutoScrollRef = useRef(true);

  const currentMessages = useMemo(() => {
    return conversations[selectedModel.id] || [];
  }, [conversations, selectedModel.id]);

  const isCurrentModelTyping = useMemo(() => {
    return typingStatus[selectedModel.id] || false;
  }, [typingStatus, selectedModel.id]);

  // --- 持久化副作用 ---
  useEffect(() => {
    localStorage.setItem('app_view', view);
  }, [view]);

  useEffect(() => {
    currentChatIdRef.current = currentChatId;
    if (currentChatId) {
      localStorage.setItem('current_chat_id', currentChatId);
    } else {
      localStorage.removeItem('current_chat_id');
    }
  }, [currentChatId]);

  // --- API 操作 ---
  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history`);
      if (res.ok) setHistoryList(await res.json());
    } catch (err) { console.error(err); }
  };

  const loadChatSession = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/history/${id}`);
      if (res.ok) {
        const data = await res.json();
        if (data.model !== selectedModel.id) {
          const targetModel = MODELS.find(m => m.id === data.model);
          if (targetModel) setSelectedModel(targetModel);
        }

        setConversations(prev => ({
          ...prev,
          [data.model]: data.messages || []
        }));

        setCurrentChatId(data.id);
        // === 2. 强制滚动 ===
        shouldAutoScrollRef.current = true;
        if (view === ViewState.LANDING) setView(ViewState.CHAT);
      }
    } catch (err) { console.error(err); }
  };

  const deleteChatSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure?')) return;
    try {
      await fetch(`${API_BASE}/history/${id}`, { method: 'DELETE' });
      if (currentChatId === id) startNewChat();
      fetchHistory();
    } catch (err) { console.error(err); }
  };

  const saveCurrentChatToBackend = async (msgs: Message[], modelId: string, chatId: string | null) => {
    if (msgs.length === 0) return;
    const id = chatId || `chat_${Date.now()}`;
    if (!chatId) setCurrentChatId(id);
    const firstUserMsg = msgs.find(m => m.role === 'user');
    const title = firstUserMsg ? firstUserMsg.content.slice(0, 20) : 'New Chat';
    try {
      await fetch(`${API_BASE}/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id, title, model: modelId, messages: msgs, updated_at: Date.now() / 1000
        })
      });
      fetchHistory();
    } catch (err) { console.error(err); }
  };

  // --- 初始化逻辑 ---
  useEffect(() => {
    fetchHistory();
    if (view === ViewState.CHAT && currentChatId) {
      loadChatSession(currentChatId);
    }
  }, []);

  // === 3. 新增：滚动监听函数 ===
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    // 阈值设为 100px，如果距离底部超过 100px，则停止自动滚动
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
    shouldAutoScrollRef.current = isAtBottom;
  };

  // === 4. 修改：智能自动滚动 ===
  useEffect(() => {
    if (scrollRef.current && shouldAutoScrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentMessages, isCurrentModelTyping]);

  // --- WebSocket 核心逻辑 ---
  const connectWebSocket = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => setIsConnected(true);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const targetModel = data.model;
      if (!targetModel) return;

      if (data.type === 'done' || data.type === 'error') {
        setTypingStatus(prev => ({ ...prev, [targetModel]: false }));
        return;
      }

      if (data.type === 'chunk') {
        const chunk = data.content;
        setConversations(prev => {
          const modelMsgs = prev[targetModel] || [];
          const lastMsg = modelMsgs[modelMsgs.length - 1];
          let newModelMsgs;
          if (lastMsg && lastMsg.role === 'assistant') {
            newModelMsgs = [...modelMsgs];
            newModelMsgs[newModelMsgs.length - 1] = { ...lastMsg, content: chunk };
          } else {
            newModelMsgs = [...modelMsgs, { role: 'assistant', content: chunk, timestamp: Date.now() }];
          }
          return { ...prev, [targetModel]: newModelMsgs };
        });
      }
    };

    socket.onerror = () => setIsConnected(false);
    socket.onclose = () => { setIsConnected(false); setTimeout(connectWebSocket, 3000); };
    socketRef.current = socket;
  }, []);

  useEffect(() => {
    if (view === ViewState.CHAT) connectWebSocket();
    return () => socketRef.current?.close();
  }, [view, connectWebSocket]);

  useEffect(() => {
    if (!isCurrentModelTyping && currentMessages.length > 0) {
      saveCurrentChatToBackend(currentMessages, selectedModel.id, currentChatIdRef.current);
    }
  }, [isCurrentModelTyping]);


  // --- 交互逻辑 ---

  const startNewChat = () => {
    setConversations(prev => ({ ...prev, [selectedModel.id]: [] }));
    setCurrentChatId(null);
    shouldAutoScrollRef.current = true; // 强制滚动
    setInput('');
  };

  const handleModelChange = (model: Model) => {
    if (selectedModel.id !== model.id) {
      setSelectedModel(model);
      setCurrentChatId(null);
      shouldAutoScrollRef.current = true; // 强制滚动
    }
  };

  const handleSendMessage = () => {
    if (isCurrentModelTyping) {
      if (socketRef.current) {
        socketRef.current.send(JSON.stringify({ type: 'stop', model: selectedModel.id }));
      }
      setTypingStatus(prev => ({ ...prev, [selectedModel.id]: false }));
      return;
    }

    if (!input.trim() || !isConnected) return;

    // 强制滚动到底部
    shouldAutoScrollRef.current = true;

    const userMessage: Message = { role: 'user', content: input, timestamp: Date.now() };

    const nextMessages = [...(conversations[selectedModel.id] || []), userMessage];
    setConversations(prev => ({
      ...prev,
      [selectedModel.id]: nextMessages
    }));

    setTypingStatus(prev => ({ ...prev, [selectedModel.id]: true }));

    if (socketRef.current) {
      socketRef.current.send(JSON.stringify({
        type: 'chat',
        model: selectedModel.id,
        message: input
      }));
    }

    if (!currentChatId) {
      const newId = `chat_${Date.now()}`;
      setCurrentChatId(newId);

      const optimisticHistoryItem: ChatSessionSummary = {
        id: newId,
        title: input.slice(0, 20),
        model: selectedModel.id,
        updated_at: Date.now() / 1000
      };
      setHistoryList(prev => [optimisticHistoryItem, ...prev]);

      saveCurrentChatToBackend(nextMessages, selectedModel.id, newId);
    }

    setInput('');
  };

  // --- 新增：重新生成与复制逻辑 ---
  const handleRegenerate = () => {
    if (isCurrentModelTyping || currentMessages.length === 0) return;

    shouldAutoScrollRef.current = true; // 强制滚动

    const reversedMsgs = [...currentMessages].reverse();
    const lastUserMsgIndex = reversedMsgs.findIndex(m => m.role === 'user');

    if (lastUserMsgIndex === -1) return;

    const realUserIndex = currentMessages.length - 1 - lastUserMsgIndex;
    const lastUserMsg = currentMessages[realUserIndex];

    const newHistory = currentMessages.slice(0, realUserIndex + 1);

    setConversations(prev => ({
      ...prev,
      [selectedModel.id]: newHistory
    }));
    setTypingStatus(prev => ({ ...prev, [selectedModel.id]: true }));

    if (socketRef.current) {
      socketRef.current.send(JSON.stringify({
        type: 'chat',
        model: selectedModel.id,
        message: lastUserMsg.content
      }));
    }
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
  };


  // --- Settings Modal ---
  const SettingsModal = () => {
    if (!showSettings) return null;
    return (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl w-full max-w-sm p-6 shadow-2xl scale-100 animate-in zoom-in-95 duration-200 border border-gray-100">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <Settings className="w-5 h-5" />
                {t('settingsTitle')}
              </h2>
              <button onClick={() => setShowSettings(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-700">
                  <Globe className="w-4 h-4" />
                  <span className="font-medium">{t('language')}</span>
                </div>
                <div className="flex bg-gray-100 p-1 rounded-lg">
                  <button onClick={() => setLang('zh')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${lang === 'zh' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}>中文</button>
                  <button onClick={() => setLang('en')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${lang === 'en' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}>English</button>
                </div>
              </div>
            </div>
            <div className="mt-8 flex justify-end">
              <button onClick={() => setShowSettings(false)} className="px-5 py-2.5 bg-[#1f1f1f] text-white rounded-xl hover:bg-black font-medium transition-colors text-sm">
                {t('close')}
              </button>
            </div>
          </div>
        </div>
    );
  };

  // --- Landing View ---
  if (view === ViewState.LANDING) {
    return (
        <div className="relative h-screen w-full flex flex-col items-center justify-center bg-[#050505] overflow-hidden text-white selection:bg-blue-500/30">
          <SettingsModal />
          <style>{`
          @keyframes blob { 0% { transform: translate(0px, 0px) scale(1); } 33% { transform: translate(30px, -50px) scale(1.1); } 66% { transform: translate(-20px, 20px) scale(0.9); } 100% { transform: translate(0px, 0px) scale(1); } }
          @keyframes textShine { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
          .animate-blob { animation: blob 7s infinite; }
          .animation-delay-2000 { animation-delay: 2s; }
          .animation-delay-4000 { animation-delay: 4s; }
          .animate-text-shine { background-size: 200% auto; animation: textShine 5s linear infinite; }
          .bg-grid-pattern { background-image: linear-gradient(to right, #ffffff05 1px, transparent 1px), linear-gradient(to bottom, #ffffff05 1px, transparent 1px); background-size: 40px 40px; mask-image: radial-gradient(circle at center, black 40%, transparent 100%); }
        `}</style>
          <div className="absolute inset-0 z-0">
            <div className="absolute inset-0 bg-grid-pattern z-0 opacity-60"></div>
            <div className="absolute top-0 -left-4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-40 animate-blob"></div>
            <div className="absolute top-0 -right-4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-40 animate-blob animation-delay-2000"></div>
            <div className="absolute -bottom-32 left-20 w-96 h-96 bg-indigo-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-40 animate-blob animation-delay-4000"></div>
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }}></div>
          </div>
          <div className="absolute top-6 right-6 z-20">
            <button onClick={() => setShowSettings(true)} className="group p-3 text-zinc-400 hover:text-white bg-white/5 hover:bg-white/10 backdrop-blur-md border border-white/5 rounded-full transition-all duration-300 hover:scale-110 hover:shadow-[0_0_20px_rgba(255,255,255,0.1)]">
              <Settings className="w-5 h-5 group-hover:rotate-90 transition-transform duration-500" />
            </button>
          </div>
          <div className="relative z-10 flex flex-col items-center px-4 max-w-4xl mx-auto text-center">
            <div className="mb-8 relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur opacity-25 group-hover:opacity-75 transition duration-1000 group-hover:duration-200"></div>
              <div className="relative bg-black/50 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-2xl ring-1 ring-white/10">
                <Sparkles className="w-12 h-12 text-blue-400 drop-shadow-[0_0_15px_rgba(96,165,250,0.5)]" />
              </div>
            </div>
            <h1 className="text-6xl md:text-8xl font-bold mb-6 tracking-tighter">
              <span className="animate-text-shine bg-clip-text text-transparent bg-[linear-gradient(110deg,#939393,45%,#ffffff,55%,#939393)]">{t('landingTitle')}</span>
            </h1>
            <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-12 font-light leading-relaxed animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-200">{t('landingDesc')}</p>
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-center w-full animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
              <button onClick={() => setView(ViewState.CHAT)} className="relative inline-flex h-14 overflow-hidden rounded-full p-[2px] focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 focus:ring-offset-slate-50 group">
                <span className="absolute inset-[-1000%] animate-[spin_2s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#E2CBFF_0%,#393BB2_50%,#E2CBFF_100%)]" />
                <span className="inline-flex h-full w-full cursor-pointer items-center justify-center rounded-full bg-slate-950 px-8 py-1 text-sm font-medium text-white backdrop-blur-3xl transition-all duration-300 group-hover:bg-slate-900 group-hover:px-10">
                <span className="flex items-center gap-2 text-lg">{t('startChat')}<ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" /></span>
              </span>
              </button>
              <a href="https://github.com" target="_blank" rel="noreferrer" className="px-8 py-4 rounded-full text-zinc-400 hover:text-white border border-white/5 hover:border-white/20 hover:bg-white/5 transition-all duration-300 flex items-center gap-2 text-sm font-medium"><span>了解更多</span></a>
            </div>
            <div className="mt-20 pt-10 border-t border-white/5 w-full max-w-lg animate-in fade-in duration-1000 delay-500">
              <p className="text-xs text-zinc-500 uppercase tracking-widest mb-6 font-semibold">Supported Models</p>
              <div className="flex justify-center gap-6 items-center grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-500">
                {MODELS.map((m) => (
                    <div key={m.id} className="relative group cursor-help">
                      <img src={m.icon} alt={m.name} className="w-8 h-8 rounded-full shadow-lg" />
                      <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-[10px] text-white bg-black/80 px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">{m.name}</span>
                    </div>
                ))}
              </div>
            </div>
          </div>
        </div>
    );
  }

  // --- Chat View ---
  const Sidebar = () => {
    const filteredHistory = historyList.filter(item => item.model === selectedModel.id);

    return (
        <aside className={`flex-shrink-0 bg-[#f8fafe] h-full transition-all duration-300 ease-in-out flex flex-col border-r border-gray-200/50 ${sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'}`}>
          <div className="p-4 flex flex-col h-full">
            <div className="flex items-center justify-between mb-6 px-2">
              <button onClick={() => setSidebarOpen(false)} className="p-2 hover:bg-gray-200/80 rounded-full text-gray-600 transition-colors"><Menu className="w-5 h-5" /></button>
            </div>
            <button onClick={startNewChat} className="group relative flex items-center gap-3 w-full px-4 py-3.5 mb-6 rounded-2xl bg-white border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition-all duration-300 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-50 to-purple-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10 p-1.5 bg-gray-100 rounded-lg group-hover:bg-blue-500 group-hover:text-white transition-colors duration-300"><Plus className="w-4 h-4 transition-transform duration-500 group-hover:rotate-90" /></div>
              <span className="relative z-10 font-medium text-gray-700 group-hover:text-gray-900 transition-colors">{t('newChat')}</span>
            </button>

            <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
              <p className="px-3 text-xs font-medium text-gray-500 mb-2 mt-2 uppercase tracking-wider">{t('recent')}</p>

              {filteredHistory.length === 0 && (
                  <div className="px-3 py-4 text-xs text-gray-400 text-center italic opacity-60">
                    No history for {selectedModel.name}
                  </div>
              )}

              {filteredHistory.map((item) => (
                  <div key={item.id} onClick={() => loadChatSession(item.id)} className={`group flex items-center gap-3 w-full px-3 py-2.5 rounded-full text-sm truncate transition-colors cursor-pointer relative ${currentChatId === item.id ? 'bg-[#d3e3fd] text-[#001d35] font-medium' : 'hover:bg-[#e0e6ed]/50 text-gray-700'}`}>
                    <MessageSquare className={`w-4 h-4 shrink-0 ${currentChatId === item.id ? 'text-blue-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
                    <span className="truncate flex-1 text-left">{item.title}</span>
                    <button onClick={(e) => deleteChatSession(e, item.id)} className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 hover:text-red-500 rounded-full transition-all absolute right-2 bg-white/50 backdrop-blur-sm" title={t('deleteChat')}><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
              ))}
            </div>

            <div className="mt-auto pt-4 border-t border-gray-200/60 space-y-1">
              <button onClick={() => setShowSettings(true)} className="flex items-center gap-3 w-full px-3 py-2.5 rounded-full hover:bg-[#e0e6ed]/50 text-gray-700 text-sm transition-colors"><Settings className="w-4 h-4" /> {t('settings')}</button>
              <button onClick={() => setView(ViewState.LANDING)} className="flex items-center gap-3 w-full px-3 py-2.5 rounded-full hover:bg-[#e0e6ed]/50 text-gray-700 text-sm transition-colors"><ChevronRight className="w-4 h-4 rotate-180" /> {t('returnHome')}</button>
            </div>
          </div>
        </aside>
    );
  };

  return (
      <div className="h-screen w-full flex bg-white text-gray-900 font-[Inter,sans-serif] animate-in fade-in slide-in-from-bottom-8 duration-500">
        <SettingsModal />
        <Sidebar />
        <main className="flex-1 flex flex-col relative h-full min-w-0 bg-white">
          <header className="absolute top-0 left-0 right-0 z-20 flex items-center p-4">
            <div className="absolute left-4 z-30">
              {!sidebarOpen && <button onClick={() => setSidebarOpen(true)} className="p-2.5 hover:bg-gray-100 rounded-full text-gray-600 transition-colors shadow-sm bg-white border border-gray-100"><Menu className="w-5 h-5" /></button>}
            </div>

            <div className="w-full flex justify-center">
              <div className="flex items-center p-1.5 bg-[#f0f4f9]/80 backdrop-blur-md rounded-full shadow-sm border border-white/50 gap-1 overflow-x-auto no-scrollbar max-w-[90%] md:max-w-4xl transition-all duration-300">
                {MODELS.map(model => {
                  const isActive = selectedModel.id === model.id;
                  const isTyping = typingStatus[model.id];
                  return (
                      <button key={model.id} onClick={() => handleModelChange(model)} className={`relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ease-out whitespace-nowrap select-none group ${isActive ? 'bg-white text-[#1f1f1f] shadow-[0_2px_8px_rgba(0,0,0,0.08)] scale-100' : 'text-gray-500 hover:text-gray-900 hover:bg-white/50 scale-95 hover:scale-100'}`}>
                        <img src={model.icon} className={`w-5 h-5 rounded-full object-cover transition-transform duration-300 ${isActive ? 'rotate-0' : 'grayscale group-hover:grayscale-0'}`} alt="" />
                        <span>{model.name}</span>
                        {isTyping && !isActive && <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-white animate-pulse"></span>}
                      </button>
                  );
                })}
              </div>
            </div>
            <div className="absolute right-6 z-30">
              <div className={`w-2.5 h-2.5 rounded-full transition-colors duration-500 ${isConnected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-red-400'}`} title={isConnected ? t('connected') : t('disconnected')}></div>
            </div>
          </header>

          <div
              ref={scrollRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto w-full pt-24 pb-40 px-4 scrollbar-hide"
          >
            {currentMessages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center p-8 max-w-4xl mx-auto animate-in fade-in duration-700">
                  <div className="flex flex-col items-center text-center space-y-8">
                    <div className="relative group">
                      <div className="absolute -inset-4 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full blur-xl opacity-20 group-hover:opacity-40 transition-opacity duration-500 animate-pulse"></div>
                      <div className="relative bg-white/80 backdrop-blur-sm p-5 rounded-3xl shadow-2xl ring-1 ring-gray-100"><Sparkles className="w-12 h-12 text-blue-500" /></div>
                    </div>
                    <div className="space-y-4">
                      <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-gray-300 select-none">{t('hello')}</h1>
                      <h2 className="text-5xl md:text-7xl font-bold tracking-tight bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 bg-clip-text text-transparent pb-2 animate-[pulse_4s_ease-in-out_infinite]">{t('chatSubtitle')}</h2>
                    </div>
                    <div className="pt-4 opacity-0 animate-in slide-in-from-bottom-4 duration-1000 fill-mode-forwards delay-300"><p className="text-gray-400 text-lg font-light flex items-center gap-2"><span>Ready to explore the infinite possibilities?</span></p></div>
                  </div>
                </div>
            ) : (
                <div className="max-w-3xl mx-auto py-4">
                  {currentMessages.map((msg, index) => (
                      <div key={index} className={`mb-8 flex gap-5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                        {msg.role === 'assistant' && (<div className="w-9 h-9 rounded-full flex-shrink-0 mt-1 overflow-hidden border border-gray-100 shadow-sm bg-white p-0.5"><img src={selectedModel.icon} className="w-full h-full object-cover rounded-full" /></div>)}

                        <div className={`max-w-full md:max-w-[85%] lg:max-w-[90%] ${msg.role === 'user' ? 'bg-[#f0f4f9] text-gray-800 rounded-[24px] px-6 py-4 rounded-tr-sm' : 'bg-transparent text-gray-900 px-0 py-0 w-full min-w-0'}`}>

                          {msg.role === 'user' ? (
                              <p className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</p>
                          ) : (
                              <div className="group">
                                <MarkdownRenderer content={msg.content} />

                                {!isCurrentModelTyping && (
                                    <div className="mt-2 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                      <button
                                          onClick={() => handleCopyContent(msg.content)}
                                          className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                                      >
                                        <Copy className="w-3.5 h-3.5" />
                                        <span>复制</span>
                                      </button>

                                      {index === currentMessages.length - 1 && (
                                          <button
                                              onClick={handleRegenerate}
                                              className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                                          >
                                            <RotateCw className="w-3.5 h-3.5" />
                                            <span>重新生成</span>
                                          </button>
                                      )}
                                    </div>
                                )}
                              </div>
                          )}
                        </div>
                      </div>
                  ))}

                  {isCurrentModelTyping && (
                      <div className="flex gap-4 items-center pl-14">
                        <div className="flex gap-1.5 h-3 items-center opacity-80">
                          <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                          <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:0.1s]"></div>
                          <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                        </div>
                      </div>
                  )}
                </div>
            )}
          </div>

          <div className="w-full bg-white pt-2 pb-6 px-4 absolute bottom-0 z-10">
            <div className="max-w-3xl mx-auto relative">
              <div className={`bg-[#f0f4f9] rounded-[32px] flex flex-col transition-all duration-200 border border-transparent focus-within:bg-white focus-within:border-gray-200 focus-within:shadow-[0_4px_20px_rgba(0,0,0,0.05)] ${isCurrentModelTyping ? 'opacity-90' : 'opacity-100'}`}>
                <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }} placeholder={t('inputPlaceholder')} className="w-full bg-transparent border-none focus:ring-0 text-gray-800 placeholder-gray-500 py-4 px-6 resize-none min-h-[64px] max-h-52 scrollbar-hide outline-none text-[16px]" rows={1} onInput={(e) => { const target = e.target as HTMLTextAreaElement; target.style.height = 'auto'; target.style.height = `${target.scrollHeight}px`; }} />
                <div className="flex justify-between items-center px-4 pb-3">
                  <div className="flex gap-1">
                    <button className="p-2.5 hover:bg-gray-100 rounded-full text-gray-500 hover:text-gray-800 transition-colors"><ImageIcon className="w-5 h-5" /></button>
                    <button className="p-2.5 hover:bg-gray-100 rounded-full text-gray-500 hover:text-gray-800 transition-colors"><Mic className="w-5 h-5" /></button>
                  </div>
                  <button onClick={handleSendMessage} disabled={(!input.trim() && !isCurrentModelTyping) || !isConnected} className={`w-10 h-10 rounded-full transition-all duration-300 flex items-center justify-center border border-transparent ${(input.trim() || isCurrentModelTyping) && isConnected ? 'bg-white text-zinc-900 shadow-md hover:bg-gray-50 hover:shadow-lg border-gray-100 transform hover:-translate-y-0.5' : 'bg-transparent text-gray-400 cursor-not-allowed'}`}>
                    {isCurrentModelTyping ? (<Square className="w-4 h-4 fill-current" />) : (<Send className="w-5 h-5 ml-0.5" />)}
                  </button>
                </div>
              </div>
              <p className="text-center text-[11px] text-gray-400 mt-3 font-light tracking-wide">{t('aiWarning')}</p>
            </div>
          </div>
        </main>
      </div>
  );
};

export default App;