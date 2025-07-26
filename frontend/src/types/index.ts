// 聊天相关类型
export interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

// 知识点相关类型
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

// 上下文相关类型
export interface ContextItem {
  id: string;
  type: 'video' | 'knowledge_point' | 'note' | 'file';
  title: string;
  description?: string;
  timestamp?: number; // 对于视频相关 context
  icon?: string;
}

// 视频相关类型
export interface Video {
  url: string;
  title: string;
  description: string;
  prerequisites: PrerequisiteModule[];
}

// API 相关类型
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface SendMessageRequest {
  message: string;
  stream: boolean;
  model: string;
  user_id: string;
  session_id: string;
}

export interface SendMessageResponse {
  content: string;
  timestamp?: string;
}

// UI 相关类型
export type AppMode = 'chat' | 'notes';
export type AgentType = 'web_agent' | 'agno_assist';

// 错误类型
export interface AppError {
  code: string;
  message: string;
  details?: unknown;
}

// 全局播放器控制接口
export interface VideoPlayerControl {
  seekTo: (time: number) => void;
  getCurrentTime: () => number;
  play: () => void;
  pause: () => void;
  captureFrame: () => Promise<string>; // 返回base64格式的截图
}

// 扩展 Window 接口
declare global {
  interface Window {
    videoPlayer?: VideoPlayerControl;
  }
}