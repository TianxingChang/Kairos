import { StateCreator } from 'zustand';
import type { AppMode } from '@/types';

export interface UISlice {
  // 状态
  currentMode: AppMode;
  notes: string;
  webSearchEnabled: boolean;
  contextMenuOpen: boolean;
  
  // 操作
  setCurrentMode: (mode: AppMode) => void;
  setNotes: (notes: string) => void;
  setWebSearchEnabled: (enabled: boolean) => void;
  setContextMenuOpen: (open: boolean) => void;
  toggleWebSearch: () => void;
  toggleContextMenu: () => void;
}

export const createUISlice: StateCreator<UISlice> = (set) => ({
  // 初始状态
  currentMode: 'chat',
  notes: '',
  webSearchEnabled: true,
  contextMenuOpen: false,

  // 操作方法
  setCurrentMode: (mode) => set({ currentMode: mode }),
  
  setNotes: (notes) => set({ notes }),

  setWebSearchEnabled: (enabled) => set({ webSearchEnabled: enabled }),

  setContextMenuOpen: (open) => set({ contextMenuOpen: open }),

  toggleWebSearch: () => set((state) => ({ 
    webSearchEnabled: !state.webSearchEnabled 
  })),

  toggleContextMenu: () => set((state) => ({ 
    contextMenuOpen: !state.contextMenuOpen 
  })),
}); 