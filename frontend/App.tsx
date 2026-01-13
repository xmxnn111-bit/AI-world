import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Plus,
  Send,
  Settings,
  Square,
  History,
  Menu,
  ChevronRight,
  Sparkles,
  Zap,
  Mic,
  Image as ImageIcon,
  Compass,
  X,
  Globe
} from 'lucide-react';
import { MODELS, WS_URL } from './constants';
import { Model, Message, ViewState } from './types';

// --- 1. 定义多语言字典 (保持不变) ---
const TRANSLATIONS = {
  zh: {
    landingTitle: 'AI Nexus',
    landingDesc: '下一代智能聚合平台。连接最强大的 AI 模型，实时交互，探索无限可能。',
    startChat: '开始对话',
    newChat: '新对话',
    recent: '最近',
    settings: '设置',
    returnHome: '返回首页',
    currentModel: '当前模型',
    hello: '你好，',
    chatSubtitle: '今天要聊点什么？',
    suggestions: ['策划一次旅行', '比较 Python 和 Rust', '写一个 SQL 查询', '生成 AI 绘图提示词'],
    inputPlaceholder: '输入问题、指令或代码...',
    aiWarning: 'AI Nexus 可能会生成不准确的信息，请务必核实。',
    settingsTitle: '设置',
    language: '语言 / Language',
    close: '关闭',
    connected: '已连接',
    disconnected: '未连接',
    historyItems: ['Python 爬虫教程', '解释 React Hooks', '工作周报模版']
  },
  en: {
    landingTitle: 'AI Nexus',
    landingDesc: 'Next-generation AI aggregation platform. Connect with the most powerful models, interact in real-time.',
    startChat: 'Start Chat',
    newChat: 'New Chat',
    recent: 'Recent',
    settings: 'Settings',
    returnHome: 'Back to Home',
    currentModel: 'Current Model',
    hello: 'Hello,',
    chatSubtitle: 'How can I help you today?',
    suggestions: ['Plan a trip', 'Compare Python & Rust', 'Write a SQL query', 'Generate AI art prompts'],
    inputPlaceholder: 'Enter a prompt here...',
    aiWarning: 'AI Nexus may display inaccurate info, so double-check its responses.',
    settingsTitle: 'Settings',
    language: 'Language',
    close: 'Close',
    connected: 'Connected',
    disconnected: 'Disconnected',
    historyItems: ['Python Crawler Guide', 'Explain React Hooks', 'Weekly Report Template']
  }
};

type LangType = 'zh' | 'en';

const App: React.FC = () => {
  // --- 状态管理 ---
  const [view, setView] = useState<ViewState>(ViewState.LANDING);
  const [selectedModel, setSelectedModel] = useState<Model>(MODELS[0]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [lang, setLang] = useState<LangType>('zh');
  const [showSettings, setShowSettings] = useState(false);

  const t = (key: keyof typeof TRANSLATIONS['zh']) => TRANSLATIONS[lang][key];

  const socketRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // WebSocket 连接逻辑
  const connectWebSocket = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => setIsConnected(true);
    socket.onmessage = (event) => {
      const chunk = event.data;
      setIsTyping(false);
      if (chunk === '[DONE]') return;

      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = { ...lastMsg, content: chunk };
          return newMessages;
        } else {
          return [...prev, { role: 'assistant', content: chunk, timestamp: Date.now() }];
        }
      });
    };
    socket.onerror = () => setIsConnected(false);
    socket.onclose = () => {
      setIsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };
    socketRef.current = socket;
  }, []);

  useEffect(() => {
    if (view === ViewState.CHAT) connectWebSocket();
    return () => socketRef.current?.close();
  }, [view, connectWebSocket]);

  const handleSendMessage = () => {

    // ===处理停止逻辑 ===
    if (isTyping) {
      // 如果正在输入，点击则发送停止指令
      if (socketRef.current) {
        socketRef.current.send(JSON.stringify({ type: 'stop' }));
      }
      return; // 结束函数，不发送消息
    }

    if (!input.trim() || !isConnected) return;
    const userMessage: Message = { role: 'user', content: input, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    if (socketRef.current) {
      socketRef.current.send(JSON.stringify({
        type: 'chat',
        model: selectedModel.id,
        message: input
      }));
    }
    setInput('');
  };

  // --- 设置弹窗 ---
  const SettingsModal = () => {
    if (!showSettings) return null;
    return (
        <div className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl w-full max-w-sm p-6 shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
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

  // --- 首页 View ---
  if (view === ViewState.LANDING) {
    return (
        <div className="h-screen w-full flex flex-col items-center justify-center bg-zinc-950 relative overflow-hidden text-zinc-50">
          <SettingsModal />
          <div className="absolute top-6 right-6 z-20">
            <button onClick={() => setShowSettings(true)} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-full transition-colors">
              <Settings className="w-6 h-6" />
            </button>
          </div>
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full"></div>
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/10 blur-[120px] rounded-full"></div>

          <div className="z-10 text-center px-6">
            <div className="flex items-center justify-center mb-6">
              <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-2xl shadow-xl">
                <Sparkles className="w-10 h-10 text-blue-400" />
              </div>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight">
              <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">{t('landingTitle')}</span>
            </h1>
            <p className="text-zinc-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 font-light leading-relaxed">{t('landingDesc')}</p>
            <button onClick={() => setView(ViewState.CHAT)} className="group relative inline-flex items-center justify-center px-8 py-4 font-semibold text-white transition-all duration-200 bg-zinc-900 border border-zinc-700 rounded-full hover:bg-zinc-800 hover:border-zinc-500 focus:outline-none">
              <span className="absolute inset-0 w-full h-full rounded-full bg-gradient-to-r from-blue-500/20 to-purple-500/20 blur-lg group-hover:blur-xl transition-all"></span>
              <span className="relative flex items-center gap-2">{t('startChat')} <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" /></span>
            </button>
          </div>
        </div>
    );
  }

  // --- 聊天页 View ---

  const Sidebar = () => (
      <aside className={`flex-shrink-0 bg-[#f0f4f9] h-full transition-all duration-300 ease-in-out flex flex-col border-r border-transparent ${sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'}`}>
        <div className="p-4 flex flex-col h-full">
          <div className="flex items-center justify-between mb-6 px-2">
            <button onClick={() => setSidebarOpen(false)} className="p-2 hover:bg-gray-200 rounded-full text-gray-600 transition-colors">
              <Menu className="w-5 h-5" />
            </button>
          </div>
          <button onClick={() => { setMessages([]); }} className="flex items-center gap-3 bg-[#dde3ea] hover:bg-[#d5dce5] text-[#1f1f1f] px-4 py-3 rounded-2xl transition-colors mb-6 w-fit min-w-[140px]">
            <Plus className="w-5 h-5 text-gray-600" />
            <span className="font-medium text-sm">{t('newChat')}</span>
          </button>
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            <p className="px-3 text-xs font-medium text-gray-500 mb-2 mt-2">{t('recent')}</p>
            {TRANSLATIONS[lang].historyItems.map((item, i) => (
                <button key={i} className="flex items-center gap-3 w-full px-3 py-2 rounded-full hover:bg-[#e0e6ed] text-gray-700 text-sm truncate transition-colors group">
                  <History className="w-4 h-4 text-gray-500" />
                  <span className="truncate">{item}</span>
                </button>
            ))}
          </div>
          <div className="mt-auto pt-4 border-t border-gray-200 space-y-1">
            <button onClick={() => setShowSettings(true)} className="flex items-center gap-3 w-full px-3 py-2.5 rounded-full hover:bg-[#e0e6ed] text-gray-700 text-sm transition-colors">
              <Settings className="w-4 h-4" /> {t('settings')}
            </button>
            <button onClick={() => setView(ViewState.LANDING)} className="flex items-center gap-3 w-full px-3 py-2.5 rounded-full hover:bg-[#e0e6ed] text-gray-700 text-sm transition-colors">
              <ChevronRight className="w-4 h-4 rotate-180" /> {t('returnHome')}
            </button>
          </div>
        </div>
      </aside>
  );

  return (
      <div className="h-screen w-full flex bg-white text-gray-900">
        <SettingsModal />
        <Sidebar />

        <main className="flex-1 flex flex-col relative h-full min-w-0 bg-white">

          {/* === 修改后的 Header === */}
          <header className="absolute top-0 left-0 right-0 z-20 flex items-center p-4 h-16 bg-white/50 backdrop-blur-sm">
            {/* 左侧：菜单按钮 */}
            <div className="w-12 flex-shrink-0">
              {!sidebarOpen && (
                  <button onClick={() => setSidebarOpen(true)} className="p-2 hover:bg-gray-100 rounded-full text-gray-600 transition-colors">
                    <Menu className="w-5 h-5" />
                  </button>
              )}
            </div>

            {/* 中间：横向模型切换器 */}
            <div className="flex-1 flex justify-center min-w-0 px-2">
              <div className="flex items-center gap-1 bg-[#f0f4f9] p-1 rounded-xl overflow-x-auto scrollbar-hide no-scrollbar max-w-full">
                {MODELS.map(model => (
                    <button
                        key={model.id}
                        onClick={() => setSelectedModel(model)}
                        className={`
                      flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap select-none
                      ${selectedModel.id === model.id
                            ? 'bg-white text-gray-900 shadow-sm' // 选中状态：白色背景 + 阴影
                            : 'text-gray-500 hover:text-gray-900 hover:bg-gray-200/50' // 未选中状态
                        }
                    `}
                    >
                      <img src={model.icon} className="w-4 h-4 rounded-full" alt="" />
                      <span>{model.name}</span>
                    </button>
                ))}
              </div>
            </div>

            {/* 右侧：状态指示灯 */}
            <div className="w-12 flex-shrink-0 flex justify-end">
              <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-400'}`} title={isConnected ? t('connected') : t('disconnected')}></div>
            </div>
          </header>
          {/* === Header 结束 === */}

          <div ref={scrollRef} className="flex-1 overflow-y-auto w-full pt-16"> {/* 增加 pt-16 避免内容被 Header 遮挡 */}
            {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center p-8 max-w-3xl mx-auto animate-in fade-in duration-500">
                  <div className="mb-10 w-full">
                    <h1 className="text-5xl md:text-6xl font-medium mb-2 tracking-tight text-[#c4c7c5]">{t('hello')}</h1>
                    <h1 className="text-5xl md:text-6xl font-medium tracking-tight bg-gradient-to-r from-[#4285f4] via-[#9b72cb] to-[#d96570] bg-clip-text text-transparent">
                      {t('chatSubtitle')}
                    </h1>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 w-full">
                    {TRANSLATIONS[lang].suggestions.map((item, i) => (
                        <button
                            key={i}
                            onClick={() => { setInput(item); }}
                            className="bg-[#f0f4f9] hover:bg-[#dfe4ea] p-4 rounded-xl text-left transition-colors h-32 relative group"
                        >
                          <p className="text-gray-700 font-medium text-sm">{item}</p>
                          <span className="absolute bottom-4 right-4 bg-white p-2 rounded-full shadow-sm opacity-0 group-hover:opacity-100 transition-opacity">
                        <Compass className="w-4 h-4 text-gray-600" />
                     </span>
                        </button>
                    ))}
                  </div>
                </div>
            ) : (
                <div className="max-w-3xl mx-auto py-8 px-4 pb-40">
                  {messages.map((msg, index) => (
                      <div key={index} className={`mb-8 flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full flex-shrink-0 mt-1 overflow-hidden">
                              <img src={selectedModel.icon} className="w-full h-full object-cover" />
                            </div>
                        )}
                        <div className={`max-w-[90%] md:max-w-[85%] ${
                            msg.role === 'user'
                                ? 'bg-[#f0f4f9] text-gray-800 rounded-[20px] px-5 py-3.5'
                                : 'bg-transparent text-gray-900 px-0 py-0 w-full'
                        }`}>
                          {msg.role === 'user' ? (
                              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                          ) : (
                              <div
                                  className="prose prose-slate max-w-none
                                   prose-p:leading-7 prose-p:mb-4 prose-p:text-gray-800
                                   prose-headings:font-medium prose-headings:text-gray-900
                                   prose-pre:bg-[#1e1e1e] prose-pre:text-gray-100 prose-pre:rounded-xl prose-pre:p-4
                                   prose-code:text-[#d96570] prose-code:bg-[#f2f2f2] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-sm
                                   prose-a:text-[#1a73e8] prose-a:no-underline hover:prose-a:underline"
                                  dangerouslySetInnerHTML={{ __html: msg.content }}
                              />
                          )}
                        </div>
                      </div>
                  ))}
                  {isTyping && (
                      <div className="flex gap-4 items-center pl-12">
                        <div className="flex gap-1 h-2 items-center opacity-60">
                          <div className="w-1.5 h-1.5 bg-[#4285f4] rounded-full animate-bounce"></div>
                          <div className="w-1.5 h-1.5 bg-[#d96570] rounded-full animate-bounce [animation-delay:0.1s]"></div>
                          <div className="w-1.5 h-1.5 bg-[#fbbc04] rounded-full animate-bounce [animation-delay:0.2s]"></div>
                        </div>
                      </div>
                  )}
                </div>
            )}
          </div>

          <div className="w-full bg-white pt-2 pb-6 px-4 absolute bottom-0 z-10">
            <div className="max-w-3xl mx-auto relative">
              <div className={`bg-[#f0f4f9] rounded-[28px] flex flex-col transition-all border border-transparent focus-within:bg-white focus-within:border-gray-200 focus-within:shadow-md ${isTyping ? 'opacity-80' : 'opacity-100'}`}>
                 <textarea
                     value={input}
                     onChange={(e) => setInput(e.target.value)}
                     onKeyDown={(e) => {
                       if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
                     }}
                     placeholder={t('inputPlaceholder')}
                     className="w-full bg-transparent border-none focus:ring-0 text-gray-800 placeholder-gray-500 py-4 px-6 resize-none min-h-[56px] max-h-48 scrollbar-hide outline-none"
                     rows={1}
                     onInput={(e) => {
                       const target = e.target as HTMLTextAreaElement;
                       target.style.height = 'auto';
                       target.style.height = `${target.scrollHeight}px`;
                     }}
                 />
                <div className="flex justify-between items-center px-4 pb-3">
                  <div className="flex gap-2">
                    <button className="p-2 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"><ImageIcon className="w-5 h-5" /></button>
                    <button className="p-2 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"><Mic className="w-5 h-5" /></button>
                  </div>
                  <button
                      onClick={handleSendMessage}
                      // 修改禁用逻辑：
                      // 1. 如果正在打字 (isTyping)，按钮必须可用（为了能点停止）
                      // 2. 如果没打字，才检查输入框是否为空
                      disabled={(!input.trim() && !isTyping) || !isConnected}

                      className={`p-2.5 rounded-full transition-all flex items-center justify-center ${
                          // 样式逻辑也要改：如果是 typing 状态，也给高亮样式
                          (input.trim() || isTyping) && isConnected
                              ? 'bg-blue-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.4)] hover:bg-blue-700'
                              : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                      }`}
                  >
                    {/* 根据状态切换图标：正在打字显示方块(停止)，否则显示飞机(发送) */}
                    {isTyping ? (
                        <Square className="w-5 h-5 fill-current" />
                    ) : (
                        <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>
              <p className="text-center text-[10px] text-gray-500 mt-3">{t('aiWarning')}</p>
            </div>
          </div>
        </main>
      </div>
  );
};

export default App;