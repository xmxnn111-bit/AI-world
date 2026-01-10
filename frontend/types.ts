
export interface Model {
  id: string;
  name: string;
  icon: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export enum ViewState {
  LANDING = 'landing',
  CHAT = 'chat'
}
