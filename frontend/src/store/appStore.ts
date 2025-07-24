import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

export interface KnowledgePoint {
  id: string;
  title: string;
  description: string;
  timestamp: number; // 视频时间点（秒）
  duration?: number; // 持续时长（秒）
}

export interface PrerequisiteModule {
  id: string;
  title: string;
  description: string;
  isExpanded: boolean;
  knowledgePoints: KnowledgePoint[];
}

export interface ContextItem {
  id: string;
  type: 'video' | 'knowledge_point' | 'note' | 'file';
  title: string;
  description?: string;
  timestamp?: number; // 对于视频相关 context
  icon?: string;
}

interface AppState {
  // 聊天状态
  messages: ChatMessage[];
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clearMessages: () => void;
  
  // 笔记状态
  notes: string;
  setNotes: (notes: string) => void;
  
  // UI状态
  currentMode: 'chat' | 'notes';
  setCurrentMode: (mode: 'chat' | 'notes') => void;
  
  // 视频状态
  currentVideo: {
    url: string;
    title: string;
    description: string;
    prerequisites: PrerequisiteModule[];
  };
  setCurrentVideo: (video: { url: string; title: string; description: string; prerequisites?: PrerequisiteModule[] }) => void;
  
  // 前置知识模块状态
  togglePrerequisiteModule: (moduleId: string) => void;
  
  // Context 状态
  selectedContexts: ContextItem[];
  currentVideoTime: number; // 当前视频播放时间点（秒）
  addContext: (context: ContextItem) => void;
  removeContext: (contextId: string) => void;
  clearContexts: () => void;
  setCurrentVideoTime: (time: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // 聊天状态初始化
  messages: [
    {
      id: '1',
      content: '你好！我是你的AI助手，有什么可以帮助你的吗？',
      isUser: false,
      timestamp: new Date(),
    },
  ],
  
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
  
  // 笔记状态
  notes: '',
  setNotes: (notes) => set({ notes }),
  
  // UI状态
  currentMode: 'chat',
  setCurrentMode: (mode) => set({ currentMode: mode }),
  
  // 视频状态
  currentVideo: {
    url: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
    title: '示例视频',
    description: '这里是视频描述信息，可以显示视频的详细说明。',
    prerequisites: [
      {
        id: '1',
        title: '线性代数基础',
        description: '向量、矩阵运算等基础概念',
        isExpanded: false,
        knowledgePoints: [
          {
            id: '1-1',
            title: '向量概念',
            description: '理解向量的定义和基本性质',
            timestamp: 120,
            duration: 30
          },
          {
            id: '1-2',
            title: '矩阵乘法',
            description: '掌握矩阵乘法的计算规则',
            timestamp: 300,
            duration: 45
          }
        ]
      },
      {
        id: '2',
        title: '微积分基础',
        description: '导数、积分等核心概念',
        isExpanded: false,
        knowledgePoints: [
          {
            id: '2-1',
            title: '导数定义',
            description: '理解导数的几何和代数意义',
            timestamp: 180,
            duration: 40
          }
        ]
      }
    ]
  },
  
  setCurrentVideo: (video) => set((state) => ({ 
    currentVideo: { 
      ...video, 
      prerequisites: video.prerequisites || state.currentVideo.prerequisites 
    } 
  })),
  
  togglePrerequisiteModule: (moduleId) => set((state) => ({
    currentVideo: {
      ...state.currentVideo,
      prerequisites: state.currentVideo.prerequisites.map(module =>
        module.id === moduleId 
          ? { ...module, isExpanded: !module.isExpanded }
          : module
      )
    }
  })),

  // Context 状态初始化
  selectedContexts: [
    {
      id: 'current-video',
      type: 'video',
      title: '当前视频',
      description: '示例视频',
      timestamp: 0,
      icon: '🎥'
    }
  ],
  currentVideoTime: 0,

  addContext: (context) => set((state) => ({
    selectedContexts: [...state.selectedContexts, context]
  })),

  removeContext: (contextId) => set((state) => ({
    selectedContexts: state.selectedContexts.filter(ctx => ctx.id !== contextId)
  })),

  clearContexts: () => set({ selectedContexts: [] }),

  setCurrentVideoTime: (time) => set({ currentVideoTime: time }),
}));