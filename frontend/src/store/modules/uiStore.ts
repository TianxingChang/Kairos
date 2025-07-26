import { StateCreator } from 'zustand';
import type { AppMode } from '@/types';

export interface UISlice {
  // 状态
  currentMode: AppMode;
  notes: string;
  contextMenuOpen: boolean;
  
  // 操作
  setCurrentMode: (mode: AppMode) => void;
  setNotes: (notes: string) => void;
  setContextMenuOpen: (open: boolean) => void;
  toggleContextMenu: () => void;
}

export const createUISlice: StateCreator<UISlice> = (set) => ({
  // 初始状态
  currentMode: 'chat',
  notes: '',
  contextMenuOpen: false,

  // 操作方法
  setCurrentMode: (mode) => set({ currentMode: mode }),
  
  setNotes: (notes) => set({ notes }),

  setContextMenuOpen: (open) => set({ contextMenuOpen: open }),

  toggleContextMenu: () => set((state) => ({ 
    contextMenuOpen: !state.contextMenuOpen 
  })),
}); 