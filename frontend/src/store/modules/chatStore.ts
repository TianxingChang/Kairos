import { StateCreator } from 'zustand';
import type { ChatMessage } from '@/types';

export interface ChatSlice {
  // 状态
  messages: ChatMessage[];
  
  // 操作
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clearMessages: () => void;
  removeMessage: (messageId: string) => void;
  updateMessage: (messageId: string, content: string) => void;
}

export const createChatSlice: StateCreator<ChatSlice> = (set) => ({
  // 初始状态
  messages: [
    {
      id: '1',
      content: '你好！我是你的AI助手，有什么可以帮助你的吗？',
      isUser: false,
      timestamp: new Date(),
    },
  ],

  // 操作方法
  addMessage: (message) => set((state) => ({
    messages: [
      ...state.messages,
      {
        ...message,
        id: Date.now().toString(),
        timestamp: new Date(),
      },
    ],
  })),

  clearMessages: () => set({ messages: [] }),

  removeMessage: (messageId) => set((state) => ({
    messages: state.messages.filter(msg => msg.id !== messageId),
  })),

  updateMessage: (messageId, content) => set((state) => ({
    messages: state.messages.map(msg => 
      msg.id === messageId ? { ...msg, content } : msg
    ),
  })),
}); 