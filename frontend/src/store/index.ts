import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { createChatSlice, type ChatSlice } from './modules/chatStore';
import { createVideoSlice, type VideoSlice } from './modules/videoStore';
import { createUISlice, type UISlice } from './modules/uiStore';
import { createContextSlice, type ContextSlice } from './modules/contextStore';

// 组合所有slice的类型
export type AppStore = ChatSlice & VideoSlice & UISlice & ContextSlice;

// 创建store
export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (...args) => ({
        ...createChatSlice(...args),
        ...createVideoSlice(...args),
        ...createUISlice(...args),
        ...createContextSlice(...args),
      }),
      {
        name: 'app-store',
        partialize: (state) => ({
          // 只持久化视频相关状态，不持久化聊天消息等临时状态
          currentVideo: state.currentVideo,
          currentVideoTime: state.currentVideoTime,
        }),
      }
    ),
    {
      name: 'app-store',
    }
  )
);

// 导出类型和hooks
export type { ChatSlice, VideoSlice, UISlice, ContextSlice };
export * from './modules/chatStore';
export * from './modules/videoStore';
export * from './modules/uiStore';
export * from './modules/contextStore'; 