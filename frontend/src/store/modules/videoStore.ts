import { StateCreator } from 'zustand';
import type { Video, PrerequisiteModule } from '@/types';

export interface VideoSlice {
  // 状态
  currentVideo: Video;
  currentVideoTime: number;
  
  // 操作
  setCurrentVideo: (video: Partial<Video>) => void;
  setCurrentVideoTime: (time: number) => void;
  togglePrerequisiteModule: (moduleId: string) => void;
  updateVideoTime: (increment: number) => void;
}

export const createVideoSlice: StateCreator<VideoSlice> = (set) => ({
  // 初始状态
  currentVideo: {
    url: 'https://www.youtube.com/embed/AVIKFXLCPY8?list=PLJV_el3uVTsPz6CTopeRp2L2t4aL_KgiI&index=1',
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
  currentVideoTime: 0,

  // 操作方法
  setCurrentVideo: (video) => set((state) => ({ 
    currentVideo: { 
      ...state.currentVideo,
      ...video,
    } 
  })),

  setCurrentVideoTime: (time) => set({ currentVideoTime: time }),

  updateVideoTime: (increment) => set((state) => ({
    currentVideoTime: state.currentVideoTime + increment,
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
}); 