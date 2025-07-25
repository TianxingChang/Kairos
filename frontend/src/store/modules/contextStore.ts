import { StateCreator } from 'zustand';
import type { ContextItem } from '@/types';

export interface ContextSlice {
  // 状态
  selectedContexts: ContextItem[];
  
  // 操作
  addContext: (context: ContextItem) => void;
  removeContext: (contextId: string) => void;
  clearContexts: () => void;
  updateContext: (contextId: string, updates: Partial<ContextItem>) => void;
  toggleContext: (context: ContextItem) => void;
}

export const createContextSlice: StateCreator<ContextSlice> = (set) => ({
  // 初始状态
  selectedContexts: [],

  // 操作方法
  addContext: (context) => set((state) => {
    // 检查是否已存在相同的context
    const exists = state.selectedContexts.some(ctx => ctx.id === context.id);
    if (exists) return state;

    return {
      selectedContexts: [...state.selectedContexts, context]
    };
  }),

  removeContext: (contextId) => set((state) => ({
    selectedContexts: state.selectedContexts.filter(ctx => ctx.id !== contextId)
  })),

  clearContexts: () => set({ selectedContexts: [] }),

  updateContext: (contextId, updates) => set((state) => ({
    selectedContexts: state.selectedContexts.map(ctx =>
      ctx.id === contextId ? { ...ctx, ...updates } : ctx
    )
  })),

  toggleContext: (context) => set((state) => {
    const exists = state.selectedContexts.some(ctx => ctx.id === context.id);
    
    if (exists) {
      return {
        selectedContexts: state.selectedContexts.filter(ctx => ctx.id !== context.id)
      };
    } else {
      return {
        selectedContexts: [...state.selectedContexts, context]
      };
    }
  }),
}); 