
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Plus, 
  Send, 
  MessageSquare, 
  Settings, 
  History, 
  User, 
  Menu, 
  ChevronRight,
  Sparkles,
  Zap,
  Command
} from 'lucide-react';
import { MODELS, WS_URL } from './constants';
import { Model, Message, ViewState } from './types';
import MarkdownRenderer from './components/MarkdownRenderer';

const App: React.FC = () => {
  // 状态管理
  const [view, setView] = useState<ViewState>(ViewState.LANDING);
  const [selectedModel, setSelectedModel] = useState<Model>(MODELS[0]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // WebSocket 引用
  const socketRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // 初始化 WebSocket
  const connectWebSocket = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log('WebSocket 连接成功');
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      const chunk = event.data;
      setIsTyping(false);
      
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          // 追加流式文本到最后一条 AI 消息
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...lastMsg,
            content: lastMsg.content + chunk
          };
          return newMessages;
        } else {
          // 创建新的 AI 消息气泡
          return [...prev, {
            role: 'assistant',
            content: chunk,
            timestamp: Date.now()
          }];
        }
      });
    };

    socket.onerror = (error) => {
      console.error('WebSocket 错误:', error);
      setIsConnected(false);
    };

    socket.onclose = () => {
      console.log('WebSocket 连接关闭');
      setIsConnected(false);
      // 3秒后尝试重连
      setTimeout(connectWebSocket, 3000);
    };

    socketRef.current = socket;
  }, []);

  useEffect(() => {
    if (view === ViewState.CHAT) {
      connectWebSocket();
    }
    return () => {
      socketRef.current?.close();
    };
  }, [view, connectWebSocket]);

  // 发送消息
  const handleSendMessage = () => {
    if (!input.trim() || !isConnected) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: Date.now()
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    if (socketRef.current) {
      socketRef.current.send(JSON.stringify({
        model: selectedModel.id,
        message: input
      }));
    }

    setInput('');
  };

  // 渲染首页
  if (view === ViewState.LANDING) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-zinc-950 relative overflow-hidden">
        {/* 背景装饰 */}
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/10 blur-[120px] rounded-full"></div>

        <div className="z-10 text-center px-6">
          <div className="flex items-center justify-center mb-6">
            <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-2xl shadow-xl">
              <Sparkles className="w-10 h-10 text-blue-400" />
            </div>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight">
            <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              AI Nexus
            </span>
          </h1>
          
          <p className="text-zinc-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 font-light leading-relaxed">
            下一代智能聚合平台。连接最强大的 AI 模型，
            实时交互，探索无限可能。
          </p>

          <button 
            onClick={() => setView(ViewState.CHAT)}
            className="group relative inline-flex items-center justify-center px-8 py-4 font-semibold text-white transition-all duration-200 bg-zinc-900 border border-zinc-700 rounded-full hover:bg-zinc-800 hover:border-zinc-500 focus:outline-none"
          >
            <span className="absolute inset-0 w-full h-full rounded-full bg-gradient-to-r from-blue-500/20 to-purple-500/20 blur-lg group-hover:blur-xl transition-all"></span>
            <span className="relative flex items-center gap-2">
              开始对话 <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </span>
          </button>
        </div>
      </div>
    );
  }

  // 渲染聊天工作区
  return (
    <div className="h-screen w-full flex bg-zinc-950 text-zinc-200">
      
      {/* 左侧边栏 */}
      <aside className={`transition-all duration-300 ease-in-out border-r border-zinc-800 flex flex-col bg-zinc-900/50 backdrop-blur-xl ${sidebarOpen ? 'w-72' : 'w-0 overflow-hidden opacity-0'}`}>
        <div className="p-4 flex flex-col h-full">
          {/* 新对话按钮 */}
          <button 
            onClick={() => setMessages([])}
            className="flex items-center gap-3 w-full bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700/50 p-3 rounded-xl transition-colors mb-6 group"
          >
            <div className="bg-blue-500/10 p-1.5 rounded-lg text-blue-400 group-hover:scale-110 transition-transform">
              <Plus className="w-5 h-5" />
            </div>
            <span className="font-medium text-sm">新对话</span>
          </button>

          {/* 模型选择 */}
          <div className="flex-1 space-y-2 overflow-y-auto pr-1">
            <p className="px-2 text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-2">选择模型</p>
            {MODELS.map((model) => (
              <button
                key={model.id}
                onClick={() => setSelectedModel(model)}
                className={`flex items-center gap-3 w-full p-3 rounded-xl transition-all duration-200 ${
                  selectedModel.id === model.id 
                  ? 'bg-blue-500/10 border border-blue-500/30 text-blue-100' 
                  : 'hover:bg-zinc-800/50 border border-transparent text-zinc-400'
                }`}
              >
                <img src={model.icon} alt={model.name} className="w-5 h-5 rounded shadow-sm" />
                <span className="text-sm font-medium">{model.name}</span>
                {selectedModel.id === model.id && <Zap className="w-3 h-3 ml-auto text-blue-400 fill-blue-400" />}
              </button>
            ))}
          </div>

          {/* 底部功能区 */}
          <div className="mt-auto pt-4 border-t border-zinc-800 space-y-1">
            <button className="flex items-center gap-3 w-full p-2.5 rounded-lg text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors text-sm">
              <History className="w-4 h-4" /> 历史记录
            </button>
            <button className="flex items-center gap-3 w-full p-2.5 rounded-lg text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors text-sm">
              <Settings className="w-4 h-4" /> 设置
            </button>
            <div className="pt-2">
              <div className="flex items-center gap-3 p-2.5 rounded-xl bg-zinc-800/30 border border-zinc-800">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-zinc-700 to-zinc-600 flex items-center justify-center text-xs font-bold">
                  JS
                </div>
                <div className="flex-1 overflow-hidden">
                  <p className="text-xs font-medium truncate">Senior Engineer</p>
                  <p className="text-[10px] text-zinc-500">Free Plan</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* 右侧主区域 */}
      <main className="flex-1 flex flex-col relative min-w-0">
        
        {/* 顶部导航栏 */}
        <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-4 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-zinc-400 text-sm font-medium">当前模型:</span>
              <div className="flex items-center gap-2 bg-zinc-900 px-2 py-1 rounded-md border border-zinc-800">
                <img src={selectedModel.icon} alt="" className="w-3.5 h-3.5 rounded" />
                <span className="text-xs font-semibold">{selectedModel.name}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-tight uppercase ${isConnected ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              {isConnected ? '已连接' : '未连接'}
            </div>
          </div>
        </header>

        {/* 聊天记录区 */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto space-y-6">
              <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-3xl shadow-2xl">
                <Sparkles className="w-12 h-12 text-blue-500/50" />
              </div>
              <div>
                <h2 className="text-3xl font-bold mb-2">你好, 我是 AI Nexus</h2>
                <p className="text-zinc-500 leading-relaxed">
                  你可以问我任何问题，无论是编写代码、翻译文章还是头脑风暴。
                  当前已接入 <span className="text-zinc-300 font-medium">{selectedModel.name}</span> 模型。
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 w-full mt-4">
                {['帮我写一段 React 代码', '解释什么是量子纠缠', '帮我制定旅行计划', '写一首关于宇宙的诗'].map((suggestion) => (
                  <button 
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="p-3 text-sm text-zinc-400 text-left border border-zinc-800 rounded-xl hover:bg-zinc-900 hover:border-zinc-700 transition-all"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto w-full space-y-10 pb-20">
              {messages.map((msg, index) => (
                <div 
                  key={index} 
                  className={`flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  {/* 头像 */}
                  <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center shadow-lg ${
                    msg.role === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-zinc-800 border border-zinc-700'
                  }`}>
                    {msg.role === 'user' ? <User className="w-4 h-4" /> : <img src={selectedModel.icon} className="w-4 h-4 rounded-sm" />}
                  </div>

                  {/* 消息体 */}
                  <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`px-4 py-2.5 rounded-2xl shadow-sm ${
                      msg.role === 'user' 
                      ? 'bg-zinc-800 text-zinc-100 rounded-tr-none' 
                      : 'bg-transparent text-zinc-200'
                    }`}>
                      {msg.role === 'user' ? (
                        <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                      ) : (
                        <MarkdownRenderer content={msg.content} />
                      )}
                    </div>
                    <span className="text-[10px] text-zinc-600 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity uppercase font-bold tracking-tighter">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))}
              
              {/* 输入中的状态 */}
              {isTyping && (
                <div className="flex gap-4 items-start animate-pulse">
                   <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                    <img src={selectedModel.icon} className="w-4 h-4 rounded-sm" />
                  </div>
                  <div className="bg-zinc-900/50 px-4 py-2 rounded-2xl border border-zinc-800 flex gap-1 items-center">
                    <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce"></div>
                    <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                    <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 底部输入框区域 */}
        <div className="p-4 md:p-8 bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent absolute bottom-0 left-0 right-0 z-10">
          <div className="max-w-4xl mx-auto relative group">
            <div className="absolute inset-0 bg-blue-500/5 blur-xl group-focus-within:bg-blue-500/10 transition-all rounded-full"></div>
            <div className="relative bg-zinc-900 border border-zinc-800 focus-within:border-zinc-700 rounded-3xl flex items-end p-2 transition-all shadow-2xl">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={`向 ${selectedModel.name} 发送消息...`}
                rows={1}
                className="flex-1 bg-transparent border-none focus:ring-0 text-zinc-200 py-3 px-4 resize-none max-h-48 scrollbar-hide"
                style={{ height: 'auto', minHeight: '48px' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${target.scrollHeight}px`;
                }}
              />
              <div className="flex items-center gap-2 p-1.5">
                <button className="p-2.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded-full transition-all">
                  <Command className="w-5 h-5" />
                </button>
                <button 
                  onClick={handleSendMessage}
                  disabled={!input.trim() || !isConnected}
                  className={`p-2.5 rounded-full transition-all flex items-center justify-center ${
                    input.trim() && isConnected 
                    ? 'bg-blue-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.4)]' 
                    : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                  }`}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
            <p className="text-[10px] text-center text-zinc-600 mt-3 font-medium uppercase tracking-widest">
              AI Nexus 可能提供不准确的信息，请务必核实其回答。
            </p>
          </div>
        </div>

      </main>
    </div>
  );
};

export default App;
