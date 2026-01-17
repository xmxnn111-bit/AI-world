import { Model } from './types';

// 使用更清晰、官方风格的图标 URL
export const MODELS: Model[] = [
  {
    id: "gemini",
    name: "Gemini",
    icon: "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://gemini.google.com&size=128"
  },
  {
    id: "gpt",
    name: "ChatGPT",
    icon: "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://chatgpt.com&size=128"
  },
  {
    id: "grok",
    name: "Grok",
    icon: "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://grok.com&size=128"
  },
  {
    id: "kimi",
    name: "Kimi",
    icon: "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://kimi.com&size=128"
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    icon: "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://deepseek.com&size=128" // DeepSeek 官方推特头像
  },
  {
    id: "doubao",
    name: "Dola",
    icon: "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://doubao.com&size=128" // 豆包常用Logo资源
  }
];

export const WS_URL = 'ws://127.0.0.1:8000/ws/chat';