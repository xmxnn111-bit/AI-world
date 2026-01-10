
import { Model } from './types';

export const MODELS: Model[] = [
  { 
    id: "gpt", 
    name: "ChatGPT-4o", 
    icon: "https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg" 
  },
  { 
    id: "deepseek", 
    name: "DeepSeek", 
    icon: "https://pbs.twimg.com/profile_images/1749838495048384512/0Yn1s68m_400x400.jpg" 
  },
  { 
    id: "doubao", 
    name: "豆包 (Doubao)", 
    icon: "https://p9-flow-image.byteimg.com/tos-cn-i-6f68e96983/5766e4a66a704c32b534e6284f163b0e~tplv-6f68e96983-image.png" 
  },
  { 
    id: "grok", 
    name: "Grok", 
    icon: "https://upload.wikimedia.org/wikipedia/commons/f/f6/Grok_logo.svg" 
  },
  { 
    id: "gemini", 
    name: "Google Gemini", 
    icon: "https://upload.wikimedia.org/wikipedia/commons/8/8a/Google_Gemini_logo.svg" 
  }
];

export const WS_URL = 'ws://127.0.0.1:8000/ws/chat';
